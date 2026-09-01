"""Configuration management for Trello CLI."""

import json
import os
from pathlib import Path

import keyring

SERVICE_NAME = "trelloctl"
API_KEY_ENV_VAR = "TRELLOCTL_API_KEY"
TOKEN_ENV_VAR = "TRELLOCTL_TOKEN"


class Config:
    """Manages Trello CLI configuration and credentials."""

    def __init__(self, profile: str = "default") -> None:
        self.profile = profile
        self.config_dir = Path.home() / ".config" / "trelloctl"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / f"{profile}.json"

    def _load_config(self) -> dict:
        """Load configuration from file."""
        if self.config_file.exists():
            return json.loads(self.config_file.read_text())
        return {}

    def _save_config(self, config: dict) -> None:
        """Save configuration to file."""
        self.config_file.write_text(json.dumps(config, indent=2))

    def get_api_key(self) -> str | None:
        """Get the API key from the environment or keyring."""
        return os.environ.get(API_KEY_ENV_VAR) or keyring.get_password(
            SERVICE_NAME, f"{self.profile}:api_key"
        )

    def set_api_key(self, api_key: str) -> None:
        """Store the API key in keyring."""
        keyring.set_password(SERVICE_NAME, f"{self.profile}:api_key", api_key)

    def get_token(self) -> str | None:
        """Get the token from the environment or keyring."""
        return os.environ.get(TOKEN_ENV_VAR) or keyring.get_password(
            SERVICE_NAME, f"{self.profile}:token"
        )

    def set_token(self, token: str) -> None:
        """Store the token in keyring."""
        keyring.set_password(SERVICE_NAME, f"{self.profile}:token", token)

    def get_default_board(self) -> str | None:
        """Get the default board ID."""
        config = self._load_config()
        return config.get("default_board")

    def set_default_board(self, board_id: str) -> None:
        """Set the default board ID."""
        config = self._load_config()
        config["default_board"] = board_id
        self._save_config(config)

    def is_configured(self) -> bool:
        """Check if credentials are configured."""
        return bool(self.get_api_key() and self.get_token())
