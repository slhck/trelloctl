"""Tests for the CLI commands."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
from click.testing import CliRunner

from trelloctl.cli import main


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


class TestCLI:
    """Tests for the main CLI."""

    @pytest.mark.parametrize(
        "command", [["card", "show", "missing-card"], ["auth", "status"]]
    )
    def test_failed_request_hides_credentials(
        self, runner: CliRunner, mocker: Any, command: list[str]
    ) -> None:
        """Command error output must never include authentication parameters."""
        config = mocker.patch("trelloctl.cli.Config").return_value
        config.get_api_key.return_value = "secret_key"
        config.get_token.return_value = "secret_token"

        def respond(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, request=request)

        with httpx.Client(transport=httpx.MockTransport(respond)) as transport_client:
            mocker.patch("trelloctl.client.httpx.Client", return_value=transport_client)
            result = runner.invoke(main, command)

        assert result.exit_code == 1
        assert "HTTP 401" in result.stderr
        assert "secret_key" not in result.output
        assert "secret_token" not in result.output

    def test_help(self, runner: CliRunner) -> None:
        """Test --help flag."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "trelloctl" in result.output
        assert "board" in result.output
        assert "card" in result.output
        assert "list" in result.output
        assert "auth" in result.output


class TestBoardCommands:
    """Tests for board commands."""

    def test_board_list(
        self, runner: CliRunner, mock_boards: list[dict], mocker: Any
    ) -> None:
        """Test board list command."""
        mock_client = MagicMock()
        mock_client.get_boards.return_value = mock_boards

        mock_config = MagicMock()
        mock_config.get_api_key.return_value = "test_key"
        mock_config.get_token.return_value = "test_token"

        with patch("trelloctl.cli.Config", return_value=mock_config):
            with patch("trelloctl.cli.TrelloClient", return_value=mock_client):
                result = runner.invoke(main, ["board", "list"])

        assert result.exit_code == 0
        assert "Development" in result.output
        assert "Marketing" in result.output

    def test_board_list_json_format(
        self, runner: CliRunner, mock_boards: list[dict], mocker: Any
    ) -> None:
        """Test board list with JSON output."""
        mock_client = MagicMock()
        mock_client.get_boards.return_value = mock_boards

        mock_config = MagicMock()
        mock_config.get_api_key.return_value = "test_key"
        mock_config.get_token.return_value = "test_token"

        with patch("trelloctl.cli.Config", return_value=mock_config):
            with patch("trelloctl.cli.TrelloClient", return_value=mock_client):
                result = runner.invoke(main, ["--format", "json", "board", "list"])

        assert result.exit_code == 0
        assert '"name": "Development"' in result.output

    def test_board_show(
        self, runner: CliRunner, mock_boards: list[dict], mocker: Any
    ) -> None:
        """Test board show command."""
        mock_client = MagicMock()
        mock_client.get_boards.return_value = mock_boards
        mock_client.get_board.return_value = mock_boards[0]

        mock_config = MagicMock()
        mock_config.get_api_key.return_value = "test_key"
        mock_config.get_token.return_value = "test_token"

        with patch("trelloctl.cli.Config", return_value=mock_config):
            with patch("trelloctl.cli.TrelloClient", return_value=mock_client):
                result = runner.invoke(main, ["board", "show", "Development"])

        assert result.exit_code == 0
        assert "Development" in result.output

    def test_board_labels(
        self,
        runner: CliRunner,
        mock_boards: list[dict],
        mock_labels: list[dict],
        mocker: Any,
    ) -> None:
        """Test board labels command."""
        mock_client = MagicMock()
        mock_client.get_boards.return_value = mock_boards
        mock_client.get_board_labels.return_value = mock_labels

        mock_config = MagicMock()
        mock_config.get_api_key.return_value = "test_key"
        mock_config.get_token.return_value = "test_token"

        with patch("trelloctl.cli.Config", return_value=mock_config):
            with patch("trelloctl.cli.TrelloClient", return_value=mock_client):
                result = runner.invoke(main, ["board", "labels", "Development"])

        assert result.exit_code == 0
        assert "Bug" in result.output
        assert "Feature" in result.output


