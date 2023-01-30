"""login.py

Implement authentication for this application.
"""

import json
from pathlib import Path

import click
import tekore

from .. import CLIENT_ID, REDIRECT_URI

ESC = "\x1b"
CYAN = f"{ESC}[36m"
BOLD = f"{ESC}[1m"
UNBOLD = f"{ESC}[22m"
END = f"{ESC}[0m"


CONFIG_DIR = Path.home() / ".config" / "spotify-serialize"
CREDS_PATH = CONFIG_DIR / "creds.json"


def prompt_confirmation() -> bool:
    bold_url = f"{BOLD}{REDIRECT_URI}{UNBOLD}"
    print(
        f"{CYAN}"
        f"NOTE: You will be redirected to {bold_url} after authorizing "
        "the application. Please paste the resulting URL back into the "
        "console after the redirect."
        f"{END}"
    )
    try:
        response = input("Login through Spotify? [y/N] ")
    except KeyboardInterrupt:
        return False
    return response.lower().startswith("y")


def ensure_creds_file() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with CREDS_PATH.open("wt", encoding="utf-8") as fp:
        json.dump({}, fp)


@click.command("login")
def login_command() -> None:
    if not prompt_confirmation():
        print("Decided not to log in.")
        return
    ensure_creds_file()
    token = tekore.prompt_for_pkce_token(CLIENT_ID, REDIRECT_URI)
    payload = {
        "access_token": token.access_token,
        "refresh_token": token.refresh_token,
    }
    with CREDS_PATH.open("wt", encoding="utf-8") as fp:
        json.dump(payload, fp)
    print(f"Authenticated! Wrote access tokens to {CREDS_PATH}")
