#!/usr/bin/env python3
"""Launch one cgroup-owned aerc evaluation; no persistent launcher process."""
from __future__ import annotations

from pathlib import Path
import argparse
import os
import stat
import subprocess
import sys

from preview_desktop import capture_desktop_paths


CONFIG_DIRECTORY = Path.home()/".config/glaze-mail/eval"
TOKEN_FILE = Path.home()/".local/state/glaze-mail/oauth.json"
KONSOLE_BINARY = Path("/usr/bin/konsole")
SOURCE_DIRECTORY = Path(__file__).resolve().parent
PREVIEW_PYTHON = Path.home()/'.local/share/glaze-mail/preview-venv/bin/python'


def systemd_command(argv: list[str]) -> str:
    if not argv or any(not value or any(c in value for c in '\x00\r\n') for value in argv):
        raise ValueError('Invalid cleanup command')
    # Transient Exec properties preserve %, but still parse quotes and expand environment variables.
    return ' '.join('"' + value.replace('\\', '\\\\').replace('"', '\\"').replace('$', '$$') + '"'
                    for value in argv)


def build_launch_command(aerc_binary: Path, config_directory: Path) -> list[str]:
    if any(not path.is_absolute() or any(c in str(path) for c in "\r\n\x00")
           for path in (aerc_binary, config_directory, KONSOLE_BINARY)):
        raise ValueError("Evaluation paths must be single-line absolute paths")
    desktop_bus = os.environ.get("DBUS_SESSION_BUS_ADDRESS", "")
    if not desktop_bus or any(c in desktop_bus for c in "\r\n\x00"):
        raise ValueError("A valid desktop bus is required for mail notifications")
    terminal = config_directory.parent/"terminal"
    command = [
        "/usr/bin/systemd-run", "--user", "--unit=glaze-mail-eval", "--collect", "--service-type=exec",
        "--property=KillMode=control-group", "--property=Restart=no", "--property=TimeoutStopSec=5s",
    ]
    command.append('--property=ExecStopPost=' + systemd_command([str(PREVIEW_PYTHON), str(SOURCE_DIRECTORY/'preview.py'), 'cleanup']))
    command.append('--setenv=GLAZE_MAIL_SERVICE_UNIT=glaze-mail-eval.service')
    desktop = capture_desktop_paths(os.environ, Path(os.environ.get('HOME', str(Path.home()))))
    command += [f'--setenv=GLAZE_MAIL_DESKTOP_{key}={value}' for key, value in sorted(desktop.items())]
    for name in ("WAYLAND_DISPLAY", "DISPLAY", "XDG_RUNTIME_DIR"):
        value = os.environ.get(name)
        if value:
            if any(c in value for c in "\x00\r\n"):
                raise ValueError("Invalid desktop environment value")
            command.append(f"--setenv={name}={value}")
    # Konsole otherwise moves itself out of the service into a new app scope.
    # Restore the real bus only for aerc and its notification-hook descendants.
    command += ["--setenv=DBUS_SESSION_BUS_ADDRESS=unix:path=/dev/null",
                "--setenv=QT_WAYLAND_DISABLE_WINDOWDECORATION=1"]
    for name in ("CONFIG", "CACHE", "STATE", "DATA"):
        command.append(f"--setenv=XDG_{name}_HOME={terminal/name.lower()}")
    command += ["--", str(KONSOLE_BINARY), "--separate", "--builtin-profile", "--desktopfile", "aerc-mail",
                "--hide-menubar", "--hide-toolbars", "--hide-tabbar"]
    for setting in ("WordMode=true", "BidiRenderingEnabled=true", "BidiLineLTR=true", "BidiTableDirOverride=true",
                    "ScrollBarPosition=2", "HistoryMode=0", "ShowTerminalSizeHint=false", "TerminalMargin=0",
                    "Font=DejaVu Sans Mono,10,-1,5,400,0,0,0,1,0", "ColorScheme=GlazeMail"):
        command += ["-p", setting]
    return [*command, "-e", "/usr/bin/env", f"DBUS_SESSION_BUS_ADDRESS={desktop_bus}", str(aerc_binary), "-I",
            "-C", str(config_directory/"aerc.conf"), "-A", str(config_directory/"accounts.conf")]


def launch(aerc_binary: Path, config_directory: Path, token_file: Path) -> None:
    command = build_launch_command(aerc_binary, config_directory)
    for binary in (aerc_binary, KONSOLE_BINARY):
        if not binary.is_file() or not os.access(binary, os.X_OK):
            raise FileNotFoundError("Mail terminal/runtime is missing or not executable")
    terminal = config_directory.parent/"terminal"
    directories = (terminal, *(terminal/name for name in ("config", "cache", "state", "data", "data/konsole")),
                   config_directory/"stylesets")
    files = (config_directory/"aerc.conf", config_directory/"accounts.conf", config_directory/"lesskey",
             terminal/"config/aerc/binds.conf", token_file,
             terminal/"data/konsole/GlazeMail.colorscheme", config_directory/"stylesets/glaze",
             *(SOURCE_DIRECTORY/name for name in ('preview.py', 'preview_files.py', 'preview_html.py',
                                                  'preview_desktop.py', 'preview_startup.lua')))
    for path in (*directories, *files):
        if any(parent.is_symlink() for parent in (path, *path.parents)):
            raise ValueError("Symlinked mail configuration paths are unsafe")
    if any(path.exists() and not path.is_dir() for path in directories):
        raise ValueError("Mail terminal configuration needs real directories")
    for path in files:
        if path.is_symlink() or not path.is_file():
            raise ValueError("A private mail config, preference, theme or separately authorized token is missing/unsafe")
        info = path.stat()
        if stat.S_IMODE(info.st_mode) != 0o600 or info.st_uid != os.getuid():
            raise ValueError("Mail config, preferences, theme and token must be owner-only files (0600)")
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory.chmod(0o700)
    venv = PREVIEW_PYTHON.parent.parent
    if any(parent.is_symlink() for parent in (venv, *venv.parents)):
        raise ValueError('Unsafe preview runtime directory')
    if not venv.is_dir() or venv.stat().st_uid != os.getuid() or stat.S_IMODE(venv.stat().st_mode) != 0o700:
        raise ValueError('Preview runtime must be private')
    if not (venv/'pyvenv.cfg').is_file() or (venv/'pyvenv.cfg').is_symlink():
        raise ValueError('Preview virtual environment is missing')
    if not PREVIEW_PYTHON.is_file() or not os.access(PREVIEW_PYTHON, os.X_OK):
        raise ValueError('Preview Python is unavailable')
    target = PREVIEW_PYTHON.resolve().stat()
    if target.st_uid not in (0, os.getuid()) or target.st_mode & 0o022:
        raise ValueError('Unsafe preview Python target')
    subprocess.run([str(PREVIEW_PYTHON), '-c',
                    'import nh3, PIL, gi; gi.require_version("Gio", "2.0"); from gi.repository import Gio; '
                    'assert nh3.__version__ == "0.3.7"'],
                   shell=False, check=True, timeout=10, capture_output=True)
    subprocess.run(command, shell=False, check=True, timeout=15, capture_output=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aerc-binary", type=Path, default=Path("/usr/bin/aerc"))
    args = parser.parse_args(argv)
    try:
        launch(args.aerc_binary, CONFIG_DIRECTORY, TOKEN_FILE)
        print("Started the owned mail evaluation session; closing its window stops its mail children.")
        return 0
    except (OSError, ValueError, subprocess.SubprocessError):
        print("Mail evaluation did not start: check Konsole/aerc, the desktop bus, private config/theme/token, or an already-running session.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
