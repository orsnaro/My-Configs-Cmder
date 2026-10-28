#!/usr/bin/env python3
"""Preview/install desktop launchers and mode guards, without activating a stack."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if not __package__:
    sys.path.insert(0, str(REPO_ROOT))
from tools.pleamar_migration.snapshot import snapshot, verify_snapshot  # noqa: E402

MARK = 'desktop-stack managed'
MODE_PATH = '.config/ml4w/settings/desktop-stack'
QS_HELPERS = ('ml4w-reload-dock', 'ml4w-toggle-dock', 'ml4w-toggle-dock-autohide',
              'ml4w-reload-statusbar', 'ml4w-toggle-statusbar', 'ml4w-toggle-statusbar-autohide')
SHELL_HELPER = '''# desktop-stack managed: shared mode reader; no resident process.
desktop_stack_is_qs() {
    local selected=pleamar
    if [[ -f "$HOME/.config/ml4w/settings/desktop-stack" ]]; then
        selected=$(<"$HOME/.config/ml4w/settings/desktop-stack")
        selected="${selected#"${selected%%[![:space:]]*}"}"
        selected="${selected%"${selected##*[![:space:]]}"}"
    fi
    [[ "$selected" == quickshell ]]
}
'''
SHELL_SOURCE = '# desktop-stack managed\nsource "$HOME/.config/ml4w/scripts/desktop-stack-mode"\n'
LUA_MODE = '''-- desktop-stack managed: shared display geometry stays independent of the shell.
local desktop_stack_mode = "pleamar"
local desktop_stack_file = io.open(os.getenv("HOME") .. "/.config/ml4w/settings/desktop-stack", "r")
if desktop_stack_file then
    desktop_stack_mode = (desktop_stack_file:read("*a") or ""):match("^%s*(.-)%s*$")
    desktop_stack_file:close()
end
'''
QS_NIGHT = '''if desktop_stack_is_qs; then
    action="${1:-toggle}"
    case "$action" in toggle|on|off|status) ;; *) exit 2 ;; esac
    running=false
    pgrep -u "$(id -u)" -x hyprsunset >/dev/null && running=true
    if [[ "$action" == status ]]; then echo "$running"; exit 0; fi
    if [[ "$action" == off || ( "$action" == toggle && "$running" == true ) ]]; then
        hyprctl hyprsunset identity >/dev/null 2>&1 || true
        pkill -u "$(id -u)" -x hyprsunset 2>/dev/null || true
    elif [[ "$running" == false ]]; then
        hyprsunset >/dev/null 2>&1 &
    fi
    exit 0
fi
'''


class InstallError(RuntimeError):
    """The destination doesn't match the reviewed integration layout."""


def replace(text: str, old: str, new: str, count: int = 1) -> str:
    if text.count(old) != count:
        raise InstallError(f'Unexpected hook layout: expected {count} occurrences of {old!r}')
    return text.replace(old, new)


def shell_prefix(text: str, body: str = '') -> str:
    if not text.startswith('#!'):
        raise InstallError('Expected a shell-script shebang')
    first, rest = text.split('\n', 1)
    return first + '\n' + SHELL_SOURCE + body + rest


