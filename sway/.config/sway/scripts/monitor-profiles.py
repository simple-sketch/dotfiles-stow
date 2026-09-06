#!/usr/bin/env python3
"""Verified Sway/Shikane profile changes, workspace restoration and lid policy."""

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

INTERNAL = re.compile(r"^(eDP|LVDS)-[0-9]+$")
EXTERNAL = re.compile(r"^(DP|HDMI-[AB]|DVI-[ADI]|VGA|USB-C)-[0-9]+(-[0-9]+)*$")
LABELS = {"laptop": "Laptop only", "undocked": "Laptop only",
          "docked": "External only", "extend": "Extend (landscape)",
          "portrait": "Extend (portrait)"}
DUAL = {"extend", "portrait"}


class ProfileError(Exception):
    pass


def quote(value):
    # Quote for Sway's command parser, never for a shell.
    if any(ord(c) < 32 for c in value):
        raise ProfileError("Invalid control character in a Sway name")
    # Sway's workspace commands keep backslashes verbatim. Prefer a delimiter
    # that needs no escaping; populated workspaces use numeric container IDs.
    for delimiter in ('"', "'"):
        if delimiter not in value:
            return delimiter + value + delimiter
    raise ProfileError("Cannot address an empty workspace containing both quote characters")


def run(args, **kwargs):
    try:
        return subprocess.run(args, text=True, capture_output=True, timeout=3, **kwargs)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProfileError(f"Could not run {args[0]}: {exc}") from exc


class Backend:
    def query(self, kind):
        error = "Invalid response"
        for attempt in range(3):
            try:
                result = run(["swaymsg", "-r", "-t", kind])
                if result.returncode:
                    raise ValueError(result.stderr.strip() or "Sway IPC failed")
                value = json.loads(result.stdout)
                if kind == "get_tree":
                    if not isinstance(value, dict) or value.get("type") != "root":
                        raise ValueError("Invalid Sway tree")
                    return value
                if not isinstance(value, list):
                    raise ValueError("Expected an array from Sway")
                if kind == "get_outputs":
                    for output in value:
                        if not isinstance(output.get("name"), str) or type(output.get("active")) is not bool:
                            raise ValueError("Invalid output in Sway response")
                        if output["active"]:
                            rect = output.get("rect", {})
                            if any(type(rect.get(k)) is not int for k in ("x", "y", "width", "height")) or min(rect["width"], rect["height"]) <= 0:
                                raise ValueError("Output dimensions are not ready")
                            if output.get("transform") not in {"normal", "90", "180", "270", "flipped", "flipped-90", "flipped-180", "flipped-270"}:
                                raise ValueError("Invalid output transform")
                return value
            except (ProfileError, ValueError, TypeError, AttributeError) as exc:
                error = str(exc)
                if attempt < 2:
                    time.sleep(.05)
        raise ProfileError(f"Cannot read {kind} from Sway: {error}")

    def command(self, command):
        result = run(["swaymsg", "-r", "--", command])
        try:
            replies = json.loads(result.stdout)
            if result.returncode or not replies or not all(r.get("success") for r in replies):
                raise ValueError(result.stderr.strip() or str(replies))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ProfileError(f"Sway rejected the display change: {exc}") from exc

    def switch(self, profile):
        result = run(["shikanectl", "switch", profile])
        if result.returncode:
            raise ProfileError(result.stderr.strip() or "Shikane is not running")

    def workspace_command(self, name, action):
        def walk(node):
            yield node
            for child in node.get("nodes", []) + node.get("floating_nodes", []):
                yield from walk(child)

        workspace = next((n for n in walk(self.query("get_tree"))
                          if n.get("type") == "workspace" and n.get("name") == name), None)
        if workspace is None:
            return  # Do not recreate a workspace that has been closed.
        node = workspace
        while node.get("nodes") or node.get("floating_nodes"):
            children = node.get("nodes", []) + node.get("floating_nodes", [])
            child_ids = node.get("focus", [])
            node = next((child for ident in child_ids for child in children if child["id"] == ident), children[0])
        if node is not workspace:
            # Numeric criteria bypass name parsing and keep the workspace's last focused window.
            self.command(f"[con_id={int(node['id'])}] {action}")
        else:
            command = f"workspace --no-auto-back-and-forth {quote(name)}"
            self.command(command if action == "focus" else command + "; " + action)

    def notify(self, message, error=False):
        print(message, file=sys.stderr if error else sys.stdout)
        try:
            run(["notify-send", "--app-name=Displays", "--urgency=" + ("critical" if error else "normal"),
                 "--hint=string:x-canonical-private-synchronous:monitor-profile", "Displays", message])
        except ProfileError:
            pass  # Keep the original error visible on stderr if D-Bus is unavailable.

    def lid_closed(self):
        for path in sorted(Path("/proc/acpi/button/lid").glob("*/state")):
            try:
                text = path.read_text().strip().lower()
            except OSError:
                continue
            if text.endswith("closed"):
                return True
            if text.endswith("open"):
                return False
        return None

    def pick(self, choices, menu="noctalia"):
        command = (["noctalia", "dmenu", "--prompt", "Displays"] if menu == "noctalia" else
                   ["wmenu", "-i", "-p", "Displays", "-l", str(len(choices))])
        try:
            result = subprocess.run(command,
                                    input="\n".join(choices) + "\n", text=True, capture_output=True)
        except OSError as exc:
            raise ProfileError(f"Cannot open the profile picker: {exc}") from exc
        if not result.stdout.strip() and (result.returncode == 0 or result.returncode == 1 and not result.stderr.strip()):
            return None  # Escape / cancelled selection.
        if result.returncode:
            raise ProfileError(result.stderr.strip() or "The profile picker failed")
        choice = result.stdout.strip()
        if choice not in choices:
            raise ProfileError("Choose one of the listed monitor profiles")
        return choice


