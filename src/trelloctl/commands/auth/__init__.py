"""Authentication commands."""

import webbrowser

import click

from trelloctl.cli import Context, pass_context
from trelloctl.output import print_error, print_info, print_success


@click.group()
def auth() -> None:
    """Authentication commands."""
    pass


@auth.command("login")
@click.option("--api-key", prompt=False, help="Trello API key")
@click.option("--token", prompt=False, help="Trello token")
@pass_context
def login(ctx: Context, api_key: str | None, token: str | None) -> None:
    """Set up authentication with Trello.

    You can get your API key at: https://trello.com/app-key
    """
    if not api_key:
        print_info("Get your API key at: https://trello.com/app-key")
        if click.confirm("Open browser to get API key?", default=True):
            webbrowser.open("https://trello.com/app-key")
        api_key = click.prompt("Enter your API key")

    ctx.config.set_api_key(api_key)
    print_success("API key saved")

    if not token:
        token_url = (
            f"https://trello.com/1/authorize?"
            f"expiration=never&scope=read,write,account&"
            f"response_type=token&name=trelloctl&key={api_key}"
        )
        print_info(f"Generate a token at: {token_url}")
        if click.confirm("Open browser to generate token?", default=True):
            webbrowser.open(token_url)
        token = click.prompt("Enter your token")

    ctx.config.set_token(token)
    print_success("Token saved")

    # Verify credentials
    try:
        client = ctx.ensure_client()
        me = client.get_me()
        print_success(f"Authenticated as: {me['fullName']} (@{me['username']})")
    except Exception as e:
        print_error(f"Authentication failed: {e}")


@auth.command("status")
@pass_context
def status(ctx: Context) -> None:
    """Check authentication status."""
    if not ctx.config.is_configured():
        print_error("Not authenticated. Run 'trelloctl auth login' first.")
        return

    try:
        client = ctx.ensure_client()
        me = client.get_me()
        print_success(f"Authenticated as: {me['fullName']} (@{me['username']})")
    except Exception as e:
        print_error(f"Authentication error: {e}")


@auth.command("logout")
@pass_context
def logout(ctx: Context) -> None:
    """Remove stored credentials."""
    import keyring
    from trelloctl.config import SERVICE_NAME

    try:
        keyring.delete_password(SERVICE_NAME, f"{ctx.profile}:api_key")
    except keyring.errors.PasswordDeleteError:
        pass

    try:
        keyring.delete_password(SERVICE_NAME, f"{ctx.profile}:token")
    except keyring.errors.PasswordDeleteError:
        pass

    print_success("Credentials removed")
