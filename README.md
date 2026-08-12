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

# Output as JSON
trelloctl --format json board list

# Output as CSV
trelloctl --format csv board list
```

Names support partial matching (case-insensitive). If multiple items match, you'll be prompted to be more specific.

## Command Reference

### Global Options

| Option | Description |
|--------|-------------|
| `--format`, `-f` | Output format: `table` (default), `json`, `csv`, `plain` |
| `--profile`, `-p` | Configuration profile to use (default: `default`) |
| `--version` | Show version and exit |
| `--help` | Show help and exit |

### `trelloctl auth`

Authentication commands.

| Command | Description |
|---------|-------------|
| `auth login` | Set up authentication with Trello |
| `auth status` | Check authentication status |
| `auth logout` | Remove stored credentials |

### `trelloctl board`

Board management commands.

| Command | Description |
|---------|-------------|
| `board list [--filter]` | List all accessible boards |
| `board show <board>` | Show details of a board |
| `board create --name <name>` | Create a new board |
| `board close <board>` | Close (archive) a board |
| `board delete <board>` | Delete a board permanently |
| `board labels <board>` | List labels on a board |
| `board members <board>` | List members of a board |

### `trelloctl list`

List management commands.

| Command | Description |
|---------|-------------|
| `list list <board>` | List all lists on a board |
| `list show <list> --board <board>` | Show details of a list |
| `list create <board> --name <name>` | Create a new list |
| `list archive <list> --board <board>` | Archive a list |
| `list cards <list> --board <board>` | List all cards in a list |

### `trelloctl card`

Card management commands.

| Command | Description |
|---------|-------------|
| `card show <card_id>` | Show details of a card |
| `card create <list> --board <board> --name <name>` | Create a new card |
| `card move <card_id> <target_list> --board <board>` | Move a card to another list |
| `card update <card_id> [--name] [--description] [--due]` | Update a card |
| `card archive <card_id>` | Archive a card |
| `card delete <card_id>` | Delete a card permanently |
| `card assign <card_id> <member_id>` | Assign a member to a card |
| `card unassign <card_id> <member_id>` | Remove a member from a card |
| `card comment <card_id> <text>` | Add a comment to a card |
| `card comments <card_id>` | List comments on a card |

### `trelloctl checklist`

Checklist management commands.

| Command | Description |
|---------|-------------|
| `checklist list <card_id>` | List all checklists and items on a card |
| `checklist create <card_id> --name <name>` | Create a checklist on a card |
| `checklist delete <checklist_id>` | Delete a checklist |
| `checklist add-item <checklist_id> --name <name> [--checked] [--member <member>] [--due <date>] [--due-reminder <minutes>]` | Add an item to a checklist |
| `checklist check <card_id> <item_id> [--uncheck]` | Mark a checklist item as complete or incomplete |
| `checklist assign <card_id> <item_id> <member>` | Assign a member to a checklist item |
| `checklist unassign <card_id> <item_id>` | Remove the assigned member from a checklist item |
| `checklist set-due <card_id> <item_id> <due> [--reminder <minutes>]` | Set or clear a checklist item's due date (`null` to clear) |
| `checklist delete-item <checklist_id> <item_id>` | Delete a checklist item |

The `<member>` argument accepts a member ID, username, or full name (partial,
case-insensitive matching), the same way board, list, and card names are resolved.

Per-item members and due dates (`add-item --member`/`--due`, `assign`, `unassign`,
`set-due`) use Trello's advanced checklists, which require a paid Trello plan. On free
plans the API accepts the request without error but does not store the value.

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
