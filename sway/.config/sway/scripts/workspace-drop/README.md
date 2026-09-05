# Sway workspace drop

A small, resident workspace selector for **Super + left-hold on a Sway title bar**.
Point at a number **1–9**, then release the left button to send the clicked window
there. The real window stays still until the drop, and your view stays on the
source workspace. Works with tiled and floating windows, including inactive tabs.

## Use

- **Super + hold left mouse on Sway's title bar**: open the selector near the window.
- **Hover a numbered tile and release left mouse**: move the original window.
- **Release over a gap, the dialog header, another window or empty workspace**:
  cancel without moving it.
- **Escape**, **Super+Escape**, or **right-click**: cancel.
- Releasing Super first is okay: the eventual **left-button release** determines
  the drop. There is no keyboard-number selection; your existing keyboard move
  shortcuts remain unchanged outside the temporary selector mode.
- A **15-second timeout** cancels an abandoned gesture.

Ordinary title-bar dragging without Super, Super-drag inside window content,
Super+right-drag resizing, and normal right-click-to-close remain unchanged.
The helper never toggles the source window's floating or fullscreen state.
Existing numbered workspace names (for example `3: chat`) are respected.

## Install / enable

Runtime dependencies on Void Linux:

```sh
sudo xbps-install -S python3 python3-gobject python3-cairo gtk+3
```

These runtime packages also pull in the required GLib/Gdk/Pango introspection
typelibs. They are included in `void-setup-elogind/install.sh` for clean installs.
`gtk-layer-shell` was installed during research but is **not used by the final
implementation**. `wtype` and `grim` are **test-only**.
No pip dependencies, compositor patches, input-group membership, root daemon,
raw `/dev/input` access, or synthetic input are used by the running helper.

The source lives in `~/.config/sway/scripts/workspace-drop/`, with the launcher at
`~/.config/sway/scripts/workspace-drop.sh` and bindings at
`~/.config/sway/workspace-drop.conf`.

Place this after the general floating-window rules / `floating_modifier` in
`~/.config/sway/config`:

```sway
include ~/.config/sway/workspace-drop.conf
```

Then:

```sh
~/.config/sway/scripts/workspace-drop.sh --check
sway --validate --config ~/.config/sway/config
swaymsg reload
```

The included `exec_always` starts the helper. A session-specific file lock prevents
duplicate daemons on reload. The program sleeps on Sway IPC events when idle; it
does not continuously poll pointer position. The dialog exists only during a
selection. No extra permanent bar or panel is installed.

## Implementation and research

1. Sway's mouse bindings operate on the container **under the cursor**, and run
   before its built-in floating/tiling move operation. The title-bar-only opening
   binding focuses that container, emits a distinct `nop` binding event, and
   enters the `workspace-drop` mode.
2. A single Sway IPC subscription receives the synchronous **focus event before
   the binding event**. The helper captures that ID, so later focus changes cannot
   redirect the move to another window. It never queries “whatever is focused” at
   drop time.
3. The popup is a normal, undecorated GTK floating surface, not layer-shell. In a
   headless Sway 1.12 test, a layer surface received motion but **no mouse release**:
   wlroots suppressed it because the opening press had been consumed by Sway.
   Sway also excludes layer surfaces from its mouse-binding hit regions.
4. In the temporary mode, a `--whole-window --release` binding reports the actual
   release through IPC and exits the mode. GTK supplies tile hit-testing. Pending
   GTK motion/leave events are processed before using the selection.
5. A successful drop runs a numeric-ID-scoped command such as:
   `[con_id=123] move --no-auto-back-and-forth container to workspace number 3`.
   Window titles are plain text, never shell commands or Pango markup.
6. A mark-based prototype was rejected: Sway's `mark` command also re-evaluates
   `for_window` rules, which unexpectedly resized manually floated test windows.
   The final implementation **does not add or remove any marks**.

Primary references:

