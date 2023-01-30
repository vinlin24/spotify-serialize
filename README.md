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


**Work in progress.**


## Description


This package serializes the current state of a Spotify library as [zlib-compressed](https://docs.python.org/3/library/zlib.html) JSON data, with support for deserializing such data directly back into a user's library.

I made this package as a blunt way to "back up" my entire Spotify library, as both a protective measure and a logical first step towards my planned project, a Spotify version control system.


## Setup


Create and activate a new virtual environment for the project directory. Then, you can install the package in **editable mode**:


```sh
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

> **NOTE:** This project uses [`pyproject.toml`](pyproject.toml) for metadata and setup instead of the legacy `setup.py` approach. If the installation fails, you probably have an outdated version of pip:
>
>   ```sh
>   python -m pip install --upgrade pip
>   ```


## Running


The CLI command is `spotify_serialize`. Below are some tentative example usages.


### Authentication


This uses [Spotify's PKCE authorization flow](https://developer.spotify.com/documentation/general/guides/authorization/code-flow/). The application will write the returned access tokens in plain text to a dedicated configuration directory under your home directory. As long as this file is present, the application will automatically use or refresh your access token, so you only need to run this for the first time:

```sh
spotify_serialize login
```

This command will automatically open a web browser prompting you to authorize my application with your Spotify user account. Afterwards, you are redirected to some URI I set, https://google.com at the moment. Copy the redirect URL and paste it back into the console to complete the login.


### Serialization


**Serializing** your library means taking a snapshot of the state of your current Spotify library and transforming its relevant attributes into a byte stream that can be saved on your local filesystem.

```sh
spotify_serialize serialize -o my_library
```

The format of the output file (e.g. `my_library`) is a zlib-compressed JSON file.


### Deserialization


**Deserializing** means using the contents of a data file produced by [serialization](#serialization) to restore the represented state of your Spotify library. To minimize destructive behavior, this command by default will only **add** playlists/tracks not already present in the library. For a **complete** restoration of state (**removing** playlists/tracks that are not present in the backup), you must explicitly confirm with an option.


```sh
spotify_serialize deserialize -i my_library
```


## Disclaimer


This is a hobby project, and I shall not be held liable for misuse of this package or lost user data.

<!-- TODO: Maybe publish a JSON schema file when your package is stable. -->

In the event that deserializing fails, you can still inspect the data files you have to figure out how to restore your data. After decompressing, the files are simply JSON documents that store information about your library (mostly in the form of [Spotify resource IDs](https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids)):

```python
import zlib
import json

# Decompress into JSON file
with open("backup_file", "rb") as fp:
    compressed = fp.read()
json_string = zlib.decompress(compressed).decode("utf-8")
json_data = json.loads(json_string)
with open("backup_file.json", "wt", encoding="utf-8") as fp:
    json.dump(json_data, fp)
```
