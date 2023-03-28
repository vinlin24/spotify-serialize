#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""transfer.py

Script for adding all songs from a playlist to another playlist.
"""

import sys
from typing import Set

from tekore.model import FullPlaylist, PlaylistTrack

from spotify_serialize.utils import get_client


def main() -> None:
    argc = len(sys.argv)
    if argc != 3:
        sys.stderr.write(f"USAGE: {sys.argv[0]} SRC_ID DEST_ID\n")
        sys.exit(22)

    src_id = sys.argv[1]
    dest_id = sys.argv[2]
    client = get_client()

    src_playlist: FullPlaylist = client.playlist(src_id)  # type: ignore
    dest_playlist: FullPlaylist = client.playlist(dest_id)  # type: ignore

    src_track_ids: Set[PlaylistTrack] = \
        {track.track.id  # type: ignore
         for track in client.all_items(src_playlist.tracks)}
    dest_track_ids: Set[PlaylistTrack] = \
        {track.track.id  # type: ignore
         for track in client.all_items(dest_playlist.tracks)}

    unique_track_ids = src_track_ids - dest_track_ids

    with client.chunked():
        client.playlist_add(dest_id, list(unique_track_ids))

    num_transferred = len(unique_track_ids)
    num_in_src = len(src_track_ids)
    num_already_present = num_in_src - num_transferred
    print(
        f"Transferred {num_transferred} tracks from "
        f"{src_playlist.name!r} (ID={src_id}, which had {num_in_src} tracks) "
        f"to {dest_playlist.name!r} (ID={dest_id}, which already had "
        f"{num_already_present} of its tracks)."
    )


if __name__ == "__main__":
    main()
