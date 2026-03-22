# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Development Commands

```bash
# Install dependencies
uv sync

# Run the CLI
uv run trelloctl

# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_resolver.py

# Run a specific test
uv run pytest tests/test_resolver.py::test_resolve_board_by_name -v

# Lint and format
uv run ruff check src tests
uv run ruff format src tests

# Type checking
uv run ty check
```

## Architecture

This is a CLI tool for Trello built with Click, using a layered architecture:

**Entry point**: `src/trelloctl/cli.py` - Defines the main Click group and `Context` class that holds shared state (profile, client, resolver, output format). Commands are registered via `_register_commands()`.

**API layer**: `src/trelloctl/client.py` - `TrelloClient` wraps httpx for authenticated Trello API calls. All API methods are defined here (boards, lists, cards, members).

**Name resolution**: `src/trelloctl/resolver.py` - `Resolver` converts user-friendly names to Trello IDs. Supports partial, case-insensitive matching. Caches board/list data to minimize API calls.

**Commands**: `src/trelloctl/commands/{auth,board,list,card}/` - Each subcommand group in its own module. Commands use `@pass_context` decorator to access the shared `Context`.

**Output**: `src/trelloctl/output.py` - `format_output()` handles table/json/csv/plain formatting via Rich.

**Config**: `src/trelloctl/config.py` - Credentials stored in system keyring via `keyring` library. Config files at `~/.config/trelloctl/{profile}.json`.

## Key Patterns

- All board/list/card arguments accept either Trello IDs (24 hex chars) or names with partial matching
- Commands access the authenticated client via `ctx.ensure_client()` which exits with error if not authenticated
- Use `ctx.resolver.resolve_board()`, `resolve_list()`, `resolve_card()` for name→ID resolution
- Output data as list of dicts, pass to `format_output()` with column definitions