def transform(name: str, text: str, home: Path) -> str:
    if MARK in text:
        if name == '.config/hypr/hyprland.lua':
            return text.replace('desktop_stack_file:read("*l")', 'desktop_stack_file:read("*a")')
        return text
    base = Path(name).name
    if name == '.config/hypr/conf/autostart.lua':
        text = replace(text, 'hl.exec_cmd("systemctl --user start pleamar.service")',
                       'hl.exec_cmd(\'"\' .. HOME .. \'/.local/bin/desktop-stack" resume\')')
        lines = text.splitlines(keepends=True)
        indices = [i for i, line in enumerate(lines) if 'lockscreen/lockscreen.plm' in line and not line.lstrip().startswith('--')]
        if len(indices) != 1:
            raise InstallError('Expected exactly one native lock startup hook')
        lines[indices[0]] = '    -- Native lock startup is owned by desktop-stack.\n'
        return '-- ' + MARK + '\n' + ''.join(lines)
    if name == '.config/hypr/hyprland.lua':
        text = replace(text, 'if vitreus_binds then', 'if desktop_stack_mode == "pleamar" and vitreus_binds then')
        for module in ('vitreus_hypr', 'vitreus_colors'):
            call = f'pcall(require, "{module}")'
            text = replace(text, call, f'if desktop_stack_mode == "pleamar" then {call} end')
        return LUA_MODE + text
    if name == '.config/systemd/user/pleamar.service':
        executable = str(home / '.local/bin/desktop-stack').replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%')
        return replace(text, '[Service]\n', f'[Service]\n# {MARK}\nExecCondition="{executable}" is pleamar\n')
    if base == 'ml4w-autostart':
        text = replace(text, 'nm-applet --indicator &', 'if ! pgrep -u "$(id -u)" -x nm-applet >/dev/null; then nm-applet --indicator & fi')
        return shell_prefix(text, 'desktop_stack_is_qs || exit 0\n')
    if base == 'ml4w-wallpaper-automation':
        return shell_prefix(text, 'case "${1:---toggle}" in --start|--toggle) desktop_stack_is_qs || exit 0 ;; esac\n')
    if base == 'ml4w-wallpaper':
        for function in ('waybar', 'quickshell', 'swaync', 'walker'):
            text = replace(text, f'reload_{function}() {{\n', f'reload_{function}() {{\n    desktop_stack_is_qs || return 0\n')
        return shell_prefix(text)
    if base == 'gtk-theme-switcher.sh':
        lines = text.splitlines(keepends=True)
        count = 0
        for i, line in enumerate(lines):
            if line.lstrip().startswith('qs '):
                indent = line[:len(line) - len(line.lstrip())]
                lines[i] = indent + 'if desktop_stack_is_qs; then ' + line.strip() + '; fi\n'
                count += 1
        if count != 4:
            raise InstallError('Expected four GTK Quickshell IPC calls')
        text = ''.join(lines)
        text = replace(text, 'if command -v walker', 'if desktop_stack_is_qs && command -v walker', 2)
        text = replace(text, 'if pgrep -x swaync', 'if desktop_stack_is_qs && pgrep -x swaync', 2)
        pattern = r'(?m)^([ \t]*)(nohup [^\n]*waybar/launch\.sh[^\n]* &)\n[ \t]*disown[ \t]*$'
        text, count = re.subn(pattern, lambda m: m[1] + 'if desktop_stack_is_qs && [[ ! -f "$HOME/.config/ml4w/settings/waybar-disabled" ]]; then\n' + m[1] + '    ' + m[2] + '\n' + m[1] + '    disown\n' + m[1] + 'fi', text)
        if count != 2:
            raise InstallError('Expected two GTK Waybar restart blocks')
        return shell_prefix(text)
    if base == 'ml4w-wallpaper-app':
        return shell_prefix(replace(text, '# Launch wallpaper app\n', '# Launch wallpaper app\ndesktop_stack_is_qs || exit 0\n'))
    if base == 'ml4w-toggle-hyprsunset':
        return shell_prefix(text, QS_NIGHT)
    if base == 'qs-lazy-toggle' or base in QS_HELPERS:
        return shell_prefix(text, 'desktop_stack_is_qs || exit 0\n')
    raise InstallError(f'Unknown integration target: {name}')


def desktop_argument(value: str) -> str:
    escaped = value.replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
    return '"' + escaped + '"'


def state(path: Path) -> tuple[str, str | bytes] | None:
    if path.is_symlink():
        return ('link', os.readlink(path))
    if path.is_file():
        return ('file', path.read_bytes())
    if path.exists():
        raise InstallError(f'Expected file, not directory: {path}')
    return None


