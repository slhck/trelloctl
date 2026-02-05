"""Checklist commands."""

import click

from trelloctl.cli import Context, pass_context
from trelloctl.output import format_output, print_error, print_success


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
                }
            )
        else:
            for item in sorted(items, key=lambda i: i.get("pos", 0)):
                state = "x" if item.get("state") == "complete" else " "
                data.append(
                    {
                        "checklist": cl["name"],
                        "checklist_id": cl["id"],
                        "item": f"[{state}] {item['name']}",
                        "item_id": item["id"],
                        "state": item.get("state", ""),
                    }
                )

    format_output(
        data,
        ctx.format,
        columns=[
            ("checklist", "Checklist"),
            ("item", "Item"),
            ("checklist_id", "Checklist ID"),
            ("item_id", "Item ID"),
        ],
        title="Checklists",
        template="{checklist}: {item}",
    )


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
@pass_context
def add_item(ctx: Context, checklist_id: str, name: str, checked: bool) -> None:
    """Add an item to a checklist."""
    client = ctx.ensure_client()

    try:
        item = client.add_checklist_item(checklist_id, name, checked=checked)
        print_success(f"Added item: {item['name']} ({item['id']})")
    except Exception as e:
        print_error(f"Failed to add item: {e}")


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