class TestListCommands:
    """Tests for list commands."""

    def test_list_list(
        self,
        runner: CliRunner,
        mock_boards: list[dict],
        mock_lists: list[dict],
        mocker: Any,
    ) -> None:
        """Test list list command."""
        mock_client = MagicMock()
        mock_client.get_boards.return_value = mock_boards
        mock_client.get_board_lists.return_value = mock_lists

        mock_config = MagicMock()
        mock_config.get_api_key.return_value = "test_key"
        mock_config.get_token.return_value = "test_token"

        with patch("trelloctl.cli.Config", return_value=mock_config):
            with patch("trelloctl.cli.TrelloClient", return_value=mock_client):
                result = runner.invoke(main, ["list", "list", "Development"])

        assert result.exit_code == 0
        assert "To Do" in result.output
        assert "Doing" in result.output
        assert "Done" in result.output

    def test_list_cards(
        self,
        runner: CliRunner,
        mock_boards: list[dict],
        mock_lists: list[dict],
        mock_cards: list[dict],
        mocker: Any,
    ) -> None:
        """Test list cards command."""
        mock_client = MagicMock()
        mock_client.get_boards.return_value = mock_boards
        mock_client.get_board_lists.return_value = mock_lists
        mock_client.get_list_cards.return_value = mock_cards

        mock_config = MagicMock()
        mock_config.get_api_key.return_value = "test_key"
        mock_config.get_token.return_value = "test_token"

        with patch("trelloctl.cli.Config", return_value=mock_config):
            with patch("trelloctl.cli.TrelloClient", return_value=mock_client):
                result = runner.invoke(
                    main, ["list", "cards", "To Do", "--board", "Development"]
                )

        assert result.exit_code == 0
        assert "Implement feature X" in result.output
        assert "Fix bug Y" in result.output


class TestCardCommands:
    """Tests for card commands."""

    def test_card_show(
        self, runner: CliRunner, mock_cards: list[dict], mocker: Any
    ) -> None:
        """Test card show command."""
        mock_client = MagicMock()
        mock_client.get_card.return_value = mock_cards[0]

        mock_config = MagicMock()
        mock_config.get_api_key.return_value = "test_key"
        mock_config.get_token.return_value = "test_token"

        with patch("trelloctl.cli.Config", return_value=mock_config):
            with patch("trelloctl.cli.TrelloClient", return_value=mock_client):
                # Use JSON format to avoid table truncation
                result = runner.invoke(
                    main,
                    ["--format", "json", "card", "show", "60d5ec49f1a4a23456789abc"],
                )

        assert result.exit_code == 0
        assert "Implement feature X" in result.output

    def test_card_create(
        self,
        runner: CliRunner,
        mock_boards: list[dict],
        mock_lists: list[dict],
        mocker: Any,
    ) -> None:
        """Test card create command."""
        mock_client = MagicMock()
        mock_client.get_boards.return_value = mock_boards
        mock_client.get_board_lists.return_value = mock_lists
        mock_client.create_card.return_value = {
            "id": "newcard12345678901234567",
            "name": "New Task",
        }

        mock_config = MagicMock()
        mock_config.get_api_key.return_value = "test_key"
        mock_config.get_token.return_value = "test_token"

        with patch("trelloctl.cli.Config", return_value=mock_config):
            with patch("trelloctl.cli.TrelloClient", return_value=mock_client):
                result = runner.invoke(
                    main,
                    [
                        "card",
                        "create",
                        "To Do",
                        "--board",
                        "Development",
                        "--name",
                        "New Task",
                    ],
                )

        assert result.exit_code == 0
        assert "Created card" in result.output
        assert "New Task" in result.output

    def test_card_move(
        self,
        runner: CliRunner,
        mock_boards: list[dict],
        mock_lists: list[dict],
        mocker: Any,
    ) -> None:
        """Test card move command."""
        mock_client = MagicMock()
        mock_client.get_boards.return_value = mock_boards
        mock_client.get_board_lists.return_value = mock_lists
        mock_client.move_card.return_value = {
            "id": "card12345678901234567890",
            "idList": "list34567890123456789012",
        }

        mock_config = MagicMock()
        mock_config.get_api_key.return_value = "test_key"
        mock_config.get_token.return_value = "test_token"

        with patch("trelloctl.cli.Config", return_value=mock_config):
            with patch("trelloctl.cli.TrelloClient", return_value=mock_client):
                result = runner.invoke(
                    main,
                    [
                        "card",
                        "move",
                        "card12345678901234567890",
                        "Done",
                        "--board",
                        "Development",
                    ],
                )

        assert result.exit_code == 0
        assert "Moved card" in result.output

    def test_card_archive(self, runner: CliRunner, mocker: Any) -> None:
        """Test card archive command."""
        mock_client = MagicMock()
        mock_client.archive_card.return_value = {
            "id": "card12345678901234567890",
            "closed": True,
        }

        mock_config = MagicMock()
        mock_config.get_api_key.return_value = "test_key"
        mock_config.get_token.return_value = "test_token"

        with patch("trelloctl.cli.Config", return_value=mock_config):
            with patch("trelloctl.cli.TrelloClient", return_value=mock_client):
                result = runner.invoke(
                    main, ["card", "archive", "card12345678901234567890"]
                )

        assert result.exit_code == 0
        assert "Archived card" in result.output


