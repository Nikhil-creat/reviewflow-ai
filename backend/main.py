"""ReviewFlow AI - FastAPI gateway. Designed & developed by NIKHIL CHARY SRIRAMOJU."""
import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Literal
from uuid import UUID

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agents.runner import run_autopilot
from connectors import get_connector
from core import bus, db, llm
from core.auth import current_user, ws_user
from core.config import settings
from core.embeddings import embed_many
from core.seed import seed_demo
from core.telemetry import emit

logging.basicConfig(level=logging.INFO)
ASSET_DIR = os.getenv("ASSET_OUTPUT_DIR", "/data/assets")
os.makedirs(ASSET_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    if settings.seed_demo:
        await seed_demo()
    task = None
    if settings.run_autopilot_in_process:
        async def loop():
            while True:
                for r in await db.pool.fetch("select id from businesses where auto_reply_enabled"):
                    await run_autopilot(r["id"], "schedule")
                await asyncio.sleep(settings.autopilot_interval_seconds)
        task = asyncio.create_task(loop())
    yield
    if task:
        task.cancel()
    await db.close()


app = FastAPI(title="ReviewFlow AI", version="1.0.0", lifespan=lifespan,
              description="Autonomous reputation engine. Designed & developed by NIKHIL CHARY SRIRAMOJU.")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/assets", StaticFiles(directory=ASSET_DIR), name="assets")


# ------------------------------------------------------------------ helpers
async def require_business(business_id: UUID, user: UUID):
    row = await db.pool.fetchrow(
        """select * from businesses b where b.id=$1 and (b.owner_id=$2 or exists
           (select 1 from business_members m where m.business_id=b.id and m.user_id=$2))""", business_id, user)
    if not row:
        raise HTTPException(404, "Business not found")
    return row


# ------------------------------------------------------------------ models
class BusinessIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    industry: str | None = None
    location: str | None = None
    connector: Literal["demo", "google_places", "manual"] = "demo"
    google_place_id: str | None = None


class ReviewIn(BaseModel):
    author_name: str | None = None
    rating: int = Field(ge=1, le=5)
    body: str = Field(min_length=3, max_length=4000)


class ApproveIn(BaseModel):
    body: str | None = Field(default=None, max_length=2000)


class BrandItem(BaseModel):
    kind: Literal["past_reply", "faq", "policy", "tone_sample"] = "past_reply"
    content: str = Field(min_length=10, max_length=2000)


class BrandIngest(BaseModel):
    items: list[BrandItem] = Field(min_length=1, max_length=50)


# ------------------------------------------------------------------ routes
@app.get("/health")
async def health():
    return {"status": "ok", "llm": "groq" if settings.llm_enabled else "heuristic-fallback",
            "author": "NIKHIL CHARY SRIRAMOJU"}


@app.get("/api/businesses")
async def list_businesses(user: UUID = Depends(current_user)):
    rows = await db.pool.fetch(
        """select b.* from businesses b where b.owner_id=$1 or exists
           (select 1 from business_members m where m.business_id=b.id and m.user_id=$1) order by created_at""", user)
    return [dict(r) for r in rows]


@app.post("/api/businesses", status_code=201)
async def create_business(body: BusinessIn, user: UUID = Depends(current_user)):
    row = await db.pool.fetchrow(
        "insert into businesses (owner_id,name,industry,location,connector,google_place_id) values ($1,$2,$3,$4,$5,$6) returning *",
        user, body.name, body.industry, body.location, body.connector, body.google_place_id)
    return dict(row)


@app.get("/api/businesses/{business_id}/reviews")
async def list_reviews(business_id: UUID, status: str | None = None, limit: int = Query(50, le=200),
                       user: UUID = Depends(current_user)):
    await require_business(business_id, user)
    rows = await db.pool.fetch(
        """select r.*,
             (select to_jsonb(d) from (select id, body, confidence, voice_match, auto_posted
                from reply_drafts where review_id=r.id order by created_at desc limit 1) d) as draft,
             (select image_path from social_assets where review_id=r.id order by created_at desc limit 1) as asset_file
           from reviews r where r.business_id=$1 and ($2::text is null or r.status::text=$2)
           order by r.reviewed_at desc limit $3""", business_id, status, limit)
    out = []
    for r in rows:
        d = dict(r)
        d["asset_url"] = f"/assets/{d.pop('asset_file')}" if d.get("asset_file") else None
        d.pop("asset_file", None)
        out.append(d)
    return out


@app.post("/api/businesses/{business_id}/reviews", status_code=201)
async def add_review(business_id: UUID, body: ReviewIn, user: UUID = Depends(current_user)):
    await require_business(business_id, user)
    row = await db.pool.fetchrow(
        "insert into reviews (business_id, platform, external_id, author_name, rating, body) values ($1,'manual',$2,$3,$4,$5) returning *",
        business_id, f"manual-{os.urandom(6).hex()}", body.author_name, body.rating, body.body)
    return dict(row)


@app.post("/api/businesses/{business_id}/autopilot/run", status_code=202)
async def trigger_autopilot(business_id: UUID, bg: BackgroundTasks, user: UUID = Depends(current_user)):
    await require_business(business_id, user)
    bg.add_task(run_autopilot, business_id, "manual")
    return {"accepted": True}


@app.post("/api/reviews/{review_id}/approve")
async def approve_review(review_id: UUID, body: ApproveIn, user: UUID = Depends(current_user)):
    rv = await db.pool.fetchrow("select * from reviews where id=$1", review_id)
    if not rv:
        raise HTTPException(404, "Review not found")
    biz = await require_business(rv["business_id"], user)
    draft = await db.pool.fetchrow("select * from reply_drafts where review_id=$1 order by created_at desc limit 1", review_id)
    if not draft:
        raise HTTPException(409, "No draft to approve yet")
    text = body.body or draft["body"]
    posted = await get_connector(biz["connector"]).post_reply(dict(biz), dict(rv), text)
    await db.pool.execute("update reply_drafts set body=$2, approved_by=$3, posted_at=case when $4 then now() end where id=$1",
                          draft["id"], text, user, posted)
    await db.pool.execute("update reviews set status='approved' where id=$1", review_id)
    await emit(rv["business_id"], "dispatcher",
               "Human approved reply" + (" and it was published" if posted else " (copy it to the platform manually)"), "success")
    return {"status": "approved", "published": posted}


@app.post("/api/reviews/{review_id}/dismiss")
async def dismiss_review(review_id: UUID, user: UUID = Depends(current_user)):
    rv = await db.pool.fetchrow("select business_id from reviews where id=$1", review_id)
    if not rv:
        raise HTTPException(404, "Review not found")
    await require_business(rv["business_id"], user)
    await db.pool.execute("update reviews set status='dismissed' where id=$1", review_id)
    return {"status": "dismissed"}


@app.post("/api/businesses/{business_id}/brand-voice", status_code=201)
async def ingest_brand_voice(business_id: UUID, body: BrandIngest, user: UUID = Depends(current_user)):
    await require_business(business_id, user)
    import time
    t0 = time.perf_counter()
    vecs = await embed_many([i.content for i in body.items])
    for item, v in zip(body.items, vecs):
        await db.pool.execute("insert into embeddings (business_id, kind, content, embedding) values ($1,$2::embedding_kind,$3,$4::vector)",
                              business_id, item.kind, item.content, db.vec(v))
    await emit(business_id, "rag_voice", f"Embedded {len(vecs)} brand-voice chunk(s) into pgvector",
               "success", duration_ms=int((time.perf_counter() - t0) * 1000))
    replies = [i.content for i in body.items if i.kind in ("past_reply", "tone_sample")]
    summary = await llm.summarize_voice(replies)
    if summary:
        await db.pool.execute("update businesses set brand_voice_summary=$2 where id=$1", business_id, summary)
    return {"embedded": len(vecs), "voice_summary": summary or None}


@app.get("/api/businesses/{business_id}/stats")
async def stats(business_id: UUID, user: UUID = Depends(current_user)):
    await require_business(business_id, user)
    row = await db.pool.fetchrow(
        """select count(*) total, count(*) filter (where status='auto_replied') auto_replied,
                  count(*) filter (where status='needs_human') needs_human,
                  coalesce(round(avg(rating)::numeric,2),0) avg_rating,
                  (select count(*) from embeddings where business_id=$1) brand_chunks,
                  (select count(*) from social_assets where business_id=$1) cards
           from reviews where business_id=$1""", business_id)
    return dict(row)


@app.get("/api/businesses/{business_id}/events")
async def events(business_id: UUID, limit: int = Query(50, le=200), user: UUID = Depends(current_user)):
    await require_business(business_id, user)
    rows = await db.pool.fetch(
        "select id, agent, level, message, duration_ms, created_at from agent_events where business_id=$1 order by id desc limit $2",
        business_id, limit)
    return [dict(r) for r in rows]


@app.websocket("/ws/telemetry/{business_id}")
async def ws_telemetry(ws: WebSocket, business_id: UUID, token: str | None = None):
    await ws.accept()
    try:
        user = ws_user(token)
        await require_business(business_id, user)
    except HTTPException:
        await ws.close(code=4401)
        return
    rows = await db.pool.fetch(
        "select id, agent, level, message, duration_ms, created_at from agent_events where business_id=$1 order by id desc limit 30",
        business_id)
    backlog = [{**dict(r), "created_at": r["created_at"].isoformat()} for r in rows]
    await ws.send_text(json.dumps({"type": "backfill", "events": backlog}))

    pubsub = bus.redis_client().pubsub()
    await pubsub.subscribe(f"telemetry:{business_id}")

    async def pump():
        async for msg in pubsub.listen():
            if msg["type"] == "message":
                await ws.send_text(json.dumps({"type": "event", "event": json.loads(msg["data"])}))

    async def watch():
        while True:
            await ws.receive_text()  # raises on disconnect

    tasks = [asyncio.create_task(pump()), asyncio.create_task(watch())]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    except WebSocketDisconnect:
        pass
    finally:
        for t in tasks:
            t.cancel()
        await pubsub.unsubscribe(f"telemetry:{business_id}")
        await pubsub.close()
