"""Card commands."""

import click

from trelloctl.cli import Context, pass_context
from trelloctl.output import exit_with_error, format_output, output_result


def _card_data(c: dict) -> dict:
    """Convert a Trello card to its output fields."""
    return {
        "id": c["id"],
        "name": c.get("name", ""),
        "description": c.get("desc", ""),
        "due": c.get("due", ""),
        "due_complete": c.get("dueComplete", False),
        "url": c.get("url", ""),
        "list_id": c.get("idList", ""),
        "labels": ", ".join(
            lbl.get("name", lbl.get("color", "")) for lbl in c.get("labels", [])
        ),
        "closed": "Yes" if c.get("closed") else "No",
    }


def _comment_data(c: dict) -> dict:
    """Convert a Trello comment action to its output fields."""
    return {
        "id": c["id"],
        "author": c.get("memberCreator", {}).get("fullName", "Unknown"),
        "date": c.get("date", ""),
        "text": c.get("data", {}).get("text", ""),
    }


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
        exit_with_error(f"Failed to get card: {e}")

    format_output(
        _card_data(c),
        ctx.format,
        columns=[
            ("name", "Name"),
            ("id", "ID"),
            ("description", "Description"),
            ("due", "Due"),
            ("due_complete", "Complete"),
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
        output_result(
            _card_data(c), ctx.format, f"Created card: {c['name']} ({c['id']})"
        )
    except Exception as e:
        exit_with_error(str(e))


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
        c = client.move_card(card_id, list_id, pos=position)
        output_result(
            _card_data(c), ctx.format, f"Moved card {card_id} to list {target_list}"
        )
    except Exception as e:
        exit_with_error(str(e))


@card.command("archive")
@click.argument("card_id")
@click.option("--unarchive", is_flag=True, help="Unarchive instead of archive")
@pass_context
def archive_card(ctx: Context, card_id: str, unarchive: bool) -> None:
    """Archive a card."""
    client = ctx.ensure_client()

    try:
        c = client.archive_card(card_id, closed=not unarchive)
        action = "Unarchived" if unarchive else "Archived"
        output_result(_card_data(c), ctx.format, f"{action} card: {card_id}")
    except Exception as e:
        exit_with_error(f"Failed to archive card: {e}")


@card.command("complete")
@click.argument("card_id")
@click.option("--undo", is_flag=True, help="Mark the card as incomplete")
@pass_context
def complete_card(ctx: Context, card_id: str, undo: bool) -> None:
    """Mark a card as complete, or undo completion.

    Sets Trello's dueComplete flag, including on cards without a due date.
    Does not move or archive the card, or change checklist items.
    """
    client = ctx.ensure_client()

    try:
        c = client.complete_card(card_id, complete=not undo)
        state = "incomplete" if undo else "complete"
        output_result(_card_data(c), ctx.format, f"Marked card {card_id} as {state}")
    except Exception as e:
        exit_with_error(f"Failed to change card completion: {e}")


@card.command("label")
@click.argument("card_id")
@click.argument("label_id")
@pass_context
def label_card(ctx: Context, card_id: str, label_id: str) -> None:
    """Add an existing label (use 'board labels' to find label IDs)."""
    client = ctx.ensure_client()

    try:
        client.add_card_label(card_id, label_id)
        output_result(
            {"id": card_id, "label_id": label_id},
            ctx.format,
            f"Added label {label_id} to card {card_id}",
        )
    except Exception as e:
        exit_with_error(f"Failed to add label: {e}")


@card.command("unlabel")
@click.argument("card_id")
@click.argument("label_id")
@pass_context
def unlabel_card(ctx: Context, card_id: str, label_id: str) -> None:
    """Remove a label from a card."""
    client = ctx.ensure_client()

    try:
        client.remove_card_label(card_id, label_id)
        output_result(
            {"id": card_id, "label_id": label_id},
            ctx.format,
            f"Removed label {label_id} from card {card_id}",
        )
    except Exception as e:
        exit_with_error(f"Failed to remove label: {e}")


@card.command("delete")
@click.argument("card_id")
@click.confirmation_option(prompt="Are you sure you want to delete this card?")
@pass_context
def delete_card(ctx: Context, card_id: str) -> None:
    """Delete a card (permanently)."""
    client = ctx.ensure_client()

    try:
        client.delete_card(card_id)
        output_result(
            {"id": card_id, "deleted": True}, ctx.format, f"Deleted card: {card_id}"
        )
    except Exception as e:
        exit_with_error(f"Failed to delete card: {e}")


@card.command("assign")
@click.argument("card_id")
@click.argument("member_id")
@pass_context
def assign_card(ctx: Context, card_id: str, member_id: str) -> None:
    """Assign a member to a card."""
    client = ctx.ensure_client()

    try:
        client.add_card_member(card_id, member_id)
        output_result(
            {"id": card_id, "member_id": member_id},
            ctx.format,
            f"Assigned {member_id} to card {card_id}",
        )
    except Exception as e:
        exit_with_error(f"Failed to assign member: {e}")


@card.command("unassign")
@click.argument("card_id")
@click.argument("member_id")
@pass_context
def unassign_card(ctx: Context, card_id: str, member_id: str) -> None:
    """Remove a member from a card."""
    client = ctx.ensure_client()

    try:
        client.remove_card_member(card_id, member_id)
        output_result(
            {"id": card_id, "member_id": member_id},
            ctx.format,
            f"Removed {member_id} from card {card_id}",
        )
    except Exception as e:
        exit_with_error(f"Failed to unassign member: {e}")


@card.command("comment")
@click.argument("card_id")
@click.argument("text")
@pass_context
def add_comment(ctx: Context, card_id: str, text: str) -> None:
    """Add a comment to a card."""
    client = ctx.ensure_client()

    try:
        comment = client.add_card_comment(card_id, text)
        output_result(_comment_data(comment), ctx.format, "Comment added")
    except Exception as e:
        exit_with_error(f"Failed to add comment: {e}")


@card.command("comments")
@click.argument("card_id")
@pass_context
def list_comments(ctx: Context, card_id: str) -> None:
    """List comments on a card."""
    client = ctx.ensure_client()

    try:
        comments = client.get_card_comments(card_id)
    except Exception as e:
        exit_with_error(f"Failed to get comments: {e}")

    format_output(
        [_comment_data(c) for c in comments],
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
        exit_with_error("No updates specified")

    try:
        c = client.update_card(card_id, **kwargs)
        output_result(_card_data(c), ctx.format, f"Updated card: {card_id}")
    except Exception as e:
        exit_with_error(f"Failed to update card: {e}")
