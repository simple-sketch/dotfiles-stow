#!/bin/sh
# Start pipewire for this sway session, after reaping the stack a previous one
# left behind.
#
# sway does not kill what it execs. When a sway session ends, its pipewire,
# wireplumber and pipewire-pulse are reparented to init and keep running; log
# in again without rebooting and there are two of each, all four talking to
# the same /run/user/$UID/pipewire-0. The second wireplumber is the damaging
# half, it is meant to be a singleton session manager. The stale one still
# holds the bluez media endpoints it registered with bluetoothd, so it wins
# the A2DP handshake and then answers on a session bus that is already gone:
#
#   dbus-daemon: Rejected send message, 0 matched rules; type="method_return"
#     sender=wireplumber (the stale one) destination=bluetoothd
#
# The headset connects, bluez sets up a transport, and no output sink is ever
# created -- only the mic source shows up in wpctl. Hence the reap.
#
# pkill -x matches the process name, so one pattern covers both the daemon and
# the pulse server, which runs as `pipewire -c pipewire-pulse.conf`. Matching
# names rather than full command lines also keeps pkill off this script's own
# arguments.

# Serialize manual recovery/login launches; never signal another user's audio.
uid=$(id -u)
if [ "$uid" -eq 0 ] || [ -z "$XDG_RUNTIME_DIR" ] ||
    [ ! -d "$XDG_RUNTIME_DIR" ] || [ -L "$XDG_RUNTIME_DIR" ] ||
    [ "$(stat -c '%u:%a' "$XDG_RUNTIME_DIR")" != "$uid:700" ]; then
    printf '%s\n' 'Audio startup requires a private desktop-user runtime directory.' >&2
    exit 1
fi
exec 9>"$XDG_RUNTIME_DIR/sway-audio-start.lock"
flock -w 10 9 || exit 1

# Stop the core first so its WirePlumber supervisor will not restart the child.
pkill -u "$uid" -x pipewire
pkill -u "$uid" -x wireplumber

# pipewire unlinks its sockets under /run/user/$UID on the way out, and it does
# so for the paths it holds regardless of which instance created them. Start
# the replacement too early and the dying one deletes the new socket, leaving a
# pipewire that nothing can connect to. Wait for it to go.
i=0
while pgrep -u "$uid" -x pipewire >/dev/null 2>&1 ||
    pgrep -u "$uid" -x wireplumber >/dev/null 2>&1; do
    if [ "$i" -ge 80 ]; then
        printf '%s\n' 'Old audio processes did not stop; refusing to start duplicates.' >&2
        exit 1
    fi
    sleep 0.1
    i=$((i + 1))
done

# The pipewire Stow package launches the WirePlumber supervisor and pulse server
# through context.exec. Release the startup lock before executing the core.
exec 9>&-
exec pipewire
