"""Exercise card workflows through the CLI and HTTP request layer."""

import csv
import io
import json
from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest
from click.testing import CliRunner

from trelloctl.cli import main
from trelloctl.client import TrelloClient


@pytest.fixture
def api(mocker) -> Iterator[tuple[list[httpx.Request], dict]]:
    """Provide a real API client with a configurable in-memory HTTP response."""
    requests: list[httpx.Request] = []
    response: dict[str, Any] = {"status": 200, "data": {"id": "card1", "name": "Task"}}

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(response["status"], json=response["data"])

    config = MagicMock()
    config.get_api_key.return_value = "test-key"
    config.get_token.return_value = "test-token"
    mocker.patch("trelloctl.cli.Config", return_value=config)
    client = TrelloClient("test-key", "test-token")
    client._client.close()
    with httpx.Client(transport=httpx.MockTransport(respond)) as transport:
        client._client = transport
        mocker.patch("trelloctl.cli.TrelloClient", return_value=client)
        yield requests, response


@pytest.mark.parametrize("undo", [False, True])
@pytest.mark.parametrize("output_format", ["table", "json", "csv", "plain"])
def test_complete_card(api, undo, output_format):
    """Completion uses a JSON boolean and works without a due date."""
    requests, response = api
    response["data"] = {
        "id": "card1",
        "name": "Task",
        "due": None,
        "dueComplete": not undo,
        "closed": False,
    }
    result = CliRunner().invoke(
        main,
        ["--format", output_format, "card", "complete", "card1"]
        + (["--undo"] if undo else []),
    )
    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    assert len(requests) == 1
    assert requests[0].method == "PUT"
    assert requests[0].url.path == "/1/cards/card1"
    assert json.loads(requests[0].content) == {"dueComplete": not undo}
    if output_format == "json":
        data = json.loads(result.stdout)
        assert data["due_complete"] is not undo
        assert data["closed"] == "No"
    elif output_format == "plain":
        assert result.stdout == "card1\n"
    elif output_format == "csv":
        data = next(csv.DictReader(io.StringIO(result.stdout)))
        assert data["due_complete"] == str(not undo)
    else:
        assert ("incomplete" if undo else "complete") in result.stdout


@pytest.mark.parametrize("command,method", [("label", "POST"), ("unlabel", "DELETE")])
def test_card_labels(api, command, method):
    """Labels use the dedicated endpoints without replacing other labels."""
    requests, response = api
    response["data"] = ["label1"] if command == "label" else None
    result = CliRunner().invoke(
        main, ["--format", "json", "card", command, "card1", "label1"]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {"id": "card1", "label_id": "label1"}
    assert requests[0].method == method
    if command == "label":
        assert requests[0].url.path == "/1/cards/card1/idLabels"
        assert requests[0].url.params["value"] == "label1"
    else:
        assert requests[0].url.path == "/1/cards/card1/idLabels/label1"


@pytest.mark.parametrize(
    "options,expected",
    [([], ["a", "b"]), (["--complete"], ["a"]), (["--incomplete"], ["b"])],
)
@pytest.mark.parametrize("archive_filter", ["open", "closed", "all"])
def test_board_cards(api, options, expected, archive_filter):
    """Archive and completion filters are independent; missing flags mean incomplete."""
    requests, response = api
    response["data"] = [
        {"id": "a", "name": "Done", "dueComplete": True},
        {"id": "b", "name": "Pending"},
    ]
    board_id = "507f1f77bcf86cd799439011"
    result = CliRunner().invoke(
        main,
        [
            "--format",
            "json",
            "board",
            "cards",
            board_id,
            "--filter",
            archive_filter,
            *options,
        ],
    )
    assert result.exit_code == 0, result.output
    assert [c["id"] for c in json.loads(result.stdout)] == expected
    assert requests[0].url.path == f"/1/boards/{board_id}/cards/{archive_filter}"


def test_board_cards_resolves_name(api, mocker):
    """Board names use the shared resolver."""
    _, response = api
    response["data"] = []
    resolve = mocker.patch(
        "trelloctl.resolver.Resolver.resolve_board", return_value="b1"
    )
    result = CliRunner().invoke(main, ["--format", "json", "board", "cards", "Dev"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == []
    resolve.assert_called_once_with("Dev")


@pytest.mark.parametrize("complete", [True, False])
@pytest.mark.parametrize("command", ["show", "list"])
def test_completion_visible(api, command, complete):
    """Card details and list cards expose a boolean completion state in JSON."""
    _, response = api
    card = {"id": "card1", "name": "Task", "dueComplete": complete}
    if command == "show":
        response["data"] = card
        args = ["card", "show", "card1"]
    else:
        response["data"] = [card]
        args = [
            "list",
            "cards",
            "507f191e810c19729de860ea",
            "-b",
            "507f1f77bcf86cd799439011",
        ]
    result = CliRunner().invoke(main, ["--format", "json", *args])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert (data if command == "show" else data[0])["due_complete"] is complete


@pytest.mark.parametrize(
    "command",
    [
        ["card", "complete", "card1"],
        ["card", "label", "card1", "label1"],
        ["card", "unlabel", "card1", "label1"],
        ["board", "cards", "507f1f77bcf86cd799439011"],
    ],
)
def test_workflow_error(api, command):
    """API failures produce only stderr and a non-zero exit code."""
    _, response = api
    response["status"] = 403
    result = CliRunner().invoke(main, ["--format", "json", *command])
    assert result.exit_code == 1
    assert result.stdout == ""
    assert "HTTP 403" in " ".join(result.stderr.split())
    assert "test-key" not in result.stderr
    assert "test-token" not in result.stderr
