"""Attachment transfer, label CRUD, and typed custom field workflows."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest
from click.testing import CliRunner

from trelloctl.cli import main
from trelloctl.client import TrelloClient
from trelloctl.commands.field import field_payload, resolve_field

CARD = "60d5ec49f1a4a23456789abc"
BOARD = "507f1f77bcf86cd799439011"
ATTACHMENT = "60d5ec49f1a4a23456789def"


@pytest.fixture
def command_client(mocker):
    """Configure a CLI client without accessing credentials or live Trello."""
    client = MagicMock()
    client.get_card.return_value = {"id": CARD, "idBoard": BOARD}
    mocker.patch("trelloctl.cli.Config").return_value = MagicMock()
    mocker.patch("trelloctl.cli.TrelloClient", return_value=client)
    return client


def invoke(*args, **kwargs):
    """Invoke a resource command with machine-readable output."""
    return CliRunner().invoke(main, ["--format", "json", *args], **kwargs)


def test_attachment_sources_are_exclusive(command_client, tmp_path):
    """Reject conflicting sources before performing any writes."""
    source = tmp_path / "input.txt"
    source.write_text("hello")
    result = invoke(
        "attachment", "add", CARD, "--file", str(source), "--url", "https://example.org"
    )
    assert result.exit_code == 2
    command_client.add_attachment.assert_not_called()


def test_attachment_upload_http(tmp_path):
    """Upload uses multipart file data, not a path string in JSON."""
    source = tmp_path / "report.txt"
    source.write_text("contents from disk")

    def respond(request):
        assert request.method == "POST"
        assert request.url.path == f"/1/cards/{CARD}/attachments"
        assert request.url.params["name"] == "Report"
        assert "multipart/form-data" in request.headers["content-type"]
        assert b'filename="report.txt"' in request.content
        assert b"contents from disk" in request.content
        return httpx.Response(200, json={"id": ATTACHMENT})

    client = TrelloClient("key", "token")
    with httpx.Client(transport=httpx.MockTransport(respond)) as transport:
        client._client.close()
        client._client = transport
        assert (
            client.add_attachment(CARD, file=source, name="Report")["id"] == ATTACHMENT
        )


def test_attachment_url_add(command_client):
    command_client.add_attachment.return_value = {
        "id": ATTACHMENT,
        "url": "https://example.org/report",
    }
    result = invoke("attachment", "add", CARD, "--url", "https://example.org/report")
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["id"] == ATTACHMENT
    command_client.add_attachment.assert_called_once_with(
        CARD, file=None, url="https://example.org/report", name=None
    )


def test_attachment_download_auth_redirect_and_no_overwrite(tmp_path):
    """Authenticate only to Trello, and never overwrite an existing file by default."""
    calls = []

    def respond(request):
        calls.append(request)
        if request.url.host == "api.trello.com":
            assert (
                request.headers["authorization"]
                == 'OAuth oauth_consumer_key="key", oauth_token="token"'
            )
            assert not request.url.query
            return httpx.Response(
                302, headers={"location": "https://storage.example.org/signed"}
            )
        assert "authorization" not in request.headers
        return httpx.Response(200, content=b"binary\x00data")

    client = TrelloClient("key", "token")
    target = tmp_path / "result.bin"
    attachment = {"id": ATTACHMENT, "name": "data.bin", "isUpload": True}
    with httpx.Client(transport=httpx.MockTransport(respond)) as transport:
        client._client.close()
        client._client = transport
        client.download_attachment(CARD, attachment, target)
        assert target.read_bytes() == b"binary\x00data"
        with pytest.raises(ValueError, match="already exists"):
            client.download_attachment(CARD, attachment, target)
        assert len(calls) == 2
        client.download_attachment(CARD, attachment, target, force=True)
    assert list(tmp_path.iterdir()) == [target]


def test_external_attachment_download_never_sends_credentials(tmp_path):
    def respond(request):
        assert "authorization" not in request.headers
        assert "key" not in request.url.params
        assert "token" not in request.url.params
        return httpx.Response(200, content=b"external")

    client = TrelloClient("secret_key", "secret_token")
    with httpx.Client(transport=httpx.MockTransport(respond)) as transport:
        client._client.close()
        client._client = transport
        client.download_attachment(
            CARD,
            {"isUpload": False, "url": "https://example.org/file"},
            tmp_path / "file",
        )
    assert (tmp_path / "file").read_bytes() == b"external"


def test_download_failure_leaves_no_partial_file(tmp_path):
    class BrokenStream(httpx.SyncByteStream):
        def __iter__(self):
            yield b"partial"
            raise httpx.ReadError("url?token=secret")

    client = TrelloClient("secret", "secret")
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, stream=BrokenStream())
        )
    ) as transport:
        client._client.close()
        client._client = transport
        with pytest.raises(ValueError, match="ReadError") as error:
            client.download_attachment(
                CARD,
                {"isUpload": True, "id": ATTACHMENT, "name": "x"},
                tmp_path / "target",
            )
    assert "secret" not in str(error.value)
    assert list(tmp_path.iterdir()) == []


def test_download_sanitizes_default_filename(command_client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    command_client.get_attachment.return_value = {
        "id": ATTACHMENT,
        "name": "../../report.txt",
    }
    result = invoke("attachment", "download", CARD, ATTACHMENT)
    assert result.exit_code == 0, result.output
    command_client.download_attachment.assert_called_once_with(
        CARD,
        command_client.get_attachment.return_value,
        Path("report.txt"),
        force=False,
    )
    assert json.loads(result.output)["path"] == str(tmp_path / "report.txt")


def test_attachment_delete_contract(command_client):
    result = invoke("attachment", "delete", CARD, ATTACHMENT, "--yes")
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["id"] == ATTACHMENT
    command_client.delete_attachment.assert_called_once_with(CARD, ATTACHMENT)


def test_label_create_and_clear_color(command_client):
    command_client.create_label.return_value = {
        "id": ATTACHMENT,
        "name": "Bug",
        "color": None,
    }
    result = invoke("label", "create", BOARD, "--name", "Bug")
    assert result.exit_code == 0, result.output
    command_client.create_label.assert_called_once_with(BOARD, "Bug", None)
    command_client.update_label.return_value = {"id": ATTACHMENT, "color": None}
    result = invoke("label", "update", ATTACHMENT, "--color", "none")
    assert result.exit_code == 0, result.output
    command_client.update_label.assert_called_once_with(ATTACHMENT, color=None)


def test_label_update_requires_change(command_client):
    assert invoke("label", "update", ATTACHMENT).exit_code == 2
    command_client.update_label.assert_not_called()


@pytest.mark.parametrize(
    "kind,value,payload",
    [
        ("text", "null", {"value": {"text": "null"}}),
        ("number", "12.50", {"value": {"number": "12.50"}}),
        ("checkbox", "FALSE", {"value": {"checked": "false"}}),
        ("date", "2026-11-27", {"value": {"date": "2026-11-27T00:00:00+00:00"}}),
    ],
)
def test_typed_field_payloads(kind, value, payload):
    assert field_payload({"type": kind}, value) == payload


@pytest.mark.parametrize(
    "kind,value",
    [("number", "NaN"), ("number", "no"), ("checkbox", "yes"), ("date", "yesterday")],
)
def test_field_payload_validation(kind, value):
    with pytest.raises(ValueError):
        field_payload({"type": kind}, value)


def test_dropdown_matches_exact_option_and_rejects_ambiguity():
    definition = {
        "type": "list",
        "options": [
            {"id": "high", "value": {"text": "High"}},
            {"id": "low", "value": {"text": "Low"}},
        ],
    }
    assert field_payload(definition, "HIGH") == {"idValue": "high"}
    with pytest.raises(ValueError):
        field_payload(definition, "H")
    with pytest.raises(ValueError):
        resolve_field(
            [{"id": "1", "name": "Effort"}, {"id": "2", "name": "Effort"}], "Effort"
        )


def test_field_set_clear_and_values(command_client):
    command_client.get_custom_fields.return_value = [
        {"id": "field1", "name": "Estimate", "type": "number"},
        {"id": "field2", "name": "Approved", "type": "checkbox"},
        {"id": "field3", "name": "Summary", "type": "text"},
    ]
    result = invoke("field", "set", CARD, "Estimate", "3.5")
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["id"] == CARD
    command_client.set_custom_field.assert_called_with(
        CARD, "field1", {"value": {"number": "3.5"}}
    )
    result = invoke("field", "clear", CARD, "Estimate")
    assert result.exit_code == 0, result.output
    command_client.set_custom_field.assert_called_with(
        CARD, "field1", {"idValue": "", "value": ""}
    )
    command_client.get_custom_field_items.return_value = [
        {"idCustomField": "field1", "value": {"number": "3.5"}},
        {"idCustomField": "field2", "value": {"checked": "false"}},
    ]
    result = invoke("field", "values", CARD)
    assert result.exit_code == 0, result.output
    assert [item["value"] for item in json.loads(result.output)] == ["3.5", False, None]


def test_resource_api_payloads_and_error_redaction(tmp_path):
    """Clear fields with empty values; sanitize authenticated upload failures."""
    source = tmp_path / "secret.txt"
    source.write_text("document")
    calls = []

    def respond(request):
        calls.append(request)
        if request.url.path.endswith("/attachments"):
            return httpx.Response(403)
        if "/customField/" in request.url.path:
            assert json.loads(request.content) == {"idValue": "", "value": ""}
            return httpx.Response(200, json={})
        assert request.url.path == "/1/labels"
        assert json.loads(request.content) == {
            "idBoard": BOARD,
            "name": "Bug",
            "color": None,
        }
        return httpx.Response(200, json={"id": ATTACHMENT})

    client = TrelloClient("secret_key", "secret_token")
    with httpx.Client(transport=httpx.MockTransport(respond)) as transport:
        client._client.close()
        client._client = transport
        assert (
            client.set_custom_field(CARD, "field", {"idValue": "", "value": ""}) == {}
        )
        assert client.create_label(BOARD, "Bug", None)["id"] == ATTACHMENT
        with pytest.raises(httpx.HTTPStatusError) as error:
            client.add_attachment(CARD, file=source)
    assert "secret_key" not in str(error.value)
    assert "secret_token" not in str(error.value)
    assert len(calls) == 3


def test_board_labels_request_exceeds_default_fifty():
    """Request the API maximum so names beyond the first 50 can resolve."""
    labels = [{"id": str(index), "name": f"Label {index}"} for index in range(75)]

    def respond(request):
        assert request.url.path == f"/1/boards/{BOARD}/labels"
        assert request.url.params["limit"] == "1000"
        return httpx.Response(200, json=labels)

    client = TrelloClient("key", "token")
    with httpx.Client(transport=httpx.MockTransport(respond)) as transport:
        client._client.close()
        client._client = transport
        assert client.get_board_labels(BOARD) == labels
