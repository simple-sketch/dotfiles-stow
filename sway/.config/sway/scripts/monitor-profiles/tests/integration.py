#!/usr/bin/env python3
"""Real display/profile/workspace tests in an isolated headless Sway session.

Pass --shikane-config PATH to test a staged configuration before installing it.
Only display names, IPC socket paths, notification delivery and picker input are
adapted; the actual controller, Sway and Shikane perform the transitions.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess as sp
import sys
import tempfile
import time
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / "monitor-profiles.py"
spec = importlib.util.spec_from_file_location("profiles", SCRIPT)
profiles = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profiles)
SHIKANE_CONFIG = SCRIPT.parents[4] / "shikane/.config/shikane/config.toml"


class TestBackend(profiles.Backend):
    def lid_closed(self):
        return (Path(os.environ["PROFILE_TEST_DIR"]) / "lid").read_text() == "closed"


def wait_for(fn, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = fn()
        if value:
            return value
        time.sleep(.03)
    raise AssertionError(f"Timed out waiting for {fn}")


def nodes(tree):
    yield tree
    for child in tree.get("nodes", []) + tree.get("floating_nodes", []):
        yield from nodes(child)


class Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="monitor-profiles-integration."))
        print("Artifacts: " + str(cls.tmp), flush=True)
        cls.original_env = dict(os.environ)
        runtime = cls.tmp / "runtime"
        runtime.mkdir(mode=0o700)
        binary = cls.tmp / "bin"
        binary.mkdir()
        (cls.tmp / "lid").write_text("open")
        (cls.tmp / "selection").write_text("")
        (cls.tmp / "notifications").write_text("")
        env = dict(os.environ, XDG_RUNTIME_DIR=str(runtime), XDG_STATE_HOME=str(cls.tmp / "state"),
                   PROFILE_TEST_DIR=str(cls.tmp), WLR_BACKENDS="headless", WLR_RENDERER="pixman",
                   WLR_HEADLESS_OUTPUTS="2", PATH=str(binary) + ":" + os.environ["PATH"],
                   SHIKANE_LOG="debug", SHIKANE_LOG_STYLE="never", PYTHONDONTWRITEBYTECODE="1")
        env.pop("SWAYSOCK", None)
        env.pop("WAYLAND_DISPLAY", None)
        validation = sp.run(["sway", "--validate", "--config", str(SCRIPT.parent.parent / "config")],
                            env=env, text=True, capture_output=True)
        if validation.returncode:
            raise AssertionError(validation.stdout + validation.stderr)
        proxy = '''#!/usr/bin/env python3
import json,os,pathlib,subprocess,sys
p=pathlib.Path(os.environ['PROFILE_TEST_DIR'])
name=pathlib.Path(sys.argv[0]).name
args=sys.argv[1:]
assert os.environ['XDG_RUNTIME_DIR']==str(p/'runtime')
if name=='shikane':
 (p/'shikane.pid').write_text(str(os.getpid()))
 os.execv('/usr/bin/shikane',['shikane','-c',str(p/'shikane.toml'),'-s',str(p/'shikane.sock')])
if name=='shikanectl':
 os.execv('/usr/bin/shikanectl',['shikanectl','-s',str(p/'shikane.sock')]+args)
if name=='notify-send':
 with open(p/'notifications','a') as log: log.write(json.dumps(args)+'\\n')
 sys.exit(0)
if name=='noctalia':
 assert args==['dmenu','--prompt','Displays'],args
 choices=sys.stdin.read()
 (p/'choices').write_text(choices)
 selection=(p/'selection').read_text()
 if selection: print(selection)
 sys.exit(0 if selection else 1)
assert name=='swaymsg'
assert os.environ['SWAYSOCK'].startswith(str(p/'runtime')+'/')
args=[a.replace('"eDP-1"','"HEADLESS-1"').replace('"HDMI-A-1"','"HEADLESS-2"') for a in args]
result=subprocess.run(['/usr/bin/swaymsg']+args,capture_output=True,text=True)
def translate(value):
 if isinstance(value,list): return [translate(v) for v in value]
 if isinstance(value,dict): return {k:({'HEADLESS-1':'eDP-1','HEADLESS-2':'HDMI-A-1'}.get(v,v) if k in ('name','output') and isinstance(v,str) else translate(v)) for k,v in value.items()}
 return value
try: print(json.dumps(translate(json.loads(result.stdout))))
except ValueError: print(result.stdout,end='')
print(result.stderr,end='',file=sys.stderr)
sys.exit(result.returncode)
'''
        for name in ("swaymsg", "shikane", "shikanectl", "notify-send", "noctalia"):
            path = binary / name
            path.write_text(proxy)
            path.chmod(0o755)
        source = SHIKANE_CONFIG.read_text()
        source = source.replace('n/^(eDP|LVDS)-[0-9]+$', 'n/^HEADLESS-1$')
        source = source.replace('d/(eDP|LVDS)-[0-9]+', 'd/.*')
        source = source.replace('n/^(DP|HDMI-[AB]|DVI-[ADI]|VGA|USB-C)-[0-9]+(-[0-9]+)*$', 'n/^HEADLESS-[23]$')
        source = source.replace('"$HOME/.config/sway/scripts/monitor-profiles.py"', '"' + str(Path(__file__).resolve()) + '" --worker')
        cls.shikane_source = source
        (cls.tmp / "shikane.toml").write_text(source)
        config = (SCRIPT.parent.parent / "config").read_text().split("### Displays (Shikane)", 1)[1].split("### Input", 1)[0]
        config = config.replace("python3 ~/.config/sway/scripts/monitor-profiles.py", "python3 " + str(Path(__file__).resolve()) + " --worker")
        (cls.tmp / "sway.conf").write_text('''set $mod Mod4
output HEADLESS-1 mode 1920x1080 position 2560 180
output HEADLESS-2 mode 2560x1440 position 0 0
seat seat0 fallback true
font pango:Sans 10
focus_follows_mouse no
''' + config)
        cls.log = open(cls.tmp / "sway.log", "w")
        cls.sway = sp.Popen(["sway", "-d", "-c", str(cls.tmp / "sway.conf")], env=env, stdout=cls.log, stderr=cls.log)
        cls.windows = []
        try:
            socket = runtime / f"sway-ipc.{os.getuid()}.{cls.sway.pid}.sock"
            wait_for(socket.exists)
            display = wait_for(lambda: re.search("Running compositor on wayland display '([^']+)'", (cls.tmp / "sway.log").read_text()))
            env.update(SWAYSOCK=str(socket), WAYLAND_DISPLAY=display[1])
            assert env["SWAYSOCK"] != cls.original_env.get("SWAYSOCK")
            assert env["XDG_RUNTIME_DIR"] != cls.original_env.get("XDG_RUNTIME_DIR")
            os.environ.clear()
            os.environ.update(env)
            cls.io = TestBackend()
            cls.controller = profiles.Controller(cls.io)
            wait_for(lambda: (cls.tmp / "shikane.sock").exists())
            wait_for(lambda: cls.controller.matches("docked", cls.controller.outputs()))
            with cls.controller.locked():
                cls.controller.apply("extend")
            for number in (1, 2, 3):
                cls.io.command(f"workspace --no-auto-back-and-forth {number}")
                app = f"monitor-test-{number}"
                process = sp.Popen(["foot", "-c", "/dev/null", "-a", app, "sleep", "3600"], stdout=cls.log, stderr=cls.log)
                cls.windows.append(process)
                wait_for(lambda: any(n.get("app_id") == app for n in nodes(json.loads(sp.check_output(["swaymsg", "-r", "-t", "get_tree"], text=True)))))
        except BaseException:
            cls.tearDownClass()
            raise

    @classmethod
    def tearDownClass(cls):
        for window in cls.windows:
            window.terminate()
            window.wait(timeout=3)
        if cls.sway.poll() is None:
            cls.sway.terminate()
            cls.sway.wait(timeout=3)
        cls.log.close()
        os.environ.clear()
        os.environ.update(cls.original_env)

    def setUp(self):
        (self.tmp / "lid").write_text("open")
        with self.controller.locked():
            self.controller.state.clear()
            self.controller.save()
            self.controller.apply("extend")
            self.io.command('output "eDP-1" scale 1; output "HDMI-A-1" scale 1')
            self.controller.place(self.controller.outputs(), "HDMI-A-1")
            for name, target in (("1", "HDMI-A-1"), ("2", "eDP-1"), ("3", "HDMI-A-1")):
                self.io.command(f'workspace --no-auto-back-and-forth "{name}"; move workspace to output "{target}"')
            self.io.command("workspace --no-auto-back-and-forth 2")
            self.controller.remember_workspaces(self.controller.outputs())
            self.controller.save()

    def apply(self, profile, **kwargs):
        with self.controller.locked():
            self.controller.apply(profile, **kwargs)

    def lid(self, closed):
        (self.tmp / "lid").write_text("closed" if closed else "open")
        with self.controller.locked():
            self.controller.lid(closed)

    def assert_profile(self, profile, left=None):
        outputs = self.controller.outputs()
        self.assertTrue(self.controller.matches(profile, outputs), outputs)
        if left:
            self.assertTrue(self.controller.placed(outputs, self.controller.positions(outputs, left)), outputs)

    def assert_workspaces(self):
        workspaces = {w["name"]: w for w in self.io.query("get_workspaces")}
        self.assertEqual(workspaces["1"]["output"], "HDMI-A-1")
        self.assertEqual(workspaces["2"]["output"], "eDP-1")
        self.assertTrue(workspaces["2"]["focused"])

    def test_01_swap_and_delayed_hook(self):
        self.apply("extend", toggle=True)
        self.assert_profile("extend", "eDP-1")
        with self.controller.locked():
            self.controller.applied("extend")
            self.controller.applied("portrait")
        self.assert_profile("extend", "eDP-1")
        self.apply("extend", toggle=True)
        self.assert_profile("extend", "HDMI-A-1")

    def test_02_portrait_and_fractional_scaling(self):
        self.apply("portrait")
        self.assert_profile("portrait", "HDMI-A-1")
        self.io.command('output "HDMI-A-1" scale 1.5; output "eDP-1" scale 1.25')
        self.apply("portrait", toggle=True)
        self.assert_profile("portrait", "eDP-1")
        self.assert_workspaces()

    def test_03_laptop_only_then_workspace_restore(self):
        self.apply("laptop")
        self.assert_profile("laptop")
        self.assertTrue(all(w["output"] == "eDP-1" for w in self.io.query("get_workspaces")))
        self.apply("extend")
        self.assert_workspaces()

    def test_04_lid_restores_portrait_order_workspaces_and_focus(self):
        self.apply("portrait", toggle=False)
        self.apply("portrait", toggle=True)
        self.lid(True)
        self.assert_profile("docked")
        saved = json.loads(self.controller.state_path.read_text())["lid_restore"]
        self.lid(True)
        self.assertEqual(saved, json.loads(self.controller.state_path.read_text())["lid_restore"])
        self.lid(False)
        self.assert_profile("portrait", "eDP-1")
        self.assert_workspaces()
        self.assertNotIn("lid_restore", json.loads(self.controller.state_path.read_text()))

    def test_05_laptop_only_lid_roundtrip(self):
        self.apply("laptop")
        self.lid(True)
        self.assert_profile("docked")
        self.lid(False)
        self.assert_profile("laptop")

    def test_06_sway_reload_preserves_profile_and_daemon(self):
        self.apply("portrait")
        self.io.command('output "HDMI-A-1" scale 1.5')
        self.apply("portrait", toggle=True)
        self.io.command("workspace --no-auto-back-and-forth 1")
        pid = (self.tmp / "shikane.pid").read_text()
        # Real config has no output directives: synthetic initial modes must not
        # override the runtime Shikane layout during this reload either.
        config = self.tmp / "sway.conf"
        config.write_text("\n".join(line for line in config.read_text().splitlines()
                                    if not line.startswith("output HEADLESS-")) + "\n")
        self.io.command("reload")
        wait_for(lambda: self.controller.matches("portrait", self.controller.outputs()))
        self.assertEqual(pid, (self.tmp / "shikane.pid").read_text())
        with self.controller.locked():
            pass  # Wait for the complete reload hook, including workspace restoration.
        self.assert_profile("portrait", "eDP-1")
        self.assertTrue(next(w for w in self.io.query("get_workspaces") if w["name"] == "1")["focused"])
        self.assertEqual(next(o for o in self.controller.outputs() if o["name"] == "HDMI-A-1")["scale"], 1.5)
        self.lid(False)
        self.assert_profile("portrait")

    def test_11_reload_while_closed_keeps_open_lid_snapshot(self):
        self.apply("portrait")
        self.lid(True)
        snapshot = json.loads(self.controller.state_path.read_text())["lid_restore"]
        self.io.command("reload")
        wait_for(lambda: self.controller.matches("docked", self.controller.outputs()))
        with self.controller.locked():
            self.assertEqual(self.controller.state["lid_restore"], snapshot)
        self.lid(False)
        self.assert_profile("portrait", "HDMI-A-1")
        self.assert_workspaces()

    def test_07_concurrent_hooks_and_swaps(self):
        workers = [sp.Popen([sys.executable, __file__, "--worker", *args], stdout=sp.PIPE, stderr=sp.PIPE, text=True)
                   for args in [("applied", "extend"), ("toggle", "extend")] * 3]
        for worker in workers:
            stdout, stderr = worker.communicate(timeout=15)
            self.assertEqual(worker.returncode, 0, stdout + stderr)
        self.assert_profile("extend", "eDP-1")

    def test_08_native_picker_selection_and_cancel(self):
        (self.tmp / "selection").write_text("Laptop only")
        self.controller.picker()
        self.assert_profile("laptop")
        self.assertIn("Extend (landscape) (current)", (self.tmp / "choices").read_text())
        (self.tmp / "selection").write_text("")
        self.controller.picker()
        self.assert_profile("laptop")

    def test_09_unapplied_profile_produces_error_notification(self):
        (self.tmp / "shikane.toml").write_text(self.shikane_source.replace('name = "laptop"', 'name = "unused"'))
        try:
            sp.run(["shikanectl", "reload"], check=True, capture_output=True)
            time.sleep(.15)
            result = sp.run([sys.executable, __file__, "--worker", "switch", "laptop"], capture_output=True, text=True, timeout=12)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("did not apply", result.stderr)
            notices = [json.loads(line) for line in (self.tmp / "notifications").read_text().splitlines()]
            self.assertIn("--urgency=critical", notices[-1])
        finally:
            (self.tmp / "shikane.toml").write_text(self.shikane_source)
            sp.run(["shikanectl", "reload"], check=True, capture_output=True)
            time.sleep(.15)

    def test_10_workspace_names_are_quoted(self):
        name = '2: docs; "quoted" \\ notes'
        self.io.command('rename workspace "2" to ' + profiles.quote(name))
        try:
            self.apply("docked")
            self.apply("extend")
            workspace = next(w for w in self.io.query("get_workspaces") if w["name"] == name)
            self.assertEqual(workspace["output"], "eDP-1")
        finally:
            self.io.command('rename workspace ' + profiles.quote(name) + ' to "2"')

    def test_90_unplug_while_closed_restores_laptop(self):
        self.lid(True)
        sp.run(["/usr/bin/swaymsg", 'output HEADLESS-2 unplug'], check=True, capture_output=True)
        wait_for(lambda: len(self.controller.outputs()) == 1)
        self.lid(False)
        self.assert_profile("undocked")


if __name__ == "__main__":
    if "--worker" in sys.argv:
        profiles.Backend = TestBackend
        sys.argv = [str(SCRIPT)] + sys.argv[sys.argv.index("--worker") + 1:]
        sys.exit(profiles.main())
    if "--shikane-config" in sys.argv:
        index = sys.argv.index("--shikane-config")
        SHIKANE_CONFIG = Path(sys.argv[index + 1])
        del sys.argv[index:index + 2]
    unittest.main(verbosity=2)
