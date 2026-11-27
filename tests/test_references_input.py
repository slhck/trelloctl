"""Exercise scoped references and multiline text through the public CLI."""

import json
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from trelloctl.cli import main
from trelloctl.resolver import Resolver

BOARD = "507f1f77bcf86cd799439011"
CARD = "60d5ec49f1a4a23456789abc"
LIST = "507f191e810c19729de860ea"
MEMBER = "60d5ec49f1a4a23456789def"
LABEL = "60d5ec49f1a4a23456789ddd"


@pytest.fixture
def client(mocker):
    """Provide the same resolved board/card/member data to all command groups."""
    client = MagicMock()
    config = MagicMock()
    config.get_api_key.return_value = "key"
    config.get_token.return_value = "token"
    mocker.patch("trelloctl.cli.Config", return_value=config)
    mocker.patch("trelloctl.cli.TrelloClient", return_value=client)
    client.get_boards.return_value = [{"id": BOARD, "name": "Development"}]
    client.get_board.return_value = {"id": BOARD}
    client.get_board_lists.return_value = [{"id": LIST, "name": "To Do"}]
    card = {
        "id": CARD,
        "name": "Fix the bug",
        "idBoard": BOARD,
        "idList": LIST,
        "desc": "Original\ntext",
        "shortLink": "AbCd1234",
    }
    client.get_card.return_value = card
    client.get_board_cards.return_value = [card]
    client.get_board_members.return_value = [
        {"id": MEMBER, "username": "jane", "fullName": "Jane Doe"}
    ]
    client.get_board_labels.return_value = [
        {"id": LABEL, "name": "Bug", "color": "red"}
    ]
    client.get_me.return_value = {"id": MEMBER}
    client.create_card.return_value = card
    client.update_card.return_value = card
    client.complete_card.return_value = card
    client.create_checklist.return_value = {"id": "checklist", "name": "Tasks"}
    client.add_card_comment.return_value = {"id": "comment", "data": {"text": "hello"}}
    return client


@pytest.mark.parametrize(
    "reference,expected",
    [
        (CARD, CARD),
        ("AbCd1234", "AbCd1234"),
        ("https://trello.com/c/AbCd1234/card-name?x=1", "AbCd1234"),
    ],
)
def test_direct_card_references(client, reference, expected):
    result = CliRunner().invoke(main, ["card", "complete", reference])
    assert result.exit_code == 0, result.output
    client.complete_card.assert_called_once_with(expected, complete=True)
    client.get_board_cards.assert_not_called()


def test_scoped_name_applies_to_card_and_checklist_commands(client):
    runner = CliRunner()
    result = runner.invoke(
        main, ["card", "complete", "bug", "--board", "Development", "--list", "To Do"]
    )
    assert result.exit_code == 0, result.output
    client.complete_card.assert_called_once_with(CARD, complete=True)
    result = runner.invoke(
        main,
        ["checklist", "create", "bug", "--board", "Development", "--name", "Tasks"],
    )
    assert result.exit_code == 0, result.output
    client.create_checklist.assert_called_once_with(CARD, "Tasks")


@pytest.mark.parametrize(
    "reference",
    [
        "https://evil.example/c/AbCd1234",
        "https://trello.com.evil.example/c/AbCd1234",
        "https://trello.com/b/AbCd1234",
        "../cards/other",
        "name with spaces",
    ],
)
def test_invalid_unscoped_reference_never_writes(client, reference):
    result = CliRunner().invoke(main, ["card", "complete", reference])
    assert result.exit_code == 1
    client.complete_card.assert_not_called()


def test_ambiguous_scoped_name_never_writes(client):
    card = client.get_card.return_value
    client.get_board_cards.return_value = [
        card,
        {**card, "id": "another", "name": "Fix another bug"},
    ]
    result = CliRunner().invoke(
        main, ["card", "complete", "bug", "--board", "Development"]
    )
    assert result.exit_code == 1
    assert "Multiple cards" in result.stderr
    client.complete_card.assert_not_called()


def test_missing_scoped_name_does_not_pass_through(client):
    result = CliRunner().invoke(
        main, ["card", "complete", "missing", "--board", "Development"]
    )
    assert result.exit_code == 1
    client.complete_card.assert_not_called()


def test_list_requires_board(client):
    result = CliRunner().invoke(main, ["card", "show", CARD, "--list", LIST])
    assert result.exit_code == 1
    assert "--list requires --board" in result.stderr
    client.get_card.assert_not_called()


def test_board_url_and_member_aliases(client):
    resolver = Resolver(client)
    assert resolver.resolve_board("https://trello.com/b/AbCd1234/board") == BOARD
    client.get_board.assert_called_once_with("AbCd1234")
    assert resolver.resolve_member(BOARD, "@jane") == MEMBER
    assert resolver.resolve_member(BOARD, "me") == MEMBER


