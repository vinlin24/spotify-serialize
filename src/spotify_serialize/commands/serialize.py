"""serialize.py

Implement serializing the user's library into a compressed data format.
"""

import json
from typing import Tuple

import click
import tekore

from ..utils import CLIENT_ID, CREDS_PATH, update_creds


class AuthenticationError(Exception):
    pass


def refresh_access_token(refresh_token: str) -> Tuple[str, str]:
    token = tekore.refresh_pkce_token(CLIENT_ID, refresh_token)
    return (token.access_token, token.refresh_token)  # type: ignore


def get_client() -> tekore.Spotify:
    if not CREDS_PATH.exists():
        raise click.Abort("") from None
    with CREDS_PATH.open("rt", encoding="utf-8") as fp:
        data = json.load(fp)

    try:
        access_token = data["access_token"]
        refresh_token = data["refresh_token"]
    except KeyError as e:
        raise AuthenticationError(e.args) from None

    spotify = tekore.Spotify(access_token)

    # If access token is invalid, request a new one
    try:
        spotify.current_user()
    except tekore.ClientError:
        access_token, refresh_token = refresh_access_token(refresh_token)
        update_creds({
            "access_token": access_token,
            "refresh_token": refresh_token,
        })
        spotify = tekore.Spotify(access_token)

    return spotify


@click.command("serialize")
def serialize_command() -> None:
    spotify = get_client()
    click.echo(spotify.current_user().display_name)
