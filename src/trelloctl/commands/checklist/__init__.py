"""Checklist commands."""

from typing import Any

import click

from trelloctl.cli import Context, pass_context
from trelloctl.output import (
    format_output,
    print_error,
    print_success,
    print_warning,
)
from trelloctl.resolver import is_trello_id


@click.group()
def checklist() -> None:
    """Checklist management commands."""
    pass


@checklist.command("list")
@click.argument("card_id")
@pass_context
def list_checklists(ctx: Context, card_id: str) -> None:
    """List all checklists and items on a card.

    CARD_ID must be a Trello card ID.
    """
    client = ctx.ensure_client()

    try:
        checklists = client.get_card_checklists(card_id)
    except Exception as e:
        print_error(f"Failed to get checklists: {e}")
        return

    member_names = _resolve_item_members(client, card_id, checklists)

    data = []
    for cl in checklists:
        items = cl.get("checkItems", [])
        if not items:
            data.append(
                {
                    "checklist": cl["name"],
                    "checklist_id": cl["id"],
                    "item": "",
                    "item_id": "",
                    "state": "",
                    "member": "",
                    "due": "",
                }
            )
        else:
            for item in sorted(items, key=lambda i: i.get("pos", 0)):
                state = "x" if item.get("state") == "complete" else " "
                member_id = item.get("idMember") or ""
                data.append(
                    {
                        "checklist": cl["name"],
                        "checklist_id": cl["id"],
                        "item": f"[{state}] {item['name']}",
                        "item_id": item["id"],
                        "state": item.get("state", ""),
                        "member": member_names.get(member_id, member_id),
                        "due": item.get("due") or "",
                    }
                )

    format_output(
        data,
        ctx.format,
        columns=[
            ("checklist", "Checklist"),
            ("item", "Item"),
            ("member", "Member"),
            ("due", "Due"),
            ("checklist_id", "Checklist ID"),
            ("item_id", "Item ID"),
        ],
        title="Checklists",
        template="{checklist}: {item}",
    )


def _resolve_item_members(
    client: Any, card_id: str, checklists: list[dict]
) -> dict[str, str]:
    """Build a map of member ID to display name for assigned checklist items.

    Returns an empty map (so callers fall back to raw IDs) when no items are
    assigned or the member lookup fails.
    """
    has_members = any(
        item.get("idMember") for cl in checklists for item in cl.get("checkItems", [])
    )
    if not has_members:
        return {}

    try:
        card = client.get_card(card_id)
        members = client.get_board_members(card["idBoard"])
    except Exception as e:
        print_warning(f"Could not resolve member names, showing IDs instead: {e}")
        return {}

    return {m["id"]: m.get("fullName") or m.get("username") or m["id"] for m in members}


def _member_id_from_card(
    ctx: Context, client: Any, card_id: str, member_ref: str
) -> str:
    """Resolve a member reference (ID, username, or name) via the card's board."""
    if is_trello_id(member_ref):
        return member_ref
    card = client.get_card(card_id)
    return ctx.resolver.resolve_member(card["idBoard"], member_ref)


def _member_id_from_checklist(
    ctx: Context, client: Any, checklist_id: str, member_ref: str
) -> str:
    """Resolve a member reference (ID, username, or name) via the checklist's board."""
    if is_trello_id(member_ref):
        return member_ref
    cl = client.get_checklist(checklist_id)
    return ctx.resolver.resolve_member(cl["idBoard"], member_ref)


@checklist.command("create")
@click.argument("card_id")
@click.option("--name", "-n", required=True, help="Checklist name")
@pass_context
def create_checklist(ctx: Context, card_id: str, name: str) -> None:
    """Create a checklist on a card.

    CARD_ID must be a Trello card ID.
    """
    client = ctx.ensure_client()

    try:
        cl = client.create_checklist(card_id, name)
        print_success(f"Created checklist: {cl['name']} ({cl['id']})")
    except Exception as e:
        print_error(f"Failed to create checklist: {e}")


@checklist.command("delete")
@click.argument("checklist_id")
@click.confirmation_option(prompt="Are you sure you want to delete this checklist?")
@pass_context
def delete_checklist(ctx: Context, checklist_id: str) -> None:
    """Delete a checklist."""
    client = ctx.ensure_client()

    try:
        client.delete_checklist(checklist_id)
        print_success(f"Deleted checklist: {checklist_id}")
    except Exception as e:
        print_error(f"Failed to delete checklist: {e}")


