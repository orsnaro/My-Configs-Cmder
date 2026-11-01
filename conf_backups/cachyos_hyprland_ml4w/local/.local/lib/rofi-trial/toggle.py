#!/usr/bin/env python
"""Toggle only this launcher's identity-checked Wayland Rofi instance."""
from __future__ import annotations

import os
import json
import signal
import subprocess
import sys
import time
from pathlib import Path


def main(mode: str) -> int:
    runtime = Path(os.environ.get('ROFI_HYPRLAND_RUNTIME',
                   str(Path(os.environ.get('XDG_RUNTIME_DIR', str(Path.home()/'.cache'))) / 'rofi-hyprland')))
    runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
    if runtime.stat().st_uid != os.getuid() or runtime.stat().st_mode & 0o077:
        raise ValueError(f'Launcher runtime directory is not private: {runtime}')
    pidfile = runtime / 'rofi.pid'
    modefile = runtime / 'mode'
    if pidfile.is_file():
        value = pidfile.read_text().strip()
        if value.isascii() and value.isdecimal():
            pid = int(value)
            proc = Path('/proc') / value
            descriptor: int | None = None
            try:
                descriptor = os.pidfd_open(pid)
                command = (proc/'cmdline').read_bytes().decode(errors='replace').strip('\0').split('\0')
                executable = Path(os.readlink(proc/'exe')).name
                if proc.stat().st_uid != os.getuid() or executable != 'rofi' or '-pid' not in command or str(pidfile) not in command:
                    raise ValueError('Launcher PID file refers to another process; refusing to signal it')
                same_mode = modefile.is_file() and modefile.read_text().strip() == mode
                signal.pidfd_send_signal(descriptor, signal.SIGTERM)
                deadline = time.monotonic()+4
                while (proc/'exe').exists() and time.monotonic()<deadline:
                    time.sleep(0.02)
                if (proc/'exe').exists():
                    raise ValueError('Existing launcher did not close')
                if same_mode:
                    return 0
            except ProcessLookupError:
                pass
            except FileNotFoundError:
                pass
            finally:
                if descriptor is not None:
                    os.close(descriptor)
    result = subprocess.run(['hyprctl', '-j', 'monitors'], capture_output=True, text=True, timeout=3, check=True)
    monitors = json.loads(result.stdout)
    monitor = next((row.get('name') for row in monitors if row.get('focused') is True), None)
    if not isinstance(monitor, str) or not monitor:
        raise ValueError('Cannot determine the focused Hyprland monitor')
    (runtime/'monitor').write_text(monitor+'\n')
    modefile.write_text(mode+'\n')
    print(pidfile)
    return 10  # A new view should be launched; no daemon is retained.


if __name__ == '__main__':
    try:
        raise SystemExit(main(sys.argv[1]))
    except (OSError, ValueError, IndexError, subprocess.SubprocessError) as error:
        print(f'Launcher toggle: {error}', file=sys.stderr)
        raise SystemExit(2)
