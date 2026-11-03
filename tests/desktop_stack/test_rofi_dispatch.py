"""Monitor and guard forwarding using an isolated HOME and command boundaries."""
from __future__ import annotations

import json
import fcntl
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import time
import unittest

PAYLOAD = Path(__file__).resolve().parents[2]/'conf_backups/cachyos_hyprland_ml4w'


class DispatchTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix='rofi-dispatch-', dir='/tmp/opencode')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root/'home with spaces'
        shutil.copytree(PAYLOAD/'local/.local/lib/rofi-trial', self.home/'.local/lib/rofi-trial')
        subprocess.run(['bash', str(self.home/'.local/lib/rofi-trial/build-dismiss.sh')],
                       check=True, capture_output=True, text=True, timeout=30)
        shutil.move(self.home/'.local/lib/rofi-trial/dismiss-guard',
                    self.home/'.local/lib/rofi-trial/native-test-guard')
        (self.home/'.local/lib/rofi-trial/smart.so').touch()
        self.binary = self.root/'bin'
        self.binary.mkdir()
        self.log = self.root/'commands.jsonl'
        fixture = self.root/'fixture.txt'
        fixture.touch()
        self.env = {**os.environ, 'HOME': str(self.home), 'PATH': f'{self.binary}:/usr/bin:/bin',
                    'ROFI_HYPRLAND_RUNTIME': str(self.root/'runtime'), 'AUDIT': str(self.log),
                    'ROFI_TRIAL_FILE_ROOT': str(self.root), 'FIXTURE_FILE': str(fixture)}
        for name in ('rofi', 'rofimoji', 'wl-copy', 'cliphist', 'hyprctl', 'fd', 'xdg-open'):
            self.stub(self.binary/name)
        self.stub(self.home/'.local/lib/rofi-trial/dismiss-guard')

    def stub(self, path: Path) -> None:
        path.write_text('#!/usr/bin/python\nimport json, os, sys\nfrom pathlib import Path\n'
                        'name=Path(sys.argv[0]).name\n'
                        'if name=="dismiss-guard" and sys.argv[1:2]==["--toggle"]:\n'
                        '    os.execv(str(Path(sys.argv[0]).with_name("native-test-guard")), sys.argv)\n'
                        'with open(os.environ["AUDIT"], "a") as f:\n'
                        '    f.write(json.dumps({"name":name,"args":sys.argv[1:]})+"\\n")\n'
                        'if name=="hyprctl": print(json.dumps([{ "name":"DP-1", "focused":False }, { "name":"DP-2", "focused":True }]))\n'
                        'if name=="cliphist": print("7\\tsynthetic fixture")\n'
                        'if name=="fd": sys.stdout.buffer.write(os.fsencode(os.environ["FIXTURE_FILE"])+b"\\0")\n'
                        'if name=="rofi":\n'
                        '    if "-dmenu" in sys.argv: sys.stdin.read()\n'
                        '    sys.exit(1)\n')
        path.chmod(0o755)

    def invoke(self, mode: str) -> list[dict[str, object]]:
        self.log.unlink(missing_ok=True)
        result = subprocess.run(['bash', str(PAYLOAD/'local/.local/bin/rofi-trial'), mode],
                                env=self.env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=8)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        deadline = time.monotonic()+1
        while True:
            rows = [json.loads(line) for line in self.log.read_text().splitlines()]
            if any(row['name']=='dismiss-guard' for row in rows) or time.monotonic()>=deadline:
                return rows
            time.sleep(.01)

    def test_all_direct_modes_forward_the_focused_monitor_and_start_one_guard(self) -> None:
        for mode in ('apps', 'run', 'calc', 'files', 'clipboard'):
            with self.subTest(mode=mode):
                rows = self.invoke(mode)
                args = next(row['args'] for row in rows if row['name']=='rofi')
                self.assertIn('-monitor', args)
                self.assertEqual(args[args.index('-monitor')+1], 'DP-2')
                guards = [row for row in rows if row['name']=='dismiss-guard']
                self.assertEqual(len(guards), 1)
                self.assertEqual(guards[0]['args'][1], 'DP-2')
                self.assertNotIn('wl-copy', [row['name'] for row in rows])

    def test_emoji_selector_forwards_the_same_monitor_without_keyboard_grab_helpers(self) -> None:
        rows = self.invoke('emoji')
        args = next(row['args'] for row in rows if row['name']=='rofimoji')
        selector = shlex.split(next(arg.split('=', 1)[1] for arg in args if arg.startswith('--selector-args=')))
        self.assertIn('-monitor', selector)
        self.assertEqual(selector[selector.index('-monitor')+1], 'DP-2')
        self.assertEqual(len([row for row in rows if row['name']=='dismiss-guard']), 1)

    def test_terminated_emoji_selector_does_not_clear_clipboard(self) -> None:
        # Exercise real Rofimoji: its SIGTERM path returns an empty DEFAULT selection.
        (self.binary/'rofimoji').unlink()
        (self.binary/'rofi').write_text('#!/usr/bin/python\nimport os, signal, sys\n'
                                      'sys.stdin.read()\nos.kill(os.getpid(), signal.SIGTERM)\n')
        rows = self.invoke('emoji')
        self.assertNotIn('wl-copy', [row['name'] for row in rows])

    def test_apps_open_without_python_command(self) -> None:
        for name in ('bash', 'mkdir', 'stat', 'flock'):
            (self.binary/name).symlink_to(shutil.which(name))
        self.env['PATH'] = str(self.binary)
        self.assertIsNone(shutil.which('python', path=self.env['PATH']))
        result = subprocess.run(['/usr/bin/bash', str(PAYLOAD/'local/.local/bin/rofi-trial'), 'apps'],
                                env=self.env, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertTrue(any(row['name']=='rofi' for row in rows))

    def test_busy_startup_does_not_spawn_or_rewrite_metadata(self) -> None:
        runtime = self.root/'runtime'
        runtime.mkdir(mode=0o700)
        (runtime/'mode').write_text('files\n')
        with (runtime/'startup.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = subprocess.run(['bash', str(PAYLOAD/'local/.local/bin/rofi-trial'), 'apps'],
                                    env=self.env, capture_output=True, text=True, timeout=3)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.log.exists(), 'A busy request must not start any commands')
        self.assertEqual((runtime/'mode').read_text(), 'files\n')

    def paused_picker(self) -> subprocess.Popen[str]:
        self.env['GATE_ROOT'] = str(self.root)
        (self.binary/'rofi').write_text(
            '#!/usr/bin/python\nimport json, os, time\nfrom pathlib import Path\n'
            'root=Path(os.environ["GATE_ROOT"])\n'
            'with open(os.environ["AUDIT"], "a") as f: f.write(json.dumps({"name":"rofi"})+"\\n")\n'
            '(root/"picker-entered").touch()\n'
            'while not (root/"release-picker").exists(): time.sleep(.005)\n')
        (self.home/'.local/lib/rofi-trial/dismiss-guard').write_text(
            '#!/usr/bin/python\nimport os, sys, time\nfrom pathlib import Path\n'
            'if sys.argv[1:2]==["--toggle"]:\n'
            '    os.execv(str(Path(sys.argv[0]).with_name("native-test-guard")), sys.argv)\n'
            'root=Path(os.environ["GATE_ROOT"])\n'
            '(root/"guard-entered").touch()\n'
            'while not (root/"release-guard").exists(): time.sleep(.005)\n'
            'if len(sys.argv)==5: os.close(int(sys.argv[4]))\n')
        return self.start_picker()

    def start_picker(self) -> subprocess.Popen[str]:
        return subprocess.Popen(['bash', str(PAYLOAD/'local/.local/bin/rofi-trial'), 'apps'],
                                env=self.env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)

    def wait_for(self, path: Path) -> None:
        deadline = time.monotonic()+3
        while not path.exists() and time.monotonic()<deadline:
            time.sleep(.005)
        self.assertTrue(path.exists(), f'Missing fixture milestone: {path.name}')

    def test_overlap_before_pid_registration_launches_only_one_picker(self) -> None:
        first = self.paused_picker()
        second: subprocess.Popen[str] | None = None
        try:
            self.wait_for(self.root/'picker-entered')
            second = self.start_picker()
            try:
                second.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                self.fail('Overlapping startup spawned another waiting picker instead of returning')
            self.assertEqual(second.returncode, 0)
            rows = [json.loads(line) for line in self.log.read_text().splitlines()]
            self.assertEqual(sum(row['name']=='rofi' for row in rows), 1)
        finally:
            (self.root/'release-guard').touch()
            (self.root/'release-picker').touch()
            first.communicate(timeout=3)
            if second is not None: second.communicate(timeout=3)

    def test_guard_handoff_releases_lock_before_picker_exits(self) -> None:
        first = self.paused_picker()
        second: subprocess.Popen[str] | None = None
        try:
            self.wait_for(self.root/'picker-entered')
            (self.root/'release-guard').touch()
            runtime = self.root/'runtime'
            deadline = time.monotonic()+2
            while time.monotonic()<deadline:
                with (runtime/'startup.lock').open('a') as lock:
                    try:
                        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError: pass
                time.sleep(.005)
            else: self.fail('Startup lock survived the guard handoff')
            self.assertIsNone(first.poll(), 'The picker should still be open')
            second = self.start_picker()
            deadline = time.monotonic()+2
            while time.monotonic()<deadline:
                rows = [json.loads(line) for line in self.log.read_text().splitlines()]
                if sum(row['name']=='rofi' for row in rows)==2: break
                time.sleep(.005)
            self.assertEqual(sum(row['name']=='rofi' for row in rows), 2)
        finally:
            (self.root/'release-guard').touch()
            (self.root/'release-picker').touch()
            first.communicate(timeout=3)
            if second is not None: second.communicate(timeout=3)

    def test_missing_guard_does_not_leave_startup_locked(self) -> None:
        guard = self.home/'.local/lib/rofi-trial/dismiss-guard'
        guard.unlink()
        result = subprocess.run(['bash', str(PAYLOAD/'local/.local/bin/rofi-trial'), 'apps'],
                                env=self.env, capture_output=True, text=True, timeout=3)
        self.assertEqual(result.returncode, 2)
        self.stub(guard)
        self.assertTrue(self.invoke('apps'))

    def test_unsafe_runtime_is_rejected_without_creating_lockfile(self) -> None:
        runtime = self.root/'runtime'
        runtime.mkdir(mode=0o755)
        runtime.chmod(0o755)
        result = subprocess.run(['bash', str(PAYLOAD/'local/.local/bin/rofi-trial'), 'apps'],
                                env=self.env, capture_output=True, text=True, timeout=3)
        self.assertEqual(result.returncode, 2)
        self.assertFalse((runtime/'startup.lock').exists())

    def test_picker_keeps_the_callers_umask(self) -> None:
        output = self.root/'picker-created-file'
        self.env['PICKER_CREATED_FILE'] = str(output)
        (self.binary/'rofi').write_text('#!/usr/bin/python\nimport os, sys\nfrom pathlib import Path\n'
                                      'Path(os.environ["PICKER_CREATED_FILE"]).write_text("fixture")\n'
                                      'sys.exit(1)\n')
        result = subprocess.run(['bash', str(PAYLOAD/'local/.local/bin/rofi-trial'), 'apps'],
                                env=self.env, capture_output=True, text=True, timeout=3, umask=0o022)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output.stat().st_mode & 0o777, 0o644)


if __name__ == '__main__':
    unittest.main()