- [Sway mouse binding, workspace move and tiling-drag documentation](https://github.com/swaywm/sway/blob/1.12/sway/sway.5.scd)
- [Sway 1.12 default pointer handler: binding precedence and hit regions](https://github.com/swaywm/sway/blob/1.12/sway/input/seatop_default.c)
- [Sway native floating drag handler](https://github.com/swaywm/sway/blob/1.12/sway/input/seatop_move_floating.c)
- [Sway IPC events and commands](https://github.com/swaywm/sway/blob/1.12/sway/sway-ipc.7.scd)
- [Sway mark command: `view_execute_criteria`](https://github.com/swaywm/sway/blob/1.12/sway/commands/mark.c)
- [Sway discussion of mouse-release binding limitations](https://github.com/swaywm/sway/issues/5333)
- [Layer-shell pointer-position approach discussed by Sway developers](https://github.com/swaywm/sway/pull/8780)
- [SFWBar's existing workspace-group drag-and-drop alternative](https://github.com/LBCrion/sfwbar/blob/main/doc/sfwbar.rst)

## Boundaries

- Starts on **Sway's server-side title bar**, not an application's own GTK/Firefox
  header bar. The latter is window content, where native Super-drag is preserved.
- Targets are 1–9, including empty workspaces; workspace 10 is intentionally not
  shown. Tiled/fullscreen layout, output placement and floating coordinates on
  the destination are still governed by Sway and existing window rules.
- Only one gesture is active at a time. Tested with one seat and two outputs,
  including a second-output source and fractional output scaling.
- The 336×360 logical-pixel dialog must fit in the source workspace's usable area;
  otherwise activation is cancelled safely.
- Dropping over a **layer-shell bar/panel** cannot trigger a Sway mouse-release
  binding. It never moves a window there. Use **Escape** to dismiss, or let the
  timeout dismiss it. Output/workspace changes and a source-window close cancel
  the selection as well.
- If the helper is killed abruptly, **Escape** still exits the Sway mode. Restart
  the helper afterward. Normal graceful shutdown restores the mode immediately.
- This is not the native window-following-pointer version of the gesture.

## Diagnostics / restart / disable

```sh
# Runtime dependency check
~/.config/sway/scripts/workspace-drop.sh --check

# Stop this session's helper (does not affect separate headless test sessions)
~/.config/sway/scripts/workspace-drop.sh --stop

# After source changes, restart it without restarting Sway
~/.config/sway/scripts/workspace-drop.sh --daemon --verbose
```

The daemon runs in the foreground when launched manually; Ctrl+C stops it. For a
normal background restart, stop it, wait a moment, then run `swaymsg reload`.

Logs: `~/.local/state/sway/workspace-drop.log` (rotates at 512 KiB, one backup).
The singleton lock is under `$XDG_RUNTIME_DIR`, keyed to `$SWAYSOCK`. Only numeric
window IDs, workspace labels and lifecycle/error messages are logged, not window
titles or keyboard input.

To disable permanently, remove/comment the `include` line, run `--stop`, then
`swaymsg reload`. This restores the original native Super+title-bar drag.

## Tests

```sh
python3 -m unittest discover \
  -s ~/.config/sway/scripts/workspace-drop/tests -p 'test_*.py' -v
python3 ~/.config/sway/scripts/workspace-drop/tests/integration.py
```

Integration dependencies: `sway`, `foot`, `wtype`, `grim`. The runner creates its
own **headless Sway** with two outputs and asserts that its IPC socket and Wayland
display differ from the desktop **before sending any test input**. No test input
is sent to the live desktop. Only the tests use virtual pointer/keyboard input.
Test logs and a screenshot are retained in `/tmp/workspace-drop-integration.*`.

Coverage: 8 unit tests and 24 headless integration tests for floating/tiled moves,
staying on the source workspace, existing numbered names, all 1–9 targets,
current-workspace no-op, outside/header/gap release, Escape/right-click/timeout,
Super release order, closed source, preserved marks, inactive-tab targeting,
cross-output moves and source placement, untouched native dragging, fractional
scaling, keyboard layouts, fast clicks, duplicate prevention, shutdown and reload.
