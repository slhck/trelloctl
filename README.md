# trelloctl

[![PyPI version](https://img.shields.io/pypi/v/trelloctl.svg)](https://pypi.org/project/trelloctl)
[![Python package](https://github.com/slhck/trelloctl/actions/workflows/python-package.yml/badge.svg)](https://github.com/slhck/trelloctl/actions/workflows/python-package.yml)

A command-line interface for Trello, written in Python.

## Requirements

- Python 3.11+

## Installation

Simply run it via [uv](https://docs.astral.sh/uv/getting-started/installation/):

```bash
uvx trelloctl
```

Or install via [pipx](https://pipx.pypa.io/latest/installation/).
Or manually via pip:

```bash
pip install trelloctl
```

## Usage

### Authentication

Before using the CLI, you need to authenticate with Trello:

1. Go to the [Trello Power-Up Admin Portal](https://trello.com/power-ups/admin)
2. Create a new Power-Up (required even for personal use)
3. Copy your API key from the Power-Up's "API Key" section
4. Run the login command:

```bash
trelloctl auth login
```

The CLI will guide you through entering your API key and generating a token. Credentials are stored securely in your system keychain.

For an ephemeral or managed environment, set `TRELLOCTL_API_KEY` and
`TRELLOCTL_TOKEN` instead. Environment values take precedence over the keyring and
are never written to it. This supports credential gateways that replace placeholder
query parameters at the network boundary.

To check your authentication status:

```bash
trelloctl auth status
```

To remove stored credentials:

```bash
trelloctl auth logout
```

### Headless Systems

On a Linux server without a desktop environment there is usually no keychain available, and `keyring` will fail to store the credentials. Install the file-based backend from `keyrings.alt` alongside trelloctl:

```bash
uv tool install trelloctl --with keyrings.alt
```

If trelloctl is already installed, add `--force` to the command above. With pipx, run `pipx inject trelloctl keyrings.alt` instead.

Then select the backend, either per shell session:

```bash
export PYTHON_KEYRING_BACKEND=keyrings.alt.file.PlaintextKeyring
```

or permanently in `~/.config/python_keyring/keyringrc.cfg`:

```ini
[backend]
default-keyring=keyrings.alt.file.PlaintextKeyring
```

Finally, log in by passing both values directly, which skips the browser prompts:

```bash
trelloctl auth login --api-key YOUR_KEY --token YOUR_TOKEN
```

The credentials are then written to `~/.local/share/python_keyring/keyring_pass.cfg`. They are only base64-encoded, not encrypted, so restrict the permissions with `chmod 600`. There is also a `keyrings.alt.file.EncryptedKeyring` backend, but it asks for a master password on every command, which makes it impractical for cron jobs and scripts.

If you already use [`pass`](https://www.passwordstore.org/), install `keyring-pass` instead and set `default-keyring=keyring_pass.PasswordStoreBackend` to get proper GPG encryption.

### Basic Command Examples

```bash
# List all boards
trelloctl board list

# List lists on a board (by name or ID)
trelloctl list list "My Board"
trelloctl list list Development

# List cards in a list
trelloctl list cards "To Do" --board Development

# Show board details
trelloctl board show Development

# Create a card
trelloctl card create "To Do" --board Development --name "New task"

# Move a card to another list
trelloctl card move <card_id> Done --board Development

# Mark a card as complete (or undo completion)
trelloctl card complete <card_id>
trelloctl card complete <card_id> --undo

# Find incomplete cards across a board
trelloctl board cards Development --incomplete

# Add or remove an existing label
trelloctl card label <card_id> <label_id>
trelloctl card unlabel <card_id> <label_id>

# Output as JSON
trelloctl --format json board list

# Output as CSV
trelloctl --format csv board list
```

Board and list names support case-insensitive partial matching. Ambiguous names
produce an error listing the matches.

## Finding and addressing cards

Search across accessible boards with Trello's search syntax, or filter the cards
on one board:

```bash
trelloctl search 'is:open due:week' --member me --incomplete
trelloctl search 'release' --board Development --label Urgent --all
trelloctl board cards Development --member me --overdue
trelloctl board cards Development --label Bug --due-before 2026-12-01
```

Search returns up to 100 matching cards by default. Use `--limit N` to change
that or `--all` to fetch all available pages, overriding `--limit`. Trello limits pagination to pages
0 through 100; the CLI warns if it reaches that boundary. Search includes archived
cards unless you pass `--filter open` or include `is:open` in the query.
`board cards` defaults to open cards. Both commands accept `--complete` or
`--incomplete`, `--member`, `--label`, `--overdue`, and `--due-before`.

`--overdue` selects incomplete cards whose due date has passed. `--due-before`
uses an exclusive boundary; a date without a time means midnight UTC at the start
of that day. Timestamps without a time zone are also interpreted as UTC.

Card commands accept IDs, shortlinks, and Trello card URLs. To address a card by
name, provide `--board`; add `--list` if its name is ambiguous within the board:

```bash
trelloctl card show https://trello.com/c/AbCd1234/example
trelloctl card complete 'Fix login' --board Development --list 'To Do'
trelloctl card assign 'Fix login' johndoe --board Development
trelloctl card label 'Fix login' Bug --board Development
```

Board arguments also accept Trello board URLs. Member references accept IDs,
usernames (with or without `@`), full names, and `me`. Label references accept IDs
or board-scoped names. Names use exact matches first, then case-insensitive
partial matches. Ambiguous names produce an error before any change is made.

## Multiline descriptions and comments

Use UTF-8 files or stdin to preserve multiline text:

```bash
trelloctl card create 'To Do' --board Development --name 'Release' --description-file release.md
trelloctl card update AbCd1234 --description-file - < release.md
trelloctl card comment AbCd1234 --text-file comment.md
trelloctl card comment AbCd1234 --text-file - < comment.md
```

Use `--editor` to open the configured editor for a description or comment.
Updating a description starts with its current text. Choose one source per
command: inline text, a file, stdin, or the editor. Closing the editor without
saving cancels the command.

## Scripting

Use `--format json` to get machine-readable output from any command except `auth login` and `auth logout`.

- Commands that return one item, including `show` commands and all write commands, print a JSON object. Commands that return several items print a JSON array.
- Every write command returns an object with an `id`. For example, `card create` returns the same fields as `card show`, including `url`. Assignment, label, deletion, and comment commands return operation-specific results.
- With `--format plain`, write commands print only the ID.
- JSON results that return full cards (`show`, `create`, `update`, `move`,
  `archive`, `complete`, search, and card listings) use the same fields. `closed` and `due_complete` are booleans, `due` is a date string or
  `null`, `member_ids` is an array of IDs, and `labels` is an array of objects
  containing `id`, `name`, and `color`. Results also include `board_id` and `list_id`.
- Board and list results also use booleans for `closed`.
- CSV quotes commas, quotes, and newlines. Nested objects and arrays are encoded as
  JSON within a cell. Tables display label names and Yes/No values.
- Failed commands print the error to stderr, print nothing to stdout, and exit with a non-zero status.

The structured fields replace the earlier display strings for `labels` and
`closed`. Scripts consuming those fields must use the new types.

```bash
card_id=$(trelloctl --format plain card create "To Do" --board Development --name "New task")
trelloctl --format json checklist create "$card_id" --name "Tasks"
```

## Command Reference

### Global Options

- `--format`, `-f`: Output format: `table` (default), `json`, `csv`, `plain`
- `--profile`, `-p`: Configuration profile to use (default: `default`)
- `--version`: Show version and exit
- `--help`: Show help and exit

### `trelloctl auth`

Authentication commands.

- `auth login`: Set up authentication with Trello
- `auth status`: Check authentication status
- `auth logout`: Remove stored credentials

### `trelloctl search`

- `search <query> [--board <board>] [--limit N] [--all]`: Search cards across boards.
- `--partial`: Match word prefixes.
- `--filter open|closed|all`: Filter archive state (default: all).
- `--member`, `--label`, `--overdue`, `--due-before`, and `--complete|--incomplete`:
  Apply the same filters as `board cards`.

### `trelloctl board`

Board management commands.

- `board cards <board> [--filter open|closed|all] [--complete|--incomplete]` lists
  cards across all lists. It defaults to open (unarchived) cards, including both
  complete and incomplete cards. Use `--filter all` to include archived cards.

- `board list [--filter]`: List all accessible boards
- `board show <board>`: Show details of a board
- `board create --name <name>`: Create a new board
- `board close <board>`: Close (archive) a board
- `board delete <board>`: Delete a board permanently
- `board labels <board>`: List labels on a board
- `board members <board>`: List members of a board

### `trelloctl list`

List management commands.

- `list list <board>`: List all lists on a board
- `list show <list> --board <board>`: Show details of a list
- `list create <board> --name <name>`: Create a new list
- `list archive <list> --board <board>`: Archive a list
- `list cards <list> --board <board>`: List all cards in a list

### `trelloctl card`

Card management commands.

- `card complete <card_id> [--undo]` marks a card as complete or incomplete.
- `card label <card> <label>` adds an existing label by ID or name.
- `card unlabel <card> <label>` removes a label. Use `board labels <board>`
  to find label IDs.

Completion sets Trello's `dueComplete` flag, including on cards without a due
date. It does not move or archive the card or complete its checklist items.
Card details, write results, and card listings include `due_complete` as a JSON
boolean. See the [Trello card API](https://developer.atlassian.com/cloud/trello/rest/api-group-cards/#api-cards-id-put).

- `card show <card_id>`: Show details of a card
- `card create <list> --board <board> --name <name>`: Create a new card
- `card move <card_id> <target_list> --board <board>`: Move a card to another list
- `card update <card> [--name] [--description | --description-file | --editor] [--due]`: Update a card
- `card archive <card_id>`: Archive a card
- `card delete <card_id>`: Delete a card permanently
- `card assign <card_id> <member_id>`: Assign a member to a card
- `card unassign <card_id> <member_id>`: Remove a member from a card
- `card comment <card> [<text> | --text-file <path> | --editor]`: Add a comment to a card
- `card comments <card_id>`: List comments on a card

### `trelloctl checklist`

Checklist management commands.

- `checklist list <card_id>`: List all checklists and items on a card
- `checklist create <card_id> --name <name>`: Create a checklist on a card
- `checklist delete <checklist_id>`: Delete a checklist
- `checklist add-item <checklist_id> --name <name> [--checked] [--member <member>] [--due <date>] [--due-reminder <minutes>]`: Add an item to a checklist
- `checklist check <card_id> <item_id> [--uncheck]`: Mark a checklist item as complete or incomplete
- `checklist assign <card_id> <item_id> <member>`: Assign a member to a checklist item
- `checklist unassign <card_id> <item_id>`: Remove the assigned member from a checklist item
- `checklist set-due <card_id> <item_id> <due> [--reminder <minutes>]`: Set or clear a checklist item's due date (`null` to clear)
- `checklist edit-item <card_id> <item_id> --name <name>`: Edit a checklist item's text
- `checklist delete-item <checklist_id> <item_id>`: Delete a checklist item

The `<member>` argument accepts a member ID, username, or full name (partial,
case-insensitive matching), the same way board, list, and card names are resolved.

Per-item members and due dates (`add-item --member`/`--due`, `assign`, `unassign`,
`set-due`) use Trello's advanced checklists, which require a paid Trello plan. On free
plans the API accepts the request without error but does not store the value.

### `trelloctl attachment`

- `attachment list <card>`: List file and URL attachments.
- `attachment add <card> --file <path> [--name <name>]`: Upload a local file.
- `attachment add <card> --url <url> [--name <name>]`: Attach an HTTP or HTTPS URL.
- `attachment download <card> <attachment_id> [--output <path>] [--force]`:
  Save an attachment to disk. The default filename comes from the attachment;
  existing files require `--force` to replace them.
- `attachment delete <card> <attachment_id> [--yes]`: Remove an attachment.

All attachment commands accept `--board` and `--list` for card names. Downloads
print metadata in the selected output format and save the file separately.

### `trelloctl label`

- `label list <board>`: List label definitions.
- `label create <board> --name <name> [--color <color>]`: Create a label.
- `label show <label> [--board <board>]`: Show a label.
- `label update <label> [--board <board>] [--name <name>] [--color <color>]`:
  Rename or recolor a label. Use `--color none` to clear its color.
- `label delete <label> [--board <board>] [--yes]`: Delete a label from its board
  and all cards using it.

Use `--board` when addressing a label by name. Color choices include Trello's
base colors and their `_light` and `_dark` variants; see `label create --help`.

### `trelloctl field`

- `field list <board>`: List custom field definitions, types, and dropdown options.
- `field values <card>`: Read values with their field names and types.
- `field set <card> <field> <value>`: Set a value by field ID or name.
- `field clear <card> <field>`: Clear a card's field value.

Card field commands accept `--board` and `--list` for scoped names. Text, number,
date, checkbox, and dropdown fields are supported. Use `true` or `false` for
checkboxes, an ISO date or timestamp for dates, and an option ID or exact option
text for dropdowns. Dates without a time zone use UTC. `field clear` removes a
value; the text `null` remains available as a literal value for text fields.
`field values` returns numbers as decimal strings to preserve their precision,
checkboxes as booleans, and unset values as `null`.

```bash
trelloctl field list Development
trelloctl field set AbCd1234 Priority High
trelloctl field set AbCd1234 Effort 3.5
trelloctl field values AbCd1234
trelloctl field clear AbCd1234 Effort
```

### Multiple Profiles

You can use multiple Trello accounts by specifying a profile:

```bash
# Set up a work profile
TRELLOCTL_PROFILE=work trelloctl auth login

# Use the work profile
trelloctl --profile work board list
```

## License

MIT License

Copyright (c) 2025 Werner Robitza

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
