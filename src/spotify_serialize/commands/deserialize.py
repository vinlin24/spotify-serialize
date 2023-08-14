"""deserialize.py

Implement deserializing the serialized data into the user's library.
"""

import json
from datetime import datetime
from pathlib import Path

import click
import tekore

from .. import CONFIG_DIR, abort_with_error
from ..client import get_client
from ..schema import PlaylistJSON, SnapshotJSON
from .serialize import Serializer

DESERIALIZE_NOTICE = (
    "You're about to use the contents of the backup file to MODIFY the "
    "current state of your Spotify library. Proceed?"
)
BACKUP_DIR = CONFIG_DIR / "backups"


class Deserializer:
    def __init__(self, spotify: tekore.Spotify) -> None:
        self.spotify = spotify

    def deserialize(self, playlist: PlaylistJSON) -> None:
        click.secho(playlist)  # TODO


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

    data_path = (input / "data.json").resolve()
    with data_path.open("rt", encoding="utf-8") as data_file:
        data: SnapshotJSON = json.load(data_file)

    # TODO: for now, if the user names multiple playlists with the same
    # name, that's on them lol
    playlists = data["ownedPlaylists"]
    playlist_names = [playlist["name"] for playlist in playlists]
    click.secho(f"Names of your owned playlists found in {data_path}:",
                fg="yellow")
    click.secho("\n".join(f"* {name}" for name in playlist_names))

    playlist_name = click.prompt(
        click.style("Choose playlist to deserialize", fg="yellow"),
        type=click.Choice(playlist_names),
        show_choices=False,
    )

    chosen_playlist: PlaylistJSON
    for playlist in playlists:
        if playlist["name"] == playlist_name:
            chosen_playlist = playlist
            break
    else:
        abort_with_error(f"Somehow couldn't get playlist for {playlist_name=}")

    prompt_confirmation()

    deserializer = Deserializer(spotify)
    click.secho(
        f"Deserializing your backup file {input} for {playlist_name!r}...",
        fg="green"
    )
    deserializer.deserialize(chosen_playlist)
    click.secho(
        f"Deserialized backup file {input} into playlist {playlist_name!r}",
        fg="green"
    )
