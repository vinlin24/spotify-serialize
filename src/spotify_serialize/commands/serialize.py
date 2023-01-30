"""serialize.py

Implement serializing the user's library into a compressed data format.
"""

import click

from ..utils import get_client


@click.command("serialize")
def serialize_command() -> None:
    spotify = get_client()
    click.echo(spotify.current_user().display_name)
