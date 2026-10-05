#!/bin/sh
# Audio only: Sway itself is launched by ~/.bash_profile.
# Void's PipeWire drop-ins start WirePlumber and pipewire-pulse in this group.
set -u

# Refuse to start an unmanaged audio stack outside a graphical session.
: "${SWAYSOCK:?Run this helper from the Sway config}"
: "${XDG_RUNTIME_DIR:?A per-user runtime directory is required}"
: "${DBUS_SESSION_BUS_ADDRESS:?Start Sway inside dbus-run-session}"

watch_pid=
setsid pipewire &
audio_pid=$!

# shellcheck disable=SC2329
cleanup() {
    trap - EXIT HUP INT TERM
    kill -TERM "-$audio_pid" 2>/dev/null || true
    # Also handle termination before setsid has created the process group.
    kill -TERM "$audio_pid" 2>/dev/null || true
    if [ -n "$watch_pid" ]; then
        kill -TERM "$watch_pid" 2>/dev/null || true
        wait "$watch_pid" 2>/dev/null || true
    fi
    wait "$audio_pid" 2>/dev/null || true
}
trap 'cleanup' EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

# Establish the group before monitoring IPC: a failed subscription may return
# immediately, and cleanup must not race setsid's startup.
i=0
until kill -0 "-$audio_pid" 2>/dev/null; do
    if ! kill -0 "$audio_pid" 2>/dev/null || [ "$i" -ge 50 ]; then
        echo 'start-audio: PipeWire failed to create its process group' >&2
        exit 1
    fi
    sleep 0.1
    i=$((i + 1))
done

# -m keeps the subscription alive after the acknowledgement. The connection
# closes on normal logout or compositor crash; either way, clean up audio.
swaymsg -m -t subscribe '["shutdown"]' >/dev/null &
watch_pid=$!
wait "$watch_pid"
exit "$?"
