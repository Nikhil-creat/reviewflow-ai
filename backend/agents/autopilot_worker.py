"""Background worker: runs the LangGraph autopilot for every business on a timer."""
import asyncio
import logging

from core import db
from core.config import settings
from core.seed import seed_demo
from .runner import run_autopilot

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("reviewflow.worker")


async def loop():
    while True:
        try:
            for row in await db.pool.fetch("select id from businesses where auto_reply_enabled"):
                await run_autopilot(row["id"], "schedule")
        except Exception:
            log.exception("worker tick failed")
        await asyncio.sleep(settings.autopilot_interval_seconds)


async def main():
    await db.connect()
    if settings.seed_demo:
        await seed_demo()
    await loop()


if __name__ == "__main__":
    asyncio.run(main())
