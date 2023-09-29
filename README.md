# Spotify Serialize

<p align=center>
  <!-- TODO: Maybe replace this with a PyPI link if you decide to publish this package. -->
  <a href="https://github.com/vinlin24/spotify-serialize/releases">
    <img src="https://img.shields.io/badge/Version-(WIP)-brightgreen">
  </a>
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Python-3.8%2B-yellowgreen">
  </a>
  <a href="https://click.palletsprojects.com/en/8.1.x/">
    <img src="https://img.shields.io/badge/CLI%20Framework-click-blueviolet">
  </a>
  <a href="https://tekore.readthedocs.io/en/stable/index.html">
    <img src="https://img.shields.io/badge/Spotify%20Framework-tekore-blue">
  </a>
</p>

Simple backup system for a user's Spotify library.

**Some features are still a work in progress.**


## Description

This package serializes the current state of a Spotify library as JSON data,
with support for deserializing such data directly back into a user's library.

I made this package as a blunt way to "back up" my entire Spotify library, as
both a protective measure and a logical first step towards a potential future
project, a Spotify version control system.


## Setup

This project has been upgraded to use the [Poetry](https://python-poetry.org/)
package manager.

If you prefer to have Poetry create a virtual environment locally in the project
directory, you can initialize your own (`.gitignore`d) `poetry.toml`
configuration file:

```toml
[virtualenvs]
create = true
in-project = true
```

Then run this to install all dependencies, including the Spotify Serialize
package itself:

```sh
poetry install
```


## Running

The script is `ss`, which you can invoke through Poetry:

```sh
poetry run ss --help
```

Below are some tentative example usages.


### Authentication

This uses [Spotify's PKCE authorization
flow](https://developer.spotify.com/documentation/general/guides/authorization/code-flow/).
The application will write the returned access tokens in plain text to a
dedicated configuration directory under your home directory.  As long as this
file is present, the application will automatically use or refresh your access
token, so you only need to run this for the first time:

```sh
poetry run ss login
```

This command will automatically open a web browser prompting you to authorize my
application with your Spotify user account.  Afterwards, you are redirected to
some URI I set, https://google.com at the moment.  Copy the redirect URL and
paste it back into the console to complete the login.


### Serialization

**Serializing** your library means taking a snapshot of the state of your
current Spotify library and transforming its relevant attributes into data that
can be saved on your local filesystem.

```sh
poetry run ss serialize -o my_library
```

The format of the output file (e.g. `my_library`) is a directory with the
following structure:

```
my_library/
  images/
    followed-playlists/
      [spotify_id].jpg
    owned-playlists/
      [spotify_id].jpg
    profile.jpg
  TIMESTAMP
  data.json
```

The meat of the data is in `data.json`, whose
[schema](schema/snapshot.schema.json) contains data like user details at the
moment of snapshot and of course owned playlists, followed playlists, and saved
songs (Liked Songs).

`TIMESTAMP` is a text file that just contains the timestamp in [ISO
format](https://en.wikipedia.org/wiki/ISO_8601) (UTC) of the snapshot.

`images/` serves as a database for the binary image data that comes with the
Spotify data.  `profile.png` is the user's profile picture at the time of
snapshot, `owned-playlists/[spotify_id].png` is the image set for the owned
playlist with given `id`, etc.

> 💡 You can also opt out of storing images with the `--no-images` flag.  Images
> take up a lot of space!

The state of the followed playlists is saved too in case one wants to peek into
what that playlist used to look like -- although it's unavailable for
deserialization (for obvious reasons).

**ADDED:** The `--playlist` option for serializing just one playlist:

```sh
poetry run ss serialize --playlist "5FpuSaX0kDeItlPMIIYBZS"
```

This will generate a `[TIMESTAMP].playlist-snapshot` directory containing a
`data.json`, but instead of it having the [full
schema](schema/snapshot.schema.json), it only contains data for the [singular
playlist](schema/playlist.schema.json).

> 📝 This was motivated by me starting a new counter using my
[counters](https://github.com/vinlin24/counters) program, where I make my main
Spotify playlist be named "Day 0x01", "Day 0x02", etc. for the rest of my senior
year until I graduate. With `--playlist`, I can hook a script up to a scheduler
such that I back up this playlist daily so I can observe how it changes over the
course of the year!


### Deserialization

**Deserializing** means using the contents of a data file produced by
[serialization](#serialization) to restore the represented state of your Spotify
library.  To minimize destructive behavior, this command at the moment only
works on one playlist at a time.  *More features to come.*

```sh
poetry run ss deserialize -i my_library
```

After entering the command with the path to the snapshot directory, the program
will parse it for your owned playlists and prompt you to choose which playlist
to deserialize.  The state of the chosen playlist will replace that in your live
Spotify library.  This includes additions *and* deletions:

* Tracks found in the snapshot but not in your playlist are **added** to the
  playlist.
* Tracks found in the playlist but not in the snapshot are **removed** from the
  playlist.
* Tracks that are found in both are untouched.  This means that not even **the**
  "date added" attribute of those tracks will be modified.


## Disclaimer

This is a hobby project, and I shall not be held liable for misuse of this
package or lost user data.
