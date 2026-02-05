"""Tests for the Trello API client."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest

from trelloctl.client import TrelloClient


class TestTrelloClient:
    """Tests for TrelloClient."""

    def test_auth_params(self) -> None:
        """Test that auth params are correctly generated."""
        client = TrelloClient(api_key="my_key", token="my_token")
        params = client._auth_params()
        assert params == {"key": "my_key", "token": "my_token"}

    def test_get_boards(self, mocker: Any, mock_boards: list[dict]) -> None:
        """Test getting boards."""
        client = TrelloClient(api_key="test_key", token="test_token")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_boards

        mock_request = mocker.patch.object(
            client._client, "request", return_value=mock_response
        )

        boards = client.get_boards()

        assert len(boards) == 3
        assert boards[0]["name"] == "Development"
        mock_request.assert_called_once()

    def test_get_board(self, mocker: Any, mock_boards: list[dict]) -> None:
        """Test getting a single board."""
        client = TrelloClient(api_key="test_key", token="test_token")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_boards[0]

        mocker.patch.object(client._client, "request", return_value=mock_response)

        board = client.get_board("board1234567890abcdef12")

        assert board["name"] == "Development"

    def test_create_board(self, mocker: Any) -> None:
        """Test creating a board."""
        client = TrelloClient(api_key="test_key", token="test_token")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "newboard123456789012345",
            "name": "New Board",
            "desc": "A new board",
        }

        mocker.patch.object(client._client, "request", return_value=mock_response)

        board = client.create_board("New Board", "A new board")

        assert board["name"] == "New Board"

    def test_get_board_lists(self, mocker: Any, mock_lists: list[dict]) -> None:
        """Test getting lists for a board."""
        client = TrelloClient(api_key="test_key", token="test_token")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_lists

        mocker.patch.object(client._client, "request", return_value=mock_response)

        lists = client.get_board_lists("board1234567890abcdef12")

        assert len(lists) == 3
        assert lists[0]["name"] == "To Do"

    def test_create_card(self, mocker: Any) -> None:
        """Test creating a card."""
        client = TrelloClient(api_key="test_key", token="test_token")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "newcard12345678901234567",
            "name": "New Card",
            "desc": "Card description",
        }

        mocker.patch.object(client._client, "request", return_value=mock_response)

        card = client.create_card(
            list_id="list12345678901234567890",
            name="New Card",
            desc="Card description",
        )

        assert card["name"] == "New Card"

    def test_move_card(self, mocker: Any) -> None:
        """Test moving a card."""
        client = TrelloClient(api_key="test_key", token="test_token")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "card12345678901234567890",
            "idList": "list34567890123456789012",
        }

        mocker.patch.object(client._client, "request", return_value=mock_response)

        card = client.move_card("card12345678901234567890", "list34567890123456789012")

        assert card["idList"] == "list34567890123456789012"

    def test_delete_card(self, mocker: Any) -> None:
        """Test deleting a card."""
        client = TrelloClient(api_key="test_key", token="test_token")

        mock_response = MagicMock()
        mock_response.status_code = 204

        mock_request = mocker.patch.object(
            client._client, "request", return_value=mock_response
        )

        client.delete_card("card12345678901234567890")

        mock_request.assert_called_once()

    def test_get_board_labels(self, mocker: Any, mock_labels: list[dict]) -> None:
        """Test getting labels for a board."""
        client = TrelloClient(api_key="test_key", token="test_token")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_labels

        mocker.patch.object(client._client, "request", return_value=mock_response)

        labels = client.get_board_labels("board1234567890abcdef12")

        assert len(labels) == 3
        assert labels[0]["name"] == "Bug"

    def test_get_board_members(self, mocker: Any, mock_members: list[dict]) -> None:
        """Test getting members for a board."""
        client = TrelloClient(api_key="test_key", token="test_token")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_members

        mocker.patch.object(client._client, "request", return_value=mock_response)

        members = client.get_board_members("board1234567890abcdef12")

        assert len(members) == 2
        assert members[0]["username"] == "johndoe"

    def test_add_card_comment(self, mocker: Any) -> None:
        """Test adding a comment to a card."""
        client = TrelloClient(api_key="test_key", token="test_token")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "comment123",
            "data": {"text": "Test comment"},
        }

        mocker.patch.object(client._client, "request", return_value=mock_response)

        comment = client.add_card_comment("card12345678901234567890", "Test comment")

        assert comment["data"]["text"] == "Test comment"

    def test_get_card_checklists(self, mocker: Any) -> None:
        """Test getting checklists for a card."""
        client = TrelloClient(api_key="test_key", token="test_token")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "checklist12345678901234",
                "name": "Tasks",
                "checkItems": [
                    {"id": "item1", "name": "Item 1", "state": "incomplete"},
                ],
            }
        ]

        mocker.patch.object(client._client, "request", return_value=mock_response)

        checklists = client.get_card_checklists("card12345678901234567890")

        assert len(checklists) == 1
        assert checklists[0]["name"] == "Tasks"

    def test_create_checklist(self, mocker: Any) -> None:
        """Test creating a checklist on a card."""
        client = TrelloClient(api_key="test_key", token="test_token")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "checklist12345678901234",
            "name": "My Checklist",
        }

        mocker.patch.object(client._client, "request", return_value=mock_response)

        cl = client.create_checklist("card12345678901234567890", "My Checklist")

        assert cl["name"] == "My Checklist"

    def test_delete_checklist(self, mocker: Any) -> None:
        """Test deleting a checklist."""
        client = TrelloClient(api_key="test_key", token="test_token")

        mock_response = MagicMock()
        mock_response.status_code = 204

        mock_request = mocker.patch.object(
            client._client, "request", return_value=mock_response
        )

        client.delete_checklist("checklist12345678901234")

        mock_request.assert_called_once()

    def test_add_checklist_item(self, mocker: Any) -> None:
        """Test adding an item to a checklist."""
        client = TrelloClient(api_key="test_key", token="test_token")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "item123",
            "name": "New Item",
            "state": "incomplete",
        }

        mocker.patch.object(client._client, "request", return_value=mock_response)

        item = client.add_checklist_item("checklist12345678901234", "New Item")

        assert item["name"] == "New Item"

    def test_update_checklist_item(self, mocker: Any) -> None:
        """Test updating a checklist item state."""
        client = TrelloClient(api_key="test_key", token="test_token")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "item123",
            "state": "complete",
        }

        mocker.patch.object(client._client, "request", return_value=mock_response)

        item = client.update_checklist_item(
            "card12345678901234567890", "item123", "complete"
        )

        assert item["state"] == "complete"

    def test_delete_checklist_item(self, mocker: Any) -> None:
        """Test deleting a checklist item."""
        client = TrelloClient(api_key="test_key", token="test_token")

        mock_response = MagicMock()
        mock_response.status_code = 204

        mock_request = mocker.patch.object(
            client._client, "request", return_value=mock_response
        )

        client.delete_checklist_item("checklist12345678901234", "item123")

        mock_request.assert_called_once()

    def test_request_raises_on_error(self, mocker: Any) -> None:
        """Test that HTTP errors are raised."""
        client = TrelloClient(api_key="test_key", token="test_token")

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )

        mocker.patch.object(client._client, "request", return_value=mock_response)

        with pytest.raises(httpx.HTTPStatusError):
            client.get_boards()
