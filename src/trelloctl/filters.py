"""Shared card filters for board listings and search results."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from trelloctl.cli import Context


def parse_due_before(value: str | None) -> datetime | None:
    """Parse an ISO date or timestamp, interpreting naive values as UTC."""
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise click.BadParameter(
            "Use an ISO date or timestamp, e.g. 2026-12-01 or 2026-12-01T12:00:00Z.",
            param_hint="--due-before",
        ) from None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def card_filter_options(command):
    """Add consistent filtering options to card-listing commands."""
    for option in reversed(
        [
            click.option("--member", help="Assigned member ID, username, name, or me"),
            click.option("--label", help="Label ID or name"),
            click.option(
                "--overdue", is_flag=True, help="Only overdue, incomplete cards"
            ),
            click.option(
                "--due-before", help="Due before an ISO date/time (UTC if no zone)"
            ),
        ]
    ):
        command = option(command)
    return command


class CardFilter:
    """Filter raw API cards while caching board-scoped name lookups."""

    def __init__(
        self,
        ctx: "Context",
        *,
        member: str | None = None,
        label: str | None = None,
        overdue: bool = False,
        due_before: str | None = None,
        complete: bool | None = None,
        archive: str = "all",
        allow_missing_references: bool = False,
    ) -> None:
        self.ctx = ctx
        self.member = member
        self.label = label
        self.overdue = overdue
        self.due_before = parse_due_before(due_before)
        self.complete = complete
        self.archive = archive
        self.allow_missing_references = allow_missing_references
        self.now = datetime.now(timezone.utc)
        self._members: dict[str, str | None] = {}
        self._labels: dict[str, str | None] = {}
        self._me: str | None = None

    def _resolve(self, kind: str, board_id: str, ref: str) -> str | None:
        """Treat absent names as nonmatches across boards; reject ambiguity."""
        cache = self._members if kind == "member" else self._labels
        if board_id not in cache:
            resolver = getattr(self.ctx.resolver, f"resolve_{kind}")
            try:
                cache[board_id] = resolver(board_id, ref)
            except ValueError as exc:
                if self.allow_missing_references and str(exc).lower().startswith(
                    f"{kind} not found"
                ):
                    cache[board_id] = None
                else:
                    raise
        return cache[board_id]

    def matches(self, card: dict, board_id: str | None = None) -> bool:
        """Return whether a card satisfies all selected conditions."""
        if self.archive != "all" and bool(card.get("closed")) != (
            self.archive == "closed"
        ):
            return False
        complete = bool(card.get("dueComplete", False))
        if self.complete is not None and complete != self.complete:
            return False
        if self.overdue or self.due_before is not None:
            value = card.get("due")
            if not value:
                return False
            try:
                due = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return False
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
            if self.overdue and (complete or due >= self.now):
                return False
            if self.due_before is not None and due >= self.due_before:
                return False
        board_id = board_id or card.get("idBoard", "")
        if self.member:
            if self.member.lower() == "me":
                if self._me is None:
                    self._me = self.ctx.ensure_client().get_me()["id"]
                member_id = self._me
            else:
                member_id = self._resolve("member", board_id, self.member)
            if member_id is None or member_id not in card.get("idMembers", []):
                return False
        if self.label:
            label_id = self._resolve("label", board_id, self.label)
            label_ids = card.get("idLabels", []) or [
                label["id"] for label in card.get("labels", [])
            ]
            if label_id is None or label_id not in label_ids:
                return False
        return True
