#!/bin/sh
# Compatibility entry point; monitor-profiles.py serializes all display changes.
set -eu
controller="$(dirname "$0")/monitor-profiles.py"
if [ "${1:-}" = --toggle ]; then
    [ "$#" -le 2 ] || { printf '%s\n' 'usage: arrange-outputs.sh --toggle [extend|portrait]' >&2; exit 1; }
    exec python3 "$controller" toggle "${2:-extend}"
fi
exec python3 "$controller" arrange "$@"
