"""Trello API client."""

from typing import Any

import httpx

BASE_URL = "https://api.trello.com/1"


class TrelloClient:
    """HTTP client for Trello API."""

    def __init__(self, api_key: str, token: str) -> None:
        self.api_key = api_key
        self.token = token
        self._client = httpx.Client(timeout=30.0)

    def _auth_params(self) -> dict[str, str]:
        """Return authentication parameters."""
        return {"key": self.api_key, "token": self.token}

    def _request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        json: dict | None = None,
    ) -> Any:
        """Make an authenticated request to Trello API."""
        url = f"{BASE_URL}{path}"
        all_params = self._auth_params()
        if params:
            all_params.update(params)

        response = self._client.request(method, url, params=all_params, json=json)
        response.raise_for_status()

        if response.status_code == 204:
            return None
        return response.json()

    def get(self, path: str, params: dict | None = None) -> Any:
        """Make a GET request."""
        return self._request("GET", path, params=params)

    def post(
        self, path: str, params: dict | None = None, json: dict | None = None
    ) -> Any:
        """Make a POST request."""
        return self._request("POST", path, params=params, json=json)

    def put(
        self, path: str, params: dict | None = None, json: dict | None = None
    ) -> Any:
        """Make a PUT request."""
        return self._request("PUT", path, params=params, json=json)

    def delete(self, path: str, params: dict | None = None) -> Any:
        """Make a DELETE request."""
        return self._request("DELETE", path, params=params)

    # Board methods
    def get_boards(self, filter: str = "open") -> list[dict]:
        """Get all boards for the authenticated user."""
        return self.get("/members/me/boards", params={"filter": filter})

    def get_board(self, board_id: str) -> dict:
        """Get a board by ID."""
        return self.get(f"/boards/{board_id}")

    def create_board(self, name: str, desc: str = "") -> dict:
        """Create a new board."""
        return self.post("/boards", params={"name": name, "desc": desc})

    def close_board(self, board_id: str, closed: bool = True) -> dict:
        """Close or reopen a board."""
        return self.put(f"/boards/{board_id}", params={"closed": str(closed).lower()})

    def delete_board(self, board_id: str) -> None:
        """Delete a board."""
        self.delete(f"/boards/{board_id}")

    def get_board_lists(self, board_id: str, filter: str = "open") -> list[dict]:
        """Get all lists on a board."""
        return self.get(f"/boards/{board_id}/lists", params={"filter": filter})

    def get_board_labels(self, board_id: str) -> list[dict]:
        """Get all labels on a board."""
        return self.get(f"/boards/{board_id}/labels")

    def get_board_members(self, board_id: str) -> list[dict]:
        """Get all members of a board."""
        return self.get(f"/boards/{board_id}/members")

    # List methods
    def get_list(self, list_id: str) -> dict:
        """Get a list by ID."""
        return self.get(f"/lists/{list_id}")

    def create_list(self, board_id: str, name: str, pos: str = "bottom") -> dict:
        """Create a new list on a board."""
        return self.post(
            "/lists", params={"idBoard": board_id, "name": name, "pos": pos}
        )

    def archive_list(self, list_id: str, closed: bool = True) -> dict:
        """Archive or unarchive a list."""
        return self.put(f"/lists/{list_id}", params={"closed": str(closed).lower()})

    def get_list_cards(self, list_id: str) -> list[dict]:
        """Get all cards in a list."""
        return self.get(f"/lists/{list_id}/cards")

    # Card methods
    def get_card(self, card_id: str) -> dict:
        """Get a card by ID."""
        return self.get(f"/cards/{card_id}")

    def create_card(
        self,
        list_id: str,
        name: str,
        desc: str = "",
        pos: str = "bottom",
        due: str | None = None,
        labels: list[str] | None = None,
        members: list[str] | None = None,
    ) -> dict:
        """Create a new card."""
        params: dict[str, Any] = {
            "idList": list_id,
            "name": name,
            "desc": desc,
            "pos": pos,
        }
        if due:
            params["due"] = due
        if labels:
            params["idLabels"] = ",".join(labels)
        if members:
            params["idMembers"] = ",".join(members)
        return self.post("/cards", params=params)

    def update_card(self, card_id: str, **kwargs: Any) -> dict:
        """Update a card."""
        return self.put(f"/cards/{card_id}", json=kwargs)

    def move_card(self, card_id: str, list_id: str, pos: str = "bottom") -> dict:
        """Move a card to a different list."""
        return self.put(f"/cards/{card_id}", params={"idList": list_id, "pos": pos})

    def archive_card(self, card_id: str, closed: bool = True) -> dict:
        """Archive or unarchive a card."""
        return self.put(f"/cards/{card_id}", params={"closed": str(closed).lower()})

    def delete_card(self, card_id: str) -> None:
        """Delete a card."""
        self.delete(f"/cards/{card_id}")

    def add_card_member(self, card_id: str, member_id: str) -> list[dict]:
        """Add a member to a card."""
        return self.post(f"/cards/{card_id}/idMembers", params={"value": member_id})

    def remove_card_member(self, card_id: str, member_id: str) -> list[dict]:
        """Remove a member from a card."""
        return self.delete(f"/cards/{card_id}/idMembers/{member_id}")

    def add_card_comment(self, card_id: str, text: str) -> dict:
        """Add a comment to a card."""
        return self.post(f"/cards/{card_id}/actions/comments", params={"text": text})

    def get_card_comments(self, card_id: str) -> list[dict]:
        """Get comments on a card."""
        return self.get(f"/cards/{card_id}/actions", params={"filter": "commentCard"})

    # Checklist methods
    def get_card_checklists(self, card_id: str) -> list[dict]:
        """Get all checklists on a card."""
        return self.get(f"/cards/{card_id}/checklists")

    def get_checklist(self, checklist_id: str) -> dict:
        """Get a checklist by ID."""
        return self.get(f"/checklists/{checklist_id}")

    def create_checklist(self, card_id: str, name: str) -> dict:
        """Create a checklist on a card."""
        return self.post(f"/cards/{card_id}/checklists", params={"name": name})

    def delete_checklist(self, checklist_id: str) -> None:
        """Delete a checklist."""
        self.delete(f"/checklists/{checklist_id}")

    def add_checklist_item(
        self,
        checklist_id: str,
        name: str,
        checked: bool = False,
        id_member: str | None = None,
        due: str | None = None,
        due_reminder: int | None = None,
    ) -> dict:
        """Add an item to a checklist.

        If id_member or due is given, the item is assigned to that member or
        given that due date. due_reminder is the number of minutes before the
        due date to send a reminder. Per-item members and due dates require a
        paid Trello plan (advanced checklists); on free plans the API accepts
        the values but does not store them.
        """
        params: dict[str, str] = {"name": name, "checked": str(checked).lower()}
        if id_member:
            params["idMember"] = id_member
        if due:
            params["due"] = due
        if due_reminder is not None:
            params["dueReminder"] = str(due_reminder)
        return self.post(f"/checklists/{checklist_id}/checkItems", params=params)

    def update_checklist_item(
        self,
        card_id: str,
        check_item_id: str,
        state: str | None = None,
        *,
        name: str | None = None,
    ) -> dict:
        """Update a checklist item's state and/or text.

        ``state`` may be ``complete`` or ``incomplete``. ``name`` updates the
        item's text. At least one field must be provided.
        """
        params: dict[str, str] = {}
        if state is not None:
            params["state"] = state
        if name is not None:
            params["name"] = name
        if not params:
            raise ValueError("At least one checklist item field must be provided")

        return self.put(
            f"/cards/{card_id}/checkItem/{check_item_id}",
            params=params,
        )

    def set_checklist_item_member(
        self, card_id: str, check_item_id: str, id_member: str
    ) -> dict:
        """Assign a member to a checklist item.

        Pass an empty string for id_member to remove the assigned member. A
        checklist item holds at most one member. Requires a paid Trello plan
        (advanced checklists); on free plans the value is silently dropped.
        """
        return self.put(
            f"/cards/{card_id}/checkItem/{check_item_id}",
            params={"idMember": id_member},
        )

    def set_checklist_item_due(
        self,
        card_id: str,
        check_item_id: str,
        due: str,
        due_reminder: int | None = None,
    ) -> dict:
        """Set a checklist item's due date.

        Pass an empty string for due to remove the due date. due_reminder is
        the number of minutes before the due date to send a reminder (-1 to
        clear it). Requires a paid Trello plan (advanced checklists); on free
        plans the value is silently dropped.
        """
        params: dict[str, str] = {"due": due}
        if due_reminder is not None:
            params["dueReminder"] = str(due_reminder)
        return self.put(
            f"/cards/{card_id}/checkItem/{check_item_id}",
            params=params,
        )

    def delete_checklist_item(self, checklist_id: str, check_item_id: str) -> None:
        """Delete a checklist item."""
        self.delete(f"/checklists/{checklist_id}/checkItems/{check_item_id}")

    # Member methods
    def get_me(self) -> dict:
        """Get the authenticated user."""
        return self.get("/members/me")
