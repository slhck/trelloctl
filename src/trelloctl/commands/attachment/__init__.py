"""Manage uploaded files and linked attachments on cards."""

from pathlib import Path

import click

from trelloctl.cli import Context, pass_context
from trelloctl.output import exit_with_error, format_output, output_result


def card_options(function):
    """Add optional scope for card names."""
    function = click.option("--board", "-b", help="Board name, ID, or URL")(function)
    return click.option("--list", "list_name", help="List name or ID for card names")(
        function
    )


@click.group()
def attachment() -> None:
    """List, add, download, and remove card attachments."""


@attachment.command("list")
@click.argument("card")
@card_options
@pass_context
def list_attachments(
    ctx: Context, card: str, board: str | None, list_name: str | None
) -> None:
    """List attachments for a card ID, URL, or scoped name."""
    try:
        card_id = ctx.resolver.resolve_card_ref(card, board, list_name)
        data = ctx.ensure_client().get_attachments(card_id)
        format_output(
            data,
            ctx.format,
            columns=[("name", "Name"), ("id", "ID"), ("url", "URL")],
            template="{id}",
        )
    except Exception as exc:
        exit_with_error(f"Failed to list attachments: {exc}")


@attachment.command("add")
@click.argument("card")
@click.option(
    "--file",
    "file_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Local file to upload",
)
@click.option("--url", help="HTTP or HTTPS URL to attach")
@click.option("--name", help="Attachment display name")
@card_options
@pass_context
def add_attachment(
    ctx: Context,
    card: str,
    file_path: Path | None,
    url: str | None,
    name: str | None,
    board: str | None,
    list_name: str | None,
) -> None:
    """Upload a file or attach a URL (provide exactly one source)."""
    if (file_path is None) == (url is None):
        raise click.UsageError("Provide exactly one of --file or --url")
    try:
        card_id = ctx.resolver.resolve_card_ref(card, board, list_name)
        result = ctx.ensure_client().add_attachment(
            card_id, file=file_path, url=url, name=name
        )
        output_result(result, ctx.format, f"Added attachment: {result['id']}")
    except Exception as exc:
        exit_with_error(f"Failed to add attachment: {exc}")


@attachment.command("download")
@click.argument("card")
@click.argument("attachment_id")
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Destination file (default: attachment filename)",
)
@click.option("--force", is_flag=True, help="Replace an existing destination file")
@card_options
@pass_context
def download_attachment(
    ctx: Context,
    card: str,
    attachment_id: str,
    output: Path | None,
    force: bool,
    board: str | None,
    list_name: str | None,
) -> None:
    """Download an attachment to disk; print its ID or metadata."""
    try:
        card_id = ctx.resolver.resolve_card_ref(card, board, list_name)
        client = ctx.ensure_client()
        item = client.get_attachment(card_id, attachment_id)
        if output is None:
            filename = str(item.get("fileName") or item.get("name") or attachment_id)
            filename = filename.replace("\\", "/").rsplit("/", 1)[-1]
            if filename in ("", ".", ".."):
                filename = attachment_id
            output = Path(filename)
        client.download_attachment(card_id, item, output, force=force)
        output_result(
            {"id": attachment_id, "path": str(output.resolve())},
            ctx.format,
            f"Downloaded attachment to {output}",
        )
    except Exception as exc:
        exit_with_error(f"Failed to download attachment: {exc}")


@attachment.command("delete")
@click.argument("card")
@click.argument("attachment_id")
@click.confirmation_option(prompt="Delete this attachment?")
@card_options
@pass_context
def delete_attachment(
    ctx: Context,
    card: str,
    attachment_id: str,
    board: str | None,
    list_name: str | None,
) -> None:
    """Permanently remove an attachment from a card."""
    try:
        card_id = ctx.resolver.resolve_card_ref(card, board, list_name)
        ctx.ensure_client().delete_attachment(card_id, attachment_id)
        output_result(
            {"id": attachment_id, "card_id": card_id},
            ctx.format,
            f"Deleted attachment: {attachment_id}",
        )
    except Exception as exc:
        exit_with_error(f"Failed to delete attachment: {exc}")
