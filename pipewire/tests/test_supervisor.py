"""Isolated Linux tests: fake audio processes, no desktop services modified."""
import importlib.machinery
import importlib.util
import json
import os
import re
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / '.local/bin/wireplumber-supervisor'
loader = importlib.machinery.SourceFileLoader('supervisor', str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
supervisor = importlib.util.module_from_spec(spec)
loader.exec_module(supervisor)


def wait_for(predicate, timeout=6):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError('condition did not become true')


class StowTests(unittest.TestCase):
    def test_clean_install_and_uninstall(self):
        with tempfile.TemporaryDirectory(prefix='audio-stow-') as home:
            repo = SCRIPT.parents[3]
            subprocess.run(['stow', '--dir=' + str(repo), '--no-folding',
                            '--target=' + home, 'pipewire'], check=True,
                           capture_output=True, text=True)
            target = Path(home)
            files = [path for path in target.rglob('*') if path.is_file()]
            self.assertEqual(len(files), 4)
            self.assertTrue(all(path.is_symlink() for path in files))
            self.assertTrue(os.access(target / '.local/bin/wireplumber-supervisor', os.X_OK))
            self.assertFalse((target / 'tests').exists())
            self.assertFalse((target / 'README.md').exists())
            subprocess.run(['stow', '--dir=' + str(repo), '--no-folding',
                            '--delete', '--target=' + home, 'pipewire'], check=True,
                           capture_output=True, text=True)
            # --no-folding may leave empty directories; all managed files and
            # links must be gone, without deleting unrelated directories.
            self.assertFalse(any(path.is_file() or path.is_symlink()
                                 for path in target.rglob('*')))


class LockTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.runtime = Path(self.temp.name)
        supervisor.STOP = False

    def tearDown(self):
        self.temp.cleanup()

    def test_private_regular_lock(self):
        fd = supervisor.acquire_lock(str(self.runtime))
        try:
            self.assertEqual((self.runtime / 'wireplumber-supervisor.lock').stat().st_mode & 0o777, 0o600)
        finally:
            os.close(fd)

    def test_reject_public_runtime(self):
        self.runtime.chmod(0o755)
        with self.assertRaises(ValueError):
            supervisor.acquire_lock(str(self.runtime))

    def test_reject_runtime_symlink(self):
        link = self.runtime / 'link'
        link.symlink_to(self.runtime, target_is_directory=True)
        with self.assertRaises(ValueError):
            supervisor.acquire_lock(str(link))

    def test_reject_symlink_fifo_and_hardlink(self):
        lock = self.runtime / 'wireplumber-supervisor.lock'
        target = self.runtime / 'target'
        target.write_text('do not overwrite')
        lock.symlink_to(target)
        with self.assertRaises(OSError):
            supervisor.acquire_lock(str(self.runtime))
        self.assertEqual(target.read_text(), 'do not overwrite')
        lock.unlink()
        os.mkfifo(lock, 0o600)
        with self.assertRaises(ValueError):
            supervisor.acquire_lock(str(self.runtime))
        lock.unlink()
        os.link(target, lock)
        with self.assertRaises(ValueError):
            supervisor.acquire_lock(str(self.runtime))

    def test_reject_public_lock(self):
        lock = self.runtime / 'wireplumber-supervisor.lock'
        lock.touch(mode=0o644)
        with self.assertRaises(ValueError):
            supervisor.acquire_lock(str(self.runtime))

    def test_pid_identity_rejects_missing_or_unrelated_process(self):
        self.assertIsNone(supervisor.process_identity(999999999))
        self.assertIsNone(supervisor.process_identity(os.getpid()))

    def test_pid_reuse_and_zombie(self):
        # Check parsing of stat fields including a changed process start time.
        fields = ['S'] + ['0'] * 18 + ['123']
        with mock.patch.object(Path, 'stat') as info, mock.patch.object(Path, 'read_text') as read:
            info.return_value.st_uid = os.getuid()
            read.return_value = '42 (pipewire) ' + ' '.join(fields)
            self.assertEqual(supervisor.process_identity(42), (42, '123'))
            fields[19] = '456'
            read.return_value = '42 (pipewire) ' + ' '.join(fields)
            self.assertNotEqual(supervisor.process_identity(42), (42, '123'))
            fields[0] = 'Z'
            read.return_value = '42 (pipewire) ' + ' '.join(fields)
            self.assertIsNone(supervisor.process_identity(42))


@unittest.skipIf(os.getuid() == 0, 'desktop-user integration tests reject root')
class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.events = self.root / 'events'
        self.events.touch()
        self.processes = []
        # The fake core has the same Linux comm as PipeWire, not its functionality.
        self.core = self.spawn([sys.executable, '-c',
            'import ctypes,time; ctypes.CDLL(None).prctl(15,b"pipewire",0,0,0); time.sleep(120)'])
        wait_for(lambda: supervisor.process_identity(self.core.pid) is not None)
        self.env = dict(os.environ, XDG_RUNTIME_DIR=str(self.root),
                        PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                        TEST_CORE=str(self.core.pid), TEST_EVENTS=str(self.events))
        self.write_tool('pw-cli', 'import os\nprint(\'application.process.id = "\' + os.environ["TEST_CORE"] + \'"\')\n')
        self.write_tool('wireplumber',
            'import os,time\n'
            'with open(os.environ["TEST_EVENTS"],"a") as f: f.write(str(os.getpid())+"\\n")\n'
            'if os.environ.get("TEST_CRASH"): raise SystemExit(1)\n'
            'time.sleep(120)\n')

    def spawn(self, args, **kwargs):
        proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)
        self.processes.append(proc)
        return proc

    def write_tool(self, name, code):
        path = self.bin / name
        path.write_text('#!' + sys.executable + '\n' + code)
        path.chmod(0o755)

    def start(self, **overrides):
        return self.spawn([sys.executable, str(SCRIPT)], env=dict(self.env, **overrides))

    def children(self):
        return [int(pid) for pid in self.events.read_text().splitlines()]

    def child_gone(self, pid):
        return not Path('/proc', str(pid)).exists()

    def tearDown(self):
        for proc in reversed(self.processes):
            if proc.poll() is None:
                proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        # Emergency cleanup is restricted to our recorded fake children.
        for pid in self.children():
            try:
                # Do not signal an unrelated process if a PID was reused.
                command = Path('/proc', str(pid), 'cmdline').read_bytes()
                if str(self.bin / 'wireplumber').encode() in command.split(b'\0'):
                    os.kill(pid, signal.SIGKILL)
            except (FileNotFoundError, ProcessLookupError):
                pass
        self.temp.cleanup()

    def test_crash_recovery_and_core_shutdown(self):
        proc = self.start()
        wait_for(lambda: len(self.children()) == 1)
        old = self.children()[0]
        # The lock must not leak to WirePlumber.
        for fd in Path('/proc', str(old), 'fd').iterdir():
            self.assertNotIn('wireplumber-supervisor.lock', os.readlink(fd))
        os.kill(old, signal.SIGKILL)
        wait_for(lambda: len(self.children()) == 2)
        self.core.terminate()
        self.core.wait(timeout=3)
        self.assertEqual(proc.wait(timeout=5), 0)
        wait_for(lambda: self.child_gone(self.children()[-1]))

    def test_config_launcher_with_spaces_in_home(self):
        # PipeWire tokenizes context.exec args by whitespace, not shell grammar.
        config = SCRIPT.parents[2] / '.config/pipewire/pipewire.conf.d/10-wireplumber.conf'
        match = re.search(r'args\s*=\s*("(?:\\.|[^"\\])*")', config.read_text())
        args = json.loads(match[1]).split()
        home = self.root / 'home with spaces ; $literal'
        bin_dir = home / '.local/bin'
        bin_dir.mkdir(parents=True)
        (bin_dir / SCRIPT.name).symlink_to(SCRIPT)
        proc = self.spawn(['/bin/sh', *args], env=dict(self.env, HOME=str(home)))
        wait_for(lambda: len(self.children()) == 1)
        self.core.terminate()
        self.core.wait(timeout=3)
        self.assertEqual(proc.wait(timeout=5), 0)
        wait_for(lambda: self.child_gone(self.children()[0]))

    def test_signal_cleanup(self):
        proc = self.start()
        wait_for(lambda: len(self.children()) == 1)
        proc.terminate()
        self.assertEqual(proc.wait(timeout=5), 0)
        wait_for(lambda: self.child_gone(self.children()[0]))

    def test_unresponsive_child_is_killed(self):
        self.write_tool('wireplumber',
            'import os,signal,time\n'
            'signal.signal(signal.SIGTERM,signal.SIG_IGN)\n'
            'with open(os.environ["TEST_EVENTS"],"a") as f: f.write(str(os.getpid())+"\\n")\n'
            'time.sleep(120)\n')
        proc = self.start()
        wait_for(lambda: len(self.children()) == 1)
        proc.terminate()
        self.assertEqual(proc.wait(timeout=5), 0)
        wait_for(lambda: self.child_gone(self.children()[0]))

    def test_singleton(self):
        self.start()
        wait_for(lambda: len(self.children()) == 1)
        duplicate = self.start()
        self.assertEqual(duplicate.wait(timeout=11), 0)
        self.assertEqual(len(self.children()), 1)

    def test_restart_backoff(self):
        proc = self.start(TEST_CRASH='1')
        wait_for(lambda: len(self.children()) == 2)
        time.sleep(1)
        self.assertEqual(len(self.children()), 2)
        proc.terminate()
        self.assertEqual(proc.wait(timeout=3), 0)

    def test_hung_core_query_is_bounded_and_interruptible(self):
        self.write_tool('pw-cli', 'import time\ntime.sleep(120)\n')
        proc = self.start()
        time.sleep(1.3)
        proc.terminate()
        self.assertNotEqual(proc.wait(timeout=3), 0)
        self.assertEqual(self.children(), [])


if __name__ == '__main__':
    unittest.main()
