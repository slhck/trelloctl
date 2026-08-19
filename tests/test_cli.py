"""Tests for the CLI commands."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from trelloctl.cli import main


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


class TestCLI:
    """Tests for the main CLI."""

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

        assert "Not authenticated" in result.output

    def test_auth_logout(self, runner: CliRunner, mocker: Any) -> None:
        """Test auth logout command."""
        mock_config = MagicMock()

        with patch("trelloctl.cli.Config", return_value=mock_config):
            with patch("keyring.delete_password"):
                result = runner.invoke(main, ["auth", "logout"])

        assert result.exit_code == 0
        assert "Credentials removed" in result.output


class TestOutputFormats:
    """Tests for different output formats."""

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
