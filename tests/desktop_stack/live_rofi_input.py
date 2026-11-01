"""Explicit live synthetic typing/focus measurements; never a physical-key test.

Pre-focus keys go only to an owned GTK entry. No global key listener, real
clipboard writes, arbitrary text logging, resident frontend or input replay.
"""
from __future__ import annotations

import json
import fcntl
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from typing import Any

from live_rofi_monitors import command, layers

EXPRESSION = '123456789+987654321'


def focused(trace: Path) -> bool:
    events = re.findall(r'wl_keyboard#[0-9]+\.(enter|leave)\(', trace.read_text())
    return bool(events and events[-1] == 'enter')


def cancel(runtime: Path) -> None:
    if not (runtime/'rofi.pid').exists():
        return
    try:
        descriptor = os.pidfd_open(int((runtime/'rofi.pid').read_text()))
        try:
            signal.pidfd_send_signal(descriptor, signal.SIGTERM)
        finally:
            os.close(descriptor)
    except ProcessLookupError:
        pass


class InputChecks(unittest.TestCase):
    def test_thirty_cycles_and_ten_overlapping_starts(self) -> None:
        self.assertFalse(any(layers().values()), 'Leave an existing picker untouched')
        results: list[dict[str, Any]] = []
        with tempfile.TemporaryDirectory(prefix='rofi-cycles-', dir='/tmp/opencode') as directory:
            root = Path(directory)
            binary = root/'bin'
            binary.mkdir()
            copy = binary/'wl-copy'
            copy.write_text('#!/usr/bin/python\nfrom pathlib import Path\nimport os\nPath(os.environ["CAPTURE_COPY"]).touch()\n')
            copy.chmod(0o755)
            for sample in range(30):
                runtime = root/f'runtime-{sample}'
                env = {**os.environ, 'PATH': f'{binary}:/usr/bin:/bin', 'CAPTURE_COPY': str(root/'copied'),
                       'ROFI_HYPRLAND_RUNTIME': str(runtime)}
                argv = [str(Path.home()/'.local/bin/rofi-trial'), 'apps']
                start = time.monotonic()
                first = subprocess.Popen(argv, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                overlap: subprocess.Popen[str] | None = None
                try:
                    if sample < 10:
                        overlap = subprocess.Popen(argv, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    deadline = time.monotonic()+6
                    while time.monotonic()<deadline:
                        current = [row for rows in layers().values() for row in rows]
                        if current and (runtime/'rofi.pid').exists():
                            with (runtime/'startup.lock').open('r') as lock:
                                try:
                                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                                    break
                                except BlockingIOError:
                                    pass
                        time.sleep(.005)
                    else:
                        self.fail('No owned picker/startup registration')
                    self.assertEqual(len(current), 1)
                    self.assertEqual(current[0]['namespace'], 'rofi')
                    self.assertEqual(current[0]['pid'], int((runtime/'rofi.pid').read_text()))
                    from live_rofi_monitors import watchers, gone
                    owned = watchers(runtime/'rofi.pid', first.pid)
                    if overlap is not None:
                        # Either simultaneous caller may have won the lock.
                        owned |= watchers(runtime/'rofi.pid', overlap.pid)
                    self.assertEqual(len(owned), 1)
                    ready_ms = (time.monotonic()-start)*1000
                    closed = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=5)
                    self.assertEqual(closed.returncode, 0, closed.stderr)
                    for child in (first, overlap):
                        if child is not None:
                            _, stderr = child.communicate(timeout=4)
                            self.assertEqual(child.returncode, 0, stderr)
                            self.assertEqual(stderr, '')
                    deadline = time.monotonic()+3
                    while (any(layers().values()) or any(not gone(pid) for pid in owned)) and time.monotonic()<deadline:
                        time.sleep(.005)
                    self.assertFalse(any(layers().values()))
                    self.assertTrue(all(gone(pid) for pid in owned))
                    self.assertFalse((root/'copied').exists())
                    results.append({'sample': sample, 'overlap': sample < 10, 'registered_ms': round(ready_ms, 1),
                                    'one_picker': True, 'no_copy': True, 'no_remaining_helpers': True})
                finally:
                    if first.poll() is None or (overlap is not None and overlap.poll() is None):
                        cancel(runtime)
                    for child in (first, overlap):
                        if child is not None:
                            child.communicate(timeout=3)
                    report = Path(os.environ.get('ROFI_CYCLE_RESULTS', '/tmp/opencode/rofi-cycle-results.json'))
                    report.write_text(json.dumps(results, indent=2)+'\n')

    def test_synthetic_early_typing_and_post_focus_delivery(self) -> None:
        self.assertFalse(any(layers().values()), 'Leave an existing picker untouched')
        results: list[dict[str, Any]] = []
        with tempfile.TemporaryDirectory(prefix='rofi-input-', dir='/tmp/opencode') as directory:
            root = Path(directory)
            binary = root/'bin'
            binary.mkdir()
            copy = binary/'wl-copy'
            copy.write_text('#!/usr/bin/python\nimport os,sys\nfrom pathlib import Path\n'
                            'Path(os.environ["CAPTURE_COPY"]).write_bytes(sys.stdin.buffer.read())\n')
            copy.chmod(0o755)
            apps = root/'data/applications'
            apps.mkdir(parents=True)
            (apps/'fixture.desktop').write_text('[Desktop Entry]\nType=Application\nName=Harmless Fixture\nExec=/usr/bin/true\n')
            for index, delay in enumerate((0, 30, 60, 120, None)*2):
                state = root/f'sink-{index}.json'
                sink = subprocess.Popen([sys.executable, str(Path(__file__).with_name('rofi_input_sink.py')), str(state)],
                                        env={**os.environ, 'GDK_BACKEND': 'wayland'}, stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL)
                process: subprocess.Popen[str] | None = None
                runtime = root/f'runtime-{index}'
                try:
                    deadline = time.monotonic()+5
                    while time.monotonic()<deadline:
                        clients = json.loads(command('hyprctl', '-j', 'clients'))
                        if state.exists() and any(row['pid']==sink.pid for row in clients):
                            break
                        self.assertIsNone(sink.poll(), 'Owned GTK sink exited')
                        time.sleep(.01)
                    else:
                        self.fail('Owned GTK sink did not map')
                    command('hyprctl', 'eval', f'for _, w in ipairs(hl.get_windows()) do if w.pid == {sink.pid} then hl.dispatch(hl.dsp.focus({{window=w}})); break end end')
                    self.assertEqual(json.loads(command('hyprctl', '-j', 'activewindow'))['pid'], sink.pid)
                    original_cursor = json.loads(command('hyprctl', '-j', 'cursorpos'))
                    trace = root/f'trace-{index}.log'
                    capture = root/f'copied-{index}'
                    env = {**os.environ, 'PATH': f'{binary}:/usr/bin:/bin', 'CAPTURE_COPY': str(capture),
                           'ROFI_HYPRLAND_RUNTIME': str(runtime), 'WAYLAND_DEBUG': 'client',
                           'XDG_DATA_HOME': str(root/'data'), 'XDG_DATA_DIRS': str(root/'empty')}
                    with trace.open('w') as log:
                        start = time.monotonic()
                        process = subprocess.Popen([str(Path.home()/'.local/bin/rofi-trial'), 'apps'], env=env,
                                                   stdout=subprocess.PIPE, stderr=log, text=True)
                        focus_ms: float | None = None
                        typed_ms: float | None = None
                        typer: subprocess.Popen[bytes] | None = None
                        while time.monotonic()-start < 6:
                            if focus_ms is None and focused(trace):
                                focus_ms = (time.monotonic()-start)*1000
                            elapsed = (time.monotonic()-start)*1000
                            if typer is None and ((delay is None and focus_ms is not None)
                                                 or (delay is not None and elapsed >= delay)):
                                if delay is None:
                                    monitors = json.loads(command('hyprctl', '-j', 'monitors'))
                                    other = next(row for row in monitors if not row['focused'])
                                    x, y = int(other['x']+other['width']/other['scale']/2), int(other['y']+other['height']/other['scale']/2)
                                    command('hyprctl', 'dispatch', f'hl.dsp.cursor.move({{x={x},y={y}}})')
                                    self.assertTrue(focused(trace), 'Pointer movement stole keyboard focus')
                                typed_ms = elapsed
                                typer = subprocess.Popen(['wtype', EXPRESSION])
                            if focus_ms is not None and typer is not None and typer.poll() is not None:
                                self.assertEqual(typer.returncode, 0)
                                break
                            self.assertIsNone(process.poll(), 'Picker exited before input focus')
                            time.sleep(.002)
                        self.assertIsNotNone(focus_ms, 'No observed keyboard-enter event')
                        time.sleep(.4)  # Let the synthetic calculation finish before Return.
                        self.assertTrue(focused(trace), 'Focus changed; do not send Return')
                        self.assertFalse(json.loads(state.read_text())['unexpected_input'], 'Operator intervened; abort without recording text')
                        subprocess.run(['wtype', '-k', 'Return'], check=True)
                        try:
                            process.communicate(timeout=1)
                        except subprocess.TimeoutExpired:
                            cancel(runtime)
                            process.communicate(timeout=3)
                        value = capture.read_text() if capture.exists() else None
                        record = {'sample': index, 'requested_delay_ms': delay,
                                  'focus_observed_ms': round(focus_ms or 0, 1),
                                  'typing_requested_ms': round(typed_ms or 0, 1),
                                  'synthetic_sink_prefix': json.loads(state.read_text())['prefix'],
                                  'result': value, 'all_characters_received': value=='1111111110',
                                  'real_clipboard_untouched': True, 'virtual_keyboard_test': True}
                        results.append(record)
                        print(json.dumps(record), flush=True)
                        if delay is None:
                            self.assertEqual(value, '1111111110', 'Post-focus input lost a character')
                        command('hyprctl', 'dispatch', f'hl.dsp.cursor.move({{x={original_cursor["x"]},y={original_cursor["y"]}}})')
                finally:
                    if process is not None and process.poll() is None:
                        cancel(runtime)
                        process.communicate(timeout=3)
                    sink.terminate()
                    sink.wait(timeout=3)
                    report = Path(os.environ.get('ROFI_INPUT_RESULTS', '/tmp/opencode/rofi-input-results.json'))
                    report.write_text(json.dumps(results, indent=2)+'\n')


if __name__ == '__main__':
    unittest.main(verbosity=2)
