import logging
from uuid import UUID

from core import bus, db
from core.telemetry import emit
from .graph import GRAPH

log = logging.getLogger("reviewflow.runner")


async def run_autopilot(business_id: UUID, trigger: str = "schedule") -> dict | None:
    r = bus.redis_client()
    if not await r.set(f"lock:autopilot:{business_id}", "1", nx=True, ex=180):
        return None  # a run is already in flight
    run_id = None
    try:
        biz = await db.pool.fetchrow("select * from businesses where id=$1", business_id)
        if not biz:
            return None
        run_id = await db.pool.fetchval("insert into agent_runs (business_id) values ($1) returning id", business_id)
        await emit(business_id, "system", f"Autopilot run started ({trigger})", run_id=run_id)
        final = await GRAPH.ainvoke({"business": dict(biz), "run_id": run_id, "queue": [], "current": None,
                                     "stats": {"reviews_seen": 0, "auto_replied": 0, "flagged": 0, "cards": 0}},
                                    {"recursion_limit": 200})
        s = final["stats"]
        await db.pool.execute(
            "update agent_runs set status='completed', reviews_seen=$2, auto_replied=$3, flagged=$4, finished_at=now() where id=$1",
            run_id, s["reviews_seen"], s["auto_replied"], s["flagged"])
        await emit(business_id, "system",
                   f"Run complete: {s['reviews_seen']} reviews · {s['auto_replied']} auto-replied · {s['flagged']} flagged · {s['cards']} cards",
                   "success", run_id=run_id, payload=s)
        return s
    except Exception as exc:
        log.exception("autopilot failed")
        if run_id:
            await db.pool.execute("update agent_runs set status='failed', error=$2, finished_at=now() where id=$1", run_id, str(exc)[:500])
        await emit(business_id, "system", f"Run failed: {exc}", "error", run_id=run_id)
        return None
    finally:
        await r.delete(f"lock:autopilot:{business_id}")
