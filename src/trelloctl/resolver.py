"""Name to ID resolution for boards, lists, and cards."""

from __future__ import annotations

import re
from urllib.parse import urlsplit
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trelloctl.client import TrelloClient


def is_trello_id(ref: str) -> bool:
    """Return True if ref looks like a 24-character hex Trello ID."""
    return len(ref) == 24 and all(c in "0123456789abcdef" for c in ref.lower())


def trello_url_ref(value: str, kind: str) -> str | None:
    """Extract a board/card identifier from a Trello URL, rejecting other hosts."""
    if "://" not in value:
        return None
    parsed = urlsplit(value)
    parts = parsed.path.strip("/").split("/")
    if (
        parsed.scheme not in {"https", "http"}
        or parsed.hostname not in {"trello.com", "www.trello.com"}
        or parsed.username is not None
        or len(parts) < 2
        or parts[0] != kind
        or not re.fullmatch(r"[A-Za-z0-9]+", parts[1])
    ):
        raise ValueError(f"Expected a Trello {'card' if kind == 'c' else 'board'} URL")
    return parts[1]


def _match_name(items: list[dict], ref: str, kind: str) -> str:
    """Prefer exact ID/name matches, rejecting ambiguous partial names."""
    if not ref.strip():
        raise ValueError(f"{kind.title()} reference cannot be empty")
    exact = [
        item
        for item in items
        if item["id"] == ref or item.get("name", "").casefold() == ref.casefold()
    ]
    matches = exact or [
        item for item in items if ref.casefold() in item.get("name", "").casefold()
    ]
    if len(matches) == 1:
        return matches[0]["id"]
    if matches:
        details = ", ".join(
            f"{item.get('name', '')} ({item['id']})" for item in matches
        )
        raise ValueError(f"Multiple {kind}s match '{ref}': {details}")
    raise ValueError(f"{kind.title()} not found: '{ref}'")


