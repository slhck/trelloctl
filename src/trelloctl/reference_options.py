"""Shared CLI options for addressing cards by URL, ID or scoped name."""

from functools import wraps
from typing import Any, Callable

import click

from trelloctl.cli import Context


def card_reference_options(
    function: Callable[..., Any] | None = None, *, board_option: bool = True
) -> Callable[..., Any]:
    """Resolve a callback's card/card_id before calling it.

    Existing commands such as card move already own --board; in that case the
    board value is retained for their callback as well as used for resolution.
    """

    def decorate(callback: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(callback)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            board = kwargs.pop("board", None) if board_option else kwargs.get("board")
            list_ref = kwargs.pop("list_ref", None)
            key = "card_id" if "card_id" in kwargs else "card"
            ctx: Context = click.get_current_context().obj
            try:
                kwargs[key] = ctx.resolver.resolve_card_ref(
                    kwargs[key], board, list_ref
                )
            except Exception as exc:
                raise click.ClickException(str(exc)) from None
            return callback(*args, **kwargs)

        wrapped = click.option(
            "--list",
            "list_ref",
            help="List name or ID to scope card names (requires --board)",
        )(wrapped)
        if board_option:
            wrapped = click.option(
                "--board", "-b", help="Board name, ID or URL to scope card names"
            )(wrapped)
        return wrapped

    return decorate(function) if function else decorate