def install(home: Path, repo: Path = REPO_ROOT, *, apply: bool = False) -> dict[str, Any]:
    home, repo = home.absolute(), repo.resolve()
    if home.is_symlink() or not home.is_dir():
        raise InstallError('HOME must be a real existing directory')
    targets = ['.config/hypr/conf/autostart.lua', '.config/hypr/hyprland.lua', '.config/systemd/user/pleamar.service',
               '.config/ml4w/scripts/ml4w-autostart', '.config/ml4w/scripts/ml4w-wallpaper',
               '.config/ml4w/scripts/ml4w-wallpaper-automation', '.config/ml4w/scripts/ml4w-wallpaper-app',
               '.config/ml4w/scripts/ml4w-toggle-hyprsunset', '.config/ml4w/listeners/gtk-theme-switcher.sh',
               '.local/bin/qs-lazy-toggle']
    targets += ['.config/ml4w/scripts/' + name for name in QS_HELPERS if (home / '.config/ml4w/scripts' / name).is_file()]
    planned: dict[str, tuple[str, str | bytes]] = {}
    for name in targets:
        path = home / name
        if not path.is_file() or not path.resolve().is_relative_to(home):
            raise InstallError(f'Missing or external integration target: {name}')
        planned[name] = ('file', transform(name, path.read_text(), home).encode())
    planned['.config/ml4w/scripts/desktop-stack-mode'] = ('file', SHELL_HELPER.encode())
    mode = home / MODE_PATH
    if mode.exists():
        if mode.is_symlink() or mode.read_text().strip() not in ('pleamar', 'quickshell'):
            raise InstallError('Invalid existing desktop selection')
    else:
        planned[MODE_PATH] = ('file', b'pleamar\n')
    for command, source in (('desktop-stack', 'desktop_stack.py'), ('switch-to-qs', 'switch-to-qs.sh'), ('switch-to-pleamar', 'switch-to-pleamar.sh')):
        tool = repo / 'tools' / source
        if not tool.is_file():
            raise InstallError(f'Missing tool: {tool}')
        planned['.local/bin/' + command] = ('link', str(tool))
    for mode_name, label in (('qs', 'QS'), ('pleamar', 'Pleamar')):
        planned[f'.local/share/applications/switch-to-{mode_name}.desktop'] = ('file', (
            '[Desktop Entry]\nType=Application\n' + f'Name=Switch to {label}\n'
            + 'Comment=Activate this complete desktop stack and stop the other\n'
            + f'Exec={desktop_argument(str(home / ".local/bin" / ("switch-to-" + mode_name)))}\n'
            + 'Icon=preferences-desktop\nTerminal=false\nCategories=Settings;DesktopSettings;\nStartupNotify=false\n').encode())
    previous = {name: state(home / name) for name in planned}
    changed = {name: wanted for name, wanted in planned.items() if wanted != previous[name]}
    for name in changed:
        if not (home / name).parent.resolve().is_relative_to(home):
            raise InstallError(f'Destination escapes HOME: {name}')
    result: dict[str, Any] = {'applied': apply, 'changed': list(changed), 'checkpoint': None}
    if not apply or not changed:
        return result
    checkpoint = home / '.local/state/desktop-stack' / ('install-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    if not checkpoint.resolve().is_relative_to(home):
        raise InstallError('Checkpoint directory escapes HOME')
    checkpoint.mkdir(parents=True, mode=0o700)
    checkpoint.chmod(0o700)
    sources = [Path(name) for name in changed if previous[name] is not None]
    snapshot(home, sources, checkpoint / 'public', checkpoint / 'private')
    problems = verify_snapshot(checkpoint / 'public') + verify_snapshot(checkpoint / 'private')
    if problems:
        raise InstallError('Install checkpoint failed verification: ' + '; '.join(problems))
    absent = checkpoint / 'previously-absent.json'
    absent.write_text(json.dumps([name for name in changed if previous[name] is None]))
    absent.chmod(0o600)
    for name in changed:
        if state(home / name) != previous[name]:
            raise InstallError(f'Config changed while preparing installation: {name}; checkpoint {checkpoint}')
    for name, (kind, value) in changed.items():
        path = home / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if state(path) != previous[name]:
            raise InstallError(f'Config changed during installation: {name}; checkpoint {checkpoint}')
        if kind == 'link':
            temporary = path.with_name(path.name + '.desktop-stack-new')
            if temporary.exists() or temporary.is_symlink():
                raise InstallError(f'Temporary link already exists: {temporary}')
            temporary.symlink_to(str(value))
            os.replace(temporary, path)
        else:
            destination = path.resolve() if path.is_symlink() else path
            mode_bits = path.stat().st_mode & 0o777 if path.exists() else (0o600 if name == MODE_PATH else 0o644)
            fd, temporary_name = tempfile.mkstemp(prefix='.desktop-stack-', dir=destination.parent)
            try:
                with os.fdopen(fd, 'wb') as handle:
                    handle.write(value if isinstance(value, bytes) else value.encode())
                os.chmod(temporary_name, mode_bits)
                os.replace(temporary_name, destination)
            finally:
                Path(temporary_name).unlink(missing_ok=True)
    result['checkpoint'] = str(checkpoint)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--dry-run', action='store_true')
    modes.add_argument('--apply', action='store_true')
    parser.add_argument('--home', type=Path, default=Path.home())
    args = parser.parse_args(argv)
    try:
        print(json.dumps(install(args.home, apply=args.apply), indent=2))
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f'Installation blocked: {error}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
