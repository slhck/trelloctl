"""Shared test fixtures."""

from __future__ import annotations

from typing import Any

import pytest

from trelloctl.client import TrelloClient
from trelloctl.resolver import Resolver


@pytest.fixture
def mock_boards() -> list[dict[str, Any]]:
    """Sample board data."""
    return [
        {
            "id": "507f1f77bcf86cd799439011",  # 24 hex chars
            "name": "Development",
            "desc": "Development board",
            "url": "https://trello.com/b/abc123/development",
            "closed": False,
        },
        {
            "id": "507f1f77bcf86cd799439022",
            "name": "Marketing",
            "desc": "Marketing board",
            "url": "https://trello.com/b/def456/marketing",
            "closed": False,
        },
        {
            "id": "507f1f77bcf86cd799439033",
            "name": "Dev/Backend",
            "desc": "Backend development",
            "url": "https://trello.com/b/ghi789/dev-backend",
            "closed": False,
        },
    ]


@pytest.fixture
def mock_lists() -> list[dict[str, Any]]:
    """Sample list data."""
    return [
        {
            "id": "507f191e810c19729de860ea",  # 24 hex chars
            "name": "To Do",
            "idBoard": "507f1f77bcf86cd799439011",
            "closed": False,
        },
        {
            "id": "507f191e810c19729de860eb",
            "name": "Doing",
            "idBoard": "507f1f77bcf86cd799439011",
            "closed": False,
        },
        {
            "id": "507f191e810c19729de860ec",
            "name": "Done",
            "idBoard": "507f1f77bcf86cd799439011",
            "closed": False,
        },
    ]


@pytest.fixture
def mock_cards() -> list[dict[str, Any]]:
    """Sample card data."""
    return [
        {
            "id": "60d5ec49f1a4a23456789abc",  # 24 hex chars
            "name": "Implement feature X",
            "desc": "Description of feature X",
            "idList": "507f191e810c19729de860ea",
            "due": "2025-03-01T12:00:00.000Z",
            "closed": False,
            "labels": [{"id": "label1", "name": "Bug", "color": "red"}],
            "url": "https://trello.com/c/abc123",
        },
        {
            "id": "60d5ec49f1a4a23456789def",
            "name": "Fix bug Y",
            "desc": "Bug description",
            "idList": "507f191e810c19729de860ea",
            "due": None,
            "closed": False,
            "labels": [],
            "url": "https://trello.com/c/def456",
        },
    ]


@pytest.fixture
def mock_labels() -> list[dict[str, Any]]:
    """Sample label data."""
    return [
        {"id": "label1", "name": "Bug", "color": "red"},
        {"id": "label2", "name": "Feature", "color": "green"},
        {"id": "label3", "name": "Urgent", "color": "orange"},
    ]


@pytest.fixture
def mock_members() -> list[dict[str, Any]]:
    """Sample member data."""
    return [
        {"id": "member1", "username": "johndoe", "fullName": "John Doe"},
        {"id": "member2", "username": "janedoe", "fullName": "Jane Doe"},
    ]


@pytest.fixture
def mock_client(mocker: Any) -> TrelloClient:
    """Create a mock Trello client."""
    client = TrelloClient(api_key="test_key", token="test_token")
    mocker.patch.object(client, "_client")
    return client


@pytest.fixture
def mock_resolver(
    mock_client: TrelloClient, mock_boards: list[dict], mock_lists: list[dict]
) -> Resolver:
    """Create a resolver with mocked client."""
    resolver = Resolver(mock_client)
    resolver._boards_cache = mock_boards
    resolver._lists_cache = {"507f1f77bcf86cd799439011": mock_lists}
    return resolver
