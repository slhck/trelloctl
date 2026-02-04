"""Output formatting utilities."""

import json
from enum import Enum
from typing import Any

from rich.console import Console
from rich.table import Table

console = Console()
error_console = Console(stderr=True)


class OutputFormat(str, Enum):
    """Output format options."""

    TABLE = "table"
    JSON = "json"
    CSV = "csv"
    PLAIN = "plain"


def output_json(data: Any) -> None:
    """Output data as JSON."""
    print(json.dumps(data, indent=2, default=str))


def output_csv(data: list[dict], fields: list[str] | None = None) -> None:
    """Output data as CSV."""
    if not data:
        return

    if fields is None:
        fields = list(data[0].keys())

    print(",".join(fields))
    for row in data:
        values = [str(row.get(f, "")).replace(",", ";") for f in fields]
        print(",".join(values))


def output_table(
    data: list[dict],
    columns: list[tuple[str, str]] | None = None,
    title: str | None = None,
) -> None:
    """Output data as a rich table.

    Args:
        data: List of dictionaries to display
        columns: List of (key, header) tuples defining columns
        title: Optional table title
    """
    if not data:
        console.print("[dim]No results[/dim]")
        return

    if columns is None:
        columns = [(k, k.title()) for k in data[0].keys()]

    table = Table(title=title)
    for _, header in columns:
        table.add_column(header)

    for row in data:
        table.add_row(*[str(row.get(key, "")) for key, _ in columns])

    console.print(table)


def output_plain(data: list[dict], template: str) -> None:
    """Output data using a simple template.

    Args:
        data: List of dictionaries
        template: Format string with {key} placeholders
    """
    for row in data:
        print(template.format(**row))


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str) -> None:
    """Print an error message to stderr."""
    error_console.print(f"[red]✗[/red] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]![/yellow] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[blue]ℹ[/blue] {message}")


def format_output(
    data: Any,
    format: OutputFormat,
    columns: list[tuple[str, str]] | None = None,
    title: str | None = None,
    template: str | None = None,
) -> None:
    """Format and output data according to the specified format."""
    if isinstance(data, dict):
        data = [data]

    if format == OutputFormat.JSON:
        output_json(data)
    elif format == OutputFormat.CSV:
        fields = [col[0] for col in columns] if columns else None
        output_csv(data, fields)
    elif format == OutputFormat.PLAIN:
        if template:
            output_plain(data, template)
        else:
            for item in data:
                print(item)
    else:  # TABLE
        output_table(data, columns, title)
