"""deserialize.py

Implement deserializing the serialized data into the user's library.
"""

from datetime import datetime
from pathlib import Path

import click
import tekore

from .. import CONFIG_DIR
from ..client import get_client
from .serialize import Serializer

DESERIALIZE_NOTICE = (
    "You're about to use the contents of the backup file to MODIFY the "
    "current state of your Spotify library. Proceed?"
)
BACKUP_DIR = CONFIG_DIR / "backups"


class Deserializer:
    def __init__(self, spotify: tekore.Spotify) -> None:
        self.spotify = spotify

    def deserialize(self, snapshot_dir: Path) -> None:
        click.secho(snapshot_dir)  # TODO


def prompt_confirmation() -> None:
    click.confirm(click.style(DESERIALIZE_NOTICE, fg="yellow"),
                  default=False,
                  abort=True,
                  show_default=True)


def create_backup(serializer: Serializer) -> None:
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().isoformat().replace(":", ",")
    backup_path = BACKUP_DIR / f"{timestamp}.snapshot"

    click.secho(f"Creating backup at {backup_path}...", fg="bright_black")
    serializer.serialize(backup_path, 2)
    click.secho("Finished creating backup.", fg="bright_black")


@click.command("deserialize")
@click.option("-i", "--input",
              required=True,
              type=click.Path(path_type=Path))
# pylint: disable=redefined-builtin
def deserialize_command(input: Path) -> None:
    spotify = get_client()
    prompt_confirmation()

    deserializer = Deserializer(spotify)
    click.secho(f"Deserializing your backup file {input}...",
                fg="green")
    deserializer.deserialize(input)
    click.secho(f"Deserialized backup file {input} into your Spotify library",
                fg="green")
