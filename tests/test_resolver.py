"""Tests for the name resolver."""

from __future__ import annotations

from typing import Any

import pytest

from trelloctl.resolver import Resolver


class TestResolver:
    """Tests for the Resolver class."""

    def test_resolve_board_by_id(self, mock_resolver: Resolver) -> None:
        """Test resolving a board by its full ID."""
        board_id = mock_resolver.resolve_board("507f1f77bcf86cd799439011")
        assert board_id == "507f1f77bcf86cd799439011"

    def test_resolve_board_by_exact_name(self, mock_resolver: Resolver) -> None:
        """Test resolving a board by exact name match."""
        board_id = mock_resolver.resolve_board("Development")
        assert board_id == "507f1f77bcf86cd799439011"

    def test_resolve_board_by_exact_name_case_insensitive(
        self, mock_resolver: Resolver
    ) -> None:
        """Test resolving a board by name is case-insensitive."""
        board_id = mock_resolver.resolve_board("development")
        assert board_id == "507f1f77bcf86cd799439011"

        board_id = mock_resolver.resolve_board("DEVELOPMENT")
        assert board_id == "507f1f77bcf86cd799439011"

    def test_resolve_board_by_partial_name(self, mock_resolver: Resolver) -> None:
        """Test resolving a board by partial name match."""
        board_id = mock_resolver.resolve_board("Marketing")
        assert board_id == "507f1f77bcf86cd799439022"

    def test_resolve_board_partial_match_ambiguous(
        self, mock_resolver: Resolver
    ) -> None:
        """Test that ambiguous partial matches raise an error."""
        # "Dev" matches both "Development" and "Dev/Backend"
        with pytest.raises(ValueError) as exc_info:
            mock_resolver.resolve_board("Dev")

        assert "Multiple boards match" in str(exc_info.value)
        assert "Development" in str(exc_info.value)
        assert "Dev/Backend" in str(exc_info.value)

    def test_resolve_board_not_found(self, mock_resolver: Resolver) -> None:
        """Test that non-existent board raises an error."""
        with pytest.raises(ValueError) as exc_info:
            mock_resolver.resolve_board("NonExistent")

        assert "Board not found" in str(exc_info.value)

    def test_resolve_list_by_id(self, mock_resolver: Resolver) -> None:
        """Test resolving a list by its full ID."""
        list_id = mock_resolver.resolve_list("Development", "507f191e810c19729de860ea")
        assert list_id == "507f191e810c19729de860ea"

    def test_resolve_list_by_exact_name(self, mock_resolver: Resolver) -> None:
        """Test resolving a list by exact name match."""
        list_id = mock_resolver.resolve_list("Development", "To Do")
        assert list_id == "507f191e810c19729de860ea"

    def test_resolve_list_by_name_case_insensitive(
        self, mock_resolver: Resolver
    ) -> None:
        """Test resolving a list by name is case-insensitive."""
        list_id = mock_resolver.resolve_list("Development", "to do")
        assert list_id == "507f191e810c19729de860ea"

    def test_resolve_list_by_partial_name(self, mock_resolver: Resolver) -> None:
        """Test resolving a list by partial name match."""
        list_id = mock_resolver.resolve_list("Development", "Doing")
        assert list_id == "507f191e810c19729de860eb"

    def test_resolve_list_partial_match_ambiguous(
        self, mock_resolver: Resolver
    ) -> None:
        """Test that ambiguous partial matches raise an error."""
        # "Do" matches both "To Do", "Doing", and "Done"
        with pytest.raises(ValueError) as exc_info:
            mock_resolver.resolve_list("Development", "Do")

        assert "Multiple lists match" in str(exc_info.value)

    def test_resolve_list_not_found(self, mock_resolver: Resolver) -> None:
        """Test that non-existent list raises an error."""
        with pytest.raises(ValueError) as exc_info:
            mock_resolver.resolve_list("Development", "NonExistent")

        assert "List not found" in str(exc_info.value)

    def test_resolve_card_by_id(
        self, mock_resolver: Resolver, mock_cards: list[dict], mocker: Any
    ) -> None:
        """Test resolving a card by its full ID."""
        mocker.patch.object(
            mock_resolver.client, "get_list_cards", return_value=mock_cards
        )

        card_id = mock_resolver.resolve_card(
            "Development", "To Do", "60d5ec49f1a4a23456789abc"
        )
        assert card_id == "60d5ec49f1a4a23456789abc"

    def test_resolve_card_by_exact_name(
        self, mock_resolver: Resolver, mock_cards: list[dict], mocker: Any
    ) -> None:
        """Test resolving a card by exact name match."""
        mocker.patch.object(
            mock_resolver.client, "get_list_cards", return_value=mock_cards
        )

        card_id = mock_resolver.resolve_card(
            "Development", "To Do", "Implement feature X"
        )
        assert card_id == "60d5ec49f1a4a23456789abc"

    def test_resolve_card_by_partial_name(
        self, mock_resolver: Resolver, mock_cards: list[dict], mocker: Any
    ) -> None:
        """Test resolving a card by partial name match."""
        mocker.patch.object(
            mock_resolver.client, "get_list_cards", return_value=mock_cards
        )

        card_id = mock_resolver.resolve_card("Development", "To Do", "bug Y")
        assert card_id == "60d5ec49f1a4a23456789def"

    def test_resolve_card_not_found(
        self, mock_resolver: Resolver, mock_cards: list[dict], mocker: Any
    ) -> None:
        """Test that non-existent card raises an error."""
        mocker.patch.object(
            mock_resolver.client, "get_list_cards", return_value=mock_cards
        )

        with pytest.raises(ValueError) as exc_info:
            mock_resolver.resolve_card("Development", "To Do", "NonExistent")

        assert "Card not found" in str(exc_info.value)

    def test_boards_cache(
        self, mock_resolver: Resolver, mock_boards: list[dict], mocker: Any
    ) -> None:
        """Test that boards are cached after first fetch."""
        # Clear the cache
        mock_resolver._boards_cache = None

        mock_get_boards = mocker.patch.object(
            mock_resolver.client, "get_boards", return_value=mock_boards
        )

        # First call should fetch
        mock_resolver.resolve_board("Development")
        assert mock_get_boards.call_count == 1

        # Second call should use cache
        mock_resolver.resolve_board("Marketing")
        assert mock_get_boards.call_count == 1

    def test_lists_cache(
        self, mock_resolver: Resolver, mock_lists: list[dict], mocker: Any
    ) -> None:
        """Test that lists are cached per board."""
        # Clear the cache
        mock_resolver._lists_cache = {}

        mock_get_board_lists = mocker.patch.object(
            mock_resolver.client, "get_board_lists", return_value=mock_lists
        )

        # First call should fetch
        mock_resolver.resolve_list("507f1f77bcf86cd799439011", "To Do")
        assert mock_get_board_lists.call_count == 1

        # Second call for same board should use cache
        mock_resolver.resolve_list("507f1f77bcf86cd799439011", "Doing")
        assert mock_get_board_lists.call_count == 1
