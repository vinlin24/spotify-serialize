"""serialize.py

Implement serializing the user's library into a compressed data format.
"""

import json
import zlib
from typing import BinaryIO, Dict, Set

import click
import tekore
from tekore.model import FullPlaylist

from ..utils import get_client

SpotifyID = str

PlaylistModel = Dict[SpotifyID, Set[SpotifyID]]


class Serializer:
    def __init__(self, spotify: tekore.Spotify) -> None:
        self.spotify = spotify

    def serialize_library(self) -> dict:
        return {
            "playlists": {
                "owned": self._serialize_owned_playlists(),
                "followed": self._serialize_followed_playlists(),
            },
            "saved": self._serialize_saved_songs()
        }

    def _serialize_owned_playlists(self) -> Set[PlaylistModel]:
        return NotImplemented

    def _serialize_followed_playlists(self) -> Set[SpotifyID]:
        return NotImplemented

    def _serialize_saved_songs(self) -> Set[SpotifyID]:
        return NotImplemented

    def _convert_playlist_model(self, playlist: FullPlaylist) -> PlaylistModel:
        return NotImplemented


@click.command("serialize")
@click.option("-o", "--output",
              required=True,
              type=click.File(mode="wb", encoding="utf-8"))
def serialize_command(output: BinaryIO) -> None:
    spotify = get_client()
    json_data = Serializer(spotify).serialize_library()
    as_bytes = json.dumps(json_data).encode("utf-8")
    payload = zlib.compress(as_bytes)
    output.write(payload)
    click.secho(f"Serialized your library into {output.name}",
                fg="green")
