#!/bin/sh
# PipeWire's context.exec starts children only once. Restart WirePlumber if it
# exits, so Bluetooth audio profiles remain registered after a failure.
set -u

state_dir=${XDG_STATE_HOME:-"$HOME/.local/state"}
mkdir -p "$state_dir"
log="$state_dir/wireplumber.log"

trap 'exit 0' HUP INT TERM
while :; do
    wireplumber >>"$log" 2>&1
    status=$?
    printf 'supervise-wireplumber: exited with status %s; restarting in 2s\n' "$status" >>"$log"
    sleep 2
done