class Controller:
    def __init__(self, backend=None, runtime=None):
        self.io = backend or Backend()
        if runtime is None:
            if not os.environ.get("SWAYSOCK") or not os.environ.get("XDG_RUNTIME_DIR"):
                raise ProfileError("Run this command inside your Sway session")
            session = hashlib.sha256(os.environ["SWAYSOCK"].encode()).hexdigest()[:16]
            runtime = Path(os.environ["XDG_RUNTIME_DIR"]) / ("sway-monitor-profiles-" + session)
        self.runtime = Path(runtime)
        self.runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.state_path = self.runtime / "state.json"
        self.state = {}

    @contextmanager
    def locked(self):
        with (self.runtime / "lock").open("a") as lock:
            deadline = time.monotonic() + 12
            while True:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise ProfileError("Another display change is still running; try again")
                    time.sleep(.02)
            try:
                self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {}
                if not isinstance(self.state, dict):
                    raise ValueError("Expected an object")
            except ValueError as exc:
                raise ProfileError(f"Cannot read display state at {self.state_path}") from exc
            yield

    def save(self):
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.state))
        temporary.replace(self.state_path)

    def outputs(self):
        return self.io.query("get_outputs")

    def available(self, outputs):
        internal = [o for o in outputs if INTERNAL.fullmatch(o["name"])]
        external = [o for o in outputs if EXTERNAL.fullmatch(o["name"])]
        if len(outputs) == 1 and len(internal) == 1:
            return ["undocked"]
        if len(outputs) == 2 and len(internal) == len(external) == 1:
            return ["laptop", "docked", "extend", "portrait"]
        return []

    def matches(self, profile, outputs):
        if profile not in self.available(outputs):
            return False
        for output in outputs:
            internal = bool(INTERNAL.fullmatch(output["name"]))
            enabled = internal if profile in {"laptop", "undocked"} else not internal if profile == "docked" else True
            if output["active"] != enabled:
                return False
            if enabled:
                transforms = {"90", "270"} if profile == "portrait" and not internal else {"normal"}
                if output.get("transform") not in transforms:
                    return False
        return True

    def current(self, outputs):
        return next((p for p in self.available(outputs) if self.matches(p, outputs)), None)

    @staticmethod
    def identity(outputs):
        return sorted([o["name"], o.get("make"), o.get("model"), o.get("serial")] for o in outputs)

    @staticmethod
    def order(outputs):
        return [o["name"] for o in sorted((o for o in outputs if o["active"]),
                                          key=lambda o: (o["rect"]["x"], o["rect"]["y"], o["name"]))]

    @staticmethod
    def positions(outputs, left):
        active = {o["name"]: o for o in outputs if o["active"]}
        if len(active) != 2 or left not in active:
            raise ProfileError("Exactly two active displays are needed for this arrangement")
        right = next(name for name in active if name != left)
        a, b = active[left]["rect"], active[right]["rect"]
        height = max(a["height"], b["height"])
        return {left: (0, (height - a["height"]) // 2),
                right: (a["width"], (height - b["height"]) // 2)}

    @staticmethod
    def placed(outputs, positions):
        active = {o["name"]: o for o in outputs if o["active"]}
        return set(active) == set(positions) and all(
            (active[name]["rect"]["x"], active[name]["rect"]["y"]) == tuple(pos)
            for name, pos in positions.items())

    def wait_for(self, predicate, message):
        deadline = time.monotonic() + 4
        while True:
            outputs = self.outputs()  # IPC errors propagate; they never select another profile.
            if predicate(outputs):
                return outputs
            if time.monotonic() >= deadline:
                raise ProfileError(message)
            time.sleep(.05)

    def place(self, outputs, left):
        positions = self.positions(outputs, left)
        if not self.placed(outputs, positions):
            self.io.command("; ".join(f"output {quote(name)} position {x} {y}"
                                      for name, (x, y) in positions.items()))
        return self.wait_for(lambda now: self.placed(now, positions), "Sway did not apply the monitor positions")

    def remember_workspaces(self, outputs):
        workspaces = self.io.query("get_workspaces")
        active = {o["name"] for o in outputs if o["active"]}
        homes = self.state.setdefault("homes", {})
        visible = self.state.setdefault("visible", {})
        # Preserve the home of a workspace displaced from a disabled display.
        self.state["homes"] = homes = {w["name"]: homes.get(w["name"], w["output"]) for w in workspaces}
        for workspace in workspaces:
            name, output = workspace["name"], workspace["output"]
            if homes[name] in active:
                homes[name] = output
            if workspace.get("visible") and homes[name] == output:
                visible[output] = name
        return next((w["name"] for w in workspaces if w.get("focused")), None)

    def restore_workspaces(self, outputs, focus=None, visible=None):
        active = {o["name"] for o in outputs if o["active"]}
        for name, target in self.state.get("homes", {}).items():
            if target not in active:
                continue
            workspaces = {w["name"]: w for w in self.io.query("get_workspaces")}
            if name in workspaces and workspaces[name]["output"] != target:
                self.io.workspace_command(name, f"move workspace to output {quote(target)}")
        for output, name in (visible if visible is not None else self.state.get("visible", {})).items():
            workspaces = {w["name"]: w for w in self.io.query("get_workspaces")}
            if output in active and name in workspaces and workspaces[name]["output"] == output:
                self.io.workspace_command(name, "focus")
        if focus and any(w["name"] == focus for w in self.io.query("get_workspaces")):
            self.io.workspace_command(focus, "focus")
        for workspace in self.io.query("get_workspaces"):
            target = self.state.get("homes", {}).get(workspace["name"])
            if target in active and workspace["output"] != target:
                raise ProfileError("The display changed, but workspace restoration failed")

    def apply(self, profile, *, toggle=False, left=None, restoring=False, focus=None, visible=None,
              remember=True, settings=None, notify=True):
        outputs = self.outputs()
        if profile == "laptop" and self.available(outputs) == ["undocked"]:
            profile = "undocked"
        if profile not in self.available(outputs):
            raise ProfileError(f"{LABELS[profile]} is unavailable for the connected displays")
        if self.io.lid_closed() and profile != "docked" and not restoring:
            raise ProfileError("Open the laptop lid before enabling its screen")
        previous_focus = self.remember_workspaces(outputs) if remember else None
        self.save()
        same = self.matches(profile, outputs)
        if toggle and same and profile in DUAL:
            left = self.order(outputs)[-1]
        if not same:
            self.io.switch(profile)
            outputs = self.wait_for(lambda now: self.matches(profile, now),
                                    f"Shikane did not apply {LABELS[profile]}; check its configuration and connected displays")
        if settings:
            commands = []
            for output in outputs:
                saved = settings.get(output["name"], {})
                if output["active"] and saved:
                    transform, scale = saved["transform"], saved["scale"]
                    if transform not in {"normal", "90", "270"} or not isinstance(scale, (float, int)) or scale <= 0:
                        raise ProfileError("Invalid saved monitor settings")
                    commands.append(f"output {quote(output['name'])} transform {transform} scale {scale}")
            if commands:
                self.io.command("; ".join(commands))
                outputs = self.outputs()
        if profile in DUAL:
            left = left or (self.order(outputs)[0] if same else next(o["name"] for o in outputs if EXTERNAL.fullmatch(o["name"])))
            outputs = self.place(outputs, left)
        else:
            output = next(o for o in outputs if o["active"])
            positions = {output["name"]: (0, 0)}
            if not self.placed(outputs, positions):
                self.io.command(f"output {quote(output['name'])} position 0 0")
                outputs = self.wait_for(lambda now: self.placed(now, positions), "Sway did not position the active display")
        self.restore_workspaces(outputs, focus or previous_focus, visible)
        if not self.matches(profile, self.outputs()):
            raise ProfileError("The connected displays changed before the profile was ready")
        self.save_layout(profile, self.outputs())
        if notify:
            self.io.notify(LABELS[profile] + (" — screens swapped" if toggle and same else ""))

    def snapshot(self, profile, outputs, focus):
        return {"identity": self.identity(outputs), "profile": profile, "order": self.order(outputs),
                "focus": focus, "visible": dict(self.state.get("visible", {})),
                "settings": {o["name"]: {"transform": o["transform"], "scale": o["scale"]}
                             for o in outputs if o["active"]}}

    def save_layout(self, profile, outputs):
        focus = next((w["name"] for w in self.io.query("get_workspaces") if w.get("focused")), None)
        self.state["profile"] = profile
        self.state["layout"] = self.snapshot(profile, outputs, focus)
        self.save()

    def reapply(self):
        snapshot = self.state.get("layout")
        if not snapshot or snapshot["identity"] != self.identity(self.outputs()):
            return
        profile = "docked" if self.io.lid_closed() and "docked" in self.available(self.outputs()) else snapshot["profile"]
        workspaces = self.io.query("get_workspaces")
        focus = next((w["name"] for w in workspaces if w.get("focused")), None)
        visible = {w["output"]: w["name"] for w in workspaces if w.get("visible")}
        self.apply(profile, left=next(iter(snapshot["order"]), None), restoring=True,
                   focus=focus, visible=visible, remember=False,
                   settings=snapshot["settings"] if profile == snapshot["profile"] else None, notify=False)

    def applied(self, profile):
        outputs = self.outputs()
        if not self.matches(profile, outputs):
            return  # An old asynchronous hook must not modify a newer profile.
        if self.io.lid_closed() and "docked" in self.available(outputs) and profile != "docked":
            self.close_lid(outputs)
            return
        arranged = profile not in DUAL or any(self.placed(outputs, self.positions(outputs, name)) for name in self.order(outputs))
        if arranged and self.state.get("profile") == profile:
            return  # A delayed hook must not undo a completed swap or steal workspace focus.
        if not arranged:
            outputs = self.place(outputs, next(o["name"] for o in outputs if EXTERNAL.fullmatch(o["name"])))
        focus = next((w["name"] for w in self.io.query("get_workspaces") if w.get("focused")), None)
        self.restore_workspaces(outputs, focus)
        self.save_layout(profile, outputs)
        self.io.notify(LABELS[profile])

    def close_lid(self, outputs):
        if "docked" not in self.available(outputs):
            return  # Do not disable the only display or change the system's suspend policy.
        if "lid_restore" not in self.state:
            profile = self.current(outputs)
            if profile is None:
                raise ProfileError("Cannot save the current custom layout for lid restoration")
            focus = self.remember_workspaces(outputs)
            self.state["lid_restore"] = self.snapshot(profile, outputs, focus)
            self.save()
        if not self.matches("docked", outputs):
            self.apply("docked", restoring=True)

    def lid(self, closed):
        actual = self.io.lid_closed()
        if actual is not None and actual != closed:
            return  # A queued close/open event is already obsolete.
        outputs = self.outputs()
        if closed:
            self.close_lid(outputs)
            return
        snapshot = self.state.get("lid_restore")
        if not snapshot:
            return  # Includes ordinary Sway reloads with an open lid.
        if self.identity(outputs) == snapshot["identity"]:
            self.apply(snapshot["profile"], left=next(iter(snapshot["order"]), None), restoring=True,
                       focus=snapshot["focus"], visible=snapshot["visible"], settings=snapshot["settings"])
        elif self.available(outputs):
            self.apply("undocked" if self.available(outputs) == ["undocked"] else "docked", restoring=True)
        else:
            raise ProfileError("Displays changed while the lid was closed; choose a supported monitor setup")
        del self.state["lid_restore"]
        self.save()

    def picker(self, menu="noctalia"):
        with self.locked():
            outputs = self.outputs()
            current = self.current(outputs)
            profiles = self.available(outputs)
            if self.io.lid_closed():
                profiles = [p for p in profiles if p == "docked"]
            choices = {LABELS[p] + (" (current)" if p == current else ""): p for p in profiles}
            if not choices:
                raise ProfileError("No monitor profiles are available for this setup")
        # Never hold the display lock while waiting for user input.
        choice = self.io.pick(choices, menu)
        if choice is not None:
            with self.locked():
                self.apply(choices[choice])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("switch", "toggle", "applied"):
        commands.add_parser(command).add_argument("profile", choices=sorted(DUAL if command == "toggle" else LABELS))
    commands.add_parser("pick").add_argument("--menu", choices=["noctalia", "wmenu"], default="noctalia")
    commands.add_parser("reapply")
    commands.add_parser("lid").add_argument("state", choices=["open", "closed"])
    arrange = commands.add_parser("arrange")
    arrange.add_argument("left")
    arrange.add_argument("right", nargs="?")
    args = parser.parse_args()
    backend = Backend()
    try:
        controller = Controller(backend)
        if args.command == "pick":
            controller.picker(args.menu)
        else:
            with controller.locked():
                if args.command in {"switch", "toggle"}:
                    controller.apply(args.profile, toggle=args.command == "toggle")
                elif args.command == "applied":
                    controller.applied(args.profile)
                elif args.command == "lid":
                    controller.lid(args.state == "closed")
                elif args.command == "reapply":
                    controller.reapply()
                elif args.command == "arrange":
                    outputs = controller.outputs()
                    if args.right and set(controller.order(outputs)) != {args.left, args.right}:
                        raise ProfileError("Requested outputs are not the two active displays")
                    controller.place(outputs, args.left)
    except (ProfileError, OSError) as exc:
        backend.notify(str(exc), error=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
