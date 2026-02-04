"""Card commands."""

import click

from trelloctl.cli import Context, pass_context
from trelloctl.output import format_output, print_error, print_success


@click.group()
def card() -> None:
    """Card management commands."""
    pass


@card.command("show")
@click.argument("card")
@pass_context
def show_card(ctx: Context, card: str) -> None:
    """Show details of a card.

    CARD must be an ID (use 'list cards' to find card IDs).
    """
    client = ctx.ensure_client()

    try:
        c = client.get_card(card)
    except Exception as e:
        print_error(f"Failed to get card: {e}")
        return

    data = {
        "id": c["id"],
        "name": c["name"],
        "description": c.get("desc", ""),
        "due": c.get("due", ""),
        "url": c.get("url", ""),
        "list_id": c.get("idList", ""),
        "labels": ", ".join(
            lbl.get("name", lbl.get("color", "")) for lbl in c.get("labels", [])
        ),
        "closed": "Yes" if c.get("closed") else "No",
    }

    format_output(
        data,
        ctx.format,
        columns=[
            ("name", "Name"),
            ("id", "ID"),
            ("description", "Description"),
            ("due", "Due"),
            ("labels", "Labels"),
            ("list_id", "List ID"),
            ("url", "URL"),
            ("closed", "Closed"),
        ],
    )


@card.command("create")
@click.argument("list_name")
@click.option("--board", "-b", required=True, help="Board name or ID")
@click.option("--name", "-n", required=True, help="Card name")
@click.option("--description", "-d", default="", help="Card description")
@click.option(
    "--position",
    "-p",
    type=click.Choice(["top", "bottom"]),
    default="bottom",
    help="Position in list",
)
@click.option("--due", help="Due date (ISO format)")
@click.option("--label", "-l", multiple=True, help="Label IDs to add")
@click.option("--member", "-m", multiple=True, help="Member IDs to assign")
@pass_context
def create_card(
    ctx: Context,
    list_name: str,
    board: str,
    name: str,
    description: str,
    position: str,
    due: str | None,
    label: tuple[str, ...],
    member: tuple[str, ...],
) -> None:
    """Create a new card in a list.

    LIST_NAME can be an ID or name (partial match supported).
    """
    client = ctx.ensure_client()

    try:
        list_id = ctx.resolver.resolve_list(board, list_name)
        c = client.create_card(
            list_id=list_id,
            name=name,
            desc=description,
            pos=position,
            due=due,
            labels=list(label) if label else None,
            members=list(member) if member else None,
        )
        print_success(f"Created card: {c['name']} ({c['id']})")
    except Exception as e:
        print_error(str(e))


@card.command("move")
@click.argument("card_id")
@click.argument("target_list")
@click.option(
    "--board", "-b", required=True, help="Board name or ID (for resolving list name)"
)
@click.option(
    "--position",
    "-p",
    type=click.Choice(["top", "bottom"]),
    default="bottom",
    help="Position in new list",
)
@pass_context
def move_card(
    ctx: Context, card_id: str, target_list: str, board: str, position: str
) -> None:
    """Move a card to a different list.

    TARGET_LIST can be an ID or name (partial match supported).
    """
    client = ctx.ensure_client()

    try:
        list_id = ctx.resolver.resolve_list(board, target_list)
        client.move_card(card_id, list_id, pos=position)
        print_success(f"Moved card {card_id} to list {target_list}")
    except Exception as e:
        print_error(str(e))


@card.command("archive")
@click.argument("card_id")
@click.option("--unarchive", is_flag=True, help="Unarchive instead of archive")
@pass_context
def archive_card(ctx: Context, card_id: str, unarchive: bool) -> None:
    """Archive a card."""
    client = ctx.ensure_client()

    try:
        client.archive_card(card_id, closed=not unarchive)
        action = "Unarchived" if unarchive else "Archived"
        print_success(f"{action} card: {card_id}")
    except Exception as e:
        print_error(f"Failed to archive card: {e}")


@card.command("delete")
@click.argument("card_id")
@click.confirmation_option(prompt="Are you sure you want to delete this card?")
@pass_context
def delete_card(ctx: Context, card_id: str) -> None:
    """Delete a card (permanently)."""
    client = ctx.ensure_client()

    try:
        client.delete_card(card_id)
        print_success(f"Deleted card: {card_id}")
    except Exception as e:
        print_error(f"Failed to delete card: {e}")


@card.command("assign")
@click.argument("card_id")
@click.argument("member_id")
@pass_context
def assign_card(ctx: Context, card_id: str, member_id: str) -> None:
    """Assign a member to a card."""
    client = ctx.ensure_client()

    try:
        client.add_card_member(card_id, member_id)
        print_success(f"Assigned {member_id} to card {card_id}")
    except Exception as e:
        print_error(f"Failed to assign member: {e}")


@card.command("unassign")
@click.argument("card_id")
@click.argument("member_id")
@pass_context
def unassign_card(ctx: Context, card_id: str, member_id: str) -> None:
    """Remove a member from a card."""
    client = ctx.ensure_client()

    try:
        client.remove_card_member(card_id, member_id)
        print_success(f"Removed {member_id} from card {card_id}")
    except Exception as e:
        print_error(f"Failed to unassign member: {e}")


@card.command("comment")
@click.argument("card_id")
@click.argument("text")
@pass_context
def add_comment(ctx: Context, card_id: str, text: str) -> None:
    """Add a comment to a card."""
    client = ctx.ensure_client()

    try:
        client.add_card_comment(card_id, text)
        print_success("Comment added")
    except Exception as e:
        print_error(f"Failed to add comment: {e}")


@card.command("comments")
@click.argument("card_id")
@pass_context
def list_comments(ctx: Context, card_id: str) -> None:
    """List comments on a card."""
    client = ctx.ensure_client()

    try:
        comments = client.get_card_comments(card_id)
    except Exception as e:
        print_error(f"Failed to get comments: {e}")
        return

    data = [
        {
            "id": c["id"],
            "author": c.get("memberCreator", {}).get("fullName", "Unknown"),
            "date": c.get("date", ""),
            "text": c.get("data", {}).get("text", ""),
        }
        for c in comments
    ]

    format_output(
        data,
        ctx.format,
        columns=[("author", "Author"), ("date", "Date"), ("text", "Comment")],
        title="Comments",
        template="{author} ({date}): {text}",
    )


@card.command("update")
@click.argument("card_id")
@click.option("--name", "-n", help="New card name")
@click.option("--description", "-d", help="New description")
@click.option("--due", help="New due date (ISO format, or 'null' to remove)")
@pass_context
def update_card(
    ctx: Context,
    card_id: str,
    name: str | None,
    description: str | None,
    due: str | None,
) -> None:
    """Update a card's properties."""
    client = ctx.ensure_client()

    kwargs: dict[str, str | None] = {}
    if name:
        kwargs["name"] = name
    if description is not None:
        kwargs["desc"] = description
    if due:
        kwargs["due"] = None if due.lower() == "null" else due

    if not kwargs:
        print_error("No updates specified")
        return

    try:
        client.update_card(card_id, **kwargs)
        print_success(f"Updated card: {card_id}")
    except Exception as e:
        print_error(f"Failed to update card: {e}")
