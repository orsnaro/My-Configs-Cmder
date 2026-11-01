#!/usr/bin/env python
"""On-demand recursive file-name picker; no index or background process."""
from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(os.environ.get('ROFI_TRIAL_FILE_ROOT', str(Path.home()))).expanduser().resolve()
    if not root.is_dir():
        print(f'File search root is not a directory: {root}', file=sys.stderr)
        return 2
    found = subprocess.run(['fd', '--type', 'f', '--print0', '--color', 'never', '--absolute-path', '.', str(root)],
                           capture_output=True, check=False)
    if found.returncode:
        sys.stderr.buffer.write(found.stderr)
        return found.returncode
    paths = sorted(os.fsdecode(item) for item in found.stdout.split(b'\0') if item)
    labels = [str(Path(path).relative_to(root)).replace('\n', ' ⏎ ').replace('\r', ' ').replace('\t', ' ')
              for path in paths]
    theme = Path.home() / '.config/rofi/trial/base.rasi'
    pid_args = ['-pid', os.environ['ROFI_HYPRLAND_PID']] if os.environ.get('ROFI_HYPRLAND_PID') else []
    monitor_args = ['-monitor', os.environ['ROFI_HYPRLAND_MONITOR']] if os.environ.get('ROFI_HYPRLAND_MONITOR') else []
    selected = subprocess.run(['rofi', '-config', str(theme), *pid_args, *monitor_args, '-dmenu', '-i', '-no-custom',
                               '-format', 'i', '-p', 'Files', *sys.argv[1:]],
                              input='\n'.join(labels), capture_output=True, text=True, check=False)
    if selected.returncode in (1, -signal.SIGTERM, -signal.SIGINT):
        return 0
    if selected.returncode:
        sys.stderr.write(selected.stderr)
        return selected.returncode
    value = selected.stdout.strip()
    if not value.isdecimal() or int(value) >= len(paths):
        print('Invalid file selection', file=sys.stderr)
        return 2
    return subprocess.run(['xdg-open', paths[int(value)]], check=False).returncode


if __name__ == '__main__':
    raise SystemExit(main())
