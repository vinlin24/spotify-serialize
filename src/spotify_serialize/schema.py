from typing import List, Literal, Optional, TypedDict


class UserJSON(TypedDict):
    id: str
    displayName: str
    numFollowers: Optional[int]


class TrackJSON(TypedDict):
    id: str
    name: str
    artists: List[str]
    addedAt: Optional[str]
    type: Literal["track", "episode"]


class PlaylistJSON(TypedDict):
    id: str
    name: str
    description: Optional[str]
    tracks: List[TrackJSON]


class FollowedPlaylistJSON(PlaylistJSON):
    owner: UserJSON


class SnapshotJSON(TypedDict):
    user: UserJSON
    likedSongs: List[TrackJSON]
    ownedPlaylists: List[PlaylistJSON]
    followedPlaylists: List[FollowedPlaylistJSON]
