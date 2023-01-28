"""main.py

Entry point for command line interface.
"""

import click


@click.group()
@click.version_option()
def cli() -> None:
    """Simple backup system for a user's Spotify library."""


if __name__ == "__main__":
    cli()
