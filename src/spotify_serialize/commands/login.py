"""login.py

Implement authentication for this application.
"""

import click
import tekore
from tekore import RefreshingToken
from tekore.model import PrivateUser

from ..utils import (APP_SCOPES, CLIENT_ID, CONFIG_DIR, CREDS_PATH,
                     REDIRECT_URI, get_client, log_event, update_creds)

REDIRECT_NOTE = (
    f"NOTE: You will be redirected to {REDIRECT_URI} after authorizing "
    "the application. Please paste the resulting URL back into the "
    "console after the redirect."
)

AUTH_LOG_PATH = CONFIG_DIR / "auth.log"


def prompt_confirmation() -> None:
    click.secho(REDIRECT_NOTE, fg="yellow")
    click.confirm("Login through Spotify?", abort=True, show_default=True)


def write_to_log(token: RefreshingToken, user: PrivateUser) -> None:
    body = (
        f"Logged in as user {user.display_name} (ID: {user.id})\n"
        f"Saved access_token={token.access_token!r} to {CREDS_PATH}\n"
        f"Saved refresh_token={token.refresh_token!r} to {CREDS_PATH}"
    )
    log_event(AUTH_LOG_PATH, body)


@click.command("login")
def login_command() -> None:
    prompt_confirmation()
    token = tekore.prompt_for_pkce_token(CLIENT_ID, REDIRECT_URI, APP_SCOPES)
    update_creds({
        "access_token": token.access_token,
        "refresh_token": token.refresh_token,
    })
    user = get_client().current_user()
    notice = (
        f"Authenticated as {user.display_name} (ID: {user.id})! "
        f"Wrote access tokens to {CREDS_PATH}"
    )
    click.secho(notice, fg="green")
    write_to_log(token, user)