class TestChecklistCommands:
    """Tests for checklist commands."""

    def test_edit_item(self, runner: CliRunner, mocker: Any) -> None:
        """Test editing a checklist item's text."""
        mock_client = MagicMock()
        mock_client.update_checklist_item.return_value = {
            "id": "item123",
            "name": "Renamed item",
        }

        mock_config = MagicMock()
        mock_config.get_api_key.return_value = "test_key"
        mock_config.get_token.return_value = "test_token"

        with patch("trelloctl.cli.Config", return_value=mock_config):
            with patch("trelloctl.cli.TrelloClient", return_value=mock_client):
                result = runner.invoke(
                    main,
                    [
                        "checklist",
                        "edit-item",
                        "card12345678901234567890",
                        "item123",
                        "--name",
                        "Renamed item",
                    ],
                )

        assert result.exit_code == 0
        assert "Updated item" in result.output
        mock_client.update_checklist_item.assert_called_once_with(
            "card12345678901234567890", "item123", name="Renamed item"
        )


class TestAuthCommands:
    """Tests for auth commands."""

    def test_auth_status_not_configured(self, runner: CliRunner, mocker: Any) -> None:
        """Test auth status when not configured."""
        mock_config = MagicMock()
        mock_config.is_configured.return_value = False

        with patch("trelloctl.cli.Config", return_value=mock_config):
            with patch("trelloctl.commands.auth.Context") as mock_context_cls:
                mock_ctx = MagicMock()
                mock_ctx.config = mock_config
                mock_context_cls.return_value = mock_ctx
                result = runner.invoke(main, ["auth", "status"])

        assert result.exit_code == 1
        assert "Not authenticated" in result.output

    def test_auth_logout(self, runner: CliRunner, mocker: Any) -> None:
        """Test auth logout command."""
        mock_config = MagicMock()

        with patch("trelloctl.cli.Config", return_value=mock_config):
            with patch("keyring.delete_password"):
                result = runner.invoke(main, ["auth", "logout"])

        assert result.exit_code == 0
        assert "Credentials removed" in result.output


CARD = {"id": "card1", "name": "Task", "url": "https://trello.com/c/x"}
BOARD = {"id": "507f1f77bcf86cd799439011", "name": "Dev", "url": "u"}
LIST = {"id": "507f191e810c19729de860ea", "name": "To Do", "idBoard": BOARD["id"]}
ITEM = {"id": "item1", "name": "Do", "state": "incomplete", "idChecklist": "cl1"}
COMMENT = {
    "id": "action1",
    "date": "2026-11-04",
    "memberCreator": {"fullName": "Jo"},
    "data": {"text": "Text"},
}
BOARD_ID = BOARD["id"]
LIST_ID = LIST["id"]


