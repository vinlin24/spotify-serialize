"""deserialize.py

Implement deserializing the serialized data into the user's library.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Generator, List, Optional, Set

import click
import tekore

from .. import CONFIG_DIR, abort_with_error
from ..client import get_client
from ..schema import PlaylistJSON, SnapshotJSON, SpotifyURI, TrackJSON
from .serialize import Serializer

DESERIALIZE_NOTICE = (
    "You're about to use the contents of the backup file to MODIFY the "
    "current state of your Spotify library. Proceed?"
)
BACKUP_DIR = CONFIG_DIR / "backups"


class Deserializer:
    def __init__(self, spotify: tekore.Spotify) -> None:
        self.spotify = spotify

    def deserialize(self, playlist_data: PlaylistJSON) -> None:
        playlist = self._get_current_playlist(playlist_data["id"])

        # Playlist doesn't exist anymore, so create it first
        if playlist is None:
            user_id = self.spotify.current_user().id
            playlist = self.spotify.playlist_create(
                user_id=user_id,
                name=playlist_data["name"],
                public=True,
                description=playlist_data["description"] or "",
            )

        track_data: List[TrackJSON] = playlist_data["tracks"]
        current_uris = self._get_playlist_tracks(playlist)
        incoming_uris = self._get_data_tracks(track_data)

        uris_to_add = incoming_uris - current_uris
        uris_to_remove = current_uris - incoming_uris

        if len(uris_to_add) == 0:
            click.echo(f"No tracks to add to {playlist.name!r}")
        else:
            self.spotify.playlist_add(
                playlist_id=playlist.id,
                uris=list(uris_to_add),
            )
            click.secho(
                f"Added {len(uris_to_add)} tracks to {playlist.name!r}",
                fg="green"
            )

        if len(uris_to_remove) == 0:
            click.echo(f"No tracks to remove from {playlist.name!r}")
        else:
            self.spotify.playlist_remove(
                playlist_id=playlist.id,
                uris=list(uris_to_remove),
            )
            click.secho(
                f"Removed {len(uris_to_remove)} tracks from {playlist.name!r}",
                fg="red"
            )

    def _get_current_playlist(self, playlist_id
                              ) -> Optional[tekore.model.FullPlaylist]:
        try:
            playlist: tekore.model.FullPlaylist
            playlist = self.spotify.playlist(playlist_id)  # type: ignore
        except tekore.NotFound:
            return None

        # Shouldn't happen but oh well
        if playlist.owner.id != self.spotify.current_user().id:
            abort_with_error(
                f"Playlist with {playlist_id=} doesn't belong to you"
            )

        return playlist

    def _get_playlist_tracks(self, playlist: tekore.model.FullPlaylist
                             ) -> Set[SpotifyURI]:
        paging = playlist.tracks
        track_iterator: Generator[tekore.model.PlaylistTrack, None, None]
        track_iterator = self.spotify.all_items(paging)  # type: ignore

        result: Set[SpotifyURI] = set()
        for track in track_iterator:
            _track = track.track
            if _track is None:  # Still don't know why this can happen
                continue
            track_id: str = _track.id  # type: ignore
            # NOTE: must use URIs instead of IDs for playlist operations
            uri = tekore.to_uri(
                "episode" if _track.episode else "track",
                track_id,
            )
            result.add(uri)
        return result

    def _get_data_tracks(self, track_data: List[TrackJSON]
                         ) -> Set[SpotifyURI]:
        return {
            tekore.to_uri(track["type"], track["id"])
            for track in track_data
        }


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
