"""deserialize.py

Implement deserializing the compressed data into the user's library.
"""

import json
import zlib
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import BinaryIO, Hashable, List, TypeVar

import click
import tekore

from ..utils import (CONFIG_DIR, PlaylistState, SpotifyID, StyledStr,
                     get_client, log_event, unstyle)
from .serialize import Serializer

# region Constants


REPLACEMENT_NOTICE = (
    "WARNING: You specified the \"replacement\" option. This will add all the "
    "playlists and tracks included in the input file, but it will also REMOVE "
    "any playlists and tracks in your library NOT present in the input file. "
    "A backup of your library will be be created beforehand. Proceed?"
)

BACKUP_PATH = CONFIG_DIR / "backup.json"
DESERIALIZER_LOG_PATH = CONFIG_DIR / "deserializer.log"


# endregion Constants


# region Type Definitions


class ChangeMode(Enum):
    CREATED = auto()
    DELETED = auto()
    MODIFIED = auto()


@dataclass
class Delta:
    original: PlaylistState
    changed: PlaylistState
    additions: List[SpotifyID] = field(init=False)
    deletions: List[SpotifyID] = field(init=False)

    def __post_init__(self) -> None:
        self.additions = get_list_diff(self.original.tracks,
                                       self.changed.tracks)
        self.deletions = get_list_diff(self.changed.tracks,
                                       self.original.tracks)


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

    def get_summary(self, deletions_allowed: bool) -> StyledStr:
        summary = ""

        liked_songs_summary = click.style("* Liked Songs",
                                          fg="black",
                                          bg="white")
        num_saved_adds = len(self.saved_delta.additions)
        num_saved_dels = len(self.saved_delta.deletions)
        if num_saved_adds == 0 and \
                (not deletions_allowed or num_saved_dels == 0):
            pass
        else:
            if num_saved_adds > 0:
                s = click.style(f"+{num_saved_adds} track(s)", fg="green")
                liked_songs_summary += f"\n  {s}"
            if deletions_allowed and num_saved_dels > 0:
                s = click.style(f"-{num_saved_dels} track(s)", fg="red")
                liked_songs_summary += f"\n  {s}"

        summary += liked_songs_summary

        # TODO: Handle playlist summary.

        return summary

    def get_full(self) -> StyledStr:
        return click.style("TODO: Full detail report.")


class Deserializer:
    def __init__(self,
                 spotify: tekore.Spotify,
                 library_json: dict,
                 hard: bool
                 ) -> None:
        self.spotify = spotify
        self.library_json = library_json
        self.hard = hard

    def deserialize_library(self) -> LibraryDelta:
        saved_delta = self._deserialize_saved_songs()
        playlist_deltas = self._deserialize_playlists()
        return LibraryDelta(saved_delta, playlist_deltas)

    def _deserialize_saved_songs(self) -> SavedSongsDelta:
        # TODO: remember to consider the self.hard option
        return NotImplemented

    def _deserialize_playlists(self) -> List[PlaylistDelta]:
        # TODO: remember to consider the self.hard option
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
    library_json = serializer.get_library_json()
    with BACKUP_PATH.open("wt") as fp:
        json.dump(library_json, fp)
    click.secho("Finished creating backup.", fg="bright_black")


def write_to_log(delta_details: StyledStr) -> None:
    raw_details = unstyle(delta_details)
    log_event(DESERIALIZER_LOG_PATH, raw_details)


T = TypeVar("T", bound=Hashable)


def get_list_diff(list1: List[T], list2: List[T]) -> List[T]:
    return [item for item in (set(list2) - set(list1))]  # lazy lol


# endregion Helper Functions


@click.command("deserialize")
@click.option("-i", "--input",
              required=True,
              type=click.File("rb", encoding="utf-8"))
@click.option("-h", "--hard", is_flag=True)
@click.option("-v", "--verbose", is_flag=True)
# pylint: disable=redefined-builtin
def deserialize_command(input: BinaryIO, hard: bool, verbose: bool) -> None:
    spotify = get_client()

    if hard:
        prompt_confirmation()
        create_backup(Serializer(spotify))

    # TODO: Make compression/decompression into own subroutines?
    as_bytes = zlib.decompress(input.read())
    json_string = as_bytes.decode("utf-8")
    library_json = json.loads(json_string)
    # Also TODO: Also accept JSON like how serialize can produce JSON

    deserializer = Deserializer(spotify, library_json, hard)
    click.secho(f"Deserializing your backup file {input.name}...",
                fg="green")

    library_delta = deserializer.deserialize_library()

    # Output a report on what the deserializer did
    click.secho("Deserialized the track differences into your library!",
                fg="green")
    full_details = library_delta.get_full()
    summary_details = library_delta.get_summary(hard)
    if verbose:
        click.secho("\nBelow is a full report on what we did:\n",
                    fg="bright_black")
        click.echo(full_details)
    else:
        click.secho("\nBelow is a summary of what we did:\n",
                    fg="bright_black")
        click.echo(summary_details)
    click.echo()

    # In any case, write the full details to the log file
    write_to_log(full_details)
