"""Simulated review source: drops 1-3 realistic reviews per sync so the demo stays alive."""
import random
import uuid

SAMPLES = [
    ("Ananya R.", 5, "Absolutely loved the filter coffee and the warm staff. Best cozy corner in the city!"),
    ("Kiran M.", 5, "The pastries were fresh and the service was lightning fast. Will be back every weekend."),
    ("Sofia L.", 4, "Great ambience and tasty food. Slightly noisy at lunch but worth it."),
    ("Rahul P.", 3, "Coffee was good but we waited 25 minutes for a table even with a booking."),
    ("Vikram S.", 2, "Order was wrong twice and nobody apologised. Disappointing for the price."),
    ("Meera D.", 1, "Found a hair in my food. I'm going to contact a lawyer and the health department if this isn't fixed."),
    ("Arjun T.", 5, "Every dish felt handmade. The owner even remembered my name. Five stars!"),
    ("Neha G.", 5, "Perfect birthday brunch - the team decorated our table without being asked."),
]


class DemoConnector:
    name = "demo"

    async def fetch(self, business: dict) -> list[dict]:
        return [{"external_id": f"demo-{uuid.uuid4().hex[:12]}", "author_name": a, "rating": r, "body": b, "platform": "manual"}
                for a, r, b in random.sample(SAMPLES, k=random.randint(1, 3))]

    async def post_reply(self, business: dict, review: dict, body: str) -> bool:
        return True  # simulated publish
