"""utils.py

Useful constants and helper functions.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import click
import tekore

StyledStr = str
SpotifyID = str

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


CONFIG_DIR = Path.home() / ".config" / "spotify-serialize"
CREDS_PATH = CONFIG_DIR / "creds.json"


class AuthenticationError(Exception):
    pass


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def update_creds(payload: dict) -> None:
    with CREDS_PATH.open("wt", encoding="utf-8") as fp:
        json.dump(payload, fp)


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


def log_event(path: Path, message: str) -> None:
    now_string = datetime.now().isoformat()

    # Standardize the delimiters around an event within each log file.
    # This will make it easier for future parsing.
    header = f"[{now_string}]"
    footer = "[/]"

    content = f"{header}\n{message}\n{footer}\n\n"
    with path.open("at", encoding="utf-8") as fp:
        fp.write(content)


ANSI_REGEX = r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"


def unstyle(s: StyledStr) -> str:
    return re.sub(ANSI_REGEX, "", s)


@dataclass
class PlaylistState:
    id: Optional[SpotifyID] = None
    name: Optional[str] = None
    description: Optional[str] = None
    photo: Optional[str] = None
    tracks: List[SpotifyID] = field(default_factory=list)
