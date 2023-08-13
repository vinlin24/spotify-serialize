import json
import sys

with open(sys.argv[1], "rt", encoding="utf-8") as file:
    data = json.load(file)

print("likedSongs:", len(data["likedSongs"]))
print("ownedPlaylists:", len(data["ownedPlaylists"]))

print()
for playlist in data["ownedPlaylists"]:
    print(f"{playlist['name']}:", len(playlist["tracks"]))
print()

print("followedPlaylists:", len(data["followedPlaylists"]))

print()
for playlist in data["followedPlaylists"]:
    print(f"{playlist['name']}:", len(playlist["tracks"]))
print()
