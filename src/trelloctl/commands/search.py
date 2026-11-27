"""Search for cards across Trello boards."""

import click

from trelloctl.cli import Context, pass_context
from trelloctl.commands.card import _card_data
from trelloctl.filters import CardFilter, card_filter_options
from trelloctl.output import exit_with_error, format_output, print_warning

PAGE_SIZE = 100
MAX_PAGE = 100


@click.command()
@click.argument("query")
@click.option("--board", "-b", multiple=True, help="Restrict to a board (repeatable)")
@click.option(
    "--limit",
    type=click.IntRange(min=1),
    default=100,
    show_default=True,
    help="Maximum matching cards to return",
)
@click.option(
    "--all",
    "all_results",
    is_flag=True,
    help="Fetch all available search pages (Trello caps pages at 100)",
)
@click.option("--partial", is_flag=True, help="Match word prefixes")
@click.option(
    "--filter",
    "archive",
    type=click.Choice(["open", "closed", "all"]),
    default="all",
    show_default=True,
    help="Filter by archive state",
)
@click.option(
    "--complete/--incomplete", default=None, help="Filter by completion state"
)
@card_filter_options
@pass_context
def search(
    ctx: Context,
    query: str,
    board: tuple[str, ...],
    limit: int,
    all_results: bool,
    partial: bool,
    archive: str,
    complete: bool | None,
    member: str | None,
    label: str | None,
    overdue: bool,
    due_before: str | None,
) -> None:
    """Search cards across boards using Trello's search syntax.

    QUERY can contain Trello operators, e.g. 'is:open due:week'. Filters are
    combined with QUERY. --limit applies after filtering. Dates without a time
    zone are interpreted as UTC.
    """
    if not query.strip():
        raise click.BadParameter("Query cannot be empty.", param_hint="QUERY")
    filters = CardFilter(
        ctx,
        member=member,
        label=label,
        overdue=overdue,
        due_before=due_before,
        complete=complete,
        archive=archive,
        allow_missing_references=True,
    )
    client = ctx.ensure_client()
    cards: list[dict] = []
    seen: set[str] = set()
    try:
        params = {
            "query": query,
            "modelTypes": "cards",
            "card_fields": "all",
            "cards_limit": PAGE_SIZE,
            "partial": str(partial).lower(),
        }
        if board:
            params["idBoards"] = ",".join(
                ctx.resolver.resolve_board(ref) for ref in board
            )
        for page in range(MAX_PAGE + 1):
            response = client.get("/search", params={**params, "cards_page": page})
            batch = response.get("cards", [])
            for card in batch:
                if card["id"] in seen:
                    continue
                seen.add(card["id"])
                if filters.matches(card):
                    cards.append(card)
                    if not all_results and len(cards) >= limit:
                        break
            if not all_results and len(cards) >= limit:
                break
            if len(batch) < PAGE_SIZE:
                break
        else:
            print_warning(
                "Trello's search page limit was reached; results may be incomplete."
            )
    except Exception as exc:
        exit_with_error(f"Failed to search cards: {exc}")

    format_output(
        [_card_data(card) for card in cards],
        ctx.format,
        columns=[
            ("name", "Name"),
            ("due", "Due"),
            ("due_complete", "Complete"),
            ("board_id", "Board ID"),
            ("id", "ID"),
        ],
        title="Search results",
        template="{name} ({id})",
    )
