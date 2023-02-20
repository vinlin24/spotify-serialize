"""serialize.py

Implement serializing the user's library into a compressed data format.
"""

import json
import zlib
from dataclasses import asdict
from pathlib import Path
from typing import BinaryIO, Generator, List, Tuple

import click
import tekore
from tekore.model import (FullPlaylist, LocalPlaylistTrack, PlaylistTrack,
                          SavedTrack, SimplePlaylist)

from ..utils import PlaylistState, SpotifyID, get_client


class Serializer:
    def __init__(self, spotify: tekore.Spotify) -> None:
        self.spotify = spotify

    def get_library_json(self) -> dict:
        owned, followed = self._serialize_playlists()
        return {
            "playlists": {
                "owned": [asdict(state) for state in owned],
                "followed": followed,
            },
            "saved": self._serialize_saved_songs()
        }

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
@click.option("-j", "--with-json", is_flag=True)
def serialize_command(output: BinaryIO,
                      with_json: bool,
                      ) -> None:
    spotify = get_client()

    output_is_json = (Path(output.name).suffix.lower() == ".json")
    format_choice = "binary"
    if output_is_json:
        format_choice = "JSON"
    elif with_json:
        format_choice = "binary + JSON"
    click.secho(f"Serializing your library ({format_choice})...",
                fg="green")

    library_json = Serializer(spotify).get_library_json()
    as_bytes = json.dumps(library_json).encode("utf-8")

    # Directly write to the output stream with JSON data as bytes.
    # Notice with_json is ignored if the output path is already JSON.
    if output_is_json:
        output.write(as_bytes)
        click.secho(f"Saved your library as a JSON document at {output.name}",
                    fg="green")
        return

    # Otherwise, convert JSON data into compressed bytes
    compressed = zlib.compress(as_bytes)
    output.write(compressed)
    click.secho(f"Serialized your library into binary file {output.name}",
                fg="green")

    # If the user wants to keep the JSON data alongside the binary
    if with_json:
        # Create it in the same directory and replace the extension (if
        # exists) with .json.
        dir_path = Path(output.name).parent
        output_stem = Path(output.name).stem
        json_path = dir_path / Path(output_stem + ".json")

        if json_path.exists():
            click.secho(f"Cannot create a JSON copy at {json_path} because it "
                        f"already exists. Binary file {output.name} is fine.",
                        fg="red",
                        err=True)
            raise click.Abort
        with json_path.open("wt", encoding="utf-8") as fp:
            json.dump(library_json, fp)
        click.secho(f"Also generated an uncompressed JSON copy at {json_path}",
                    fg="green")
