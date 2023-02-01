#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple zlib compression/decompression script.

USAGE: {c,d,compress,decompress} FROM_PATH TO_PATH
"""

import json
import sys
import zlib
from pathlib import Path
from typing import Callable, NoReturn

__author__ = "Vincent Lin"

USAGE_LINE = "{c,d,compress,decompress} FROM_PATH TO_PATH"


def compress(src_path: Path, bin_path: Path) -> None:
    """Compress a JSON file into a binary file."""
    with src_path.open("rt", encoding="utf-8") as fp:
        json_dict = json.load(fp)
    json_string = json.dumps(json_dict)
    payload = zlib.compress(json_string.encode("utf-8"))
    with bin_path.open("wb") as fp:
        fp.write(payload)


def decompress(bin_path: Path, src_path: Path) -> None:
    """Decompress a binary file into a JSON file."""
    with bin_path.open("rb") as fp:
        compressed = fp.read()
    json_string = zlib.decompress(compressed).decode("utf-8")
    json_dict = json.loads(json_string)
    with src_path.open("wt", encoding="utf-8") as fp:
        json.dump(json_dict, fp)


def exit_with_message(message: str) -> NoReturn:
    """Write an error and usage message to stderr and exit with 1."""
    sys.stderr.write(f"{message}\n")
    sys.stderr.write(f"USAGE: {USAGE_LINE}\n")
    sys.exit(1)


def main() -> None:
    """Parse command line arguments and execute request."""
    try:
        _, command, from_path, to_path, *_ = sys.argv
    except ValueError:
        exit_with_message(
            f"Expected at least 3 arguments, got {len(sys.argv)} instead.")

    from_path = Path(from_path)
    to_path = Path(to_path)

    def execute_command(func: Callable[[Path, Path], None],
                        from_path: Path,
                        to_path: Path
                        ) -> None:
        try:
            func(from_path, to_path)
        except FileNotFoundError as e:
            exit_with_message(str(e))

    option = command.lower()[0]
    if option == "c":
        execute_command(compress, from_path, to_path)
        print(f"Compressed {from_path} to {to_path}.")
    elif option == "d":
        execute_command(decompress, from_path, to_path)
        print(f"Decompressed {from_path} to {to_path}.")
    else:
        exit_with_message("Expected[c]ompress/[d]ecompress as first argument.")


if __name__ == "__main__":
    main()
