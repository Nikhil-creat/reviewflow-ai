"""Reads the latest reviews via the Google Places API (New). The API returns at most 5 reviews per place
and CANNOT publish replies - live replying needs the Google Business Profile API (OAuth)."""
import httpx

from core.config import settings


class GooglePlacesConnector:
    name = "google_places"

    async def fetch(self, business: dict) -> list[dict]:
        pid, key = business.get("google_place_id"), settings.google_places_api_key
        if not pid or not key:
            return []
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"https://places.googleapis.com/v1/places/{pid}",
                            headers={"X-Goog-Api-Key": key, "X-Goog-FieldMask": "reviews"})
            r.raise_for_status()
        out = []
        for rv in r.json().get("reviews", []):
            out.append({"external_id": rv["name"], "platform": "google",
                        "author_name": rv.get("authorAttribution", {}).get("displayName"),
                        "rating": int(rv.get("rating", 3)), "body": (rv.get("text") or {}).get("text", ""),
                        "reviewed_at": rv.get("publishTime")})
        return out

    async def post_reply(self, business: dict, review: dict, body: str) -> bool:
        return False  # staged for the owner; requires Business Profile API OAuth to publish
