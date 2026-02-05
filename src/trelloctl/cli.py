"""Main CLI entry point."""

from __future__ import annotations

import os
import sys

import click

from trelloctl import __version__
from trelloctl.client import TrelloClient
from trelloctl.config import Config
from trelloctl.output import OutputFormat, print_error
from trelloctl.resolver import Resolver


class Context:
    """CLI context object holding shared state."""

    def __init__(self) -> None:
        self.profile = os.environ.get("TRELLOCTL_PROFILE", "default")
        self.config = Config(self.profile)
        self.client: TrelloClient | None = None
        self._resolver: Resolver | None = None
        self.format = OutputFormat.TABLE

    def ensure_client(self) -> TrelloClient:
        """Ensure we have an authenticated client."""
        if self.client is None:
            api_key = self.config.get_api_key()
            token = self.config.get_token()

            if not api_key or not token:
                print_error("Not authenticated. Run 'trelloctl auth login' first.")
                sys.exit(1)

            self.client = TrelloClient(api_key, token)

        return self.client

    @property
    def resolver(self) -> Resolver:
        """Get the name resolver."""
        if self._resolver is None:
            self._resolver = Resolver(self.ensure_client())
        return self._resolver


pass_context = click.make_pass_decorator(Context, ensure=True)


@click.group()
@click.version_option(version=__version__, prog_name="trelloctl")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json", "csv", "plain"]),
    default="table",
    help="Output format",
)
@click.option(
    "--profile",
    "-p",
    envvar="TRELLOCTL_PROFILE",
    default="default",
    help="Configuration profile to use",
)
@pass_context
def main(ctx: Context, format: str, profile: str) -> None:
    """trelloctl - Manage your Trello boards from the command line."""
    ctx.format = OutputFormat(format)
    ctx.profile = profile
    ctx.config = Config(profile)


def _register_commands() -> None:
    """Register command groups with the main CLI."""
    from trelloctl.commands import auth, board, card, checklist
    from trelloctl.commands import list as list_cmd

    main.add_command(auth.auth)
    main.add_command(board.board)
    main.add_command(card.card)
    main.add_command(checklist.checklist)
    main.add_command(list_cmd.list_)


_register_commands()


if __name__ == "__main__":
    main()
