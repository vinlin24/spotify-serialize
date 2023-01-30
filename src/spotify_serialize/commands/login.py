"""login.py

Implement authentication for this application.
"""

import click
import tekore

from ..utils import CLIENT_ID, CREDS_PATH, REDIRECT_URI, update_creds

REDIRECT_NOTE = (
    f"NOTE: You will be redirected to {REDIRECT_URI} after authorizing "
    "the application. Please paste the resulting URL back into the "
    "console after the redirect."
)


def prompt_confirmation() -> None:
    click.secho(REDIRECT_NOTE, fg="yellow")
    click.confirm("Login through Spotify?", abort=True, show_default=True)


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
