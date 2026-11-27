"""Read multiline command text from arguments, files, stdin or an editor."""

from pathlib import Path
import sys

import click


def read_text(
    value: str | None,
    filename: str | None,
    editor: bool,
    *,
    initial: str = "",
    required: bool = False,
) -> str | None:
    """Read one explicit source without normalizing whitespace or newlines."""
    if sum((value is not None, filename is not None, editor)) > 1:
        raise click.UsageError("Use only one text argument, file option, or --editor")
    if filename is not None:
        try:
            value = (
                sys.stdin.read()
                if filename == "-"
                else Path(filename).read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError) as exc:
            raise click.ClickException(f"Could not read text: {exc}") from None
    elif editor:
        value = click.edit(initial, extension=".md")
        if value is None:
            raise click.ClickException("Editor closed without saving; no changes made")
    if required and (value is None or not value.strip()):
        raise click.UsageError("Comment text is required")
    return value
