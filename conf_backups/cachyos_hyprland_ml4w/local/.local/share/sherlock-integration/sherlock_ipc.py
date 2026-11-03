from __future__ import annotations

import os
import json
import fcntl
from pathlib import Path
import socket
import struct
import subprocess
import sys
import time


def wait_ready(path: str, expected_pid: int, timeout: float = 15) -> None:
    deadline = time.monotonic()+timeout
    while True:
        with socket.socket(socket.AF_UNIX) as connection:
            connection.settimeout(.1)
            try:
                connection.connect(path)
            except OSError as error:
                if time.monotonic() >= deadline:
                    raise TimeoutError('Sherlock IPC did not become ready') from error
                time.sleep(.025)
                continue
            pid, uid, _gid = struct.unpack('3i', connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            if pid != expected_pid or uid != os.getuid():
                raise PermissionError('Unexpected Sherlock IPC owner')
            return


def send_request(path: str, expected_pid: int, request: dict[str, object]) -> None:
    payload = json.dumps(request).encode()
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(2)
        connection.connect(path)
        pid, uid, _gid = struct.unpack('3i', connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        if pid != expected_pid or uid != os.getuid():
            raise PermissionError('Unexpected Sherlock IPC owner')
        connection.sendall(struct.pack('>I', len(payload))+payload)


def restart_daemon() -> int:
    # Intentional mode switches must not count as a rapid crash/restart loop.
    subprocess.run(['systemctl', '--user', 'reset-failed', 'sherlock.service'], check=True, timeout=5)
    subprocess.run(['systemctl', '--user', 'restart', 'sherlock.service'], check=True, timeout=30)
    return int(Path('/tmp/sherlock.lock').read_text())


def control_request(mode: str, path: str, expected_pid: int | None, runtime: Path) -> None:
    runtime.mkdir(mode=0o700, exist_ok=True)
    if runtime.is_symlink() or runtime.stat().st_uid != os.getuid():
        raise PermissionError('Unexpected Sherlock runtime owner')
    runtime.chmod(0o700)
    with (runtime/'mode.lock').open('a') as lock:
        # Serialize the cache decision as well as the send, including rapid presses.
        fcntl.flock(lock, fcntl.LOCK_EX)
        if expected_pid is None:
            expected_pid = int(Path(path).with_name('sherlock.lock').read_text())
        if mode == 'close':
            send_request(path, expected_pid, {'settings': ['Close']})
            return
        marker = runtime/'mode.json'
        try:
            previous = json.loads(marker.read_text())
        except (OSError, ValueError):
            previous = {}
        if not isinstance(previous, dict):
            previous = {}

        current = previous.get('mode') if previous.get('pid') == expected_pid else 'fresh'
        loaded_mode = mode
        if mode == 'invalidate':
            loaded_mode = 'clipboard'
        elif mode == 'reset':
            # A newer app/emoji request may already have replaced the history UI.
            if current != 'clipboard':
                return
            expected_pid = restart_daemon()
            loaded_mode = 'fresh'
        elif mode == 'apps' and current == 'apps':
            # Re-populating the live model on every hotkey can spin GTK permanently.
            send_request(path, expected_pid, {'Show': 'all'})
        else:
            submenu = {'apps': 'all', 'emoji': 'emoji'}[mode]
            if current != 'fresh':
                if current == 'clipboard':
                    # Let the waiting native selection client receive cancellation first.
                    send_request(path, expected_pid, {'settings': ['Close']})
                    with (runtime/'clipboard.lock').open('a') as selection_lock:
                        deadline = time.monotonic()+2
                        while True:
                            try:
                                fcntl.flock(selection_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                                break
                            except BlockingIOError:
                                if time.monotonic() >= deadline:
                                    raise TimeoutError('Clipboard selection did not close')
                                time.sleep(.025)
                expected_pid = restart_daemon()
            # Never repeatedly rebuild models in one process: native hot reload can spin GTK.
            send_request(path, expected_pid,
                         {'settings': ['Close', {'Show': submenu}, {'SwitchMode': 'Search'}]})
        marker.write_text(json.dumps({'pid': expected_pid, 'mode': loaded_mode})+'\n')


if __name__ == '__main__':
    if sys.argv[1] in ('show', 'reset', 'invalidate', 'close'):
        mode = sys.argv[2] if sys.argv[1] == 'show' else sys.argv[1]
        owner = int(sys.argv[2]) if mode == 'close' else None
        control_request(mode, '/tmp/sherlock_daemon.sock', owner,
                        Path(os.environ['XDG_RUNTIME_DIR'])/'sherlock-launch')
    else:
        wait_ready(sys.argv[1], int(sys.argv[2]))
