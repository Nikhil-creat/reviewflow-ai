import time
from datetime import datetime, timezone

import httpx

from connectors import get_connector
from core import db, llm
from core.config import settings
from core.embeddings import embed_one
from core.telemetry import emit


def _ms(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)


# 1) Scraper / Sync agent ----------------------------------------------------
async def sync_node(state):
    biz, run = state["business"], state["run_id"]
    t0 = time.perf_counter()
    conn = get_connector(biz.get("connector", "demo"))
    await emit(biz["id"], "scraper", f"Sync agent connecting to source '{conn.name}'…", run_id=run)
    try:
        fetched = await conn.fetch(biz)
    except Exception as exc:
        await emit(biz["id"], "scraper", f"Source fetch failed: {exc}", "error", run_id=run)
        fetched = []
    new = 0
    for rv in fetched:
        when = rv.get("reviewed_at")
        when = datetime.fromisoformat(when.replace("Z", "+00:00")) if isinstance(when, str) else datetime.now(timezone.utc)
        res = await db.pool.execute(
            """insert into reviews (business_id, platform, external_id, author_name, rating, body, reviewed_at)
               values ($1, $2::review_platform, $3, $4, $5, $6, $7) on conflict do nothing""",
            biz["id"], rv.get("platform", "manual"), rv["external_id"], rv.get("author_name"),
            rv["rating"], rv["body"], when)
        new += res.endswith("1")
    await db.pool.execute("update businesses set last_synced_at = now() where id = $1", biz["id"])
    queue = [dict(r) for r in await db.pool.fetch(
        "select * from reviews where business_id=$1 and status='pending' order by reviewed_at limit 10", biz["id"])]
    await emit(biz["id"], "scraper", f"Sync complete: {new} new, {len(queue)} queued for the autopilot",
               "success", run_id=run, duration_ms=_ms(t0))
    return {"queue": queue, "stats": {"reviews_seen": len(queue), "auto_replied": 0, "flagged": 0, "cards": 0}}


async def next_node(state):
    q = list(state.get("queue", []))
    return {"current": q.pop(0) if q else None, "queue": q}


# 2) Sentiment agent -----------------------------------------------------------
async def sentiment_node(state):
    biz, rv, run = state["business"], state["current"], state["run_id"]
    await emit(biz["id"], "sentiment", f"Agent evaluating sentiment: {rv['author_name'] or 'anonymous'} ({rv['rating']}★)…", run_id=run)
    await db.pool.execute("update reviews set status='analyzing' where id=$1", rv["id"])
    t0 = time.perf_counter()
    a = await llm.analyze_sentiment(rv)
    ms = _ms(t0)
    await db.pool.execute(
        """update reviews set sentiment=$2::review_sentiment, sentiment_score=$3, intent_tags=$4::text[],
           risk_flags=$5::text[], key_phrases=$6::text[] where id=$1""",
        rv["id"], a["sentiment"], a["score"], a["intent_tags"], a["risk_flags"], a["key_phrases"])
    risky = bool(a["risk_flags"])
    await emit(biz["id"], "sentiment",
               f"Sentiment {a['sentiment']} ({a['score']:+.2f}) · tags: {', '.join(a['intent_tags']) or '-'}"
               + (f" · RISK: {', '.join(a['risk_flags'])}" if risky else ""),
               "warning" if risky else "success", run_id=run, duration_ms=ms, payload=a)
    return {"analysis": a}


