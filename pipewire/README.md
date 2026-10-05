# PipeWire crash recovery (Void Linux / Sway)

This package starts one WirePlumber supervisor and the PipeWire PulseAudio
compatibility server using PipeWire's `context.exec` drop-ins. WirePlumber is
restarted if it exits, including when `libspa-bluez5.so` crashes after a Bluetooth
adapter disappears during suspend/resume. This is a **recovery workaround**, not
a fix for the underlying plugin bug; a crash can still briefly interrupt sound.

## Clean-machine setup

Install the dependencies (administrator privileges are needed only here):

```sh
sudo xbps-install -S git stow pipewire libspa-bluetooth wireplumber wireplumber-elogind bluez dbus elogind python3 procps-ng util-linux
sudo ln -s /etc/sv/dbus /var/service/       # only if not already enabled
sudo ln -s /etc/sv/elogind /var/service/    # only if not already enabled
sudo ln -s /etc/sv/bluetoothd /var/service/ # only if not already enabled
cd "$HOME/dotfiles-stow"
stow --target="$HOME" pipewire sway
```

Log into Sway as a normal user through a D-Bus session (for example,
`dbus-run-session sway`). Elogind/PAM must provide the user-owned, mode-0700
`XDG_RUNTIME_DIR`. Sway's `start-audio.sh` starts the core, and the core launches
this package's drop-ins. A different desktop may start `pipewire` itself once.
Use the default `pipewire-0` core; multiple independent cores are not supported.

Do **not** also launch WirePlumber or PipeWire from system services, another
session manager, an autostart entry, or another `context.exec` configuration.
Check `/etc/pipewire/pipewire.conf.d` and your user drop-ins for duplicates.
Do not link `/usr/share/examples/wireplumber/10-wireplumber.conf`: this package
replaces that unsupervised launch. Python 3, `pw-cli`, and `wireplumber` must be
available on the desktop session's PATH. No username or repository location is
hard-coded, and `$HOME/.local/bin` does not need to be on PATH.

For an existing installation, Stow reports conflicting files: back those up
outside the target directory before stowing. Avoid `stow --adopt`, which would
replace the repository configuration with your old files. No Bluetooth pairing
records, headset addresses, passwords, or runtime lock files are stored here.
Pair your own headset normally and select its output in your audio controls.

## Recovery and limits

- Automatic restart delays are 2, 4, 8, 16, then 30 seconds. The delay resets
  after WirePlumber stays alive for a minute; persistent crashes do not spin.
- A private, non-symlink lock prevents duplicate supervisors. The child does not
  inherit the lock. Unsafe locks (symlink, FIFO, hard link, public permissions)
  are rejected. Never remove a lock file while a supervisor is running.
- Core identity includes its owner, PID, and Linux process start time. When the
  original core exits, the supervisor terminates/reaps its child, escalating to
  SIGKILL after three seconds if necessary. It does not attach to a new core
  that reused the same PID. SIGTERM/SIGINT/SIGHUP also clean up the child.
- `pw-cli` discovery has bounded retries/timeouts. Failures are logged to stderr,
  as are restart attempts; there is no privileged daemon or periodic cron job.
- Manual Sway recovery: `~/.config/sway/scripts/start-audio.sh &`. This interrupts
  **all audio for your user**. The script serializes startup, signals only your
  user's processes, and refuses to start duplicates if shutdown times out.
- Bluetooth adapter/firmware failures, unavailable earphones, and pairing
  problems need separate troubleshooting. This does not force-connect a headset
  or change volume, codec, routing, Bluetooth policy, or power management.

## Tests

```sh
cd "$HOME/dotfiles-stow"
make check-audio
```

Install `make` and `ShellCheck` to run this target (`sudo xbps-install -S make ShellCheck`).
The separate `make check-shell` target also requires `shfmt`.

Tests use temporary private runtime directories and fake audio processes; they
never restart real desktop audio or suspend the machine. They cover lock safety,
PID identity/reuse, singleton behavior, restart backoff, child cleanup, crash
recovery, and hung core discovery. ShellCheck checks the Sway launcher. To test
installation separately without changing your home:

```sh
target=$(mktemp -d)
stow --target="$target" pipewire
find "$target" -type l
stow --delete --target="$target" pipewire
rmdir "$target"
```

A real suspend/resume test is still required on the target hardware. Reconnect
and inspect `bluetoothctl info <your-headset-address>` and `wpctl status` afterward.
