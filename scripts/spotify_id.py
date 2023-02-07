#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""spotify_id.py

Simple command line script for determining what a Spotify ID represents.
"""

# pylint: disable=no-member

import sys
from typing import Callable, List, Optional

import tekore
from dotenv import load_dotenv
from tekore import BadRequest, NotFound, Spotify
from tekore.model import Model

__author__ = "Vincent Lin"

SpotifyID = str
ResourceGetter = Callable[[Spotify, SpotifyID], Model]


RESOURCE_GETTERS: List[ResourceGetter] = [
    Spotify.track,
    Spotify.playlist,  # type: ignore
    Spotify.artist,
    Spotify.user,
    Spotify.album,
    Spotify.episode,
    Spotify.show,
    Spotify.chapter,
    Spotify.audiobook,
]
"""
Bound methods of tekore.Spotify instances that take a Spotify ID
argument and return a model representing the corresponding Spotify
resource.  They are arranged in order of search priority based on what
is more likely to be searched.
"""


def get_client() -> tekore.Spotify:
    """
    Load application credentials from .env file and initialize and
    return an authenticated Spotify client instance.
    """
    load_dotenv()
    creds = tekore.config_from_environment(return_refresh=True)
    client_id, client_secret, _, user_refresh = creds
    token = tekore.refresh_user_token(client_id, client_secret, user_refresh)
    return Spotify(token.access_token)


def get_spotify_resource(spotify_id: SpotifyID) -> Optional[Model]:
    """
    Try searching for the given ID through a sequence of resource
    classes, such as track, playlist, artist, etc.  Return the resulting
    model, or None if the ID could not be resolved.
    """
    spotify = get_client()
    for getter in RESOURCE_GETTERS:
        try:
            return getter(spotify, spotify_id)
        except (NotFound, BadRequest):
            continue
    return None


def main() -> None:
    """Main driver function."""
    try:
        spotify_id = sys.argv[1]
    except IndexError:
        sys.stderr.write("Expected at least one argument.\n")
        sys.exit(1)

    result = get_spotify_resource(spotify_id)
    if result is None:
        sys.stderr.write(f"No resource found with ID {spotify_id!r}.\n")
        sys.exit(1)
    print(result)


if __name__ == "__main__":
    main()