class TestWriteOutput:
    """Tests for the output of write commands in machine-readable formats."""

    @pytest.mark.parametrize(
        ("command", "method", "response", "expected"),
        [
            (
                ["card", "create", LIST_ID, "-b", BOARD_ID, "-n", "Task"],
                "create_card",
                CARD,
                {"id": "card1", "url": CARD["url"]},
            ),
            (
                ["card", "move", "card1", LIST_ID, "-b", BOARD_ID],
                "move_card",
                CARD,
                {"id": "card1"},
            ),
            (
                ["card", "update", "card1", "-n", "Task"],
                "update_card",
                CARD,
                {"id": "card1", "name": "Task"},
            ),
            (["card", "archive", "card1"], "archive_card", CARD, {"id": "card1"}),
            (
                ["card", "delete", "card1", "--yes"],
                "delete_card",
                None,
                {"id": "card1", "deleted": True},
            ),
            (
                ["card", "assign", "card1", "member1"],
                "add_card_member",
                [],
                {"id": "card1", "member_id": "member1"},
            ),
            (
                ["card", "unassign", "card1", "member1"],
                "remove_card_member",
                [],
                {"id": "card1", "member_id": "member1"},
            ),
            (
                ["card", "comment", "card1", "Text"],
                "add_card_comment",
                COMMENT,
                {"id": "action1", "author": "Jo", "text": "Text"},
            ),
            (
                ["board", "create", "--name", "Dev"],
                "create_board",
                BOARD,
                {"id": BOARD_ID, "url": "u"},
            ),
            (["board", "close", BOARD_ID], "close_board", BOARD, {"id": BOARD_ID}),
            (
                ["board", "delete", BOARD_ID, "--yes"],
                "delete_board",
                None,
                {"id": BOARD_ID, "deleted": True},
            ),
            (
                ["list", "create", BOARD_ID, "--name", "To Do"],
                "create_list",
                LIST,
                {"id": LIST_ID, "board_id": BOARD_ID},
            ),
            (
                ["list", "archive", LIST_ID, "-b", BOARD_ID],
                "archive_list",
                LIST,
                {"id": LIST_ID},
            ),
            (
                ["checklist", "create", "card1", "--name", "Tasks"],
                "create_checklist",
                {"id": "cl1", "name": "Tasks"},
                {"id": "cl1", "name": "Tasks", "card_id": "card1"},
            ),
            (
                ["checklist", "delete", "cl1", "--yes"],
                "delete_checklist",
                None,
                {"id": "cl1", "deleted": True},
            ),
            (
                ["checklist", "add-item", "cl1", "--name", "Do"],
                "add_checklist_item",
                ITEM,
                {"id": "item1", "checklist_id": "cl1"},
            ),
            (
                ["checklist", "assign", "card1", "item1", BOARD_ID],
                "set_checklist_item_member",
                ITEM,
                {"id": "item1"},
            ),
            (
                ["checklist", "unassign", "card1", "item1"],
                "set_checklist_item_member",
                ITEM,
                {"id": "item1"},
            ),
            (
                ["checklist", "set-due", "card1", "item1", "2026-12-01"],
                "set_checklist_item_due",
                ITEM,
                {"id": "item1"},
            ),
            (
                ["checklist", "edit-item", "card1", "item1", "--name", "Do"],
                "update_checklist_item",
                ITEM,
                {"id": "item1", "name": "Do"},
            ),
            (
                ["checklist", "check", "card1", "item1"],
                "update_checklist_item",
                ITEM,
                {"id": "item1", "state": "incomplete"},
            ),
            (
                ["checklist", "delete-item", "cl1", "item1"],
                "delete_checklist_item",
                None,
                {"id": "item1", "deleted": True},
            ),
        ],
    )
    def test_json_output(
        self,
        runner: CliRunner,
        command: list[str],
        method: str,
        response: Any,
        expected: dict,
    ) -> None:
        """Write commands must print one JSON object and no status message."""
        mock_client = MagicMock()
        getattr(mock_client, method).return_value = response

        mock_config = MagicMock()
        mock_config.get_api_key.return_value = "test_key"
        mock_config.get_token.return_value = "test_token"

        with patch("trelloctl.cli.Config", return_value=mock_config):
            with patch("trelloctl.cli.TrelloClient", return_value=mock_client):
                result = runner.invoke(main, ["--format", "json", *command])

        assert result.exit_code == 0, result.output
        assert result.stderr == ""
        assert expected.items() <= json.loads(result.stdout).items()

    def test_plain_output_is_id(self, runner: CliRunner) -> None:
        """Write commands in plain format must print only the ID."""
        mock_client = MagicMock()
        mock_client.create_checklist.return_value = {"id": "cl1", "name": "Tasks"}

        mock_config = MagicMock()
        mock_config.get_api_key.return_value = "test_key"
        mock_config.get_token.return_value = "test_token"

        with patch("trelloctl.cli.Config", return_value=mock_config):
            with patch("trelloctl.cli.TrelloClient", return_value=mock_client):
                result = runner.invoke(
                    main,
                    ["--format", "plain", "checklist", "create", "card1", "-n", "T"],
                )

        assert result.stdout == "cl1\n"

    def test_csv_output_has_header_and_row(self, runner: CliRunner) -> None:
        """Write commands in CSV format must print a header and one row."""
        mock_client = MagicMock()
        mock_client.create_checklist.return_value = {"id": "cl1", "name": "Tasks"}

        mock_config = MagicMock()
        mock_config.get_api_key.return_value = "test_key"
        mock_config.get_token.return_value = "test_token"

        with patch("trelloctl.cli.Config", return_value=mock_config):
            with patch("trelloctl.cli.TrelloClient", return_value=mock_client):
                result = runner.invoke(
                    main, ["--format", "csv", "checklist", "create", "card1", "-n", "T"]
                )

        assert result.stdout == "id,name,card_id\ncl1,Tasks,card1\n"

    def test_auth_status_json(self, runner: CliRunner) -> None:
        """Auth status must honor the output format."""
        mock_client = MagicMock()
        mock_client.get_me.return_value = {
            "id": "member1",
            "username": "jo",
            "fullName": "Jo",
        }

        mock_config = MagicMock()
        mock_config.get_api_key.return_value = "test_key"
        mock_config.get_token.return_value = "test_token"

        with patch("trelloctl.cli.Config", return_value=mock_config):
            with patch("trelloctl.cli.TrelloClient", return_value=mock_client):
                result = runner.invoke(main, ["--format", "json", "auth", "status"])

        assert json.loads(result.stdout) == {
            "id": "member1",
            "username": "jo",
            "full_name": "Jo",
        }


