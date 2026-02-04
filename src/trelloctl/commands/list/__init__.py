"""List commands."""

import click

from trelloctl.cli import Context, pass_context
from trelloctl.output import format_output, print_error, print_success


@click.group("list")
def list_() -> None:
    """List management commands."""
    pass


@list_.command("list")
@click.argument("board")
@click.option(
    "--filter",
    "-f",
    type=click.Choice(["all", "closed", "open"]),
    default="open",
    help="Filter lists",
)
@pass_context
def list_lists(ctx: Context, board: str, filter: str) -> None:
    """List all lists on a board.

    BOARD can be an ID or name (partial match supported).
    """
    client = ctx.ensure_client()

    try:
        board_id = ctx.resolver.resolve_board(board)
        lists = client.get_board_lists(board_id, filter=filter)
    except Exception as e:
        print_error(str(e))
        return

    data = [
        {
            "id": lst["id"],
            "name": lst["name"],
            "closed": "Yes" if lst.get("closed") else "No",
        }
        for lst in lists
    ]

    format_output(
        data,
        ctx.format,
        columns=[("name", "Name"), ("id", "ID"), ("closed", "Closed")],
        title="Lists",
        template="{name} ({id})",
    )


@list_.command("show")
@click.argument("list_name")
@click.option("--board", "-b", required=True, help="Board name or ID")
@pass_context
def show_list(ctx: Context, list_name: str, board: str) -> None:
    """Show details of a list.

    LIST_NAME can be an ID or name (partial match supported).
    """
    client = ctx.ensure_client()

    try:
        list_id = ctx.resolver.resolve_list(board, list_name)
        lst = client.get_list(list_id)
    except Exception as e:
        print_error(str(e))
        return

    data = {
        "id": lst["id"],
        "name": lst["name"],
        "closed": "Yes" if lst.get("closed") else "No",
        "board_id": lst.get("idBoard", ""),
    }

    format_output(
        data,
        ctx.format,
        columns=[
            ("name", "Name"),
            ("id", "ID"),
            ("board_id", "Board ID"),
            ("closed", "Closed"),
        ],
    )


@list_.command("create")
@click.argument("board")
@click.option("--name", "-n", required=True, help="List name")
@click.option(
    "--position",
    "-p",
    type=click.Choice(["top", "bottom"]),
    default="bottom",
    help="Position in board",
)
@pass_context
def create_list(ctx: Context, board: str, name: str, position: str) -> None:
    """Create a new list on a board.

    BOARD can be an ID or name (partial match supported).
    """
    client = ctx.ensure_client()

    try:
        board_id = ctx.resolver.resolve_board(board)
        lst = client.create_list(board_id, name, pos=position)
        print_success(f"Created list: {lst['name']} ({lst['id']})")
    except Exception as e:
        print_error(str(e))


@list_.command("archive")
@click.argument("list_name")
@click.option("--board", "-b", required=True, help="Board name or ID")
@click.option("--unarchive", is_flag=True, help="Unarchive instead of archive")
@pass_context
def archive_list(ctx: Context, list_name: str, board: str, unarchive: bool) -> None:
    """Archive a list.

    LIST_NAME can be an ID or name (partial match supported).
    """
    client = ctx.ensure_client()

    try:
        list_id = ctx.resolver.resolve_list(board, list_name)
        client.archive_list(list_id, closed=not unarchive)
        action = "Unarchived" if unarchive else "Archived"
        print_success(f"{action} list: {list_name}")
    except Exception as e:
        print_error(str(e))


@list_.command("cards")
@click.argument("list_name")
@click.option("--board", "-b", required=True, help="Board name or ID")
@pass_context
def list_cards(ctx: Context, list_name: str, board: str) -> None:
    """List all cards in a list.

    LIST_NAME can be an ID or name (partial match supported).
    """
    client = ctx.ensure_client()

    try:
        list_id = ctx.resolver.resolve_list(board, list_name)
        cards = client.get_list_cards(list_id)
    except Exception as e:
        print_error(str(e))
        return

    data = [
        {
            "id": c["id"],
            "name": c["name"],
            "due": c.get("due", ""),
            "labels": ", ".join(
                lbl.get("name", lbl.get("color", "")) for lbl in c.get("labels", [])
            ),
        }
        for c in cards
    ]

    format_output(
        data,
        ctx.format,
        columns=[("name", "Name"), ("due", "Due"), ("labels", "Labels"), ("id", "ID")],
        title="Cards",
        template="{name} ({id})",
    )