@pytest.mark.parametrize(
    "command,method",
    [
        ("assign", "add_card_member"),
        ("unassign", "remove_card_member"),
        ("label", "add_card_label"),
        ("unlabel", "remove_card_label"),
    ],
)
def test_card_member_and_label_names(client, command, method):
    member = command in {"assign", "unassign"}
    result = CliRunner().invoke(
        main, ["card", command, CARD, "Jane Doe" if member else "bug"]
    )
    assert result.exit_code == 0, result.output
    getattr(client, method).assert_called_once_with(CARD, MEMBER if member else LABEL)


def test_create_card_resolves_members_and_labels(client):
    result = CliRunner().invoke(
        main,
        [
            "card",
            "create",
            "To Do",
            "--board",
            "Development",
            "--name",
            "Task",
            "--member",
            "jane",
            "--label",
            "Bug",
        ],
    )
    assert result.exit_code == 0, result.output
    assert client.create_card.call_args.kwargs["members"] == [MEMBER]
    assert client.create_card.call_args.kwargs["labels"] == [LABEL]


@pytest.mark.parametrize("source", ["file", "stdin"])
def test_description_multiline_sources(client, tmp_path, source):
    text = "First paragraph\n\nSecond paragraph, with ümlaut\n"
    path = tmp_path / "description.md"
    path.write_text(text, encoding="utf-8")
    result = CliRunner().invoke(
        main,
        [
            "card",
            "update",
            CARD,
            "--description-file",
            "-" if source == "stdin" else str(path),
        ],
        input=text,
    )
    assert result.exit_code == 0, result.output
    client.update_card.assert_called_once_with(CARD, desc=text)


def test_comment_stdin_preserves_newlines(client):
    text = "one\n\ntwo\n"
    result = CliRunner().invoke(
        main,
        ["--format", "json", "card", "comment", CARD, "--text-file", "-"],
        input=text,
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["id"] == "comment"
    client.add_card_comment.assert_called_once_with(CARD, text)


@pytest.mark.parametrize(
    "args",
    [
        ["--description", "inline", "--description-file", "-"],
        ["--description-file", "-", "--editor"],
    ],
)
def test_description_sources_are_mutually_exclusive(client, args):
    result = CliRunner().invoke(main, ["card", "update", CARD, *args], input="body")
    assert result.exit_code == 2
    client.update_card.assert_not_called()


def test_editor_uses_current_description(client, mocker):
    edit = mocker.patch(
        "trelloctl.text_input.click.edit", return_value="Updated\nbody\n"
    )
    result = CliRunner().invoke(main, ["card", "update", CARD, "--editor"])
    assert result.exit_code == 0, result.output
    edit.assert_called_once_with("Original\ntext", extension=".md")
    client.update_card.assert_called_once_with(CARD, desc="Updated\nbody\n")


def test_cancelled_editor_does_not_write(client, mocker):
    mocker.patch("trelloctl.text_input.click.edit", return_value=None)
    result = CliRunner().invoke(main, ["card", "update", CARD, "--editor"])
    assert result.exit_code == 1
    client.update_card.assert_not_called()


def test_empty_comment_rejected(client):
    result = CliRunner().invoke(
        main, ["card", "comment", CARD, "--text-file", "-"], input="\n"
    )
    assert result.exit_code == 2
    client.add_card_comment.assert_not_called()


def test_ambiguous_label_rejected(client):
    client.get_board_labels.return_value = [
        {"id": "one", "name": "Bug"},
        {"id": "two", "name": "Bug"},
    ]
    result = CliRunner().invoke(main, ["card", "label", CARD, "Bug"])
    assert result.exit_code == 1
    assert "Multiple labels" in result.stderr
    client.add_card_label.assert_not_called()


def test_missing_description_file_does_not_write(client, tmp_path):
    result = CliRunner().invoke(
        main,
        ["card", "update", CARD, "--description-file", str(tmp_path / "missing.md")],
    )
    assert result.exit_code == 1
    assert "Could not read text" in result.stderr
    client.update_card.assert_not_called()


def test_create_description_stdin(client):
    text = "A description\n\nwith paragraphs\n"
    result = CliRunner().invoke(
        main,
        [
            "card",
            "create",
            LIST,
            "--board",
            BOARD,
            "--name",
            "Task",
            "--description-file",
            "-",
        ],
        input=text,
    )
    assert result.exit_code == 0, result.output
    assert client.create_card.call_args.kwargs["desc"] == text


def test_empty_scoped_reference_never_writes(client):
    result = CliRunner().invoke(main, ["card", "complete", "", "--board", BOARD])
    assert result.exit_code == 1
    client.complete_card.assert_not_called()
