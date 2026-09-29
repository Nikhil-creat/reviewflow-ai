from typing import TypedDict


class AutopilotState(TypedDict, total=False):
    business: dict
    run_id: str
    queue: list          # reviews still to process this run
    current: dict | None
    analysis: dict
    chunks: list
    draft: dict
    stats: dict          # reviews_seen, auto_replied, flagged, cards
