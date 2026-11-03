from __future__ import annotations

import os
import json
from pathlib import Path
import socket
import struct
import tempfile
import unittest
from unittest.mock import call, patch
from concurrent.futures import ThreadPoolExecutor

import sherlock_ipc
from sherlock_ipc import send_request, wait_ready


class ReadyTests(unittest.TestCase):
    def test_intentional_mode_restart_does_not_trip_crash_start_limit(self) -> None:
        with patch('sherlock_ipc.subprocess.run') as run, patch.object(Path, 'read_text', return_value='4321'):
            self.assertEqual(sherlock_ipc.restart_daemon(), 4321)
        self.assertEqual(run.call_args_list, [
            call(['systemctl', '--user', 'reset-failed', 'sherlock.service'], check=True, timeout=5),
            call(['systemctl', '--user', 'restart', 'sherlock.service'], check=True, timeout=30),
        ])

    def test_control_request_has_native_length_framing(self) -> None:
        with tempfile.TemporaryDirectory(prefix='sherlock-ipc-') as name:
            path = str(Path(name)/'daemon.sock')
            with socket.socket(socket.AF_UNIX) as server:
                server.bind(path)
                server.listen()
                request = {'settings': ['Close', {'Show': 'all'}, {'SwitchMode': 'Search'}]}
                send_request(path, os.getpid(), request)
                with server.accept()[0] as connection:
                    connection.settimeout(1)
                    size = struct.unpack('>I', connection.recv(4))[0]
                    self.assertEqual(json.loads(connection.recv(size)), request)

    def test_accepts_an_owned_listening_daemon(self) -> None:
        with tempfile.TemporaryDirectory(prefix='sherlock-ready-') as name:
            path = str(Path(name)/'daemon.sock')
            with socket.socket(socket.AF_UNIX) as server:
                server.bind(path)
                server.listen()
                self.assertIsNone(wait_ready(path, os.getpid(), .1))

    def test_missing_socket_times_out(self) -> None:
        with tempfile.TemporaryDirectory(prefix='sherlock-ready-') as name:
            with self.assertRaises(TimeoutError):
                wait_ready(str(Path(name)/'absent.sock'), os.getpid(), .01)

    def test_stale_socket_times_out(self) -> None:
        with tempfile.TemporaryDirectory(prefix='sherlock-ready-') as name:
            path = str(Path(name)/'stale.sock')
            with socket.socket(socket.AF_UNIX) as server:
                server.bind(path)
            with self.assertRaises(TimeoutError):
                wait_ready(path, os.getpid(), .01)

    def test_unexpected_server_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix='sherlock-ready-') as name:
            path = str(Path(name)/'wrong.sock')
            with socket.socket(socket.AF_UNIX) as server:
                server.bind(path)
                server.listen()
                with self.assertRaises(PermissionError):
                    wait_ready(path, os.getpid()+1, .1)


class ModeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix='sherlock-mode-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.runtime = self.root/'runtime'
        self.runtime.mkdir(mode=0o700)
        self.path = str(self.root/'daemon.sock')
        self.server = socket.socket(socket.AF_UNIX)
        self.addCleanup(self.server.close)
        self.server.bind(self.path)
        self.server.listen(16)
        self.server.settimeout(1)
        self.restart = patch('sherlock_ipc.restart_daemon', create=True, return_value=os.getpid()).start()
        self.addCleanup(patch.stopall)

    def control(self, mode: str) -> None:
        function = getattr(sherlock_ipc, 'control_request', None)
        self.assertTrue(callable(function), 'Missing mode-aware control transaction')
        function(mode, self.path, os.getpid(), self.runtime)

    def receive(self) -> object:
        with self.server.accept()[0] as connection:
            connection.settimeout(1)
            size = struct.unpack('>I', connection.recv(4))[0]
            data = b''
            while len(data) < size:
                data += connection.recv(size-len(data))
            return json.loads(data)

    def test_repeated_apps_request_does_not_reload_or_close(self) -> None:
        self.control('apps')
        self.receive()
        self.control('apps')
        self.assertEqual(self.receive(), {'Show': 'all'})

    def test_close_preserves_loaded_apps_without_restart(self) -> None:
        self.control('apps')
        self.receive()
        before = (self.runtime/'mode.json').read_bytes()
        try:
            self.control('close')
        except KeyError:
            self.fail('Missing native Close control branch')
        self.assertEqual(self.receive(), {'settings': ['Close']})
        self.assertEqual((self.runtime/'mode.json').read_bytes(), before)
        self.restart.assert_not_called()
        self.control('apps')
        self.assertEqual(self.receive(), {'Show': 'all'})

    def test_close_does_not_populate_an_unknown_model(self) -> None:
        try:
            self.control('close')
        except KeyError:
            self.fail('Missing native Close control branch')
        self.assertEqual(self.receive(), {'settings': ['Close']})
        self.assertFalse((self.runtime/'mode.json').exists())
        self.restart.assert_not_called()

    def test_close_rejects_a_different_native_peer_pid(self) -> None:
        with self.assertRaises(PermissionError):
            sherlock_ipc.control_request('close', self.path, os.getpid()+1, self.runtime)
        self.restart.assert_not_called()

    def test_concurrent_apps_requests_schedule_only_one_reload(self) -> None:
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(self.control, ['apps']*8))
        requests = [self.receive() for _ in range(8)]
        self.assertEqual(requests.count({'Show': 'all'}), 7)
        self.assertEqual(requests.count({'settings': ['Close', {'Show': 'all'}, {'SwitchMode': 'Search'}]}), 1)
        self.restart.assert_not_called()

    def test_emoji_to_apps_restores_apps_once(self) -> None:
        self.control('emoji')
        self.assertEqual(self.receive(), {'settings': ['Close', {'Show': 'emoji'}, {'SwitchMode': 'Search'}]})
        self.control('apps')
        self.assertEqual(self.receive(), {'settings': ['Close', {'Show': 'all'}, {'SwitchMode': 'Search'}]})
        self.control('apps')
        self.assertEqual(self.receive(), {'Show': 'all'})
        self.assertEqual(self.restart.call_count, 1, 'Switching from emoji must discard the reloaded native model')

    def test_clipboard_invalidation_requires_app_model_restore(self) -> None:
        self.control('apps')
        self.receive()
        self.control('invalidate')
        self.control('apps')
        self.assertEqual(self.receive(), {'settings': ['Close']})
        self.assertEqual(self.receive(), {'settings': ['Close', {'Show': 'all'}, {'SwitchMode': 'Search'}]})
        self.restart.assert_called_once_with()

    def test_hidden_reset_invalidates_the_loaded_mode(self) -> None:
        self.control('apps')
        self.receive()
        self.control('invalidate')
        self.control('reset')
        self.restart.assert_called_once_with()
        self.control('apps')
        self.assertEqual(self.receive(), {'settings': ['Close', {'Show': 'all'}, {'SwitchMode': 'Search'}]})
        self.restart.assert_called_once_with()

    def test_reopening_emoji_restarts_before_rebuilding_grid(self) -> None:
        self.control('emoji')
        self.receive()
        self.control('emoji')
        self.receive()
        self.restart.assert_called_once_with()

    def test_delayed_history_reset_cannot_hide_a_newer_app_open(self) -> None:
        self.control('invalidate')
        self.control('apps')
        self.receive()
        self.receive()
        self.control('reset')
        self.restart.assert_called_once_with()
        self.control('apps')
        self.assertEqual(self.receive(), {'Show': 'all'})

    def test_native_lock_pid_is_read_when_transaction_begins(self) -> None:
        (self.root/'sherlock.lock').write_text(str(os.getpid()))
        sherlock_ipc.control_request('apps', self.path, None, self.runtime)
        self.assertEqual(self.receive(), {'settings': ['Close', {'Show': 'all'}, {'SwitchMode': 'Search'}]})

    def test_old_daemon_pid_cannot_skip_model_restore(self) -> None:
        (self.runtime/'mode.json').write_text(json.dumps({'pid': os.getpid()+1, 'mode': 'apps'}))
        self.control('apps')
        self.assertEqual(self.receive(), {'settings': ['Close', {'Show': 'all'}, {'SwitchMode': 'Search'}]})

    def test_malformed_mode_marker_recovers_safely(self) -> None:
        for content in ('not json', '[]'):
            with self.subTest(content=content):
                (self.runtime/'mode.json').write_text(content)
                self.control('apps')
                self.assertEqual(self.receive(), {'settings': ['Close', {'Show': 'all'}, {'SwitchMode': 'Search'}]})

    def test_failed_send_does_not_cache_a_successful_load(self) -> None:
        self.server.close()
        with self.assertRaises(ConnectionRefusedError):
            self.control('apps')
        self.assertFalse((self.runtime/'mode.json').exists())


if __name__ == '__main__':
    unittest.main()
