"""Card commands."""

import click

from trelloctl.cli import Context, pass_context
from trelloctl.models import card_data as _card_data
from trelloctl.output import exit_with_error, format_output, output_result
from trelloctl.reference_options import card_reference_options
from trelloctl.resolver import is_trello_id
from trelloctl.text_input import read_text


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
@card_reference_options
@pass_context
def show_card(ctx: Context, card: str) -> None:
    """Show details of a card.

    CARD accepts an ID, shortlink, URL, or a name scoped with --board.
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
@click.option("--description", "-d", help="Card description")
@click.option(
    "--description-file",
    type=click.Path(dir_okay=False),
    help="Read description from a UTF-8 file, or - for stdin",
)
@click.option("--editor", is_flag=True, help="Compose description in $EDITOR")
@click.option(
    "--position",
    "-p",
    type=click.Choice(["top", "bottom"]),
    default="bottom",
    help="Position in list",
)
@click.option("--due", help="Due date (ISO format)")
@click.option("--label", "-l", multiple=True, help="Label IDs or names to add")
@click.option(
    "--member", "-m", multiple=True, help="Member IDs, usernames or names to assign"
)
@pass_context
def create_card(
    ctx: Context,
    list_name: str,
    board: str,
    name: str,
    description: str | None,
    description_file: str | None,
    editor: bool,
    position: str,
    due: str | None,
    label: tuple[str, ...],
    member: tuple[str, ...],
) -> None:
    """Create a new card in a list.

    LIST_NAME can be an ID or name (partial match supported).
    """
    description = read_text(description, description_file, editor) or ""
    client = ctx.ensure_client()

    try:
        list_id = ctx.resolver.resolve_list(board, list_name)
        c = client.create_card(
            list_id=list_id,
            name=name,
            desc=description,
            pos=position,
            due=due,
            labels=[ctx.resolver.resolve_label(board, ref) for ref in label] or None,
            members=[ctx.resolver.resolve_member(board, ref) for ref in member] or None,
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
@card_reference_options(board_option=False)
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
@card_reference_options
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
@card_reference_options
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
@card_reference_options
@pass_context
def label_card(ctx: Context, card_id: str, label_id: str) -> None:
    """Add an existing label by ID or name."""
    client = ctx.ensure_client()

    try:
        if not is_trello_id(label_id):
            board_id = client.get_card(card_id)["idBoard"]
            label_id = ctx.resolver.resolve_label(board_id, label_id)
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
@card_reference_options
@pass_context
def unlabel_card(ctx: Context, card_id: str, label_id: str) -> None:
    """Remove a label from a card."""
    client = ctx.ensure_client()

    try:
        if not is_trello_id(label_id):
            board_id = client.get_card(card_id)["idBoard"]
            label_id = ctx.resolver.resolve_label(board_id, label_id)
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
@card_reference_options
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
@card_reference_options
@pass_context
def assign_card(ctx: Context, card_id: str, member_id: str) -> None:
    """Assign a member to a card."""
    client = ctx.ensure_client()

    try:
        if not is_trello_id(member_id):
            board_id = client.get_card(card_id)["idBoard"]
            member_id = ctx.resolver.resolve_member(board_id, member_id)
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
@card_reference_options
@pass_context
def unassign_card(ctx: Context, card_id: str, member_id: str) -> None:
    """Remove a member from a card."""
    client = ctx.ensure_client()

    try:
        if not is_trello_id(member_id):
            board_id = client.get_card(card_id)["idBoard"]
            member_id = ctx.resolver.resolve_member(board_id, member_id)
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
@click.argument("text", required=False)
@click.option(
    "--text-file",
    type=click.Path(dir_okay=False),
    help="Read comment from a UTF-8 file, or - for stdin",
)
@click.option("--editor", is_flag=True, help="Compose comment in $EDITOR")
@card_reference_options
@pass_context
def add_comment(
    ctx: Context, card_id: str, text: str | None, text_file: str | None, editor: bool
) -> None:
    """Add a comment to a card."""
    text = read_text(text, text_file, editor, required=True) or ""
    client = ctx.ensure_client()

    try:
        comment = client.add_card_comment(card_id, text)
        output_result(_comment_data(comment), ctx.format, "Comment added")
    except Exception as e:
        exit_with_error(f"Failed to add comment: {e}")


@card.command("comments")
@click.argument("card_id")
@card_reference_options
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
@click.option(
    "--description-file",
    type=click.Path(dir_okay=False),
    help="Read description from a UTF-8 file, or - for stdin",
)
@click.option("--editor", is_flag=True, help="Edit current description in $EDITOR")
@click.option("--due", help="New due date (ISO format, or 'null' to remove)")
@card_reference_options
@pass_context
def update_card(
    ctx: Context,
    card_id: str,
    name: str | None,
    description: str | None,
    description_file: str | None,
    editor: bool,
    due: str | None,
) -> None:
    """Update a card's properties."""
    client = ctx.ensure_client()

    if sum((description is not None, description_file is not None, editor)) > 1:
        raise click.UsageError(
            "Use only one description argument, file option, or --editor"
        )
    initial = ""
    if editor:
        try:
            initial = client.get_card(card_id).get("desc", "")
        except Exception as exc:
            exit_with_error(f"Failed to get current description: {exc}")
    description = read_text(description, description_file, editor, initial=initial)
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