class TestExitCodes:
    """Tests for exit codes of failed commands."""

    @pytest.mark.parametrize(
        ("command", "method"),
        [
            (["board", "list"], "get_boards"),
            (["board", "create", "--name", "New"], "create_board"),
            (["card", "archive", "card1"], "archive_card"),
            (["card", "delete", "card1", "--yes"], "delete_card"),
            (["card", "comment", "card1", "Text"], "add_card_comment"),
            (["checklist", "create", "card1", "--name", "New"], "create_checklist"),
            (["checklist", "add-item", "cl1", "--name", "New"], "add_checklist_item"),
            (["checklist", "delete-item", "cl1", "item1"], "delete_checklist_item"),
        ],
    )
    def test_api_failure_exits_non_zero(
        self, runner: CliRunner, command: list[str], method: str
    ) -> None:
        """Failed API calls must exit with status 1 and report on stderr."""
        mock_client = MagicMock()
        getattr(mock_client, method).side_effect = RuntimeError("HTTP 500")

        mock_config = MagicMock()
        mock_config.get_api_key.return_value = "test_key"
        mock_config.get_token.return_value = "test_token"

        with patch("trelloctl.cli.Config", return_value=mock_config):
            with patch("trelloctl.cli.TrelloClient", return_value=mock_client):
                result = runner.invoke(main, command)

        assert result.exit_code == 1
        assert "HTTP 500" in result.stderr
        assert result.stdout == ""

    def test_card_update_without_changes_exits_non_zero(
        self, runner: CliRunner
    ) -> None:
        """A card update with no fields must exit with status 1."""
        mock_config = MagicMock()
        mock_config.get_api_key.return_value = "test_key"
        mock_config.get_token.return_value = "test_token"

        with patch("trelloctl.cli.Config", return_value=mock_config):
            with patch("trelloctl.cli.TrelloClient", return_value=MagicMock()):
                result = runner.invoke(main, ["card", "update", "card1"])

        assert result.exit_code == 1
        assert "No updates specified" in result.stderr