@checklist.command("add-item")
@click.argument("checklist_id")
@click.option("--name", "-n", required=True, help="Item name")
@click.option("--checked", is_flag=True, help="Mark as checked")
@click.option(
    "--member",
    "-m",
    help="Member ID, username, or name to assign (see 'board members')",
)
@click.option("--due", help="Due date (ISO format, e.g. 2026-07-01)")
@click.option(
    "--due-reminder",
    type=int,
    help="Minutes before the due date to send a reminder",
)
@pass_context
def add_item(
    ctx: Context,
    checklist_id: str,
    name: str,
    checked: bool,
    member: str | None,
    due: str | None,
    due_reminder: int | None,
) -> None:
    """Add an item to a checklist.

    Use --member and --due to assign a member or due date to the item; both
    require a paid Trello plan (advanced checklists).
    """
    client = ctx.ensure_client()

    try:
        member_id = (
            _member_id_from_checklist(ctx, client, checklist_id, member)
            if member
            else None
        )
        item = client.add_checklist_item(
            checklist_id,
            name,
            checked=checked,
            id_member=member_id,
            due=due,
            due_reminder=due_reminder,
        )
        print_success(f"Added item: {item['name']} ({item['id']})")
    except Exception as e:
        print_error(f"Failed to add item: {e}")


@checklist.command("assign")
@click.argument("card_id")
@click.argument("item_id")
@click.argument("member")
@pass_context
def assign_item(ctx: Context, card_id: str, item_id: str, member: str) -> None:
    """Assign a member to a checklist item.

    CARD_ID is the card containing the item.
    ITEM_ID is the checklist item to assign.
    MEMBER is the member ID, username, or name (see 'board members').

    Requires a paid Trello plan (advanced checklists).
    """
    client = ctx.ensure_client()

    try:
        member_id = _member_id_from_card(ctx, client, card_id, member)
        client.set_checklist_item_member(card_id, item_id, member_id)
        print_success(f"Assigned {member} to item {item_id}")
    except Exception as e:
        print_error(f"Failed to assign member: {e}")


@checklist.command("unassign")
@click.argument("card_id")
@click.argument("item_id")
@pass_context
def unassign_item(ctx: Context, card_id: str, item_id: str) -> None:
    """Remove the assigned member from a checklist item.

    CARD_ID is the card containing the item.
    ITEM_ID is the checklist item to clear.
    """
    client = ctx.ensure_client()

    try:
        client.set_checklist_item_member(card_id, item_id, "")
        print_success(f"Removed assigned member from item {item_id}")
    except Exception as e:
        print_error(f"Failed to unassign member: {e}")


@checklist.command("set-due")
@click.argument("card_id")
@click.argument("item_id")
@click.argument("due")
@click.option(
    "--reminder",
    type=int,
    help="Minutes before the due date to send a reminder (-1 to clear)",
)
@pass_context
def set_item_due(
    ctx: Context, card_id: str, item_id: str, due: str, reminder: int | None
) -> None:
    """Set or clear the due date on a checklist item.

    CARD_ID is the card containing the item.
    ITEM_ID is the checklist item to update.
    DUE is an ISO date (e.g. 2026-07-01), or 'null' to remove the due date.

    Requires a paid Trello plan (advanced checklists).
    """
    client = ctx.ensure_client()
    due_value = "" if due.lower() == "null" else due

    try:
        client.set_checklist_item_due(
            card_id, item_id, due_value, due_reminder=reminder
        )
        if due_value:
            print_success(f"Set due date on item {item_id} to {due_value}")
        else:
            print_success(f"Removed due date from item {item_id}")
    except Exception as e:
        print_error(f"Failed to set due date: {e}")


@checklist.command("edit-item")
@click.argument("card_id")
@click.argument("item_id")
@click.option("--name", "name", required=True, help="New item text")
@pass_context
def edit_item(ctx: Context, card_id: str, item_id: str, name: str) -> None:
    """Edit a checklist item's text.

    CARD_ID is the card containing the item.
    ITEM_ID is the checklist item to update.
    """
    client = ctx.ensure_client()

    try:
        client.update_checklist_item(card_id, item_id, name=name)
        print_success(f"Updated item: {item_id}")
    except Exception as e:
        print_error(f"Failed to update item: {e}")


@checklist.command("check")
@click.argument("card_id")
@click.argument("item_id")
@click.option("--uncheck", is_flag=True, help="Mark as incomplete instead")
@pass_context
def check_item(ctx: Context, card_id: str, item_id: str, uncheck: bool) -> None:
    """Mark a checklist item as complete (or incomplete with --uncheck).

    CARD_ID is the card containing the item.
    ITEM_ID is the checklist item to update.
    """
    client = ctx.ensure_client()
    state = "incomplete" if uncheck else "complete"

    try:
        client.update_checklist_item(card_id, item_id, state)
        action = "Unchecked" if uncheck else "Checked"
        print_success(f"{action} item: {item_id}")
    except Exception as e:
        print_error(f"Failed to update item: {e}")


@checklist.command("delete-item")
@click.argument("checklist_id")
@click.argument("item_id")
@pass_context
def delete_item(ctx: Context, checklist_id: str, item_id: str) -> None:
    """Delete a checklist item."""
    client = ctx.ensure_client()

    try:
        client.delete_checklist_item(checklist_id, item_id)
        print_success(f"Deleted item: {item_id}")
    except Exception as e:
        print_error(f"Failed to delete item: {e}")
