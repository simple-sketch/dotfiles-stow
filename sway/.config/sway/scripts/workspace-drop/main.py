#!/usr/bin/env python3
"""Resident, event-driven workspace picker. See README.md for installation."""

import argparse
import fcntl
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import signal
import sys

from core import (APP_ID, BEGIN, BINDING, CANCEL, Decoder, HEIGHT, IPC, MODE, MODE_EVENT,
                  OUTPUT, RELEASE, SHUTDOWN, STOP, TICK, WIDTH, WINDOW, WORKSPACE,
                  counts, find_target, is_window, move_command, popup_position, walk)

LOG = logging.getLogger("workspace-drop")


def load_gui():
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    gi.require_version("GLibUnix", "2.0")
    from gi.repository import GLib, GLibUnix, Gdk, Gtk
    import overlay
    return GLib, GLibUnix, Gdk, Gtk, overlay.Dialog


class Picker:
    def __init__(self, path, timeout):
        self.GLib, GLibUnix, self.Gdk, self.Gtk, self.Dialog = load_gui()
        self.GLib.set_prgname(APP_ID)
        self.GLib.set_application_name("Workspace drop")
        self.ipc = IPC(path)
        self.events = IPC(path)
        result = self.events.request(2, ["window", "binding", "mode", "workspace", "output", "shutdown", "tick"])
        if not result.get("success"):
            raise RuntimeError("Unable to subscribe to Sway events")
        self.events.sock.setblocking(False)
        self.decoder = Decoder()
        self.focused_id = next((n["id"] for n, _, _ in walk(self.ipc.request(4))
                                if n.get("focused") and is_window(n)), None)
        self.target = None
        self.dialog = None
        self.helper_id = None
        self.timeout_ms = int(timeout * 1000)
        self.timeout_source = None
        self.mode_source = None
        self.shutting_down = False
        self.io_source = self.GLib.io_add_watch(
            self.events.sock, self.GLib.IO_IN | self.GLib.IO_HUP | self.GLib.IO_ERR, self.read_events)
        GLibUnix.signal_add(self.GLib.PRIORITY_DEFAULT, signal.SIGTERM, self.quit)
        GLibUnix.signal_add(self.GLib.PRIORITY_DEFAULT, signal.SIGINT, self.quit)
        self.reset_mode()
        LOG.info("Ready on %s", path)

    def reset_mode(self):
        if self.ipc.request(12).get("name") == MODE:
            self.ipc.command('mode "default"')

    def remove_timer(self, attribute):
        source = getattr(self, attribute)
        if source is not None:
            self.GLib.source_remove(source)
            setattr(self, attribute, None)

    def read_events(self, _socket, condition):
        try:
            data = self.events.sock.recv(65536)
            if not data:
                self.quit()
                return False
            for kind, event in self.decoder.feed(data):
                self.handle(kind, event)
        except BlockingIOError:
            return True
        except Exception:
            LOG.exception("Event processing failed")
            self.quit()
            return False
        return not self.shutting_down

    def handle(self, kind, event):
        if kind == WINDOW:
            node = event.get("container", {})
            change = event.get("change")
            if change == "focus":
                self.focused_id = node["id"]
            elif (self.target and change == "new" and node.get("app_id") == APP_ID
                  and node.get("pid") == os.getpid()):
                self.place_dialog(node["id"])
            elif self.target and change == "close" and node.get("id") in (self.target.id, self.helper_id):
                self.cancel("window closed")
        elif kind == BINDING:
            command = event.get("binding", {}).get("command", "")
            if command == BEGIN:
                self.begin(self.focused_id)
            elif command.startswith(RELEASE + ";"):
                # GDK and Sway IPC are separate sockets. Process queued GDK motion/leave
                # before using the hover value; mode-exit cancellation has a grace period.
                self.remove_timer("mode_source")
                self.GLib.idle_add(self.release)
            elif command.startswith(CANCEL + ";"):
                self.cancel("cancel binding")
        elif kind == MODE_EVENT and self.target and event.get("change") != MODE:
            self.remove_timer("mode_source")
            self.mode_source = self.GLib.timeout_add(150, self.mode_left)
        elif self.target and (kind == OUTPUT or (kind == WORKSPACE and event.get("change") == "focus")):
            self.cancel("output/workspace changed")
        elif kind == SHUTDOWN:
            # A config reload also emits shutdown::restart on some Sway versions.
            if event.get("change") == "exit":
                self.quit()
            else:
                self.cancel("configuration reloaded")
        elif kind == TICK and event.get("payload") == STOP:
            self.quit()

    def begin(self, node_id):
        # The mouse binding focuses the clicked container first. Its focus event
        # PRECEDES the binding event on this SAME socket. Capture that ID, not a
        # later focus query (which can race the pointer moving to another window).
        # Do not use marks: Sway's mark command also re-evaluates for_window rules.
        if self.target:
            self.cancel("repeated activation")
            return
        tree = self.ipc.request(4)
        target = find_target(tree, node_id)
        if not target or self.ipc.request(12).get("name") != MODE:
            self.reset_mode()
            return
        if target.area["width"] < WIDTH or target.area["height"] < HEIGHT:
            LOG.warning("Workspace is too small for the selector")
            self.reset_mode()
            return
        self.target = target
        self.timeout_source = self.GLib.timeout_add(self.timeout_ms, self.expired)
        self.dialog = self.Dialog(target, counts(tree), self.cancel)
        LOG.info("Begin window=%s workspace=%s", target.id, target.workspace)

    def place_dialog(self, node_id):
        self.helper_id = node_id
        x, y = popup_position(self.target)
        prefix = f"[con_id={node_id}]"
        workspace = json.dumps(self.target.workspace, ensure_ascii=False)
        self.ipc.command(
            f"{prefix} floating enable, border none, resize set {WIDTH} px {HEIGHT} px, "
            f"move container to workspace {workspace}; {prefix} move absolute position {x} px {y} px")
        self.GLib.idle_add(self.dialog_positioned, node_id)

    def dialog_positioned(self, node_id):
        if self.dialog and self.helper_id == node_id:
            self.dialog.positioned()
        return False

    def release(self):
        if not self.dialog:
            return False
        self.Gdk.Display.get_default().sync()
        while self.Gtk.events_pending():
            self.Gtk.main_iteration_do(False)
        if not self.dialog:
            return False
        number = self.dialog.hover
        target = self.target
        try:
            if number is not None:
                # Recheck that the original window still exists on its original workspace.
                current = find_target(self.ipc.request(4), target.id)
                if current and current.workspace == target.workspace:
                    self.ipc.command(move_command(target.id, number))
                    LOG.info("Moved window=%s to workspace=%s", target.id, number)
        except Exception:
            LOG.exception("Could not move window=%s", target.id)
        finally:
            self.cancel("released" if number else "released outside grid")
        return False

    def expired(self):
        self.timeout_source = None
        self.cancel("timeout")
        return False

    def mode_left(self):
        self.mode_source = None
        self.cancel("mode exited")
        return False

    def cancel(self, reason):
        if self.target:
            LOG.info("End window=%s: %s", self.target.id, reason)
        self.target = None
        self.helper_id = None
        self.remove_timer("timeout_source")
        self.remove_timer("mode_source")
        dialog, self.dialog = self.dialog, None
        if dialog:
            dialog.destroy()
        try:
            self.reset_mode()
        except (OSError, RuntimeError, ValueError):
            LOG.debug("Sway unavailable during cleanup", exc_info=True)
        return False

    def quit(self):
        if not self.shutting_down:
            self.shutting_down = True
            self.cancel("shutdown")
            self.Gtk.main_quit()
        return False

    def run(self):
        try:
            self.Gtk.main()
        finally:
            self.cancel("exiting")
            self.events.close()
            self.ipc.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--daemon", action="store_true", help="run the resident helper (default)")
    actions.add_argument("--check", action="store_true", help="check GUI dependencies and Wayland display")
    actions.add_argument("--stop", action="store_true", help="stop the helper in this Sway session")
    parser.add_argument("--timeout", type=float, default=15, help="cancel after this many seconds (default: 15)")
    parser.add_argument("--verbose", action="store_true", help="also write diagnostic messages to stderr")
    args = parser.parse_args()
    if args.check:
        _, _, Gdk, Gtk, _ = load_gui()
        if not Gdk.Display.get_default() or not os.environ.get("WAYLAND_DISPLAY"):
            parser.error("A Wayland display is required")
        print(f"OK: Python GObject, Cairo, GTK {Gtk.get_major_version()}.{Gtk.get_minor_version()}, Wayland")
        return 0
    path = os.environ.get("SWAYSOCK")
    if not path:
        parser.error("SWAYSOCK is not set; run inside Sway")
    if args.stop:
        ipc = IPC(path)
        try:
            ipc.request(10, STOP)
        finally:
            ipc.close()
        return 0
    if not 0.25 <= args.timeout <= 120:
        parser.error("--timeout must be between 0.25 and 120 seconds")
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime:
        parser.error("XDG_RUNTIME_DIR is not set")
    key = hashlib.sha256(path.encode()).hexdigest()[:16]
    # Scope the singleton to a compositor, so headless tests cannot affect the desktop.
    lock = open(Path(runtime) / f"workspace-drop-{key}.lock", "a")
    os.chmod(lock.name, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return 0
    state = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "sway"
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    handler = RotatingFileHandler(state / "workspace-drop.log", maxBytes=512 * 1024, backupCount=1)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    LOG.setLevel(logging.INFO)
    LOG.addHandler(handler)
    if args.verbose:
        LOG.addHandler(logging.StreamHandler())
    try:
        Picker(path, args.timeout).run()
    except Exception:
        LOG.exception("Workspace drop failed")
        print(f"workspace-drop failed: see {state / 'workspace-drop.log'}", file=sys.stderr)
        return 1
    finally:
        lock.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