class TestOutputFormats:
    """Tests for different output formats."""

    @pytest.mark.parametrize(
        ("command", "method", "response"),
        [
            (
                ["card", "show", "card1"],
                "get_card",
                {"id": "card1", "name": "Task"},
            ),
            (
                ["board", "show", "507f1f77bcf86cd799439011"],
                "get_board",
                {"id": "507f1f77bcf86cd799439011", "name": "Dev", "url": "u"},
            ),
        ],
    )
    def test_show_json_is_object(
        self, runner: CliRunner, command: list[str], method: str, response: dict
    ) -> None:
        """Commands that show one item must print a JSON object."""
        mock_client = MagicMock()
        getattr(mock_client, method).return_value = response

        mock_config = MagicMock()
        mock_config.get_api_key.return_value = "test_key"
        mock_config.get_token.return_value = "test_token"

        with patch("trelloctl.cli.Config", return_value=mock_config):
            with patch("trelloctl.cli.TrelloClient", return_value=mock_client):
                result = runner.invoke(main, ["--format", "json", *command])

        assert result.exit_code == 0
        assert json.loads(result.stdout)["id"] == response["id"]

    def test_warning_keeps_json_stdout_valid(self, runner: CliRunner) -> None:
        """Warnings must go to stderr, so stdout stays parseable."""
        mock_client = MagicMock()
        mock_client.get_card_checklists.return_value = [
            {
                "id": "cl1",
                "name": "Tasks",
                "checkItems": [{"id": "item1", "name": "Do", "idMember": "member1"}],
            }
        ]
        mock_client.get_card.side_effect = RuntimeError("HTTP 500")

        mock_config = MagicMock()
        mock_config.get_api_key.return_value = "test_key"
        mock_config.get_token.return_value = "test_token"

        with patch("trelloctl.cli.Config", return_value=mock_config):
            with patch("trelloctl.cli.TrelloClient", return_value=mock_client):
                result = runner.invoke(
                    main, ["--format", "json", "checklist", "list", "card1"]
                )

        assert result.exit_code == 0
        assert json.loads(result.stdout)[0]["item_id"] == "item1"
        assert "Could not resolve member names" in result.stderr

    def test_csv_output(
        self, runner: CliRunner, mock_boards: list[dict], mocker: Any
    ) -> None:
        """Test CSV output format."""
        mock_client = MagicMock()
        mock_client.get_boards.return_value = mock_boards

        mock_config = MagicMock()
        mock_config.get_api_key.return_value = "test_key"
        mock_config.get_token.return_value = "test_token"

        with patch("trelloctl.cli.Config", return_value=mock_config):
            with patch("trelloctl.cli.TrelloClient", return_value=mock_client):
                result = runner.invoke(main, ["--format", "csv", "board", "list"])

        assert result.exit_code == 0
        assert "id,name" in result.output or "name,id" in result.output

    def test_plain_output(
        self, runner: CliRunner, mock_boards: list[dict], mocker: Any
    ) -> None:
        """Test plain output format."""
        mock_client = MagicMock()
        mock_client.get_boards.return_value = mock_boards

        mock_config = MagicMock()
        mock_config.get_api_key.return_value = "test_key"
        mock_config.get_token.return_value = "test_token"

        with patch("trelloctl.cli.Config", return_value=mock_config):
            with patch("trelloctl.cli.TrelloClient", return_value=mock_client):
                result = runner.invoke(main, ["--format", "plain", "board", "list"])

        assert result.exit_code == 0
        assert "Development" in result.output
