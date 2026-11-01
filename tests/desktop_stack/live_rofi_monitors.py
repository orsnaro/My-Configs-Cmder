"""Explicit live Wayland test; never discovered by normal unittest runs.

Requires a test-only virtual-pointer click client at ROFI_TEST_CLICKER.
Uses synthetic clipboard data and replaces wl-copy, never the user's clipboard.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from typing import Any


def command(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


def layers() -> dict[str, list[dict[str, Any]]]:
    data = json.loads(command('hyprctl', '-j', 'layers'))
    return {name: [row for level in monitor['levels'].values() for row in level
                   if row['namespace'] in ('rofi', 'rofi-dismiss-guard')]
            for name, monitor in data.items()}


def gone(pid: int) -> bool:
    try:
        return not (Path('/proc')/str(pid)/'cmdline').read_bytes()
    except FileNotFoundError:
        return True


class MonitorChecks(unittest.TestCase):
    def test_every_other_monitor_dismisses_each_picker_without_copying(self) -> None:
        clicker = os.environ.get('ROFI_TEST_CLICKER', '/tmp/opencode/rofi-send-click')
        self.assertTrue(Path(clicker).is_file(), 'Provide the test-only virtual-pointer click client')
        self.assertFalse(any(layers().values()), 'Close your current picker before this explicit live test')
        original = json.loads(command('hyprctl', '-j', 'cursorpos'))
        results: list[dict[str, Any]] = []
        with tempfile.TemporaryDirectory(prefix='rofi-monitors-', dir='/tmp/opencode') as directory:
            root = Path(directory)
            binary = root/'bin'
            binary.mkdir()
            copy = binary/'wl-copy'
            copy.write_text('#!/usr/bin/python\nfrom pathlib import Path\nimport os, sys\n'
                            'Path(os.environ["CAPTURE_COPY"]).write_bytes(sys.stdin.buffer.read())\n')
            copy.chmod(0o755)
            database = root/'clipboard.db'
            subprocess.run(['cliphist', '-db-path', str(database), 'store'], input=b'synthetic preview text', check=True)
            image = subprocess.check_output(['magick', '-size', '32x24', 'xc:coral', 'png:-'])
            subprocess.run(['cliphist', '-db-path', str(database), 'store'], input=image, check=True)
            env = {**os.environ, 'PATH': f'{binary}:/usr/bin:/bin', 'CAPTURE_COPY': str(root/'copied'),
                   'ROFI_TRIAL_CLIPHIST_DB': str(database)}
            try:
                for mode in ('apps', 'emoji', 'clipboard'):
                    monitors = json.loads(command('hyprctl', '-j', 'monitors'))
                    excluded = next(row['name'] for row in monitors if row['focused'])
                    anchor = next(row['id'] for row in monitors if row['name'] == excluded)
                    targets = [row['name'] for row in monitors if row['name'] != excluded]
                    self.assertTrue(targets, 'This test requires at least two connected monitors')
                    for index, target in enumerate(targets):
                        # The previous outside click legitimately changes monitor focus.
                        command('hyprctl', 'dispatch', f'hl.dsp.focus({{monitor={anchor}}})')
                        runtime = root/f'runtime-{mode}-{index}'
                        env['ROFI_HYPRLAND_RUNTIME'] = str(runtime)
                        args = ['-filter', '2+2'] if mode == 'apps' else []
                        process = subprocess.Popen([str(Path.home()/'.local/bin/rofi-trial'), mode, *args],
                                                   env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        owned_guards: set[int] = set()
                        try:
                            deadline = time.monotonic()+6
                            current: dict[str, list[dict[str, Any]]] = {}
                            active: list[str] = []
                            guarded: list[str] = []
                            while time.monotonic()<deadline and process.poll() is None:
                                current = layers()
                                active = [name for name, rows in current.items() if any(row['namespace']=='rofi' for row in rows)]
                                guarded = [name for name, rows in current.items() if any(row['namespace']=='rofi-dismiss-guard' and row['w']>0 and row['h']>0 for row in rows)]
                                if active == [excluded] and set(guarded) == set(targets): break
                                time.sleep(.02)
                            self.assertEqual(set(guarded), set(targets), 'Other monitors have no click guards')
                            self.assertEqual(active, [excluded])
                            row = next(row for row in current[target] if row['namespace']=='rofi-dismiss-guard')
                            owned_guards = {entry['pid'] for rows in current.values() for entry in rows if entry['namespace']=='rofi-dismiss-guard'}
                            self.assertEqual(len(owned_guards), 1, 'One on-demand helper should cover all other outputs')
                            pss = 0
                            for pid in owned_guards:
                                text = (Path('/proc')/str(pid)/'smaps_rollup').read_text()
                                pss += int(next(line.split()[1] for line in text.splitlines() if line.startswith('Pss:')))
                            x, y = row['x']+row['w']//2, row['y']+row['h']//2
                            command('hyprctl', 'dispatch', f'hl.dsp.cursor.move({{x={x},y={y}}})')
                            self.assertIsNone(process.poll(), 'Pointer movement alone dismissed the picker')
                            subprocess.run([clicker], check=True)
                            stdout, stderr = process.communicate(timeout=3)
                            self.assertEqual(process.returncode, 0, stderr)
                            self.assertEqual(stderr, '')
                            self.assertFalse((root/'copied').exists(), 'Dismissal wrote to the clipboard')
                            deadline = time.monotonic()+3
                            while (any(layers().values()) or any(not gone(pid) for pid in owned_guards)) and time.monotonic()<deadline:
                                time.sleep(.02)
                            self.assertFalse(any(layers().values()), 'A transparent guard surface remained')
                            self.assertTrue(all(gone(pid) for pid in owned_guards), 'A helper survived its picker')
                            results.append({'mode': mode, 'clicked_monitor': target, 'rofi_monitor': excluded,
                                            'guard_pss_kib': pss, 'no_copy': True, 'no_remaining_guards': True})
                        finally:
                            if process.poll() is None:
                                subprocess.run(['wtype', '-k', 'Escape'], check=True)
                                process.communicate(timeout=3)
            finally:
                command('hyprctl', 'dispatch', f'hl.dsp.cursor.move({{x={original["x"]},y={original["y"]}}})')
                report = Path(os.environ.get('ROFI_MONITOR_RESULTS', '/tmp/opencode/rofi-cross-monitor-results.json'))
                report.write_text(json.dumps(results, indent=2)+'\n')


if __name__ == '__main__':
    unittest.main(verbosity=2)
