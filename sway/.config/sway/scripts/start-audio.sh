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

pkill -x wireplumber
pkill -x pipewire

# pipewire unlinks its sockets under /run/user/$UID on the way out, and it does
# so for the paths it holds regardless of which instance created them. Start
# the replacement too early and the dying one deletes the new socket, leaving a
# pipewire that nothing can connect to. Wait for it to go.
i=0
while pgrep -x pipewire >/dev/null 2>&1 && [ "$i" -lt 50 ]; do
    sleep 0.1
    i=$((i + 1))
done

# wireplumber and pipewire-pulse come up as children of this process, from the
# context.exec drop-ins in ~/.config/pipewire/pipewire.conf.d.
exec pipewire
