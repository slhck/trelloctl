"""Name to ID resolution for boards, lists, and cards."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trelloctl.client import TrelloClient


class Resolver:
    """Resolves names to Trello IDs."""

    def __init__(self, client: TrelloClient) -> None:
        self.client = client
        self._boards_cache: list[dict] | None = None
        self._lists_cache: dict[str, list[dict]] = {}

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

    def resolve_board(self, board_ref: str) -> str:
        """Resolve a board reference (ID or name) to an ID.

        Args:
            board_ref: Board ID or name (can be partial, case-insensitive)

        Returns:
            Board ID

        Raises:
            ValueError: If board not found or multiple matches
        """
        # If it looks like an ID (24 hex chars), try it directly
        if len(board_ref) == 24 and all(
            c in "0123456789abcdef" for c in board_ref.lower()
        ):
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
        if len(list_ref) == 24 and all(
            c in "0123456789abcdef" for c in list_ref.lower()
        ):
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
        if len(card_ref) == 24 and all(
            c in "0123456789abcdef" for c in card_ref.lower()
        ):
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
