"""Board commands."""

import click

from trelloctl.cli import Context, pass_context
from trelloctl.commands.card import _card_data
from trelloctl.output import exit_with_error, format_output, output_result


def _board_data(b: dict) -> dict:
    """Convert a Trello board to its output fields."""
    return {
        "id": b["id"],
        "name": b.get("name", ""),
        "description": b.get("desc", ""),
        "url": b.get("url", ""),
        "closed": "Yes" if b.get("closed") else "No",
    }


@click.group()
def board() -> None:
    """Board management commands."""
    pass


@board.command("list")
@click.option(
    "--filter",
    "-f",
    type=click.Choice(
        ["all", "closed", "members", "open", "organization", "public", "starred"]
    ),
    default="open",
    help="Filter boards",
)
@pass_context
def list_boards(ctx: Context, filter: str) -> None:
    """List all accessible boards."""
    client = ctx.ensure_client()

    try:
        boards = client.get_boards(filter=filter)
    except Exception as e:
        exit_with_error(f"Failed to list boards: {e}")

    data = [
        {
            "id": b["id"],
            "name": b["name"],
            "url": b["url"],
            "closed": "Yes" if b.get("closed") else "No",
        }
        for b in boards
    ]

    format_output(
        data,
        ctx.format,
        columns=[("name", "Name"), ("id", "ID"), ("closed", "Closed")],
        title="Boards",
        template="{name} ({id})",
    )


@board.command("show")
@click.argument("board")
@pass_context
def show_board(ctx: Context, board: str) -> None:
    """Show details of a board.

    BOARD can be an ID or name (partial match supported).
    """
    client = ctx.ensure_client()

    try:
        board_id = ctx.resolver.resolve_board(board)
        board_data = client.get_board(board_id)
    except Exception as e:
        exit_with_error(str(e))

    format_output(
        _board_data(board_data),
        ctx.format,
        columns=[
            ("name", "Name"),
            ("id", "ID"),
            ("description", "Description"),
            ("url", "URL"),
            ("closed", "Closed"),
        ],
    )


@board.command("create")
@click.option("--name", "-n", required=True, help="Board name")
@click.option("--description", "-d", default="", help="Board description")
@pass_context
def create_board(ctx: Context, name: str, description: str) -> None:
    """Create a new board."""
    client = ctx.ensure_client()

    try:
        board_data = client.create_board(name, description)
        output_result(
            _board_data(board_data),
            ctx.format,
            f"Created board: {board_data['name']} ({board_data['id']})",
        )
    except Exception as e:
        exit_with_error(f"Failed to create board: {e}")


@board.command("close")
@click.argument("board")
@click.option("--reopen", is_flag=True, help="Reopen instead of close")
@pass_context
def close_board(ctx: Context, board: str, reopen: bool) -> None:
    """Close (archive) a board.

    BOARD can be an ID or name (partial match supported).
    """
    client = ctx.ensure_client()

    try:
        board_id = ctx.resolver.resolve_board(board)
        board_data = client.close_board(board_id, closed=not reopen)
        action = "Reopened" if reopen else "Closed"
        output_result(_board_data(board_data), ctx.format, f"{action} board: {board}")
    except Exception as e:
        exit_with_error(str(e))


@board.command("delete")
@click.argument("board")
@click.confirmation_option(prompt="Are you sure you want to delete this board?")
@pass_context
def delete_board(ctx: Context, board: str) -> None:
    """Delete a board (permanently).

    BOARD can be an ID or name (partial match supported).
    """
    client = ctx.ensure_client()

    try:
        board_id = ctx.resolver.resolve_board(board)
        client.delete_board(board_id)
        output_result(
            {"id": board_id, "deleted": True}, ctx.format, f"Deleted board: {board}"
        )
    except Exception as e:
        exit_with_error(str(e))


@board.command("labels")
@click.argument("board")
@pass_context
def board_labels(ctx: Context, board: str) -> None:
    """List labels on a board.

    BOARD can be an ID or name (partial match supported).
    """
    client = ctx.ensure_client()

    try:
        board_id = ctx.resolver.resolve_board(board)
        labels = client.get_board_labels(board_id)
    except Exception as e:
        exit_with_error(str(e))

    data = [
        {
            "id": label["id"],
            "name": label.get("name", ""),
            "color": label.get("color", ""),
        }
        for label in labels
    ]

    format_output(
        data,
        ctx.format,
        columns=[("name", "Name"), ("color", "Color"), ("id", "ID")],
        title="Labels",
        template="{name} ({color})",
    )


@board.command("cards")
@click.argument("board")
@click.option(
    "--filter",
    "-f",
    type=click.Choice(["open", "closed", "all"]),
    default="open",
    show_default=True,
    help="Filter by archive state",
)
@click.option(
    "--complete/--incomplete",
    default=None,
    help="Filter by completion state",
)
@pass_context
def board_cards(ctx: Context, board: str, filter: str, complete: bool | None) -> None:
    """List cards across all lists on a board.

    BOARD can be an ID or name (partial match supported).
    """
    client = ctx.ensure_client()

    try:
        board_id = ctx.resolver.resolve_board(board)
        cards = client.get_board_cards(board_id, filter=filter)
    except Exception as e:
        exit_with_error(f"Failed to list cards: {e}")

    data = [
        _card_data(c)
        for c in cards
        if complete is None or bool(c.get("dueComplete", False)) == complete
    ]
    format_output(
        data,
        ctx.format,
        columns=[
            ("name", "Name"),
            ("due", "Due"),
            ("due_complete", "Complete"),
            ("list_id", "List ID"),
            ("id", "ID"),
        ],
        title="Cards",
        template="{name} ({id})",
    )


@board.command("members")
@click.argument("board")
@pass_context
def board_members(ctx: Context, board: str) -> None:
    """List members of a board.

    BOARD can be an ID or name (partial match supported).
    """
    client = ctx.ensure_client()

    try:
        board_id = ctx.resolver.resolve_board(board)
        members = client.get_board_members(board_id)
    except Exception as e:
        exit_with_error(str(e))

    data = [
        {
            "id": m["id"],
            "username": m.get("username", ""),
            "fullName": m.get("fullName", ""),
        }
        for m in members
    ]

    format_output(
        data,
        ctx.format,
        columns=[("fullName", "Name"), ("username", "Username"), ("id", "ID")],
        title="Members",
        template="{fullName} (@{username})",
    )
