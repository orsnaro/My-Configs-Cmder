#!/usr/bin/env python
"""Cliphist 0.7-compatible picker with private image previews."""
from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
import tempfile
from pathlib import Path


def cliphist(*arguments: str) -> list[str]:
    database = os.environ.get('ROFI_TRIAL_CLIPHIST_DB')
    return ['cliphist', *(['-db-path', database] if database else []), *arguments]


def main() -> int:
    history = subprocess.run(cliphist('list'), capture_output=True, text=True, check=False)
    if history.returncode:
        sys.stderr.write(history.stderr)
        return history.returncode
    entries: list[tuple[str, str]] = []
    for line in history.stdout.splitlines():
        identifier, separator, label = line.partition('\t')
        if separator and identifier.isascii() and identifier.isdecimal():
            entries.append((identifier, re.sub(r'[\x00-\x1f\x7f]', ' ', label)))
    parent = Path(os.environ.get('XDG_RUNTIME_DIR', str(Path.home() / '.cache/rofi-trial')))
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='rofi-clipboard-', dir=parent) as temporary:
        rows: list[str] = []
        for identifier, label in entries:
            row = label
            image = re.search(r'\b(png|jpe?g|bmp|gif|webp|tiff?)\b', label, re.IGNORECASE)
            if label.startswith('[[ binary data') and image:
                path = Path(temporary) / f'{identifier}.{image.group(1).lower()}'
                with path.open('wb') as output:
                    decoded = subprocess.run(cliphist('decode', identifier), stdout=output,
                                             stderr=subprocess.DEVNULL, check=False)
                if decoded.returncode == 0 and path.stat().st_size:
                    row += f'\0icon\x1f{path}'
            rows.append(row)
        theme = Path.home() / '.config/rofi/trial/clipboard.rasi'
        pid_args = ['-pid', os.environ['ROFI_HYPRLAND_PID']] if os.environ.get('ROFI_HYPRLAND_PID') else []
        monitor_args = ['-monitor', os.environ['ROFI_HYPRLAND_MONITOR']] if os.environ.get('ROFI_HYPRLAND_MONITOR') else []
        selected = subprocess.run(['rofi', '-config', str(theme), *pid_args, *monitor_args, '-dmenu', '-i',
                                   '-no-custom', '-format', 'i', '-p', 'Clipboard', *sys.argv[1:]],
                                  input='\n'.join(rows), capture_output=True, text=True, check=False)
        if selected.returncode in (1, -signal.SIGTERM, -signal.SIGINT):
            return 0
        if selected.returncode:
            sys.stderr.write(selected.stderr)
            return selected.returncode
        value = selected.stdout.strip()
        if not value.isascii() or not value.isdecimal() or int(value) >= len(entries):
            print('Invalid clipboard selection', file=sys.stderr)
            return 2
        # Decode before invoking wl-copy: a deleted entry must not empty the clipboard.
        decoded = subprocess.run(cliphist('decode', entries[int(value)][0]), capture_output=True, check=False)
        if decoded.returncode:
            sys.stderr.buffer.write(decoded.stderr)
            return decoded.returncode
        return subprocess.run(['wl-copy'], input=decoded.stdout, check=False).returncode


if __name__ == '__main__':
    raise SystemExit(main())
