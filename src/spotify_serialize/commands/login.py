"""login.py

Implement authentication for this application.
"""

import json
from pathlib import Path

import click
import tekore

from .. import CLIENT_ID, REDIRECT_URI

CONFIG_DIR = Path.home() / ".config" / "spotify-serialize"
CREDS_PATH = CONFIG_DIR / "creds.json"

REDIRECT_NOTE = (
    f"NOTE: You will be redirected to {REDIRECT_URI} after authorizing "
    "the application. Please paste the resulting URL back into the "
    "console after the redirect."
)


def prompt_confirmation() -> None:
    click.secho(REDIRECT_NOTE, fg="yellow")
    click.confirm("Login through Spotify?", abort=True, show_default=True)


def update_creds(payload: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with CREDS_PATH.open("wt", encoding="utf-8") as fp:
        json.dump(payload, fp)


@click.command("login")
def login_command() -> None:
    prompt_confirmation()
    token = tekore.prompt_for_pkce_token(CLIENT_ID, REDIRECT_URI)
    update_creds({
        "access_token": token.access_token,
        "refresh_token": token.refresh_token,
    })
    click.secho(f"Authenticated! Wrote access tokens to {CREDS_PATH}",
                fg="green")