class Resolver:
    """Resolves names to Trello IDs."""

    def __init__(self, client: TrelloClient) -> None:
        self.client = client
        self._boards_cache: list[dict] | None = None
        self._lists_cache: dict[str, list[dict]] = {}
        self._members_cache: dict[str, list[dict]] = {}

    def _get_boards(self) -> list[dict]:
        """Get all boards (cached)."""
        if self._boards_cache is None:
            self._boards_cache = self.client.get_boards(filter="all")
        return self._boards_cache

    def _get_lists(self, board_id: str) -> list[dict]:
        """Get all lists for a board (cached)."""
        if board_id not in self._lists_cache:
            self._lists_cache[board_id] = self.client.get_board_lists(
                board_id, filter="all"
            )
        return self._lists_cache[board_id]

    def _get_members(self, board_id: str) -> list[dict]:
        """Get all members for a board (cached)."""
        if board_id not in self._members_cache:
            self._members_cache[board_id] = self.client.get_board_members(board_id)
        return self._members_cache[board_id]

    def resolve_board(self, board_ref: str) -> str:
        """Resolve a board reference (ID or name) to an ID.

        Args:
            board_ref: Board ID or name (can be partial, case-insensitive)

        Returns:
            Board ID

        Raises:
            ValueError: If board not found or multiple matches
        """
        url_ref = trello_url_ref(board_ref, "b")
        if url_ref:
            return self.client.get_board(url_ref)["id"]
        # If it looks like an ID (24 hex chars), try it directly
        if is_trello_id(board_ref):
            return board_ref

        boards = self._get_boards()
        board_ref_lower = board_ref.lower()

        # Try exact match first
        exact_matches = [b for b in boards if b["name"].lower() == board_ref_lower]
        if len(exact_matches) == 1:
            return exact_matches[0]["id"]

        # Try partial match
        partial_matches = [b for b in boards if board_ref_lower in b["name"].lower()]
        if len(partial_matches) == 1:
            return partial_matches[0]["id"]
        if len(partial_matches) > 1:
            names = [b["name"] for b in partial_matches]
            raise ValueError(f"Multiple boards match '{board_ref}': {', '.join(names)}")

        raise ValueError(f"Board not found: '{board_ref}'")

    def resolve_list(self, board_ref: str, list_ref: str) -> str:
        """Resolve a list reference (ID or name) to an ID.

        Args:
            board_ref: Board ID or name
            list_ref: List ID or name (can be partial, case-insensitive)

        Returns:
            List ID

        Raises:
            ValueError: If list not found or multiple matches
        """
        board_id = self.resolve_board(board_ref)

        # If it looks like an ID, try it directly
        if is_trello_id(list_ref):
            return list_ref

        lists = self._get_lists(board_id)
        list_ref_lower = list_ref.lower()

        # Try exact match first
        exact_matches = [lst for lst in lists if lst["name"].lower() == list_ref_lower]
        if len(exact_matches) == 1:
            return exact_matches[0]["id"]

        # Try partial match
        partial_matches = [
            lst for lst in lists if list_ref_lower in lst["name"].lower()
        ]
        if len(partial_matches) == 1:
            return partial_matches[0]["id"]
        if len(partial_matches) > 1:
            names = [lst["name"] for lst in partial_matches]
            raise ValueError(f"Multiple lists match '{list_ref}': {', '.join(names)}")

        raise ValueError(f"List not found: '{list_ref}' in board '{board_ref}'")

    def resolve_card(self, board_ref: str, list_ref: str, card_ref: str) -> str:
        """Resolve a card reference (ID or name) to an ID.

        Args:
            board_ref: Board ID or name
            list_ref: List ID or name
            card_ref: Card ID or name (can be partial, case-insensitive)

        Returns:
            Card ID

        Raises:
            ValueError: If card not found or multiple matches
        """
        list_id = self.resolve_list(board_ref, list_ref)

        # If it looks like an ID, try it directly
        if is_trello_id(card_ref):
            return card_ref

        cards = self.client.get_list_cards(list_id)
        card_ref_lower = card_ref.lower()

        # Try exact match first
        exact_matches = [c for c in cards if c["name"].lower() == card_ref_lower]
        if len(exact_matches) == 1:
            return exact_matches[0]["id"]

        # Try partial match
        partial_matches = [c for c in cards if card_ref_lower in c["name"].lower()]
        if len(partial_matches) == 1:
            return partial_matches[0]["id"]
        if len(partial_matches) > 1:
            names = [c["name"] for c in partial_matches]
            raise ValueError(f"Multiple cards match '{card_ref}': {', '.join(names)}")

        raise ValueError(f"Card not found: '{card_ref}' in list '{list_ref}'")

    def resolve_card_ref(
        self, card_ref: str, board_ref: str | None = None, list_ref: str | None = None
    ) -> str:
        """Resolve URLs, IDs and shortlinks, or names scoped to a board/list.

        Without a board, alphanumeric references pass through to Trello as they
        did before name resolution was introduced. Scoped names never fall back
        to passing an unmatched string to a write endpoint.
        """
        if list_ref and not board_ref:
            raise ValueError("--list requires --board")
        url_ref = trello_url_ref(card_ref, "c")
        if url_ref:
            return url_ref
        if is_trello_id(card_ref):
            return card_ref
        if not board_ref:
            if re.fullmatch(r"[A-Za-z0-9]+", card_ref):
                return card_ref
            raise ValueError("Card names require --board (and optionally --list)")
        board_id = self.resolve_board(board_ref)
        cards = self.client.get_board_cards(board_id, filter="all")
        if list_ref:
            list_id = self.resolve_list(board_id, list_ref)
            cards = [card for card in cards if card.get("idList") == list_id]
        # A shortlink should also work with an explicitly provided scope.
        direct = [
            card
            for card in cards
            if card.get("shortLink") == card_ref
            or card.get("url", "").split("/")[4:5] == [card_ref]
        ]
        if len(direct) == 1:
            return direct[0]["id"]
        return _match_name(cards, card_ref, "card")

    def resolve_label(self, board_ref: str, label_ref: str) -> str:
        """Resolve a label ID or case-insensitive name on a board."""
        if is_trello_id(label_ref):
            return label_ref
        board_id = self.resolve_board(board_ref)
        return _match_name(self.client.get_board_labels(board_id), label_ref, "label")

    def resolve_member(self, board_ref: str, member_ref: str) -> str:
        """Resolve a member reference (ID, username, or full name) to an ID.

        Args:
            board_ref: Board ID or name the member belongs to
            member_ref: Member ID, username, or full name (partial,
                case-insensitive)

        Returns:
            Member ID

        Raises:
            ValueError: If member not found or multiple matches
        """
        if member_ref.casefold() == "me":
            return self.client.get_me()["id"]
        member_ref = member_ref.removeprefix("@")
        if not member_ref.strip():
            raise ValueError("Member reference cannot be empty")
        # If it looks like an ID, try it directly
        if is_trello_id(member_ref):
            return member_ref

        board_id = self.resolve_board(board_ref)
        members = self._get_members(board_id)
        id_matches = [member for member in members if member["id"] == member_ref]
        if id_matches:
            return id_matches[0]["id"]
        member_ref_lower = member_ref.lower()

        # Try exact username match first
        username_matches = [
            m for m in members if m.get("username", "").lower() == member_ref_lower
        ]
        if len(username_matches) == 1:
            return username_matches[0]["id"]

        # Then exact full name match
        fullname_matches = [
            m for m in members if m.get("fullName", "").lower() == member_ref_lower
        ]
        if len(fullname_matches) == 1:
            return fullname_matches[0]["id"]

        # Fall back to partial match on username or full name
        partial_matches = [
            m
            for m in members
            if member_ref_lower in m.get("username", "").lower()
            or member_ref_lower in m.get("fullName", "").lower()
        ]
        if len(partial_matches) == 1:
            return partial_matches[0]["id"]
        if len(partial_matches) > 1:
            names = [
                m.get("username") or m.get("fullName") or m["id"]
                for m in partial_matches
            ]
            raise ValueError(
                f"Multiple members match '{member_ref}': {', '.join(names)}"
            )

        raise ValueError(f"Member not found: '{member_ref}' in board '{board_ref}'")
