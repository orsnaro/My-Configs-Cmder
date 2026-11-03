"""Hand only sanitized local previews to the normal desktop's HTTPS browser."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
import argparse
import json
import math
import os
import re
import subprocess
import sys
import time

from preview_files import HEX_ID, NAMESPACE, PAGES, PreviewContext, validate_preview_path


DESKTOP_PREFIX = 'GLAZE_MAIL_DESKTOP_'
XDG_DEFAULTS = {'CONFIG': '.config', 'DATA': '.local/share', 'CACHE': '.cache', 'STATE': '.local/state'}
DESKTOP_KEYS = ('WAYLAND_DISPLAY', 'DISPLAY', 'XDG_RUNTIME_DIR', 'DBUS_SESSION_BUS_ADDRESS',
                'LANG', 'LC_ALL', 'LC_CTYPE', 'XDG_CURRENT_DESKTOP', 'XDG_SESSION_TYPE',
                'XDG_SESSION_DESKTOP', 'HYPRLAND_INSTANCE_SIGNATURE', 'USER', 'LOGNAME')


def _single_line(value: str) -> str:
    if not value or any(c in value for c in '\x00\r\n'):
        raise ValueError('Invalid desktop environment value')
    return value


def _absolute(value: str) -> str:
    _single_line(value)
    path = Path(value)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('Desktop paths must be absolute')
    return value


def capture_desktop_paths(environ: Mapping[str, str], home: Path) -> dict[str, str]:
    _absolute(str(home))
    return {f'XDG_{key}_HOME': _absolute(environ.get(f'XDG_{key}_HOME', str(home / suffix)))
            for key, suffix in XDG_DEFAULTS.items()}


def desktop_environment(environ: Mapping[str, str]) -> dict[str, str]:
    result = {key: _single_line(environ[key]) for key in DESKTOP_KEYS if environ.get(key)}
    result['HOME'] = _absolute(environ.get('HOME', str(Path.home())))
    result['PATH'] = '/usr/local/bin:/usr/bin:/bin'
    for key in XDG_DEFAULTS:
        name = f'XDG_{key}_HOME'
        if DESKTOP_PREFIX + name not in environ:
            raise ValueError('Normal desktop context is missing; reopen mail after setup')
        result[name] = _absolute(environ[DESKTOP_PREFIX + name])
    if not result.get('XDG_RUNTIME_DIR') or not result.get('DBUS_SESSION_BUS_ADDRESS'):
        raise ValueError('Desktop runtime or bus is unavailable')
    return result


def build_browser_command(path: Path, context: PreviewContext, environ: Mapping[str, str]) -> list[str]:
    validate_preview_path(path, context)
    environment = desktop_environment(environ)
    if Path(environment['XDG_RUNTIME_DIR']) != context.runtime_dir:
        raise ValueError('Desktop runtime does not match preview ownership')
    command = ['/usr/bin/systemd-run', '--user', '--collect', '--service-type=exec',
               '--unit=glaze-mail-browser-' + path.parent.name,
               '--property=ExitType=cgroup', '--property=Restart=no']
    command += [f'--setenv={key}={value}' for key, value in sorted(environment.items())]
    return [*command, '--', sys.executable, str(Path(__file__).resolve()), 'open', str(path),
            '--runtime', str(context.runtime_dir), '--mail-invocation', context.invocation_id,
            '--mail-unit', context.unit_name]


def launch_preview(path: Path, context: PreviewContext) -> None:
    subprocess.run(build_browser_command(path, context, os.environ), shell=False, check=True,
                   timeout=15, capture_output=True)


def app_browser(browser: Any, path: Path) -> Any:
    import gi
    gi.require_version('GioUnix', '2.0')
    from gi.repository import GioUnix, GLib

    # Empty launch URIs remove the original %U; %% preserves URI escapes in Exec.
    app_argument = '"--app=' + path.as_uri().replace('%', '%%') + '"'
    entry = GLib.KeyFile()
    for key, value in {'Type': 'Application', 'Name': 'aerc Mail preview',
                       'Exec': browser.get_commandline() + ' ' + app_argument}.items():
        entry.set_string('Desktop Entry', key, value)
    result = GioUnix.DesktopAppInfo.new_from_keyfile(entry)
    if result is None:
        raise ValueError('Browser does not support a separate preview window')
    return result


def window_clients() -> list[dict[str, Any]]:
    result = subprocess.run(['/usr/bin/hyprctl', 'clients', '-j'], capture_output=True,
                            text=True, check=True, timeout=2)
    clients = json.loads(result.stdout)
    if not isinstance(clients, list) or any(not isinstance(client, dict) for client in clients):
        raise ValueError('Invalid compositor window data')
    return clients


def workspace_snapshot(context: PreviewContext) -> tuple[int, set[str], str] | None:
    try:
        result = subprocess.run(['/usr/bin/systemctl', '--user', 'show', context.unit_name,
                                 '--property=MainPID,InvocationID,ActiveState'],
                                capture_output=True, text=True, check=True, timeout=2)
        values = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
        if values.get('ActiveState') != 'active' or values.get('InvocationID') != context.invocation_id:
            return None
        clients = window_clients()
        mail = [c for c in clients if c.get('class') == 'aerc-mail' and str(c.get('pid')) == values.get('MainPID')]
        if len(mail) != 1:
            return None
        workspace = mail[0].get('workspace', {}).get('id')
        address = mail[0].get('address', '')
        if (type(workspace) is not int or not 1 <= workspace <= 2147483647 or
                not isinstance(address, str) or not re.fullmatch(r'0x[0-9a-fA-F]+', address)):
            return None
        return workspace, {c['address'] for c in clients if isinstance(c.get('address'), str)}, address
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def prepare_preview(path: Path, target: tuple[int, set[str], str]) -> bool:
    workspace, previous, mail_address = target
    if (type(workspace) is not int or not 1 <= workspace <= 2147483647 or
            mail_address not in previous or not re.fullmatch(r'0x[0-9a-fA-F]+', mail_address) or
            not HEX_ID.fullmatch(path.parent.name) or not HEX_ID.fullmatch(path.parent.parent.name) or
            path.parent.parent.parent.name != NAMESPACE or path.name not in PAGES):
        return False
    script = Path(__file__).with_name('preview_startup.lua').resolve()
    code = (f'(assert(loadfile({json.dumps(str(script))})))()('
            f'{{ workspace = {workspace}, mail_address = "{mail_address}", '
            f'invocation = "{path.parent.parent.name}" }})')
    try:
        result = subprocess.run(['/usr/bin/hyprctl', 'eval', code], capture_output=True,
                                text=True, check=True, timeout=2)
        return result.stdout.strip() == 'ok'
    except (OSError, subprocess.SubprocessError):
        return False


def _window_box(window: dict[str, Any]) -> tuple[float, float, float, float]:
    values = [*window['at'], *window['size']]
    if (len(values) != 4 or any(type(value) not in (int, float) or not math.isfinite(value) for value in values)
            or values[2] <= 0 or values[3] <= 0):
        raise ValueError('Invalid compositor window geometry')
    return values[0], values[1], values[2], values[3]


def place_preview(path: Path, target: tuple[int, set[str], str]) -> bool:
    """Verify startup placement without moving or changing any mapped window."""
    workspace, previous, mail_address = target
    if (type(workspace) is not int or not 1 <= workspace <= 2147483647 or
            mail_address not in previous or not re.fullmatch(r'0x[0-9a-fA-F]+', mail_address)):
        return False
    marker = 'aerc Mail preview ' + path.parent.name
    deadline = time.monotonic() + 8
    address: str | None = None
    stable_since: float | None = None
    try:
        while time.monotonic() < deadline:
            clients = window_clients()
            mail = next((c for c in clients if c.get('address') == mail_address and
                         c.get('class') == 'aerc-mail' and c.get('workspace', {}).get('id') == workspace), None)
            if mail is None:
                return False
            matches = [c for c in clients if isinstance(c.get('class'), str) and c['class'].startswith('brave-') and
                       '_' + path.parent.name + '_' + path.name + '-' in c['class'] and
                       c.get('title') in (marker, marker + ' - Brave') and
                       isinstance(c.get('address'), str) and c['address'] not in previous and
                       re.fullmatch(r'0x[0-9a-fA-F]+', c['address'])]
            if len(matches) > 1:
                return False
            if matches:
                window = matches[0]
                if address is not None and window['address'] != address:
                    return False
                address = window['address']
                if (window.get('fullscreen') or window.get('fullscreenClient') or window.get('floating') or
                        mail.get('floating') or window.get('workspace', {}).get('id') != workspace):
                    return False
                mx, my, mw, mh = _window_box(mail)
                px, py, _, ph = _window_box(window)
                if px < mx + mw - 2 or min(my + mh, py + ph) <= max(my, py):
                    return False
                # Confirm the tiled relationship survives compositor/client state updates.
                now = time.monotonic()
                if stable_since is None:
                    stable_since = now
                elif now - stable_since >= .35:
                    return True
            else:
                stable_since = None
            time.sleep(.05)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        return False
    return False


def open_in_desktop(path: Path, context: PreviewContext) -> None:
    validate_preview_path(path, context)
    # This broker starts with restored XDG paths; importing GIO earlier can cache isolated defaults.
    import gi
    gi.require_version('Gio', '2.0')
    from gi.repository import Gio

    browser = Gio.AppInfo.get_default_for_uri_scheme('https')
    if browser is None:
        raise ValueError('No normal HTTPS browser is configured')
    separate = browser.get_id() == 'brave-browser.desktop'
    target = workspace_snapshot(context) if separate else None
    if separate:
        if target is None or not prepare_preview(path, target):
            raise ValueError('Preview startup placement is unavailable')
        browser = app_browser(browser, path)
    if not browser.launch_uris([] if separate else [path.as_uri()], None):
        raise ValueError('Normal browser launch failed')
    if separate and (target is None or not place_preview(path, target)):
        subprocess.run(['/usr/bin/notify-send', '-a', 'aerc-mail', '-t', '6000', 'aerc Mail',
                        'Preview opened, but its initial right-side placement could not be verified.'],
                       capture_output=True, check=False, timeout=5)


def report_failure() -> None:
    print('HTML preview could not open in the default browser.', file=sys.stderr)
    try:
        subprocess.run(['/usr/bin/notify-send', '-a', 'aerc-mail', '-i', 'internet-mail', '-t', '6000',
                        'aerc Mail', 'HTML preview could not open in the default browser.'],
                       capture_output=True, check=False, timeout=5)
    except (OSError, subprocess.SubprocessError):
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('open',))
    parser.add_argument('path', type=Path)
    parser.add_argument('--runtime', required=True, type=Path)
    parser.add_argument('--mail-invocation', required=True)
    parser.add_argument('--mail-unit', required=True)
    args = parser.parse_args(argv)
    try:
        open_in_desktop(args.path, PreviewContext(args.runtime, args.mail_invocation, args.mail_unit))
        return 0
    except Exception:
        report_failure()
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
