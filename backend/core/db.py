import asyncio
import json
import logging

import asyncpg

from .config import settings

log = logging.getLogger("reviewflow.db")
pool: asyncpg.Pool | None = None


async def _init(conn: asyncpg.Connection):
    for t in ("json", "jsonb"):
        await conn.set_type_codec(t, encoder=json.dumps, decoder=json.loads, schema="pg_catalog")


async def connect(retries: int = 30):
    global pool
    for attempt in range(1, retries + 1):
        try:
            pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=10, init=_init)
            log.info("database connected")
            return
        except Exception as exc:  # db still booting
            log.warning("db not ready (%s/%s): %s", attempt, retries, exc)
            await asyncio.sleep(2)
    raise RuntimeError("could not connect to database")


async def close():
    if pool:
        await pool.close()


def vec(values) -> str:
    """Format a float list as a pgvector literal."""
    return "[" + ",".join(f"{float(x):.6f}" for x in values) + "]"
