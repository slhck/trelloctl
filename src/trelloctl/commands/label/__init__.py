"""Manage board label definitions."""

import click

from trelloctl.cli import Context, pass_context
from trelloctl.output import exit_with_error, format_output, output_result

# Trello supports base colors and light/dark variants; none removes color.
_BASE_COLORS = (
    "green",
    "yellow",
    "orange",
    "red",
    "purple",
    "blue",
    "sky",
    "lime",
    "pink",
    "black",
)
COLORS = click.Choice(
    [
        "none",
        *_BASE_COLORS,
        *[f"{color}_{shade}" for color in _BASE_COLORS for shade in ("light", "dark")],
    ]
)


@click.group()
def label() -> None:
    """Create, inspect, update, and delete board labels."""


@label.command("list")
@click.argument("board")
@pass_context
def list_labels(ctx: Context, board: str) -> None:
    """List a board's labels."""
    try:
        data = ctx.ensure_client().get_board_labels(ctx.resolver.resolve_board(board))
        format_output(
            data,
            ctx.format,
            columns=[("id", "ID"), ("name", "Name"), ("color", "Color")],
            template="{id}",
        )
    except Exception as exc:
        exit_with_error(f"Failed to list labels: {exc}")


@label.command("create")
@click.argument("board")
@click.option("--name", "-n", required=True, help="Label name")
@click.option("--color", type=COLORS, default="none", show_default=True)
@pass_context
def create_label(ctx: Context, board: str, name: str, color: str) -> None:
    """Create a label on a board."""
    try:
        result = ctx.ensure_client().create_label(
            ctx.resolver.resolve_board(board), name, None if color == "none" else color
        )
        output_result(result, ctx.format, f"Created label: {result['id']}")
    except Exception as exc:
        exit_with_error(f"Failed to create label: {exc}")


def _resolve(ctx: Context, label_ref: str, board: str | None) -> str:
    """Allow raw IDs without requiring board context."""
    if board:
        return ctx.resolver.resolve_label(board, label_ref)
    return label_ref


@label.command("show")
@click.argument("label_ref", metavar="LABEL")
@click.option("--board", "-b", help="Resolve a label name on this board")
@pass_context
def show_label(ctx: Context, label_ref: str, board: str | None) -> None:
    """Inspect a label ID, or name with --board."""
    try:
        result = ctx.ensure_client().get_label(_resolve(ctx, label_ref, board))
        format_output(
            result,
            ctx.format,
            columns=[("id", "ID"), ("name", "Name"), ("color", "Color")],
            template="{id}",
        )
    except Exception as exc:
        exit_with_error(f"Failed to show label: {exc}")


@label.command("update")
@click.argument("label_ref", metavar="LABEL")
@click.option("--board", "-b", help="Resolve a label name on this board")
@click.option("--name", "-n", help="New name; an empty string clears it")
@click.option("--color", type=COLORS, help="New color; none clears it")
@pass_context
def update_label(
    ctx: Context, label_ref: str, board: str | None, name: str | None, color: str | None
) -> None:
    """Rename or recolor a label."""
    if name is None and color is None:
        raise click.UsageError("Provide --name and/or --color")
    changes = {}
    if name is not None:
        changes["name"] = name
    if color is not None:
        changes["color"] = None if color == "none" else color
    try:
        result = ctx.ensure_client().update_label(
            _resolve(ctx, label_ref, board), **changes
        )
        output_result(result, ctx.format, f"Updated label: {result['id']}")
    except Exception as exc:
        exit_with_error(f"Failed to update label: {exc}")


@label.command("delete")
@click.argument("label_ref", metavar="LABEL")
@click.option("--board", "-b", help="Resolve a label name on this board")
@click.confirmation_option(prompt="Delete this label from the board and all its cards?")
@pass_context
def delete_label(ctx: Context, label_ref: str, board: str | None) -> None:
    """Permanently delete a label from its board."""
    try:
        label_id = _resolve(ctx, label_ref, board)
        ctx.ensure_client().delete_label(label_id)
        output_result({"id": label_id}, ctx.format, f"Deleted label: {label_id}")
    except Exception as exc:
        exit_with_error(f"Failed to delete label: {exc}")
