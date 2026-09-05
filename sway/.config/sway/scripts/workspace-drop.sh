#!/bin/sh
# Keep the source alongside the Sway configuration; no pip packages required.
exec python3 "$(dirname -- "$0")/workspace-drop/main.py" "$@"
