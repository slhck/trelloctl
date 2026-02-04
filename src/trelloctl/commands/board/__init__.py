"""Board commands."""

import click

from trelloctl.cli import Context, pass_context
from trelloctl.output import format_output, print_error, print_success


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
    boards = client.get_boards(filter=filter)

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
        print_error(str(e))
        return

    data = {
        "id": board_data["id"],
        "name": board_data["name"],
        "description": board_data.get("desc", ""),
        "url": board_data["url"],
        "closed": "Yes" if board_data.get("closed") else "No",
    }

    format_output(
        data,
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
        print_success(f"Created board: {board_data['name']} ({board_data['id']})")
    except Exception as e:
        print_error(f"Failed to create board: {e}")


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
        client.close_board(board_id, closed=not reopen)
        action = "Reopened" if reopen else "Closed"
        print_success(f"{action} board: {board}")
    except Exception as e:
        print_error(str(e))


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
        print_success(f"Deleted board: {board}")
    except Exception as e:
        print_error(str(e))


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
        print_error(str(e))
        return

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
        print_error(str(e))
        return

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
