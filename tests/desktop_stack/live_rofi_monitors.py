"""Explicit live Wayland test; never discovered by normal unittest runs.

Requires a test-only virtual-pointer click client at ROFI_TEST_CLICKER.
Uses synthetic clipboard data and replaces wl-copy, never the user's clipboard.
"""
from __future__ import annotations

import json
import fcntl
import os
from pathlib import Path
import subprocess
import signal
import sys
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
    except (FileNotFoundError, ProcessLookupError):
        return True


def watchers(pidfile: Path, owner: int) -> set[int]:
    found: set[int] = set()
    for process in Path('/proc').iterdir():
        if not process.name.isdecimal():
            continue
        try:
            args = (process/'cmdline').read_bytes().rstrip(b'\0').split(b'\0')
            if len(args) in (4, 5) and args[1] == os.fsencode(pidfile) and args[3] == str(owner).encode():
                if (process/'exe').readlink().name == 'dismiss-guard':
                    found.add(int(process.name))
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            pass
    return found


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
                    anchor = next(row for row in monitors if row['name'] == excluded)
                    targets = [row['name'] for row in monitors if row['name'] != excluded]
                    self.assertTrue(targets, 'This test requires at least two connected monitors')
                    cases = [(target, button) for target in targets for button in (272, 273, 274)]
                    for index, (target, button) in enumerate(cases):
                        target_monitor = next(row for row in monitors if row['name'] == target)
                        tx = int(target_monitor['x']+target_monitor['width']/target_monitor['scale']/2)
                        ty = int(target_monitor['y']+target_monitor['height']/target_monitor['scale']/2)
                        command('hyprctl', 'dispatch', f'hl.dsp.cursor.move({{x={tx},y={ty}}})')
                        command('hyprctl', 'dispatch', f'hl.dsp.focus({{monitor={target_monitor["id"]}}})')
                        sink_state = root/f'sink-{mode}-{index}.json'
                        sink = subprocess.Popen([sys.executable, str(Path(__file__).with_name('rofi_input_sink.py')), str(sink_state)],
                                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        self.addCleanup(lambda child=sink: child.poll() is None and child.terminate())
                        deadline = time.monotonic()+5
                        while True:
                            clients = json.loads(command('hyprctl', '-j', 'clients'))
                            sink_window = next((row for row in clients if row['pid']==sink.pid), None)
                            if sink_window and sink_state.exists():
                                break
                            self.assertLess(time.monotonic(), deadline, 'Owned click sink did not map')
                            time.sleep(.01)
                        # The previous outside click legitimately changes monitor focus.
                        # Align the pointer too, so focus-follows-mouse cannot undo it.
                        ax = int(anchor['x'] + anchor['width']/anchor['scale']/2)
                        ay = int(anchor['y'] + anchor['height']/anchor['scale']/2)
                        command('hyprctl', 'dispatch', f'hl.dsp.cursor.move({{x={ax},y={ay}}})')
                        command('hyprctl', 'dispatch', f'hl.dsp.focus({{monitor={anchor["id"]}}})')
                        deadline = time.monotonic()+2
                        while True:
                            focused = next(row['name'] for row in json.loads(command('hyprctl', '-j', 'monitors')) if row['focused'])
                            if focused == excluded: break
                            self.assertLess(time.monotonic(), deadline, 'Fixture monitor focus did not settle')
                            time.sleep(.01)
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
                            while time.monotonic()<deadline and process.poll() is None:
                                current = layers()
                                active = [name for name, rows in current.items() if any(row['namespace']=='rofi' for row in rows)]
                                if active == [excluded] and (runtime/'rofi.pid').exists():
                                    with (runtime/'startup.lock').open('r') as lock:
                                        try:
                                            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                                            break
                                        except BlockingIOError:
                                            pass
                                time.sleep(.02)
                            self.assertEqual(active, [excluded])
                            self.assertFalse(any(row['namespace']=='rofi-dismiss-guard' for rows in current.values() for row in rows),
                                             'The replacement must not create helper overlays')
                            # Layer geometry is published before the first buffer is mapped.
                            # Click only once the owned picker is visibly ready, not mid-startup.
                            picker = next(entry for entry in current[excluded] if entry['namespace']=='rofi')
                            self.assertEqual(picker['pid'], int((runtime/'rofi.pid').read_text()))
                            width = {'apps': 750, 'emoji': 900, 'clipboard': 1000}[mode]
                            bx = picker['x']+(picker['w']-width)//2
                            by = picker['y']+picker['h']//2
                            deadline = time.monotonic()+6
                            while True:
                                pixel = subprocess.check_output(['grim', '-g', f'{bx},{by} 1x1', '-'])
                                color = subprocess.run(['magick', 'png:-', '-format', '%[hex:p{0,0}]', 'info:'],
                                                       input=pixel, capture_output=True, check=True).stdout
                                if color.startswith(b'8AD0EE'): break
                                self.assertLess(time.monotonic(), deadline, f'{mode}: picker did not render')
                                time.sleep(.01)
                            owned_guards = watchers(runtime/'rofi.pid', process.pid)
                            self.assertEqual(len(owned_guards), 1, 'One on-demand helper should cover all other outputs')
                            if os.environ.get('ROFI_MONITOR_RELOAD') == '1':
                                command('hyprctl', 'reload', 'config-only')
                                self.assertEqual(command('hyprctl', 'configerrors'), '')
                                time.sleep(.3)
                            pss = 0
                            for pid in owned_guards:
                                text = (Path('/proc')/str(pid)/'smaps_rollup').read_text()
                                pss += int(next(line.split()[1] for line in text.splitlines() if line.startswith('Pss:')))
                            row = next(row for row in json.loads(command('hyprctl', '-j', 'clients')) if row['pid']==sink.pid)
                            self.assertEqual(row['monitor'], target_monitor['id'])
                            x, y = int(row['at'][0]+row['size'][0]/2), int(row['at'][1]+row['size'][1]/2)
                            command('hyprctl', 'dispatch', f'hl.dsp.cursor.move({{x={x},y={y}}})')
                            time.sleep(.2)
                            self.assertIsNone(process.poll(), 'Pointer movement alone dismissed the picker')
                            subprocess.run([clicker, str(button)], check=True)
                            stdout, stderr = process.communicate(timeout=3)
                            self.assertEqual(process.returncode, 0, stderr)
                            self.assertEqual(stderr, '')
                            self.assertFalse((root/'copied').exists(), 'Dismissal wrote to the clipboard')
                            deadline = time.monotonic()+3
                            while (any(layers().values()) or any(not gone(pid) for pid in owned_guards)) and time.monotonic()<deadline:
                                time.sleep(.02)
                            self.assertFalse(any(layers().values()), 'A picker/helper surface remained')
                            self.assertTrue(all(gone(pid) for pid in owned_guards), 'A helper survived its picker')
                            self.assertEqual(json.loads(sink_state.read_text())['clicks'], 0,
                                             'Dismissal activated the underlying owned window')
                            # Once closed, the same ordinary button must work again.
                            subprocess.run([clicker, str(button)], check=True)
                            deadline = time.monotonic()+2
                            while json.loads(sink_state.read_text())['clicks'] == 0 and time.monotonic()<deadline:
                                time.sleep(.01)
                            self.assertEqual(json.loads(sink_state.read_text())['clicks'], 1,
                                             'A normal mouse button stayed intercepted after close')
                            results.append({'mode': mode, 'clicked_monitor': target, 'rofi_monitor': excluded,
                                             'button': button, 'watcher_pss_kib': pss,
                                             'reload': os.environ.get('ROFI_MONITOR_RELOAD') == '1',
                                             'underlying_not_clicked': True, 'normal_button_restored': True,
                                             'no_copy': True, 'no_remaining_helpers': True})
                        finally:
                            if process.poll() is None:
                                if (runtime/'rofi.pid').exists():
                                    fd = os.pidfd_open(int((runtime/'rofi.pid').read_text()))
                                    try:
                                        signal.pidfd_send_signal(fd, signal.SIGTERM)
                                    finally:
                                        os.close(fd)
                                process.communicate(timeout=3)
                            sink.terminate()
                            sink.wait(timeout=3)
            finally:
                command('hyprctl', 'dispatch', f'hl.dsp.cursor.move({{x={original["x"]},y={original["y"]}}})')
                report = Path(os.environ.get('ROFI_MONITOR_RESULTS', '/tmp/opencode/rofi-cross-monitor-results.json'))
                report.write_text(json.dumps(results, indent=2)+'\n')


if __name__ == '__main__':
    unittest.main(verbosity=2)
