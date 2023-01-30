"""utils.py

Useful constants and helper functions.
"""

import json
from pathlib import Path

CLIENT_ID = "2ab65a4aa7f1406a859eef2cbe28ac9e"
REDIRECT_URI = "https://google.com"

CONFIG_DIR = Path.home() / ".config" / "spotify-serialize"
CREDS_PATH = CONFIG_DIR / "creds.json"


def update_creds(payload: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with CREDS_PATH.open("wt", encoding="utf-8") as fp:
        json.dump(payload, fp)
