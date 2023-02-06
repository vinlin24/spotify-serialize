"""serialize.py

Implement serializing the user's library into a compressed data format.
"""

import json
import zlib
from typing import BinaryIO, Generator, Set

import click
import tekore
from tekore.model import FullPlaylist, LocalPlaylistTrack, PlaylistTrack

from ..utils import PlaylistState, SpotifyID, get_client


class Serializer:
    def __init__(self, spotify: tekore.Spotify) -> None:
        self.spotify = spotify

    def serialize_library(self) -> bytes:
        json_data = {
            "playlists": {
                "owned": self._serialize_owned_playlists(),
                "followed": self._serialize_followed_playlists(),
            },
            "saved": self._serialize_saved_songs()
        }
        as_bytes = json.dumps(json_data).encode("utf-8")
        payload = zlib.compress(as_bytes)
        return payload

    def _serialize_owned_playlists(self) -> Set[PlaylistState]:
        return NotImplemented

    def _serialize_followed_playlists(self) -> Set[SpotifyID]:
        return NotImplemented

    def _serialize_saved_songs(self) -> Set[SpotifyID]:
        return NotImplemented

    def _convert_playlist_model(self, playlist: FullPlaylist) -> PlaylistState:
        image_url = playlist.images[0].url if playlist.images else None

        playlist_track_iterator: Generator[PlaylistTrack, None, None] = \
            self.spotify.all_items(playlist.tracks)  # type: ignore

        track_ids = set()
        for playlist_track in playlist_track_iterator:
            track = playlist_track.track
            # No support for local tracks yet.  A LocalPlaylistTrack object
            # has id=None, and that's just annoying.
            if track is None or isinstance(track, LocalPlaylistTrack):
                raise Exception(
                    "Unknown playlist track format. "
                    "Local tracks are not yet supported."
                )
            track_ids.add(track.id)

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
    payload = Serializer(spotify).serialize_library()
    output.write(payload)
    click.secho(f"Serialized your library into {output.name}",
                fg="green")
