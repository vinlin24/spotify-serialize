"""deserialize.py

Implement deserializing the compressed data into the user's library.
"""

import json
import zlib
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import (BinaryIO, Dict, Generator, Hashable, List, Optional, Set,
                    Tuple, TypeVar)

import click
import tekore
from tekore.model import (FullPlaylist, PlaylistTrack, SavedTrack,
                          SimplePlaylist)

from ..utils import (CONFIG_DIR, PlaylistState, SpotifyID, StyledStr,
                     get_client, log_event, unstyle)
from .serialize import Serializer

# region Constants


DESERIALIZE_NOTICE = (
    "You're about to use the contents of the backup file to MODIFY the "
    "current state of your Spotify library. Proceed?"
)

HARD_OPTION_NOTICE = (
    "WARNING: You specified the \"hard\" option. This will add all the "
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
    mode: ChangeMode


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

    def get_header_style(self, mode: ChangeMode
                         ) -> Tuple[str, Optional[str]]:
        if mode is ChangeMode.CREATED:
            bullet_point = "+"
            color = "green"
        elif mode is ChangeMode.DELETED:
            bullet_point = "-"
            color = "red"
        else:
            bullet_point = "*"
            color = None
        return (bullet_point, color)

    def format_delta_summary(self, delta: Delta, hard: bool) -> str:
        summary = ""

        # Figure out header based on change mode, name change, etc.

        old_name = delta.original.name
        new_name = delta.changed.name
        old_playlist_id = delta.original.id
        new_playlist_id = delta.changed.id

        is_liked_songs = (old_playlist_id is None and new_playlist_id is None)
        if is_liked_songs:
            header = click.style("* Liked Songs", fg="black", bg="white")
        else:
            playlist_delta: PlaylistDelta = delta  # type: ignore
            mode = playlist_delta.mode
            name_changed = (mode == ChangeMode.MODIFIED
                            and new_name != old_name)
            if name_changed:
                striked = click.style(old_name, strikethrough=True, dim=True)
                header = click.style(f"> {striked} {new_name}")
            else:
                bullet_point, color = self.get_header_style(mode)
                header = click.style(f"{bullet_point} {old_name}", fg=color)

        summary += header

        # Figure out the additions, deletions, total size change, etc.

        num_saved_adds = len(delta.additions)
        num_saved_dels = len(delta.deletions)
        old_size = len(delta.original.tracks)

        deletions_allowed = hard
        if num_saved_adds == 0 and \
                (not deletions_allowed or num_saved_dels == 0):
            summary += f"\n  No change! {old_size} total track(s)"

        else:
            new_size = old_size + num_saved_adds

            if num_saved_adds > 0:
                s = click.style(f"+{num_saved_adds} track(s)", fg="green")
                summary += f"\n  {s}"
            if deletions_allowed and num_saved_dels > 0:
                s = click.style(f"-{num_saved_dels} track(s)", fg="red")
                summary += f"\n  {s}"
                new_size -= num_saved_dels

            size_diff = new_size - old_size
            if size_diff > 0:
                colored_diff = click.style(f"(+{size_diff})", fg="green")
            else:
                colored_diff = click.style(f"({size_diff})", fg="red")

            size = f"{colored_diff} {old_size} -> {new_size} total track(s)"
            summary += f"\n {size}"  # One space to align nums

        return summary + "\n"

    def get_summary(self, hard: bool) -> StyledStr:
        summary = ""

        liked_songs_summary = self.format_delta_summary(self.saved_delta, hard)

        playlist_summaries = []
        for playlist_delta in self.playlist_deltas:
            playlist_summary = self.format_delta_summary(playlist_delta, hard)
            playlist_summaries.append(playlist_summary)
        playlists_summary = "\n".join(playlist_summaries)

        summary += liked_songs_summary
        summary += playlists_summary
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
        delta = self._get_saved_tracks_diff()

        # TODO: Maybe somehow decouple this chunked business
        with self.spotify.chunked(True):
            self.spotify.saved_tracks_add(delta.additions)
            if self.hard:
                self.spotify.saved_tracks_delete(delta.deletions)

        return delta

    def _deserialize_playlists(self) -> List[PlaylistDelta]:
        # TODO: remember to consider the self.hard option
        deltas = []

        library_owned, library_followed = self._get_library_playlists()

        # Take care of followed playlists

        new_follows, removed_follows = \
            self._get_followed_diff(library_followed)

        # Restore the followers that have been since removed
        for playlist_id in removed_follows:
            dummy = PlaylistState(id=playlist_id)
            delta = PlaylistDelta(dummy, dummy, ChangeMode.CREATED)
            deltas.append(delta)

        # If permitted, get rid of the new follows
        if self.hard:
            for playlist_id in new_follows:
                dummy = PlaylistState(id=playlist_id)
                delta = PlaylistDelta(dummy, dummy, ChangeMode.DELETED)
                deltas.append(delta)

        # Take care of owned playlists

        backup_owned: Dict[SpotifyID, dict] = {
            model["id"]: model
            for model in self.library_json["playlists"]["owned"]
        }

        library_owned_ids = {playlist.id for playlist in library_owned}
        backup_owned_ids = set(backup_owned.keys())

        new_playlist_ids = library_owned_ids - backup_owned_ids
        removed_playlist_ids = backup_owned_ids - library_owned_ids
        preserved_playlist_ids = library_owned_ids & backup_owned_ids

        # Restore playlists that have been removed since
        for playlist_id in removed_playlist_ids:
            json_playlist = backup_owned[playlist_id]
            delta = self._restore_playlist(json_playlist)
            deltas.append(delta)

        # If permitted, remove playlists that have been added since
        if self.hard:
            for playlist_id in new_playlist_ids:
                delta = self._remove_playlist(playlist_id)
                deltas.append(delta)

        # Extract parallel details and compute diff with helper
        for playlist_id in preserved_playlist_ids:
            json_playlist = backup_owned[playlist_id]
            delta = self._get_playlist_diff(json_playlist)
            if delta is not None:
                deltas.append(delta)

        return deltas

    def _get_saved_tracks_diff(self) -> SavedSongsDelta:
        backup_tracks: List[SpotifyID] = self.library_json["saved"]

        # TODO: Maybe refactor all this into a separate helper generator
        library_tracks: List[SpotifyID] = []
        current_saved_tracks: Generator[SavedTrack, None, None] = \
            self.spotify.all_items(self.spotify.saved_tracks())  # type: ignore
        for saved_track in current_saved_tracks:
            library_tracks.append(saved_track.track.id)

        current = PlaylistState(tracks=library_tracks)
        before = PlaylistState(tracks=backup_tracks)
        return SavedSongsDelta(current, before)

    def _get_library_playlists(self) -> Tuple[List[FullPlaylist],
                                              List[FullPlaylist]]:
        user_id = self.spotify.current_user().id
        paging = self.spotify.playlists(user_id)
        simple_playlists: Generator[SimplePlaylist, None, None] = \
            self.spotify.all_items(paging)  # type: ignore

        owned_playlists = []
        followed_playlists = []

        for simple_playlist in simple_playlists:
            full_playlist = self.spotify.playlist(simple_playlist.id)
            if full_playlist.id == user_id:  # type: ignore
                owned_playlists.append(full_playlist)
            else:
                followed_playlists.append(full_playlist)

        return (owned_playlists, followed_playlists)

    def _get_followed_diff(self, library_followed: List[FullPlaylist]
                           ) -> Tuple[Set[SpotifyID], Set[SpotifyID]]:
        library_follows = {playlist.id for playlist in library_followed}
        backup_follows: Set[SpotifyID] = \
            set(self.library_json["playlists"]["followed"])

        new_follows = library_follows - backup_follows
        removed_follows = backup_follows - library_follows
        return (new_follows, removed_follows)

    def _get_playlist_diff(self, backup_playlist: dict
                           ) -> Optional[PlaylistDelta]:
        playlist_id = backup_playlist["id"]

        library_playlist: FullPlaylist = \
            self.spotify.playlist(playlist_id)  # type: ignore

        old_name = backup_playlist["name"]
        new_name = library_playlist.name

        old_description = backup_playlist["description"]
        new_description = library_playlist.description

        old_photo = backup_playlist["photo"]
        if library_playlist.images:
            new_photo = library_playlist.images[0].url
        else:
            new_photo = None

        playlist_tracks: Generator[PlaylistTrack, None, None] = \
            self.spotify.all_items(library_playlist.tracks)  # type: ignore

        library_tracks = [t.track.id for t in playlist_tracks]  # type: ignore
        backup_tracks = backup_playlist["tracks"]

        original = PlaylistState(playlist_id, old_name, old_description,
                                 old_photo, library_tracks)  # type: ignore
        changed = PlaylistState(playlist_id, new_name, new_description,
                                new_photo, backup_tracks)

        if original == changed:
            return None
        return PlaylistDelta(original, changed, ChangeMode.MODIFIED)

    def _restore_playlist(self, json_playlist: dict) -> PlaylistDelta:
        name = json_playlist["name"]
        description = json_playlist["description"]
        photo = json_playlist["photo"]
        tracks = json_playlist["tracks"]

        user_id = self.spotify.current_user().id
        new_playlist = self.spotify.playlist_create(user_id=user_id,
                                                    name=name,
                                                    description=description,
                                                    public=True)
        # NOTE: Maybe add support for creating playlist with custom
        # visibility (public/private).

        # NOTE: Should also change saving photo from a potentially
        # transient URL to actually saving the photo locally.
        if photo is not None:
            click.secho(f"NOTE: restoring image (URL={photo}) "
                        "not supported yet.",
                        fg="black")

        dummy = PlaylistState()
        changed = PlaylistState(id=new_playlist.id,
                                name=name,
                                description=description,
                                photo=None,
                                tracks=tracks)
        return PlaylistDelta(dummy, changed, ChangeMode.CREATED)

    def _remove_playlist(self, playlist_id: SpotifyID) -> PlaylistDelta:
        # Refactor your damn data structures so you don't have
        # to re-request this
        playlist: FullPlaylist = \
            self.spotify.playlist(playlist_id)  # type: ignore

        # TODO: Maybe refactor this annoying if/else into a helper
        if playlist.images:
            photo = playlist.images[0].url
        else:
            photo = None

        track_ids = [t.track.id for t in  # type: ignore
                     self.spotify.all_items(playlist.tracks)]

        # "Deleting" your playlist is the same as unfollowing it
        self.spotify.playlist_unfollow(playlist_id)

        original = PlaylistState(id=playlist_id,
                                 name=playlist.name,
                                 description=playlist.description,
                                 photo=photo,
                                 tracks=track_ids)
        dummy = PlaylistState()
        return PlaylistDelta(original, dummy, ChangeMode.DELETED)


# endregion Type Definitions


# region Helper Functions


def prompt_confirmation() -> None:
    click.confirm(click.style(DESERIALIZE_NOTICE, fg="yellow"),
                  default=False,
                  abort=True,
                  show_default=True)


def prompt_hard_confirmation() -> None:
    click.confirm(click.style(HARD_OPTION_NOTICE, fg="red"),
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

    prompt_confirmation()

    if hard:
        prompt_hard_confirmation()
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

    if hard:
        click.secho("Added the missing playlists and/or tracks in your backup "
                    "file back into your library, and removed all playlists "
                    "and/or tracks that were not present in the backup file.",
                    fg="green")
    else:
        click.secho("Added the missing playlists and/or tracks in your backup "
                    "file back into your library.",
                    fg="green")

    # Output a report on what the deserializer did
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