# 3) RAG brand voice agent -------------------------------------------------------
async def rag_node(state):
    biz, rv, a, run = state["business"], state["current"], state["analysis"], state["run_id"]
    t0 = time.perf_counter()
    qvec = await embed_one(f"{rv['body']} {' '.join(a['intent_tags'])}")
    rows = await db.pool.fetch("select * from match_brand_chunks($1, $2::vector, 5, 0.2, null)", biz["id"], db.vec(qvec))
    chunks = [dict(r) for r in rows]
    voice_match = sum(c["similarity"] for c in chunks) / len(chunks) if chunks else 0.0
    await emit(biz["id"], "rag_voice",
               f"Vector search complete ({_ms(t0)}ms): {len(chunks)} chunks, mean similarity {voice_match:.2f}",
               "success" if chunks else "warning", run_id=run, duration_ms=_ms(t0))
    t1 = time.perf_counter()
    d = await llm.draft_reply(biz, rv, a, chunks)
    # confidence = model self-assessment blended with how well we could ground the voice
    grounding = min(1.0, voice_match / 0.6)
    confidence = round(0.65 * d["confidence"] + 0.35 * grounding, 3)
    await db.pool.execute(
        """insert into reply_drafts (review_id, business_id, body, model, confidence, voice_match, retrieved_chunks)
           values ($1,$2,$3,$4,$5,$6,$7::uuid[])""",
        rv["id"], biz["id"], d["reply"], settings.groq_model_smart if settings.llm_enabled else "template",
        confidence, round(voice_match, 3), [c["id"] for c in chunks])
    await db.pool.execute("update reviews set status='drafted' where id=$1", rv["id"])
    await emit(biz["id"], "rag_voice", f"Reply drafted in owner's voice · confidence {confidence:.2f}",
               "success", run_id=run, duration_ms=_ms(t1))
    return {"draft": {**d, "confidence": confidence, "voice_match": voice_match}}


# 4) Action dispatcher -------------------------------------------------------------
async def dispatch_node(state):
    biz, rv, a, d, run = state["business"], state["current"], state["analysis"], state["draft"], state["run_id"]
    stats = dict(state["stats"])
    reasons = []
    if not biz["auto_reply_enabled"]: reasons.append("auto-reply disabled")
    if a["sentiment"] in ("negative", "volatile"): reasons.append(f"sentiment {a['sentiment']}")
    if a["risk_flags"]: reasons.append("risk: " + ", ".join(a["risk_flags"]))
    if rv["rating"] < biz["auto_reply_min_stars"]: reasons.append(f"rating below {biz['auto_reply_min_stars']}★")
    if d["confidence"] < settings.auto_reply_min_confidence: reasons.append(f"confidence {d['confidence']:.2f} < {settings.auto_reply_min_confidence}")

    if reasons:
        await db.pool.execute("update reviews set status='needs_human' where id=$1", rv["id"])
        stats["flagged"] += 1
        await emit(biz["id"], "dispatcher", "Flagged for human review: " + "; ".join(reasons), "warning", run_id=run)
    else:
        posted = await get_connector(biz.get("connector", "demo")).post_reply(biz, rv, d["reply"])
        if posted:
            await db.pool.execute("update reply_drafts set auto_posted=true, posted_at=now() where id=(select id from reply_drafts where review_id=$1 order by created_at desc limit 1)", rv["id"])
            await db.pool.execute("update reviews set status='auto_replied' where id=$1", rv["id"])
            stats["auto_replied"] += 1
            await emit(biz["id"], "dispatcher", f"Auto-replied to {rv['author_name'] or 'customer'} (safe, confidence {d['confidence']:.2f})", "success", run_id=run)
        else:
            await emit(biz["id"], "dispatcher", "Reply staged - this source cannot publish automatically; approve to copy/post", "info", run_id=run)
    return {"stats": stats}


# 5) Vision agent (5-star reviews -> social quote card) ------------------------------
async def vision_node(state):
    biz, rv, a, run = state["business"], state["current"], state["analysis"], state["run_id"]
    stats = dict(state["stats"])
    quote = (a["key_phrases"] or [rv["body"][:120]])[0]
    t0 = time.perf_counter()
    await emit(biz["id"], "vision", "Vision pipeline rendering social quote card…", run_id=run)
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"{settings.vision_service_url}/render", json={
                "quote": quote, "author": rv["author_name"] or "Happy customer", "business_name": biz["name"],
                "rating": rv["rating"], "theme": biz["quote_card_theme"], "asset_id": str(rv["id"])})
            r.raise_for_status()
            info = r.json()
        await db.pool.execute(
            "insert into social_assets (business_id, review_id, theme, image_path, quote_text, width, height) values ($1,$2,$3,$4,$5,$6,$7)",
            biz["id"], rv["id"], biz["quote_card_theme"], info["filename"], quote, info["width"], info["height"])
        stats["cards"] += 1
        await emit(biz["id"], "vision", f"Quote card ready ({info['layout']['band']} band, {info['layout']['text_color']} text) · {_ms(t0)}ms",
                   "success", run_id=run, duration_ms=_ms(t0))
    except Exception as exc:
        await emit(biz["id"], "vision", f"Quote card failed: {exc}", "error", run_id=run)
    return {"stats": stats}
