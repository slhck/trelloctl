"""Exercise search pagination and card filters through the CLI and HTTP layer."""

import json
from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest
from click.testing import CliRunner

from trelloctl.cli import main
from trelloctl.client import TrelloClient

BOARD = "507f1f77bcf86cd799439011"
MEMBER = "507f1f77bcf86cd799439022"
LABEL = "507f1f77bcf86cd799439033"


@pytest.fixture
def api(mocker) -> Iterator[tuple[list[httpx.Request], dict]]:
    """Serve deterministic search pages and board cards over mock HTTP."""
    requests: list[httpx.Request] = []
    state: dict[str, Any] = {"pages": [[]], "cards": [], "status": 200}

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/1/search":
            page = int(request.url.params["cards_page"])
            pages = state["pages"]
            data = {"cards": pages[page] if page < len(pages) else []}
        elif request.url.path == "/1/members/me":
            data = {"id": MEMBER}
        elif request.url.path.endswith("/members"):
            data = [{"id": MEMBER, "username": "werner", "fullName": "Werner"}]
        elif request.url.path.endswith("/labels"):
            data = [{"id": LABEL, "name": "Urgent", "color": "red"}]
        else:
            data = state["cards"]
        return httpx.Response(state["status"], json=data)

    config = MagicMock()
    config.get_api_key.return_value = "secret-key"
    config.get_token.return_value = "secret-token"
    mocker.patch("trelloctl.cli.Config", return_value=config)
    client = TrelloClient("secret-key", "secret-token")
    client._client.close()
    with httpx.Client(transport=httpx.MockTransport(respond)) as transport:
        client._client = transport
        mocker.patch("trelloctl.cli.TrelloClient", return_value=client)
        yield requests, state


def card(identifier="task", **fields):
    """Build raw API card data."""
    return {"id": identifier, "name": identifier, "idBoard": BOARD, **fields}


def invoke(*args):
    """Invoke the registered production CLI using JSON output."""
    return CliRunner().invoke(main, ["--format", "json", *args])


def test_search_query_and_board_scope(api):
    requests, state = api
    state["pages"] = [[card()]]
    result = invoke("search", "is:open report", "--board", BOARD, "--partial")
    assert result.exit_code == 0, result.output
    assert [item["id"] for item in json.loads(result.stdout)] == ["task"]
    assert requests[0].url.path == "/1/search"
    params = requests[0].url.params
    assert params["query"] == "is:open report"
    assert params["idBoards"] == BOARD
    assert params["modelTypes"] == "cards"
    assert params["card_fields"] == "all"
    assert params["partial"] == "true"
    assert params["cards_page"] == "0"


def test_search_pages_until_enough_matching_cards(api):
    requests, state = api
    state["pages"] = [
        [card(str(i), dueComplete=True) for i in range(100)],
        [card("wanted"), card("also"), card("extra")],
    ]
    result = invoke("search", "report", "--incomplete", "--limit", "2")
    assert result.exit_code == 0, result.output
    assert [item["id"] for item in json.loads(result.stdout)] == ["wanted", "also"]
    assert [req.url.params["cards_page"] for req in requests] == ["0", "1"]


def test_search_all_deduplicates_across_pages(api):
    requests, state = api
    state["pages"] = [
        [card(str(i)) for i in range(100)],
        [card("99"), card("last")],
    ]
    result = invoke("search", "report", "--all", "--limit", "1")
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert len(data) == 101
    assert data[-1]["id"] == "last"
    assert len(requests) == 2


def test_search_warns_when_api_page_cap_is_reached(api, mocker):
    _, state = api
    mocker.patch("trelloctl.commands.search.MAX_PAGE", 1)
    state["pages"] = [
        [card(str(i)) for i in range(100)],
        [card(str(i + 100)) for i in range(100)],
    ]
    result = invoke("search", "report", "--all")
    assert result.exit_code == 0, result.output
    assert len(json.loads(result.stdout)) == 200
    assert "results may be incomplete" in " ".join(result.stderr.split())


