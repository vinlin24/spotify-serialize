"""deserialize.py

Implement deserializing the compressed data into the user's library.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import BinaryIO, List, Set

import click
import tekore

from ..utils import CONFIG_DIR, StyledStr, get_client, unstyle
from .serialize import Serializer, SpotifyID

# region Constants


REPLACEMENT_NOTICE = (
    "WARNING: You specified the \"replacement\" option. This will add all the "
    "playlists and tracks included in the input file, but it will also REMOVE "
    "any playlists and tracks in your library NOT present in the input file. "
    "A backup of your library will be be created beforehand. Proceed?"
)

BACKUP_PATH = CONFIG_DIR / "backup"
DESERIALIZER_LOG_PATH = CONFIG_DIR / "deserializer.log"


# endregion Constants


# region Type Definitions


class ChangeMode(Enum):
    CREATED = auto()
    DELETED = auto()
    MODIFIED = auto()


@dataclass
class PlaylistState:
    id: SpotifyID
    name: str
    description: str
    photo: str
    tracks: Set[SpotifyID]


@dataclass
class Delta:
    original: PlaylistState
    changed: PlaylistState
    additions: Set[SpotifyID] = field(init=False)
    deletions: Set[SpotifyID] = field(init=False)

    def __post_init__(self) -> None:
        self.additions = self.changed.tracks - self.original.tracks
        self.deletions = self.original.tracks - self.changed.tracks


@dataclass
class PlaylistDelta(Delta):
    mode = ChangeMode


@dataclass
class SavedSongsDelta(Delta):
    pass


class LibraryDelta:
    def __init__(self,
                 saved_delta: SavedSongsDelta,
                 playlist_deltas: List[PlaylistDelta]
                 ) -> None:
        self.saved_delta = saved_delta
        self.playlist_deltas = playlist_deltas

    def get_summary(self) -> StyledStr:
        return click.style("TODO: Summary report.")

    def get_full(self) -> StyledStr:
        return click.style("TODO: Full detail report.")


class Deserializer:
    # pylint: disable=redefined-builtin
    def __init__(self,
                 spotify: tekore.Spotify,
                 input: BinaryIO,
                 replace: bool
                 ) -> None:
        self.spotify = spotify
        self.input = input
        self.replace = replace

    def deserialize_library(self) -> LibraryDelta:
        saved_delta = self._deserialize_saved_songs()
        playlist_deltas = self._deserialize_playlists()
        return LibraryDelta(saved_delta, playlist_deltas)

    def _deserialize_saved_songs(self) -> SavedSongsDelta:
        # TODO: remember to consider the self.replace option
        return NotImplemented

    def _deserialize_playlists(self) -> List[PlaylistDelta]:
        # TODO: remember to consider the self.replace option
        return NotImplemented


# endregion Type Definitions


# region Helper Functions


def prompt_confirmation() -> None:
    click.confirm(click.style(REPLACEMENT_NOTICE, fg="red"),
                  default=False,
                  abort=True,
                  show_default=True)


def create_backup(serializer: Serializer) -> None:
    click.secho(f"Creating backup at {BACKUP_PATH}...", fg="bright_black")
    payload = serializer.serialize_library()
    with BACKUP_PATH.open("wb") as fp:
        fp.write(payload)
    click.secho("Finished creating backup.", fg="bright_black")


def write_to_log(delta_details: StyledStr) -> None:
    raw_details = unstyle(delta_details)
    now_string = datetime.now().isoformat()

    # Define start and end delimiters in case I'd want to regex parse later
    header = f"[{now_string}]"
    footer = "[/]"

    content = f"{header}\n{raw_details}\n{footer}\n\n"
    with DESERIALIZER_LOG_PATH.open("at", encoding="utf-8") as fp:
        fp.write(content)


# endregion Helper Functions


@click.command("deserialize")
@click.option("-i", "--input",
              required=True,
              type=click.File("rb", encoding="utf-8"))
@click.option("-r", "--replace", is_flag=True)
@click.option("-v", "--verbose", is_flag=True)
# pylint: disable=redefined-builtin
def deserialize_command(input: BinaryIO, replace: bool, verbose: bool) -> None:
    spotify = get_client()

    if replace:
        prompt_confirmation()
        create_backup(Serializer(spotify))

    deserializer = Deserializer(spotify, input, replace)
    library_delta = deserializer.deserialize_library()

    # Output a report on what the deserializer did
    full_details = library_delta.get_full()
    summary_details = library_delta.get_summary()
    if verbose:
        click.echo(full_details)
    else:
        click.echo(summary_details)

    # In any case, write the full details to the log file
    write_to_log(full_details)
