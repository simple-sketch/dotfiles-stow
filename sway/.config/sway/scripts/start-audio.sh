#!/bin/sh
# Audio only: Sway itself is launched by ~/.bash_profile.
# PipeWire's drop-ins start WirePlumber and pipewire-pulse in the same process
# group, so stopping that group cleans up the whole audio stack.
set -u

# This connection closes when Sway exits (including a compositor crash).
swaymsg -m -t subscribe '["shutdown"]' >/dev/null &
watch_pid=$!

setsid pipewire &
audio_pid=$!

# shellcheck disable=SC2329
cleanup() {
    trap - EXIT HUP INT TERM
    kill -TERM "-$audio_pid" 2>/dev/null || true
    kill -TERM "$watch_pid" 2>/dev/null || true
    wait "$audio_pid" 2>/dev/null || true
    wait "$watch_pid" 2>/dev/null || true
}
trap 'cleanup' EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

# Wait for Sway's IPC connection to close, then run the cleanup trap.
wait "$watch_pid"
exit "$?"
