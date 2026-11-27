"""Read and set typed custom field values."""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

import click

from trelloctl.cli import Context, pass_context
from trelloctl.commands.attachment import card_options
from trelloctl.output import exit_with_error, format_output, output_result


@click.group()
def field() -> None:
    """Inspect board custom fields and read or set card values."""


def resolve_field(definitions: list[dict], reference: str) -> dict:
    """Resolve a field ID or a case-insensitive name without ambiguity."""
    for definition in definitions:
        if definition["id"] == reference:
            return definition
    exact = [
        item for item in definitions if item["name"].casefold() == reference.casefold()
    ]
    matches = exact or [
        item for item in definitions if reference.casefold() in item["name"].casefold()
    ]
    if len(matches) != 1:
        raise ValueError(
            f"{'Multiple custom fields match' if matches else 'Custom field not found'}: {reference}"
        )
    return matches[0]


def field_payload(definition: dict, value: str) -> dict:
    """Validate user input and encode Trello's typed, string-valued payload."""
    kind = definition["type"]
    if kind == "list":
        options = definition.get("options", [])
        matches = [item for item in options if item["id"] == value]
        if not matches:
            matches = [
                item
                for item in options
                if item["value"]["text"].casefold() == value.casefold()
            ]
        if len(matches) != 1:
            raise ValueError(f"Unknown or ambiguous option: {value}")
        return {"idValue": matches[0]["id"]}
    if kind == "checkbox":
        if value.casefold() not in ("true", "false"):
            raise ValueError("Checkbox value must be true or false")
        return {"value": {"checked": value.casefold()}}
    if kind == "number":
        try:
            number = Decimal(value)
        except InvalidOperation:
            raise ValueError("Number field requires a finite number") from None
        if not number.is_finite():
            raise ValueError("Number field requires a finite number")
    elif kind == "date":
        try:
            date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("Date field requires an ISO date or timestamp") from None
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        value = date.isoformat()
    elif kind != "text":
        raise ValueError(f"Unsupported custom field type: {kind}")
    return {"value": {kind: value}}


def _card_fields(
    ctx: Context, card: str, board: str | None, list_name: str | None
) -> tuple[str, list[dict]]:
    """Always use the card's actual board to resolve field definitions."""
    card_ref = ctx.resolver.resolve_card_ref(card, board, list_name)
    client = ctx.ensure_client()
    card_data = client.get_card(card_ref)
    return card_data["id"], client.get_custom_fields(card_data["idBoard"])


@field.command("list")
@click.argument("board")
@pass_context
def list_fields(ctx: Context, board: str) -> None:
    """List board field definitions, types, and dropdown options."""
    try:
        data = ctx.ensure_client().get_custom_fields(ctx.resolver.resolve_board(board))
        format_output(
            data,
            ctx.format,
            columns=[
                ("id", "ID"),
                ("name", "Name"),
                ("type", "Type"),
                ("options", "Options"),
            ],
            template="{id}",
        )
    except Exception as exc:
        exit_with_error(f"Failed to list custom fields: {exc}")


@field.command("values")
@click.argument("card")
@card_options
@pass_context
def field_values(
    ctx: Context, card: str, board: str | None, list_name: str | None
) -> None:
    """Read a card's values, with field names and types."""
    try:
        card_id, definitions = _card_fields(ctx, card, board, list_name)
        items = {
            item["idCustomField"]: item
            for item in ctx.ensure_client().get_custom_field_items(card_id)
        }
        data = []
        for definition in definitions:
            item = items.get(definition["id"], {})
            value = None
            if definition["type"] == "list":
                value = next(
                    (
                        option["value"]["text"]
                        for option in definition.get("options", [])
                        if option["id"] == item.get("idValue")
                    ),
                    None,
                )
            elif item.get("value"):
                value = next(iter(item["value"].values()))
                if definition["type"] == "checkbox":
                    value = value == "true"
                # Keep decimal strings lossless for a read/write round trip.
            data.append(
                {
                    "id": definition["id"],
                    "name": definition["name"],
                    "type": definition["type"],
                    "value": value,
                }
            )
        format_output(
            data,
            ctx.format,
            columns=[
                ("id", "ID"),
                ("name", "Name"),
                ("type", "Type"),
                ("value", "Value"),
            ],
            template="{name}: {value}",
        )
    except Exception as exc:
        exit_with_error(f"Failed to read custom fields: {exc}")


@field.command("set")
@click.argument("card")
@click.argument("field_ref", metavar="FIELD")
@click.argument("value")
@card_options
@pass_context
def set_field(
    ctx: Context,
    card: str,
    field_ref: str,
    value: str,
    board: str | None,
    list_name: str | None,
) -> None:
    """Set a field by ID or name; dropdowns accept an option ID or exact text."""
    try:
        card_id, definitions = _card_fields(ctx, card, board, list_name)
        definition = resolve_field(definitions, field_ref)
        payload = field_payload(definition, value)
        ctx.ensure_client().set_custom_field(card_id, definition["id"], payload)
        output_result(
            {"id": card_id, "field_id": definition["id"], **payload},
            ctx.format,
            f"Set {definition['name']} on card {card_id}",
        )
    except Exception as exc:
        exit_with_error(f"Failed to set custom field: {exc}")


@field.command("clear")
@click.argument("card")
@click.argument("field_ref", metavar="FIELD")
@card_options
@pass_context
def clear_field(
    ctx: Context, card: str, field_ref: str, board: str | None, list_name: str | None
) -> None:
    """Clear a card's field value without deleting its board definition."""
    try:
        card_id, definitions = _card_fields(ctx, card, board, list_name)
        definition = resolve_field(definitions, field_ref)
        ctx.ensure_client().set_custom_field(
            card_id, definition["id"], {"idValue": "", "value": ""}
        )
        output_result(
            {"id": card_id, "field_id": definition["id"], "value": None},
            ctx.format,
            f"Cleared {definition['name']} on card {card_id}",
        )
    except Exception as exc:
        exit_with_error(f"Failed to clear custom field: {exc}")
