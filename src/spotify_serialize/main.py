"""main.py

Entry point for command line interface.
"""

import click

from .commands import login_command, serialize_command


@click.group()
@click.version_option()
def cli() -> None:
    """Simple backup system for a user's Spotify library."""


cli.add_command(login_command)
cli.add_command(serialize_command)


if __name__ == "__main__":
    cli()
