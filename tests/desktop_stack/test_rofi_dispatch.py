"""Monitor and guard forwarding using an isolated HOME and command boundaries."""
from __future__ import annotations

import json
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


if __name__ == '__main__':
    unittest.main()
