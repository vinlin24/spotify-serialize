"""serialize.py

Implement serializing the user's library into a compressed data format.
"""

import json
from typing import Any, Dict, Generator, Iterator, List, TextIO, Tuple, Union

import click
import tekore

from ..client import get_client

# TODO: handle downloading images

JSONData = Dict[str, Any]

User = Union[tekore.model.PublicUser, tekore.model.PrivateUser]


def user_model_to_json(user: User) -> JSONData:
    """
    Convert a tekore user model to the format of user.schema.json.
    """
    return {
        "id": user.id,
        "displayName": user.display_name,
        "numFollowers": user.followers and user.followers.total,
    }


Track = Union[tekore.model.SavedTrack, tekore.model.PlaylistTrack]


def track_model_to_json(track: Track) -> JSONData:
    """
    Convert a tekore track model to the format of track.model.json.
    """
    _track: Union[tekore.model.FullTrack, tekore.model.FullPlaylistTrack]
    _track = track.track  # type: ignore
    return {
        "id": _track.id,
        "name": _track.name,
        "artists": [artist.name for artist in _track.artists],
        "addedAt": track.added_at.isoformat()
    }


Playlist = tekore.model.SimplePlaylist


def playlist_model_to_json(playlist: Playlist, spotify: tekore.Spotify
                           ) -> JSONData:
    """
    Convert a tekore playlist model to the format of
    playlist.schema.json.
    """
    # Convert simple playlist to full playlist to access tracks
    full_playlist: tekore.model.FullPlaylist
    full_playlist = spotify.playlist(playlist.id)  # type: ignore

    paging = full_playlist.tracks
    track_iterator: Generator[tekore.model.PlaylistTrack, None, None]
    track_iterator = spotify.all_items(paging)  # type: ignore

    # NOTE: I don't know why, but for some reason the iterator has to be
    # iterated through once beforehand for the comprehension below to
    # work.  Maybe something to do with the click.progressbar()?
    list(track_iterator)

    return {
        "id": full_playlist.id,
        "name": full_playlist.name,
        "description": full_playlist.description or None,
        "tracks": [track_model_to_json(track) for track in track_iterator]
    }


class Serializer:
    def __init__(self, spotify: tekore.Spotify) -> None:
        self.spotify = spotify

    def serialize(self) -> JSONData:
        user_data = self._serialize_profile()
        saved_songs = self._serialize_saved_songs()
        owned_playlists, followed_playlists = self._serialize_playlists()
        return {
            "user": user_data,
            "likedSongs": saved_songs,
            "ownedPlaylists": owned_playlists,
            "followedPlaylists": followed_playlists,
        }

    def _serialize_profile(self) -> JSONData:
        user = self.spotify.current_user()
        data = user_model_to_json(user)
        click.secho("Gathered data for user profile", dim=True)
        return data

    def _serialize_saved_songs(self) -> List[JSONData]:
        paging = self.spotify.saved_tracks()
        saved_track_iterator: Generator[tekore.model.SavedTrack, None, None]
        saved_track_iterator = self.spotify.all_items(paging)  # type: ignore

        click.secho("Gathering data for saved songs...", dim=True)
        iterator: Iterator[tekore.model.SavedTrack]
        with click.progressbar(saved_track_iterator) as iterator:
            data = [track_model_to_json(saved_track)
                    for saved_track in iterator]
        click.secho("Gathered data for saved songs", dim=True)

        return data

    def _serialize_playlists(self) -> Tuple[List[JSONData],
                                            List[JSONData]]:
        """
        Return a 2-tuple with data for the owned playlists and followed
        playlists.

        NOTE: Both playlist types are fetched in one subroutine because
        the API only supports returning all playlists -- both owned and
        followed -- instead of individually, so this way we only make
        one API call.
        """
        user_id = self.spotify.current_user().id

        paging = self.spotify.playlists(user_id)
        playlist_iterator: Generator[tekore.model.SimplePlaylist, None, None]
        playlist_iterator = self.spotify.all_items(paging)  # type: ignore

        owned: List[JSONData] = []
        followed: List[JSONData] = []

        click.secho("Gathering data for playlists...", dim=True)
        iterator: Iterator[tekore.model.SimplePlaylist]
        with click.progressbar(playlist_iterator) as iterator:
            for simple_playlist in iterator:
                data = playlist_model_to_json(simple_playlist, self.spotify)
                owner_id = simple_playlist.owner.id
                if owner_id == user_id:
                    owned.append(data)
                else:
                    # Extend data with information about the owner
                    data["owner"] = user_model_to_json(simple_playlist.owner)
                    followed.append(data)
        click.secho("Gathered data for playlists", dim=True)

        return (owned, followed)


@click.command("serialize")
@click.option("-o", "--output",
              required=True,
              type=click.File(mode="wt", encoding="utf-8"))
def serialize_command(output: TextIO) -> None:
    spotify = get_client()
    click.secho(f"Serializing your library to JSON...", fg="green")
    library_json = Serializer(spotify).serialize()
    json.dump(library_json, output)
    click.secho(f"Saved your library at {output.name}", fg="green")
