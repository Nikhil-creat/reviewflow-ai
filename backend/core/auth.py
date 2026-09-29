from uuid import UUID

import jwt
from fastapi import Header, HTTPException

from .config import settings

DEV_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


def _verify(token: str) -> UUID:
    try:
        claims = jwt.decode(token, settings.supabase_jwt_secret, algorithms=["HS256"], audience="authenticated")
        return UUID(claims["sub"])
    except Exception as exc:
        raise HTTPException(401, f"invalid token: {exc}")


async def current_user(authorization: str | None = Header(default=None)) -> UUID:
    """Dev mode (no SUPABASE_JWT_SECRET): everyone is the seeded dev user.
    Production: require a Supabase access token."""
    if not settings.supabase_jwt_secret:
        return DEV_USER_ID
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "missing bearer token")
    return _verify(authorization.split(" ", 1)[1])


def ws_user(token: str | None) -> UUID:
    if not settings.supabase_jwt_secret:
        return DEV_USER_ID
    if not token:
        raise HTTPException(401, "missing token")
    return _verify(token)