@pytest.mark.parametrize("source", ["search", "board"])
def test_combines_member_label_overdue_and_completion(api, source):
    requests, state = api
    cards = [
        card("match", due="2000-01-01T10:00:00Z", idMembers=[MEMBER], idLabels=[LABEL]),
        card(
            "complete",
            due="2000-01-01",
            dueComplete=True,
            idMembers=[MEMBER],
            idLabels=[LABEL],
        ),
        card("future", due="2999-01-01", idMembers=[MEMBER], idLabels=[LABEL]),
        card("unassigned", due="2000-01-01", idLabels=[LABEL]),
        card("unlabelled", due="2000-01-01", idMembers=[MEMBER]),
        card("undated", idMembers=[MEMBER], idLabels=[LABEL]),
    ]
    state["pages"] = [cards]
    state["cards"] = cards
    command = ["search", "report"] if source == "search" else ["board", "cards", BOARD]
    result = invoke(
        *command,
        "--member",
        "me",
        "--label",
        "Urgent",
        "--overdue",
        "--incomplete",
        "--due-before",
        "2001-01-01",
    )
    assert result.exit_code == 0, result.output
    assert [item["id"] for item in json.loads(result.stdout)] == ["match"]
    assert len([req for req in requests if req.url.path == "/1/members/me"]) == 1
    assert len([req for req in requests if req.url.path.endswith("/labels")]) == 1


def test_board_member_name_and_strict_due_boundary(api):
    _, state = api
    state["cards"] = [
        card("before", idMembers=[MEMBER], due="2026-12-01T00:59:59+01:00"),
        card("boundary", idMembers=[MEMBER], due="2026-12-01T01:00:00+01:00"),
    ]
    result = invoke(
        "board", "cards", BOARD, "--member", "werner", "--due-before", "2026-12-01"
    )
    assert result.exit_code == 0, result.output
    assert [item["id"] for item in json.loads(result.stdout)] == ["before"]


@pytest.mark.parametrize("source", ["search", "board"])
def test_bad_date_fails_before_request(api, source):
    requests, _ = api
    command = ["search", "report"] if source == "search" else ["board", "cards", BOARD]
    result = invoke(*command, "--due-before", "next tuesday")
    assert result.exit_code == 2
    assert result.stdout == ""
    assert "--due-before" in result.stderr
    assert requests == []


def test_search_failure_has_no_partial_stdout_or_credentials(api):
    _, state = api
    state["status"] = 403
    result = invoke("search", "report")
    assert result.exit_code == 1
    assert result.stdout == ""
    assert "HTTP 403" in " ".join(result.stderr.split())
    assert "secret-key" not in result.output
    assert "secret-token" not in result.output


def test_search_empty_query(api):
    requests, _ = api
    result = invoke("search", " ")
    assert result.exit_code == 2
    assert result.stdout == ""
    assert requests == []


def test_search_archive_filter(api):
    _, state = api
    state["pages"] = [[card("open"), card("closed", closed=True)]]
    result = invoke("search", "report", "--filter", "closed")
    assert result.exit_code == 0, result.output
    assert [item["id"] for item in json.loads(result.stdout)] == ["closed"]


def test_board_rejects_missing_label(api):
    _, state = api
    state["cards"] = [card()]
    result = invoke("board", "cards", BOARD, "--label", "missing")
    assert result.exit_code == 1
    assert result.stdout == ""
    assert "Label not found" in result.stderr


def test_search_missing_labels_on_other_boards_are_nonmatches(api, mocker):
    _, state = api
    other_board = "507f1f77bcf86cd799439044"
    state["pages"] = [
        [card("first", idLabels=[LABEL]), card("other", idBoard=other_board)]
    ]
    resolve = mocker.patch(
        "trelloctl.resolver.Resolver.resolve_label",
        side_effect=[LABEL, ValueError("Label not found: Urgent")],
    )
    result = invoke("search", "report", "--label", "Urgent")
    assert result.exit_code == 0, result.output
    assert [item["id"] for item in json.loads(result.stdout)] == ["first"]
    assert resolve.call_count == 2


def test_ambiguous_search_label_fails_without_partial_output(api, mocker):
    _, state = api
    state["pages"] = [[card("task", idLabels=[LABEL])]]
    mocker.patch(
        "trelloctl.resolver.Resolver.resolve_label",
        side_effect=ValueError("Multiple labels match 'Urg': Urgent, Urgency"),
    )
    result = invoke("search", "report", "--label", "Urg")
    assert result.exit_code == 1
    assert result.stdout == ""
    assert "Multiple labels match" in result.stderr
