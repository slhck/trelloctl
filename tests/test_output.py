"""Verify typed card data and lossless output across formats."""

import csv
import io
import json

from trelloctl.models import card_data
from trelloctl.output import OutputFormat, format_output


def test_card_json_keeps_types_and_relationships(capsys):
    """Automation can filter membership and labels without parsing display text."""
    card = {
        "id": "card1",
        "name": "Fix, then deploy\nwith care",
        "closed": False,
        "idMembers": ["member1", "member2"],
        "idBoard": "board1",
        "idList": "list1",
        "labels": [{"id": "label1", "name": "Bug", "color": "red"}],
    }
    format_output(card_data(card), OutputFormat.JSON)
    result = json.loads(capsys.readouterr().out)
    assert result["closed"] is False
    assert result["due_complete"] is False
    assert result["due"] is None
    assert result["labels"] == card["labels"]
    assert result["member_ids"] == card["idMembers"]
    assert result["board_id"] == "board1"
    assert result["list_id"] == "list1"


def test_csv_preserves_punctuation_newlines_and_nested_data(capsys):
    """CSV quoting preserves literal text and structured JSON cells."""
    row = {
        "name": 'Fix, then "deploy"\nwith care',
        "labels": [{"id": "label1", "name": "Bug, urgent", "color": "red"}],
        "member_ids": ["member1", "member2"],
        "closed": False,
    }
    format_output([row], OutputFormat.CSV)
    result = next(csv.DictReader(io.StringIO(capsys.readouterr().out)))
    assert result["name"] == row["name"]
    assert json.loads(result["labels"]) == row["labels"]
    assert json.loads(result["member_ids"]) == row["member_ids"]
    assert result["closed"] == "False"


def test_table_renders_labels_without_python_repr(capsys):
    """Readable tables keep label names while JSON keeps the underlying objects."""
    format_output(
        [{"labels": [{"id": "a", "name": "Bug", "color": "red"}], "closed": False}],
        OutputFormat.TABLE,
    )
    result = capsys.readouterr().out
    assert "Bug" in result
    assert "No" in result
    assert "'color'" not in result
