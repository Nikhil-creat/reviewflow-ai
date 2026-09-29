"""Groq (OpenAI-compatible) client + prompts. Every call has a heuristic fallback so the
pipeline still runs without a key (useful for demos and CI)."""
import json
import logging
import re

from openai import AsyncOpenAI

from .config import settings

log = logging.getLogger("reviewflow.llm")
_client: AsyncOpenAI | None = None

RISK_WORDS = {
    "legal_threat": ["lawyer", "sue ", "lawsuit", "legal action", "consumer court"],
    "safety_issue": ["food poisoning", "got sick", "unsafe", "hospital", "health department", "injur"],
    "refund_demand": ["refund", "money back", "chargeback"],
    "media_threat": ["news", "social media", "post this everywhere", "viral"],
    "profanity": ["wtf", "shit", "fuck", "scam", "fraud"],
}


def client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.groq_api_key, base_url=settings.groq_base_url, timeout=30)
    return _client


async def chat_json(system: str, user: str, model: str, temperature: float = 0.2, max_tokens: int = 700) -> dict:
    resp = await client().chat.completions.create(
        model=model, temperature=temperature, max_tokens=max_tokens,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return json.loads(resp.choices[0].message.content)


# ---------------------------------------------------------------- sentiment
SENTIMENT_SYSTEM = """You are the Sentiment Evaluation Agent of a local-business reputation tool.
Return ONLY JSON with keys:
sentiment: one of positive|neutral|negative|volatile (volatile = angry, threatening, or risky to answer automatically)
score: number -1..1
intent_tags: up to 4 short lowercase tags (e.g. service, pricing, food, cleanliness, wait_time, staff)
risk_flags: subset of [legal_threat, safety_issue, profanity, discrimination, fake_review_suspected, refund_demand, media_threat]
key_phrases: 1-3 short VERBATIM quotes (max 14 words each) from the review that are most quotable
summary: one sentence."""


def _heuristic_sentiment(rv: dict) -> dict:
    body = (rv.get("body") or "").lower()
    rating = rv["rating"]
    flags = [k for k, words in RISK_WORDS.items() if any(w in body for w in words)]
    sentiment = "positive" if rating >= 4 else "neutral" if rating == 3 else "negative"
    if flags or (rating <= 2 and any(w in body for w in ["never", "worst", "disgust", "terrible"])):
        sentiment = "volatile" if flags else sentiment
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", rv.get("body") or "") if s.strip()]
    phrases = [s for s in sentences if len(s.split()) <= 14][:2] or [" ".join((rv.get("body") or "").split()[:12])]
    return {"sentiment": sentiment, "score": round((rating - 3) / 2, 2), "intent_tags": [],
            "risk_flags": flags, "key_phrases": [p for p in phrases if p], "summary": ""}


async def analyze_sentiment(rv: dict) -> dict:
    if not settings.llm_enabled:
        return _heuristic_sentiment(rv)
    try:
        out = await chat_json(SENTIMENT_SYSTEM, f"Rating: {rv['rating']}/5\nReview: {rv['body']}", settings.groq_model_fast)
        s = out.get("sentiment")
        if s not in ("positive", "neutral", "negative", "volatile"):
            s = _heuristic_sentiment(rv)["sentiment"]
        flags = [f for f in out.get("risk_flags", []) if isinstance(f, str)][:6]
        if flags and s != "volatile":
            s = "volatile"
        body_l = (rv.get("body") or "").lower()
        phrases = [p.strip() for p in out.get("key_phrases", []) if isinstance(p, str) and p.strip().lower() in body_l][:3]
        if not phrases:
            phrases = _heuristic_sentiment(rv)["key_phrases"]
        return {"sentiment": s, "score": max(-1.0, min(1.0, float(out.get("score", 0)))),
                "intent_tags": [str(t)[:24] for t in out.get("intent_tags", [])][:4],
                "risk_flags": flags, "key_phrases": phrases, "summary": str(out.get("summary", ""))[:240]}
    except Exception as exc:
        log.warning("sentiment LLM failed, using heuristic: %s", exc)
        return _heuristic_sentiment(rv)


# ---------------------------------------------------------------- drafting
DRAFT_SYSTEM = """You write replies to customer reviews AS the business owner. Mirror the owner's real voice
shown in the examples: same greeting style, sentence length, warmth, sign-off and emoji habits.
Rules: never invent facts, discounts, names or policies not present in the context; keep it under 90 words;
if the review is negative, acknowledge the specific issue and offer to continue offline; never admit legal liability.
Return ONLY JSON: {"reply": string, "confidence": number 0..1 (how sure you are this is safe to post unedited)}."""


def _fallback_reply(business: dict, rv: dict) -> dict:
    name = (rv.get("author_name") or "there").split()[0]
    if rv["rating"] >= 4:
        text = f"Thank you so much, {name}! We're delighted you enjoyed your visit to {business['name']}. See you again soon!"
        conf = 0.9
    else:
        text = (f"Hi {name}, we're sorry we fell short. We'd like to make this right - please reach out to us "
                f"directly so the team at {business['name']} can help.")
        conf = 0.5
    return {"reply": text, "confidence": conf}


async def draft_reply(business: dict, rv: dict, analysis: dict, chunks: list[dict]) -> dict:
    if not settings.llm_enabled:
        return _fallback_reply(business, rv)
    examples = "\n".join(f"- {c['content']}" for c in chunks if c["kind"] in ("past_reply", "tone_sample")) or "(none yet)"
    facts = "\n".join(f"- {c['content']}" for c in chunks if c["kind"] in ("faq", "policy")) or "(none)"
    user = (f"Business: {business['name']} ({business.get('industry') or 'local business'}, {business.get('location') or ''})\n"
            f"Voice summary: {business.get('brand_voice_summary') or 'friendly and professional'}\n\n"
            f"Owner's past replies (mirror this voice):\n{examples}\n\nFacts you may rely on:\n{facts}\n\n"
            f"Review by {rv.get('author_name') or 'a customer'} ({rv['rating']}/5, {analysis['sentiment']}): {rv['body']}\n"
            f"Detected topics: {', '.join(analysis['intent_tags']) or 'n/a'}; risk flags: {', '.join(analysis['risk_flags']) or 'none'}")
    try:
        out = await chat_json(DRAFT_SYSTEM, user, settings.groq_model_smart, temperature=0.5)
        reply = str(out.get("reply", "")).strip()
        if not reply:
            raise ValueError("empty reply")
        return {"reply": reply, "confidence": max(0.0, min(1.0, float(out.get("confidence", 0.6))))}
    except Exception as exc:
        log.warning("draft LLM failed, using template: %s", exc)
        return _fallback_reply(business, rv)


async def summarize_voice(samples: list[str]) -> str:
    if not settings.llm_enabled or not samples:
        return ""
    try:
        out = await chat_json(
            'Describe the writing voice of these business-owner replies in 2 sentences (tone, greeting, sign-off, emoji use). Return JSON {"summary": string}.',
            "\n".join(f"- {s}" for s in samples[:12]), settings.groq_model_fast)
        return str(out.get("summary", ""))[:400]
    except Exception:
        return ""
