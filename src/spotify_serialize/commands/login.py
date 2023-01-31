"""login.py

Implement authentication for this application.
"""

from datetime import datetime

import click
import tekore
from tekore import RefreshingToken
from tekore.model import PrivateUser

from ..utils import (CLIENT_ID, CONFIG_DIR, CREDS_PATH, REDIRECT_URI,
                     get_client, update_creds)

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

    now_string = datetime.now().isoformat()
    header = f"[{now_string}]"
    footer = "[/]"

    content = f"{header}\n{body}\n{footer}\n\n"
    with AUTH_LOG_PATH.open("at", encoding="utf-8") as fp:
        fp.write(content)


@click.command("login")
def login_command() -> None:
    prompt_confirmation()
    token = tekore.prompt_for_pkce_token(CLIENT_ID, REDIRECT_URI)
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
