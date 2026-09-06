"""Failure paths and UI contracts; integration.py exercises real Sway/Shikane."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[2] / "monitor-profiles.py"
spec = importlib.util.spec_from_file_location("profiles", SCRIPT)
profiles = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profiles)


def output(name, width, height, x=0, y=0, transform="normal", active=True):
    return dict(name=name, active=active, transform=transform, scale=1.0,
                rect=dict(x=x, y=y, width=width, height=height))


class Backend:
    def __init__(self):
        self.outputs = [output("HDMI-A-1", 2560, 1440), output("eDP-1", 1920, 1080, 2560, 180)]
        self.switches = []
        self.commands = []
        self.notifications = []
        self.closed = False
        self.choice = None
        self.workspaces = [dict(name="1", output="HDMI-A-1", focused=True, visible=True),
                           dict(name="2", output="eDP-1", focused=False, visible=True)]

    def query(self, kind):
        return copy.deepcopy(self.outputs if kind == "get_outputs" else self.workspaces)

    def command(self, command):
        self.commands.append(command)

    def switch(self, profile):
        self.switches.append(profile)  # Deliberately acknowledge without applying.

    def notify(self, message, error=False):
        self.notifications.append((message, error))

    def lid_closed(self):
        return self.closed

    def pick(self, choices, menu):
        self.choices = choices
        self.menu = menu
        return self.choice


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.backend = Backend()
        self.controller = profiles.Controller(self.backend, self.tmp.name)

    def test_failed_query_never_switches(self):
        self.backend.query = lambda kind: (_ for _ in ()).throw(profiles.ProfileError("IPC unavailable"))
        with self.controller.locked(), self.assertRaisesRegex(profiles.ProfileError, "IPC unavailable"):
            self.controller.apply("portrait")
        self.assertEqual(self.backend.switches, [])
        self.assertEqual(self.backend.commands, [])

    def test_malformed_ipc_is_an_error(self):
        for text in ("", "not json", "{}", '[{"name":"eDP-1"}]'):
            with self.subTest(text=text), patch.object(profiles, "run", return_value=subprocess.CompletedProcess([], 0, text, "")), patch.object(profiles.time, "sleep"):
                with self.assertRaises(profiles.ProfileError):
                    profiles.Backend().query("get_outputs")

    def test_shikanectl_success_is_not_profile_success(self):
        with self.controller.locked(), patch.object(profiles.time, "monotonic", side_effect=[0, 5]), self.assertRaisesRegex(profiles.ProfileError, "did not apply"):
            self.controller.apply("portrait")
        self.assertEqual(self.backend.switches, ["portrait"])
        self.assertEqual(self.backend.notifications, [])

    def test_unavailable_profiles_do_not_reach_shikane(self):
        self.backend.outputs.append(output("DP-2", 1920, 1080))
        with self.controller.locked(), self.assertRaisesRegex(profiles.ProfileError, "unavailable"):
            self.controller.apply("extend")
        self.assertEqual(self.backend.switches, [])

    def test_stale_hook_does_not_move_outputs(self):
        with self.controller.locked():
            self.controller.applied("portrait")
        self.assertEqual(self.backend.commands, [])
        self.assertEqual(self.backend.notifications, [])

    def test_late_hook_preserves_completed_swap_and_focus(self):
        self.backend.outputs[0]["rect"]["x"] = 1920
        self.backend.outputs[1]["rect"]["x"] = 0
        with self.controller.locked():
            self.controller.state["profile"] = "extend"
            self.controller.applied("extend")
        self.assertEqual(self.backend.commands, [])
        self.assertEqual(self.backend.notifications, [])

    def test_displaced_workspace_home_is_preserved(self):
        with self.controller.locked():
            self.controller.remember_workspaces(self.backend.outputs)
            self.backend.outputs[1]["active"] = False
            self.backend.workspaces[1]["output"] = "HDMI-A-1"
            self.controller.remember_workspaces(self.backend.outputs)
            self.assertEqual(self.controller.state["homes"]["2"], "eDP-1")

    def test_deliberate_workspace_move_with_both_active_is_remembered(self):
        with self.controller.locked():
            self.controller.remember_workspaces(self.backend.outputs)
            self.backend.workspaces[1]["output"] = "HDMI-A-1"
            self.controller.remember_workspaces(self.backend.outputs)
            self.assertEqual(self.controller.state["homes"]["2"], "HDMI-A-1")

    def test_lid_close_without_external_does_nothing(self):
        self.backend.outputs = self.backend.outputs[1:]
        self.backend.closed = True
        with self.controller.locked():
            self.controller.lid(True)
        self.assertEqual(self.backend.commands, [])
        self.assertEqual(self.backend.switches, [])
        self.assertFalse(self.controller.state_path.exists())

    def test_open_lid_reload_does_not_change_profile(self):
        with self.controller.locked():
            self.controller.lid(False)
        self.assertEqual(self.backend.commands, [])
        self.assertEqual(self.backend.switches, [])

    def test_closed_lid_rejects_laptop_only(self):
        self.backend.closed = True
        with self.controller.locked(), self.assertRaisesRegex(profiles.ProfileError, "Open the laptop lid"):
            self.controller.apply("laptop")
        self.assertEqual(self.backend.switches, [])

    def test_obsolete_lid_event_is_ignored(self):
        with self.controller.locked():
            self.controller.lid(True)
        self.assertEqual(self.backend.switches, [])

    def test_picker_cancel_and_current_marker(self):
        self.controller.picker()
        self.assertEqual(self.backend.menu, "noctalia")
        self.assertIn("Extend (landscape) (current)", self.backend.choices)
        self.assertIn("Laptop only", self.backend.choices)
        self.assertEqual(self.backend.switches, [])

    def test_noctalia_dmenu_is_default(self):
        result = subprocess.CompletedProcess([], 0, "Laptop only\n", "")
        with patch.object(profiles.subprocess, "run", return_value=result) as run:
            self.assertEqual(profiles.Backend().pick({"Laptop only": "laptop"}), "Laptop only")
        self.assertEqual(run.call_args.args[0], ["noctalia", "dmenu", "--prompt", "Displays"])

    def test_picker_cancel_and_failure_are_distinct(self):
        for status, stderr, expected_error in [(0, "", False), (1, "", False), (1, "Cannot connect to Noctalia", True)]:
            with self.subTest(status=status, stderr=stderr), patch.object(profiles.subprocess, "run", return_value=subprocess.CompletedProcess([], status, "", stderr)):
                if expected_error:
                    with self.assertRaises(profiles.ProfileError):
                        profiles.Backend().pick({"Laptop only": "laptop"})
                else:
                    self.assertIsNone(profiles.Backend().pick({"Laptop only": "laptop"}))

    def test_missing_saved_workspaces_are_not_recreated(self):
        with self.controller.locked():
            self.controller.state["homes"] = {"already closed": "HDMI-A-1"}
            self.controller.restore_workspaces(self.backend.outputs, "already closed")
        self.assertEqual(self.backend.commands, [])


if __name__ == "__main__":
    unittest.main()
