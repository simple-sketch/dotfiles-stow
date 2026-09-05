#!/usr/bin/env python3
"""Real pointer/keyboard tests in a NEW headless Sway, never the user's desktop.

Requires sway, foot, wtype, grim and the helper's Python GUI dependencies.
Artifacts are retained under /tmp/workspace-drop-integration.* for inspection.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core import APP_ID, IPC, MODE, WIDTH, HEIGHT, cell_rect, find_target, walk
from virtual_pointer import Pointer


def wait_for(function, timeout=4):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = function()
        if value:
            return value
        time.sleep(.02)
    raise AssertionError(f"Timed out waiting for {function}")


class HeadlessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for tool in ("sway", "foot", "wtype", "grim"):
            if not shutil.which(tool):
                raise unittest.SkipTest(f"Missing test tool: {tool}")
        cls.tmp = Path(tempfile.mkdtemp(prefix="workspace-drop-integration."))
        print(f"\nHeadless test artifacts: {cls.tmp}", flush=True)
        cls.env = dict(os.environ, WLR_BACKENDS="headless", WLR_RENDERER="pixman",
                       WLR_HEADLESS_OUTPUTS="2", XDG_STATE_HOME=str(cls.tmp / "state"),
                       PYTHONDONTWRITEBYTECODE="1")
        cls.env.pop("SWAYSOCK", None)
        cls.env.pop("WAYLAND_DISPLAY", None)
        config = (ROOT.parents[1] / "workspace-drop.conf").read_text()
        config = "\n".join(line for line in config.splitlines() if not line.startswith("exec_always"))
        cls.config = cls.tmp / "config"
        cls.config.write_text('''set $mod Mod4
output * resolution 1280x720
output HEADLESS-1 position 0 0
output HEADLESS-2 position 1280 0
workspace 1 output HEADLESS-1
workspace 2 output HEADLESS-2
seat seat0 fallback true
font pango:Sans 10
focus_follows_mouse yes
floating_modifier $mod normal
for_window [floating] resize set width 45 ppt height 55 ppt, move position center
''' + config + '\n')
        cls.sway_log = open(cls.tmp / "sway.log", "w")
        cls.sway = subprocess.Popen(["sway", "-c", str(cls.config), "-d"], env=cls.env,
                                    stdout=cls.sway_log, stderr=cls.sway_log, start_new_session=True)
        cls.helper = None
        try:
            socket_path = Path(cls.env["XDG_RUNTIME_DIR"]) / f"sway-ipc.{os.getuid()}.{cls.sway.pid}.sock"
            wait_for(socket_path.exists)
            display = wait_for(lambda: re.search(r"Running compositor on wayland display '([^']+)'",
                                                  (cls.tmp / "sway.log").read_text()))
            cls.env.update(SWAYSOCK=str(socket_path), WAYLAND_DISPLAY=display[1])
            # This assertion is the guard against accidentally injecting test input on the desktop.
            assert cls.env["SWAYSOCK"] != os.environ.get("SWAYSOCK")
            assert cls.env["WAYLAND_DISPLAY"] != os.environ.get("WAYLAND_DISPLAY")
            cls.ipc = IPC(str(socket_path))
            cls.helper_log = open(cls.tmp / "helper.stderr", "w")
            cls.start_helper()
        except BaseException:
            cls.sway.terminate()
            cls.sway.wait(timeout=5)
            cls.sway_log.close()
            raise

    @classmethod
    def start_helper(cls, timeout=2):
        cls.helper = subprocess.Popen([sys.executable, str(ROOT / "main.py"), "--daemon", "--verbose",
                                       "--timeout", str(timeout)], env=cls.env,
                                      stdout=cls.helper_log, stderr=cls.helper_log)
        time.sleep(.3)
        if cls.helper.poll() is not None:
            raise AssertionError((cls.tmp / "helper.stderr").read_text())

    @classmethod
    def tearDownClass(cls):
        if cls.helper and cls.helper.poll() is None:
            cls.helper.terminate()
            cls.helper.wait(timeout=5)
        try:
            cls.ipc.command("exit")
        except ConnectionError:
            pass  # Sway exits before replying to the exit command.
        cls.ipc.close()
        cls.sway.wait(timeout=5)
        cls.helper_log.close()
        cls.sway_log.close()

    def setUp(self):
        self.windows = []
        self.keyboards = []
        self.ipc.command('mode default; output HEADLESS-1 scale 1; workspace --no-auto-back-and-forth number 1')
        self.pointer = Pointer(self.env)
        self.pointer.motion(1100, 650)
        self.source = self.new_window("A")
        self.ipc.command(f'[con_id={self.source}] floating enable, resize set 700 450, move absolute position 150 100')
        self.wait_layout()

    def tearDown(self):
        self.pointer.close()
        for keyboard in self.keyboards:
            if keyboard.poll() is None:
                keyboard.terminate()
            keyboard.wait(timeout=3)
        self.ipc.command("mode default")
        time.sleep(.2)
        for process in self.windows:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=3)
        self.assertIsNone(self.helper.poll(), (self.tmp / "helper.stderr").read_text())

    def new_window(self, suffix):
        app = f"workspace-drop-test-{suffix}"
        process = subprocess.Popen(["foot", "-c", "/dev/null", "-a", app, "-T", f"Test window {suffix}",
                                    "sleep", "3600"], env=self.env, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
        self.windows.append(process)
        return wait_for(lambda: next((n['id'] for n, _, _ in walk(self.ipc.request(4)) if n.get('app_id') == app), None))

    def node(self, node_id):
        return next((n for n, _, _ in walk(self.ipc.request(4)) if n.get('id') == node_id), None)

    def dialog(self):
        return next((n for n, _, _ in walk(self.ipc.request(4)) if n.get('app_id') == APP_ID), None)

    def wait_layout(self):
        time.sleep(.12)

    def logo(self, extra=None):
        args = ["wtype", "-P", "Super_L", "-M", "logo", "-s", "650", "-m", "logo", "-p", "Super_L"] if extra == 'release' else [
            "wtype", "-M", "logo", "-s", "10000", "-m", "logo"]
        p = subprocess.Popen(args, env=self.env)
        self.keyboards.append(p)
        time.sleep(.08)
        return p

    def begin(self, point=None, super_release=False):
        node = self.node(self.source)
        if point is None:
            point = node['rect']['x'] + 60, node['rect']['y'] - 5
        self.pointer.motion(*point)
        keyboard = self.logo('release' if super_release else None)
        self.pointer.button(True)
        dialog = wait_for(self.dialog)
        self.wait_layout()
        self.assertEqual(self.ipc.request(12)['name'], MODE)
        return dialog, keyboard

    def hover(self, number):
        rect = self.dialog()['rect']
        x, y, w, h = cell_rect(number)
        self.pointer.motion(rect['x'] + x + w // 2 - 4, rect['y'] + y + h // 2)
        self.pointer.motion(rect['x'] + x + w // 2, rect['y'] + y + h // 2)

    def done(self):
        wait_for(lambda: self.dialog() is None and self.ipc.request(12)['name'] == 'default')
        self.assertNotIn('__workspace_drop_target', self.ipc.request(5))

    def assert_workspace(self, number):
        self.assertEqual(find_target(self.ipc.request(4), self.source).number, number)

    def drop(self, number):
        self.begin()
        self.hover(number)
        self.pointer.button(False)
        self.done()

    def test_01_floating_drop_and_stay(self):
        before = self.node(self.source)
        self.begin()
        self.hover(3)
        subprocess.run(['grim', '-o', 'HEADLESS-1', str(self.tmp / 'selector.png')], env=self.env, check=True)
        self.pointer.button(False)
        self.done()
        self.assert_workspace(3)
        self.assertEqual(next(w['num'] for w in self.ipc.request(1) if w['focused']), 1)
        after = self.node(self.source)
        self.assertEqual(after['type'], before['type'])
        self.assertEqual(after['rect'], before['rect'])

    def test_02_tiled_drop_stays_tiled(self):
        self.ipc.command(f'[con_id={self.source}] floating disable')
        self.wait_layout()
        self.drop(9)
        self.assert_workspace(9)
        self.assertEqual(self.node(self.source)['type'], 'con')

    def test_03_current_workspace_no_back_and_forth(self):
        self.ipc.command('workspace_auto_back_and_forth yes')
        try:
            self.drop(1)
            self.assert_workspace(1)
        finally:
            self.ipc.command('workspace_auto_back_and_forth no')

    def test_04_numbered_name(self):
        self.ipc.command('workspace "3: named"; workspace --no-auto-back-and-forth number 1')
        # Empty invisible workspaces disappear, so hold it open with a second window.
        other = self.new_window('B')
        self.ipc.command(f'[con_id={other}] move container to workspace "3: named"')
        self.drop(3)
        self.assertEqual(find_target(self.ipc.request(4), self.source).workspace, '3: named')

    def test_05_release_outside(self):
        self.begin()
        self.hover(3)
        self.pointer.motion(1150, 650)
        self.pointer.button(False)
        self.done()
        self.assert_workspace(1)

    def test_06_gap_is_not_target(self):
        self.begin()
        rect = self.dialog()['rect']
        x, y, w, _ = cell_rect(1)
        self.pointer.motion(rect['x'] + x + w + 3, rect['y'] + y + 30)
        self.pointer.button(False)
        self.done()
        self.assert_workspace(1)

    def test_07_escape(self):
        self.begin()
        self.hover(3)
        subprocess.run(['wtype', '-k', 'Escape'], env=self.env, check=True)
        self.done()
        self.assert_workspace(1)

    def test_08_super_released_first_still_drops_on_mouse_release(self):
        _, keyboard = self.begin(super_release=True)
        self.hover(3)
        keyboard.wait(timeout=3)
        self.assertIsNotNone(self.dialog())
        self.assertEqual(self.ipc.request(12)['name'], MODE)
        self.pointer.button(False)
        self.done()
        self.assert_workspace(3)

    def test_09_timeout(self):
        self.begin()
        self.hover(3)
        self.done()
        self.assert_workspace(1)

    def test_10_source_closed(self):
        self.begin()
        self.ipc.command(f'[con_id={self.source}] kill')
        self.done()
        self.assertIsNone(self.node(self.source))

    def test_11_existing_marks_preserved(self):
        self.ipc.command(f'[con_id={self.source}] mark --add user-mark')
        self.drop(4)
        self.assertEqual(self.node(self.source)['marks'], ['user-mark'])

    def test_12_inactive_tab_targets_clicked_window(self):
        self.ipc.command(f'[con_id={self.source}] floating disable; layout tabbed')
        other = self.new_window('B')
        self.wait_layout()
        self.assertTrue(self.node(other)['focused'])
        self.begin(point=(70, 12))
        self.hover(5)
        self.pointer.button(False)
        self.done()
        self.assert_workspace(5)
        self.assertEqual(find_target(self.ipc.request(4), other).number, 1)

    def test_13_destination_on_another_output(self):
        other = self.new_window('B')
        self.ipc.command(f'[con_id={other}] move container to workspace number 2')
        self.drop(2)
        self.assert_workspace(2)
        self.assertEqual(next(w['num'] for w in self.ipc.request(1) if w['focused']), 1)

    def test_14_native_content_drag_unchanged(self):
        before = self.node(self.source)['rect'].copy()
        self.pointer.motion(before['x'] + 80, before['y'] + 90)
        self.logo()
        self.pointer.button(True)
        self.pointer.motion(before['x'] + 180, before['y'] + 140)
        self.pointer.button(False)
        self.wait_layout()
        self.assertIsNone(self.dialog())
        self.assertEqual(self.ipc.request(12)['name'], 'default')
        self.assertNotEqual(before['x'], self.node(self.source)['rect']['x'])
        self.assert_workspace(1)

    def test_15_plain_titlebar_drag_unchanged(self):
        before = self.node(self.source)['rect'].copy()
        self.pointer.motion(before['x'] + 80, before['y'] - 5)
        self.pointer.button(True)
        self.pointer.motion(before['x'] + 180, before['y'] + 45)
        self.pointer.button(False)
        self.wait_layout()
        self.assertIsNone(self.dialog())
        self.assertNotEqual(before['x'], self.node(self.source)['rect']['x'])

    def test_16_fractional_scaling(self):
        self.ipc.command('output HEADLESS-1 scale 1.5')
        self.wait_layout()
        self.ipc.command(f'[con_id={self.source}] resize set 500 300, move absolute position 100 45')
        self.wait_layout()
        self.drop(6)
        self.assert_workspace(6)

    def test_17_duplicate_daemon(self):
        result = subprocess.run([sys.executable, str(ROOT / 'main.py'), '--daemon'], env=self.env, timeout=3)
        self.assertEqual(result.returncode, 0)
        self.drop(7)
        self.assert_workspace(7)

    def test_18_quick_click_does_not_leave_mode(self):
        r = self.node(self.source)['rect']
        self.pointer.motion(r['x'] + 80, r['y'] - 5)
        self.logo()
        self.pointer.button(True)
        self.pointer.button(False)
        self.done()
        self.assert_workspace(1)

    def test_19_shutdown_cancels_and_restarts(self):
        self.begin()
        self.hover(3)
        self.helper.terminate()
        self.helper.wait(timeout=4)
        self.done()
        self.assert_workspace(1)
        type(self).start_helper()

    def test_20_reload_cancels(self):
        self.begin()
        self.ipc.command('reload')
        self.done()
        self.assert_workspace(1)

    def test_21_right_click_cancels(self):
        self.begin()
        self.hover(3)
        self.pointer.button(True, 273)
        self.done()
        self.assert_workspace(1)

    def test_22_header_release_cancels(self):
        self.begin()
        self.hover(3)
        rect = self.dialog()['rect']
        self.pointer.motion(rect['x'] + 70, rect['y'] + 20)
        self.pointer.button(False)
        self.done()
        self.assert_workspace(1)

    def test_23_second_keyboard_layout(self):
        self.ipc.command('input type:keyboard xkb_layout "us,lt"; input type:keyboard xkb_switch_layout 1')
        try:
            self.drop(8)
            self.assert_workspace(8)
        finally:
            self.ipc.command('input type:keyboard xkb_layout "us"')

    def test_24_second_output_source(self):
        self.ipc.command(f'[con_id={self.source}] move container to workspace number 2; workspace number 2')
        self.ipc.command(f'[con_id={self.source}] move absolute position 1480 100')
        self.wait_layout()
        self.drop(3)
        self.assert_workspace(3)
        self.assertEqual(next(w['num'] for w in self.ipc.request(1) if w['focused']), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
