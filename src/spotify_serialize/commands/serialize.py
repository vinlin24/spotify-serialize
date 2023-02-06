"""serialize.py

Implement serializing the user's library into a compressed data format.
"""

import json
import zlib
from dataclasses import asdict
from typing import BinaryIO, Generator, List, Tuple

import click
import tekore
from tekore.model import (FullPlaylist, LocalPlaylistTrack, PlaylistTrack,
                          SavedTrack, SimplePlaylist)

from ..utils import PlaylistState, SpotifyID, get_client


class Serializer:
    def __init__(self, spotify: tekore.Spotify) -> None:
        self.spotify = spotify

    def serialize_library(self) -> bytes:
        owned, followed = self._serialize_playlists()
        json_data = {
            "playlists": {
                "owned": [asdict(state) for state in owned],
                "followed": followed,
            },
            "saved": self._serialize_saved_songs()
        }
        as_bytes = json.dumps(json_data).encode("utf-8")
        payload = zlib.compress(as_bytes)
        return payload

    def _serialize_playlists(self) -> Tuple[List[PlaylistState],
                                            List[SpotifyID]]:
        user_id = self.spotify.current_user().id
        user_playlists = self.spotify.playlists(user_id)
        simple_playlist_iterator: Generator[SimplePlaylist, None, None] = \
            self.spotify.all_items(user_playlists)  # type: ignore

        owned: List[PlaylistState] = []
        followed: List[SpotifyID] = []

        for simple_playlist in simple_playlist_iterator:
            owner_id = simple_playlist.owner.id
            if owner_id == user_id:
                full_playlist: FullPlaylist = \
                    self.spotify.playlist(simple_playlist.id)  # type: ignore
                playlist_state = self._convert_playlist_model(full_playlist)
                owned.append(playlist_state)
            else:
                followed.append(simple_playlist.id)

        return (owned, followed)

    def _serialize_saved_songs(self) -> List[SpotifyID]:
        saved_track_iterator: Generator[SavedTrack, None, None] = \
            self.spotify.all_items(self.spotify.saved_tracks())  # type: ignore

        return [saved_track.track.id for saved_track in saved_track_iterator]

    def _convert_playlist_model(self, playlist: FullPlaylist) -> PlaylistState:
        image_url = playlist.images[0].url if playlist.images else None

        playlist_track_iterator: Generator[PlaylistTrack, None, None] = \
            self.spotify.all_items(playlist.tracks)  # type: ignore

        track_ids = []
        for playlist_track in playlist_track_iterator:
            track = playlist_track.track
            # No support for local tracks yet.  A LocalPlaylistTrack object
            # has id=None, and that's just annoying.
            if track is None or isinstance(track, LocalPlaylistTrack):
                raise Exception(
                    "Unknown playlist track format. "
                    "Local tracks are not yet supported."
                )
            track_ids.append(track.id)

        return PlaylistState(
            id=playlist.id,
            name=playlist.name,
            description=playlist.description,
            photo=image_url,
            tracks=track_ids
        )


@click.command("serialize")
@click.option("-o", "--output",
              required=True,
              type=click.File(mode="wb", encoding="utf-8"))
def serialize_command(output: BinaryIO) -> None:
    spotify = get_client()

    click.secho("Serializing your library...", fg="green")
    payload = Serializer(spotify).serialize_library()
    output.write(payload)
    click.secho(f"Serialized your library into {output.name}", fg="green")
