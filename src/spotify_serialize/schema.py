from typing import List, Literal, Optional, TypedDict

SpotifyID = str
SpotifyURI = str


class UserJSON(TypedDict):
    id: SpotifyID
    displayName: str
    numFollowers: Optional[int]


class TrackJSON(TypedDict):
    id: SpotifyID
    name: str
    artists: List[str]
    addedAt: Optional[str]
    type: Literal["track", "episode"]


class PlaylistJSON(TypedDict):
    id: SpotifyID
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
