"""
# Spotify Serialize

Simple backup system for a user's Spotify library.
"""

from pathlib import Path
from typing import NoReturn, Optional

import click

__author__ = "Vincent Lin"
__version__ = "0.0.0"

CONFIG_DIR = Path.home() / ".config" / "spotify-serialize"


def echo_warning(message: str) -> None:
    click.secho("WARNING: ", nl=False, fg="yellow", bold=True)
    click.secho(message, fg="yellow")


def abort_with_error(message: Optional[str] = None) -> NoReturn:
    if message is not None:
        click.secho("ERROR: ", nl=False, fg="red", bold=True)
        click.secho(message, fg="red")
    raise click.Abort()
