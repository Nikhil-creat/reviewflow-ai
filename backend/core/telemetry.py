"""Every agent step is persisted to agent_events AND published on Redis so the
dashboard receives it over WebSocket in real time."""
import json
from uuid import UUID

from . import db
from .bus import redis_client


async def emit(business_id, agent: str, message: str, level: str = "info",
               run_id=None, duration_ms: int | None = None, payload: dict | None = None) -> dict:
    row = await db.pool.fetchrow(
        """insert into agent_events (run_id, business_id, agent, level, message, duration_ms, payload)
           values ($1, $2, $3, $4::event_level, $5, $6, $7::jsonb)
           returning id, created_at""",
        run_id, UUID(str(business_id)), agent, level, message, duration_ms, payload or {},
    )
    event = {
        "id": row["id"], "agent": agent, "level": level, "message": message,
        "duration_ms": duration_ms, "created_at": row["created_at"].isoformat(),
    }
    await redis_client().publish(f"telemetry:{business_id}", json.dumps(event))
    return event
