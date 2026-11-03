from __future__ import annotations

import fcntl
import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name('sherlock-launch')


class LauncherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix='sherlock-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bin = self.root/'.local/bin'
        self.bin.mkdir(parents=True)
        self.runtime = self.root/'runtime'
        self.runtime.mkdir(mode=0o700)
        self.sink = self.root/'clipboard-sink'
        self.sink.write_bytes(b'original clipboard fixture')
        self.reset_marker = self.root/'reset-marker'
        self.env = {**os.environ, 'HOME': str(self.root), 'XDG_RUNTIME_DIR': str(self.runtime),
                    'COPY_SINK': str(self.sink), 'SELECTED': '7\n', 'CLIENT_STATUS': '1',
                    'DECODED_HEX': '68656c6c6f', 'HELPER_STATUS': '0', 'DECODE_STATUS': '0',
                    'RESET_MARKER': str(self.reset_marker), 'INVALIDATE_MARKER': str(self.root/'invalidate-marker')}
        ipc = self.root/'.local/share/sherlock-integration/sherlock_ipc.py'
        ipc.parent.mkdir(parents=True)
        ipc.write_text('import os, sys\nfrom pathlib import Path\nassert sys.argv[1:] in (["reset"],["invalidate"])\nPath(os.environ["RESET_MARKER" if sys.argv[1]=="reset" else "INVALIDATE_MARKER"]).touch()\n')
        self.command('systemctl', 'import sys\nsys.exit(0)\n')
        self.command('sherlock-clp', '''import os, sys
sys.stdout.write('{"settings":[],"elements":[{"title":"synthetic","result":"7"}]}')
sys.exit(int(os.environ['HELPER_STATUS']))
''')
        self.command('sherlock', '''import json, os, sys
data=sys.stdin.read()
if data:
    assert json.loads(data)['elements'][0]['result']=='7'
sys.stdout.write(os.environ['SELECTED'])
sys.exit(int(os.environ['CLIENT_STATUS']))
''')
        self.command('cliphist', '''import os, sys
assert sys.argv[1:]==['decode']
assert sys.stdin.read()=='7'
sys.stdout.buffer.write(bytes.fromhex(os.environ['DECODED_HEX']))
sys.exit(int(os.environ['DECODE_STATUS']))
''')
        self.command('wl-copy', '''import os, sys
from pathlib import Path
Path(os.environ['COPY_SINK']).write_bytes(sys.stdin.buffer.read())
''')

    def command(self, name: str, body: str) -> None:
        path = self.bin/name
        path.write_text('#!/usr/bin/python3\n'+body)
        path.chmod(0o755)

    def launch(self, **environment: str) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(['bash', str(SCRIPT), 'clipboard'], input=b'', capture_output=True,
                              env={**self.env, **environment}, timeout=5)

    def test_native_status_one_still_copies_selected_text(self) -> None:
        result = self.launch()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.sink.read_bytes(), b'hello')

    def test_clipboard_invalidates_cached_mode_before_native_selection(self) -> None:
        self.command('sherlock', '''import os, sys
from pathlib import Path
if not Path(os.environ['INVALIDATE_MARKER']).exists():
    sys.exit(42)
sys.stdout.write('7')
sys.exit(1)
''')
        result = self.launch()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.sink.read_bytes(), b'hello')

    def test_unicode_and_multiline_text_is_byte_exact(self) -> None:
        data = 'مرحبا\nSherlock 👋\n'.encode()
        result = self.launch(DECODED_HEX=data.hex())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.sink.read_bytes(), data)

    def test_binary_data_is_not_put_in_a_shell_variable(self) -> None:
        data = b'\x89PNG\r\n\x1a\n\x00\xff\x00image\x00'
        result = self.launch(DECODED_HEX=data.hex())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.sink.read_bytes(), data)

    def test_cancellation_preserves_clipboard(self) -> None:
        result = self.launch(SELECTED='')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.sink.read_bytes(), b'original clipboard fixture')

    def test_selection_releases_the_history_model(self) -> None:
        result = self.launch()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.reset_marker.exists(), 'History thumbnails were not released')

    def test_cancellation_releases_the_history_model(self) -> None:
        result = self.launch(SELECTED='')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.reset_marker.exists(), 'History thumbnails were not released')

    def test_native_client_lock_is_released_before_mode_reset(self) -> None:
        ipc = self.root/'.local/share/sherlock-integration/sherlock_ipc.py'
        ipc.write_text('''import fcntl, os, sys
from pathlib import Path
if sys.argv[1]=='reset':
    path=Path(os.environ['XDG_RUNTIME_DIR'])/'sherlock-launch/clipboard.lock'
    with path.open('a') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            sys.exit(42)
    Path(os.environ['RESET_MARKER']).touch()
''')
        result = self.launch()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.reset_marker.exists(), 'Native-response lock was still held during service coordination')

    def test_non_numeric_selection_never_executes_or_copies(self) -> None:
        marker = self.root/'must-not-exist'
        result = self.launch(SELECTED=f'7; touch {marker}')
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(marker.exists())
        self.assertEqual(self.sink.read_bytes(), b'original clipboard fixture')

    def test_helper_failure_preserves_clipboard(self) -> None:
        result = self.launch(HELPER_STATUS='7')
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertEqual(self.sink.read_bytes(), b'original clipboard fixture')

    def test_partial_failed_decode_preserves_clipboard(self) -> None:
        result = self.launch(DECODE_STATUS='1')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.sink.read_bytes(), b'original clipboard fixture')

    def test_empty_decode_preserves_clipboard(self) -> None:
        result = self.launch(DECODED_HEX='')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.sink.read_bytes(), b'original clipboard fixture')

    def test_unexpected_client_failure_preserves_clipboard(self) -> None:
        result = self.launch(CLIENT_STATUS='2')
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(self.sink.read_bytes(), b'original clipboard fixture')

    def test_runtime_selection_file_is_removed(self) -> None:
        result = self.launch()
        self.assertEqual(result.returncode, 0, result.stderr)
        files = list((self.runtime/'sherlock-launch').iterdir())
        self.assertEqual([path.name for path in files], ['clipboard.lock'])

    def test_overlapping_clipboard_request_is_ignored(self) -> None:
        directory = self.runtime/'sherlock-launch'
        directory.mkdir(mode=0o700)
        with (directory/'clipboard.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.launch()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.sink.read_bytes(), b'original clipboard fixture')


class UpstreamIntegrationTests(unittest.TestCase):
    def test_real_cliphist_helper_round_trips_text_and_png(self) -> None:
        helper = Path.home()/'.local/bin/sherlock-clp'
        text = 'Sherlock synthetic مرحبا\nsecond line 👋\n'.encode()
        png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a8XcAAAAASUVORK5CYII=')
        with tempfile.TemporaryDirectory(prefix='sherlock-real-test-') as name:
            root = Path(name)
            bin_directory = root/'bin'
            bin_directory.mkdir()
            command = bin_directory/'cliphist'
            command.write_text(f'#!/usr/bin/env bash\nexec /usr/bin/cliphist -db-path "{root}/db" -config-path /dev/null "$@"\n')
            command.chmod(0o755)
            env = {**os.environ, 'PATH': str(bin_directory)+':'+os.environ['PATH']}
            for data in (text, png):
                subprocess.run([str(command), 'store'], input=data, env=env, check=True, capture_output=True)
            response = subprocess.run([str(helper)], env=env, check=True, capture_output=True)
            elements = [item for item in json.loads(response.stdout)['elements'] if item['result']]
            self.assertEqual(len(elements), 2)
            decoded = [subprocess.run([str(command), 'decode'], input=item['result'].encode(),
                                      env=env, check=True, capture_output=True).stdout for item in elements]
            self.assertCountEqual(decoded, [text, png])
            images = [bytes(item['binary']) for item in elements if item['binary']]
            self.assertEqual(images, [png])


if __name__ == '__main__':
    unittest.main()
