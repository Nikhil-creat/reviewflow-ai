from typing import Protocol


class Connector(Protocol):
    name: str

    async def fetch(self, business: dict) -> list[dict]:
        """Return dicts: external_id, author_name, rating, body, reviewed_at(optional), platform"""

    async def post_reply(self, business: dict, review: dict, body: str) -> bool:
        """Return True only if the reply was really published on the platform."""
