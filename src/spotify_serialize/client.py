"""client.py

Spotify client configuration and initialization.
"""

import json
from typing import Tuple

import click
import tekore

from . import CONFIG_DIR

CLIENT_ID = "2ab65a4aa7f1406a859eef2cbe28ac9e"
REDIRECT_URI = "https://google.com"
APP_SCOPES = tekore.Scope(
    tekore.scope.ugc_image_upload,
    tekore.scope.playlist_read_private,
    tekore.scope.playlist_read_collaborative,
    tekore.scope.playlist_modify_private,
    tekore.scope.playlist_modify_public,
    tekore.scope.user_library_read,
    tekore.scope.user_library_modify,
)
CREDS_PATH = CONFIG_DIR / "creds.json"


def update_creds(payload: dict) -> None:
    with CREDS_PATH.open("wt", encoding="utf-8") as creds_file:
        json.dump(payload, creds_file)


def refresh_access_token(refresh_token: str) -> Tuple[str, str]:
    token = tekore.refresh_pkce_token(CLIENT_ID, refresh_token)
    return (token.access_token, token.refresh_token)  # type: ignore


def get_client() -> tekore.Spotify:
    if not CREDS_PATH.exists():
        raise click.Abort(f"{CREDS_PATH} doesn't exist") from None

    with CREDS_PATH.open("rt", encoding="utf-8") as creds_file:
        data = json.load(creds_file)

    try:
        access_token = data["access_token"]
        refresh_token = data["refresh_token"]
    except KeyError as exc:
        raise click.Abort(
            f"missing key {exc.args[0]!r} in {CREDS_PATH}"
        ) from None

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
