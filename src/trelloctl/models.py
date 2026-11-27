"""Stable, typed representations shared by card commands."""


def card_data(card: dict) -> dict:
    """Keep labels and membership structured for machine-readable output."""
    return {
        "id": card["id"],
        "name": card.get("name", ""),
        "description": card.get("desc", ""),
        "due": card.get("due"),
        "due_complete": bool(card.get("dueComplete", False)),
        "url": card.get("url", ""),
        "board_id": card.get("idBoard", ""),
        "list_id": card.get("idList", ""),
        "labels": [
            {
                "id": label["id"],
                "name": label.get("name", ""),
                "color": label.get("color"),
            }
            for label in card.get("labels", [])
        ],
        "member_ids": list(card.get("idMembers", [])),
        "closed": bool(card.get("closed", False)),
    }
