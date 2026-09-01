"""Tests for configuration and credential lookup."""

from trelloctl.config import API_KEY_ENV_VAR, TOKEN_ENV_VAR, Config, SERVICE_NAME


def test_api_key_environment_variable_takes_precedence(
    monkeypatch, mocker, tmp_path
) -> None:
    """Use a process-provided key without accessing the system keyring."""
    monkeypatch.setenv(API_KEY_ENV_VAR, "environment-key")
    keyring_get = mocker.patch("trelloctl.config.keyring.get_password")
    config = Config()
    config.config_dir = tmp_path

    assert config.get_api_key() == "environment-key"
    keyring_get.assert_not_called()


def test_token_environment_variable_takes_precedence(
    monkeypatch, mocker, tmp_path
) -> None:
    """Use a process-provided token without accessing the system keyring."""
    monkeypatch.setenv(TOKEN_ENV_VAR, "environment-token")
    keyring_get = mocker.patch("trelloctl.config.keyring.get_password")
    config = Config()
    config.config_dir = tmp_path

    assert config.get_token() == "environment-token"
    keyring_get.assert_not_called()


def test_credentials_fall_back_to_keyring(mocker, tmp_path) -> None:
    """Retain the existing keyring behavior when no environment is set."""
    keyring_get = mocker.patch(
        "trelloctl.config.keyring.get_password", side_effect=["keyring-key", "keyring-token"]
    )
    config = Config()
    config.config_dir = tmp_path

    assert config.get_api_key() == "keyring-key"
    assert config.get_token() == "keyring-token"
    assert keyring_get.call_args_list == [
        mocker.call(SERVICE_NAME, "default:api_key"),
        mocker.call(SERVICE_NAME, "default:token"),
    ]
