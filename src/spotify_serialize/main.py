"""main.py

Entry point for command line interface.
"""

import click

from . import CONFIG_DIR
from .commands import deserialize_command, login_command, serialize_command


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


@click.group()
@click.version_option()
def cli() -> None:
    """Simple backup system for a user's Spotify library."""
    ensure_config_dir()


cli.add_command(login_command)
cli.add_command(serialize_command)
cli.add_command(deserialize_command)

if __name__ == "__main__":
    cli()
