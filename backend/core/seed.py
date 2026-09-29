"""Local-dev seed: one demo business with a few real-sounding owner replies for RAG."""
import logging

from . import db
from .auth import DEV_USER_ID
from .embeddings import embed_many

log = logging.getLogger("reviewflow.seed")

REPLIES = [
    ("past_reply", "Thank you so much, Ananya! 🌸 It means the world to our little café team. Your next filter coffee is on us - see you soon! - Priya & the Blue Lotus family"),
    ("past_reply", "Hey Kiran, so glad the pastries hit the spot! We bake them at 6am every day just for regulars like you. Come hungry next time 🥐 - Priya"),
    ("past_reply", "Hi Rahul, thank you for telling us about the wait - that's not the experience we want for anyone. Please write to hello@bluelotus.example and we'll sort your next booking personally. - Priya"),
    ("faq", "We are open 8am to 10pm every day. Table bookings are held for 15 minutes."),
    ("faq", "All our pastries and breads are baked fresh every morning in-house; we use no preservatives."),
    ("policy", "For any food-quality complaint we offer a free replacement or refund on the spot, and the owner follows up personally."),
    ("tone_sample", "Warm, first-name greetings, one emoji at most, sign off with 'Priya' or 'Priya & the Blue Lotus family'."),
]


async def seed_demo():
    try:
        await db.pool.execute("insert into auth.users (id, email) values ($1, 'dev@reviewflow.local') on conflict do nothing", DEV_USER_ID)
    except Exception as exc:
        log.info("seed skipped (%s)", exc)
        return
    if await db.pool.fetchval("select count(*) from businesses where owner_id=$1", DEV_USER_ID):
        return
    bid = await db.pool.fetchval(
        """insert into businesses (owner_id, name, industry, location, brand_voice_summary, connector)
           values ($1,'Blue Lotus Café','Café & bakery','Hyderabad, India',
           'Warm, personal and lightly playful; first-name greetings, at most one emoji, signs off with the owner''s name.','demo')
           returning id""", DEV_USER_ID)
    vecs = await embed_many([c for _, c in REPLIES])
    for (kind, content), v in zip(REPLIES, vecs):
        await db.pool.execute("insert into embeddings (business_id, kind, content, embedding) values ($1,$2::embedding_kind,$3,$4::vector)",
                              bid, kind, content, db.vec(v))
    log.info("seeded demo business %s", bid)
