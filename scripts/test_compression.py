#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_compression.py

Unit tester for the compression.py script.

USAGE: 'python -m unittest' OR './test_compression.py'
"""

import shlex
import subprocess
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from typing import Union

__author__ = "Vincent Lin"

EXIT_SUCCESS = 0


def AbsPath(relative: Union[str, Path]) -> Path:
    """
    Convert a string or pathlib.Path path relative from THIS SCRIPT to a
    resolved pathlib.Path instance.
    """
    return (Path(__file__).parent / relative).resolve()


EXAMPLE_SRC = AbsPath("example.json")
EXAMPLE_BIN = AbsPath("example")
EXAMPLE_UNDO = AbsPath("result.json")
UUT = AbsPath("compression.py")


def run_command(command: str, **kwargs) -> CompletedProcess:
    """Run a shell command in a subprocess and return the process."""
    # pylint: disable=subprocess-run-check
    args = shlex.split(command)
    return subprocess.run(args,
                          shell=True,
                          capture_output=True,
                          **kwargs)


class TestCompression(unittest.TestCase):
    """Unit tester for the compression.py script."""

    @classmethod
    def setUpClass(cls) -> None:
        EXAMPLE_BIN.unlink(missing_ok=True)
        EXAMPLE_UNDO.unlink(missing_ok=True)

    @classmethod
    def tearDownClass(cls) -> None:
        EXAMPLE_BIN.unlink(missing_ok=True)
        EXAMPLE_UNDO.unlink(missing_ok=True)

    def _assertErrorWithMessage(self, child: CompletedProcess) -> str:
        """
        Helper function for asserting that a subprocess exited with an
        error code and printed a message to stderr that at least
        contains a USAGE: line. Return the decoded stderr.
        """
        self.assertNotEqual(child.returncode, EXIT_SUCCESS)
        stderr = child.stderr.decode("utf-8")
        self.assertIn("USAGE:", stderr)
        return stderr

    def test_insufficient_args(self) -> None:
        """Test that running with <= 3 arguments fails with message."""
        child = run_command(f"python '{UUT}' c '{EXAMPLE_SRC}'")
        self._assertErrorWithMessage(child)

    def test_option_shorthands(self) -> None:
        """
        Test that running with any string beginning with 'c' is
        equivalent to passing in 'compress' and any string beginning
        with 'd' is equivalent to passing in 'decompress'.
        """
        c_test = f"python '{UUT}' cantaloupe '{EXAMPLE_SRC}' '{EXAMPLE_BIN}'"
        d_test = f"python '{UUT}' diabolical '{EXAMPLE_BIN}' '{EXAMPLE_UNDO}'"
        self.assertEqual(run_command(c_test).returncode, EXIT_SUCCESS)
        self.assertEqual(run_command(d_test).returncode, EXIT_SUCCESS)

    def test_invalid_first_arg(self) -> None:
        """
        Test that running with an invalid first arg fails with message.
        """
        e_test = f"python '{UUT}' e '{EXAMPLE_SRC}' '{EXAMPLE_BIN}'"
        child = run_command(e_test)
        self._assertErrorWithMessage(child)

    def test_invalid_path(self) -> None:
        """Test that providing an invalid path results in an error."""
        nonexistent_src = f"python '{UUT}' c bogus.txt '{EXAMPLE_BIN}'"
        child = run_command(nonexistent_src)
        message = self._assertErrorWithMessage(child)
        self.assertIn("No such file or directory", message)
        self.assertIn("bogus.txt", message)

        nonexistent_bin = f"python '{UUT}' d bogus '{EXAMPLE_UNDO}'"
        child = run_command(nonexistent_bin)
        message = self._assertErrorWithMessage(child)
        self.assertIn("No such file or directory", message)
        self.assertIn("bogus", message)

    # THIS IS THE REAL IMPORTANT ONE
    def test_round_trip(self) -> None:
        """
        Test that compressing a file and then decompressing the
        output file produces an identical file.
        """
        compress = f"python '{UUT}' c '{EXAMPLE_SRC}' '{EXAMPLE_BIN}'"
        decompress = f"python '{UUT}' d '{EXAMPLE_BIN}' '{EXAMPLE_UNDO}'"
        self.assertEqual(run_command(compress).returncode, EXIT_SUCCESS)
        self.assertEqual(run_command(decompress).returncode, EXIT_SUCCESS)

        diff = f"diff -u --strip-trailing-cr '{EXAMPLE_SRC}' '{EXAMPLE_UNDO}'"
        self.assertEqual(run_command(diff).returncode, EXIT_SUCCESS)


if __name__ == "__main__":
    unittest.main()
