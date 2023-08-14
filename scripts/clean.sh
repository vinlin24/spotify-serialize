#!/usr/bin/env bash
find . -type d -name "*.snapshot" -not -path ".venv" -exec rm -rf {} \;
find . -type d -name "__pycache__" -not -path ".venv" -exec rm -rf {} \;
