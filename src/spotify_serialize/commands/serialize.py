"""serialize.py

Implement serializing the user's library into a compressed data format.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, Iterator, List, Optional, Tuple, Union

import click
import requests
import tekore

from .. import abort_with_error
from ..client import get_client

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


def track_model_to_json(track: Track) -> Optional[JSONData]:
    """
    Convert a tekore track model to the format of track.model.json.
    """
    _track = track.track  # type: ignore

    # NOTE: for some reason, _track can be None
    if _track is None:
        return None

    # Episodes don't have artists
    if isinstance(_track, tekore.model.FullEpisode):
        artists = []
        track_type = "episode"
    else:
        artists = [artist.name for artist in _track.artists]
        track_type = "track"

    return {
        "id": _track.id,
        "name": _track.name,
        "artists": artists,
        "addedAt": track.added_at.isoformat(),
        "type": track_type,
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

    # TODO: somehow decouple progressbar from conversion function
    iterator: Iterator[tekore.model.PlaylistTrack]
    tracks: List[JSONData] = []
    skipped: List[Track] = []

    with click.progressbar(
        track_iterator,
        label=full_playlist.name,
        length=paging.total,
        show_pos=True,
        show_percent=True,
    ) as iterator:
        for track in iterator:
            data = track_model_to_json(track)
            if data is None:
                skipped.append(track)
            else:
                tracks.append(data)

    if skipped:
        warn_about_skipped_tracks(skipped)

    return {
        "id": full_playlist.id,
        "name": full_playlist.name,
        "description": full_playlist.description or None,
        "tracks": tracks
    }


def echo_warning(message: str) -> None:
    click.secho("WARNING: ", nl=False, fg="yellow", bold=True)
    click.secho(message, fg="yellow")


def warn_about_skipped_tracks(tracks: List[Track]) -> None:
    echo_warning("Was unable to gather data for the following tracks:")
    for track in tracks:
        click.secho(track)


def download_image(url: str, dest_path: Path) -> bool:
    response = requests.get(url)
    if not response.ok:
        echo_warning(f"Was unable to download image at {url} to {dest_path}.")
        return False
    data = response.content
    with dest_path.open("wb") as dest_file:
        dest_file.write(data)
    return True


class Serializer:
    def __init__(self, spotify: tekore.Spotify, with_images: bool) -> None:
        self.spotify = spotify
        self.with_images = with_images

    def serialize(self, output_dir: Optional[Path], indent: int) -> Path:
        timestamp = datetime.now().isoformat()
        if output_dir is None:
            output_dir = Path(timestamp.replace(":", ""))

        output_dir.mkdir(parents=True)
        images_dir = output_dir / "images"
        if self.with_images:
            images_dir.mkdir()

        user_data = self._serialize_profile(images_dir)
        saved_songs = self._serialize_saved_songs()
        owned_playlists, followed_playlists = \
            self._serialize_playlists(images_dir)

        timestamp_path = output_dir / "TIMESTAMP"
        timestamp_path.write_text(timestamp)

        json_data = {
            "user": user_data,
            "likedSongs": saved_songs,
            "ownedPlaylists": owned_playlists,
            "followedPlaylists": followed_playlists,
        }

        json_path = output_dir / "data.json"
        with json_path.open("wt", encoding="utf-8") as json_file:
            json.dump(json_data, json_file, indent=indent)

        return output_dir

    def _serialize_profile(self, images_dir: Path) -> JSONData:
        user = self.spotify.current_user()
        if self.with_images:
            image = user.images[-1] if user.images else None
            if image is not None:
                download_image(image.url, images_dir / "profile.png")
        data = user_model_to_json(user)
        click.secho("Gathered data for user profile")
        return data

    def _serialize_saved_songs(self) -> List[JSONData]:
        paging = self.spotify.saved_tracks()
        saved_track_iterator: Generator[tekore.model.SavedTrack, None, None]
        saved_track_iterator = self.spotify.all_items(paging)  # type: ignore

        iterator: Iterator[tekore.model.SavedTrack]
        saved_songs: List[JSONData] = []
        skipped: List[Track] = []

        with click.progressbar(
            saved_track_iterator,
            label="Gathering data for saved songs",
            length=paging.total,
            show_pos=True,
            show_percent=True,
        ) as iterator:
            for saved_track in iterator:
                data = track_model_to_json(saved_track)
                if data is None:
                    skipped.append(saved_track)
                else:
                    saved_songs.append(data)

        if skipped:
            warn_about_skipped_tracks(skipped)

        return saved_songs

    def _serialize_playlists(self, images_dir: Path) -> Tuple[List[JSONData],
                                                              List[JSONData]]:
        """
        Return a 2-tuple with data for the owned playlists and followed
        playlists.

        NOTE: Both playlist types are fetched in one subroutine because
        the API only supports returning all playlists -- both owned and
        followed -- instead of individually, so this way we only make
        one API call.
        """
        owned_images = images_dir / "owned-playlists"
        followed_images = images_dir / "followed-playlists"
        if self.with_images:
            owned_images.mkdir()
            followed_images.mkdir()

        user_id = self.spotify.current_user().id

        paging = self.spotify.playlists(user_id)
        playlist_iterator: Generator[tekore.model.SimplePlaylist, None, None]
        playlist_iterator = self.spotify.all_items(paging)  # type: ignore

        owned: List[JSONData] = []
        followed: List[JSONData] = []

        click.secho("Gathering data for playlists...")

        def _download_image(playlist: tekore.model.SimplePlaylist, user: bool):
            if not playlist.images:
                return
            image = playlist.images[-1]
            if user:
                path = owned_images / f"{playlist.id}.png"
            else:
                path = followed_images / f"{playlist.id}.png"
            download_image(image.url, path)

        for simple_playlist in playlist_iterator:
            data = playlist_model_to_json(simple_playlist, self.spotify)
            owner_id = simple_playlist.owner.id

            if owner_id == user_id:
                owned.append(data)
            else:
                # Extend data with information about the owner
                data["owner"] = user_model_to_json(simple_playlist.owner)
                followed.append(data)

            if self.with_images:
                _download_image(simple_playlist, owner_id == user_id)

        click.secho("Gathered data for playlists")
        return (owned, followed)


@click.command("serialize")
@click.option("-o", "--output",
              type=click.Path(path_type=Path),
              default=None)
@click.option("-i", "--indent",
              type=int,
              default=2)
@click.option("--no-images", is_flag=True)
def serialize_command(output: Optional[Path], indent: int, no_images: bool
                      ) -> None:
    spotify = get_client()
    if output and output.exists():
        abort_with_error(f"{output} already exists!")

    click.secho(f"Serializing your library to JSON...", fg="green")
    serializer = Serializer(spotify, with_images=not no_images)
    output = serializer.serialize(output, indent)
    click.secho(f"Saved your library at {output.name}", fg="green")
