#!/usr/bin/env python3
"""Mutually exclusive desktop stacks; no resident manager or polling at idle."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

MODES = ('quickshell', 'pleamar')
POLKIT = '/usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1'
QS_UNITS = ('quickshell.service', 'ml4w-dock.service', 'walker.service', 'elephant.service', 'swaync.service', 'waybar.service')


class SwitchError(RuntimeError):
    """A transition failed or could not be performed safely."""


@dataclass(frozen=True)
class Process:
    pid: int
    argv: tuple[str, ...]
    start: str
    ppid: int = 0

    @property
    def name(self) -> str:
        return Path(self.argv[0]).name if self.argv else ''


def read_process(pid: int) -> Process | None:
    """Use UID + start time, not just PID, to avoid signaling a reused process."""
    root = Path('/proc') / str(pid)
    try:
        if root.stat().st_uid != os.getuid() or pid == os.getpid():
            return None
        fields = (root / 'stat').read_text().rsplit(')', 1)[1].split()
        if fields[0] == 'Z':
            return None
        args = tuple(part.decode(errors='surrogateescape') for part in (root / 'cmdline').read_bytes().split(b'\0') if part)
        return Process(pid, args, fields[19], int(fields[1])) if args else None
    except (OSError, ValueError, IndexError):
        return None


def same_process(current: Process | None, original: Process) -> bool:
    # Parentage changes when a keeper exits; UID/start time/argv remain identity.
    return current is not None and (current.pid, current.start, current.argv) == (original.pid, original.start, original.argv)


class Backend:
    """The system boundary, replaceable by a deterministic fixture backend."""
    def __init__(self, home: Path) -> None:
        self.home = home
        self.env = {**os.environ, 'HOME': str(home), 'PATH': f'{home}/.local/bin:{os.environ.get("PATH", "/usr/bin:/bin")}'}
        self.log = home / '.local/state/desktop-stack/operations.log'

    def has_command(self, name: str) -> bool:
        return shutil.which(name, path=self.env['PATH']) is not None

    def validate_context(self) -> None:
        # setsid alone does not escape systemd's service cgroup.
        groups = {part for line in Path('/proc/self/cgroup').read_text().splitlines() for part in line.split('/')}
        if groups.intersection({'pleamar.service', *QS_UNITS}):
            raise SwitchError('Use the application launcher or an external terminal, not a terminal embedded in the stack being stopped')

    def run(self, argv: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(argv, env=self.env, capture_output=True, text=True, timeout=20, check=check)
        except (OSError, subprocess.SubprocessError) as error:
            raise SwitchError(f'Command failed: {argv[0]} {" ".join(argv[1:4])}: {error}') from error

    def spawn(self, argv: list[str], env: dict[str, str] | None = None) -> None:
        self.log.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(self.log, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, 'ab') as output:
            subprocess.Popen(argv, env={**self.env, **(env or {})}, stdin=subprocess.DEVNULL,
                             stdout=output, stderr=output, start_new_session=True, close_fds=True)

    def processes(self) -> list[Process]:
        return [process for path in Path('/proc').iterdir() if path.name.isdigit()
                if (process := read_process(int(path.name))) is not None]

    def signal(self, processes: list[Process], sig: int = signal.SIGTERM) -> None:
        for process in processes:
            if same_process(read_process(process.pid), process):
                try:
                    os.kill(process.pid, sig)
                except ProcessLookupError:
                    pass

    def wait_stopped(self, processes: list[Process]) -> None:
        deadline = time.monotonic() + 4
        while remaining := [p for p in processes if same_process(read_process(p.pid), p)]:
            if time.monotonic() >= deadline:
                self.signal(remaining, signal.SIGKILL)
                for process in remaining:
                    # Reap direct children if this invocation started them.
                    try:
                        os.waitpid(process.pid, os.WNOHANG)
                    except ChildProcessError:
                        pass
                if any(same_process(read_process(p.pid), p) for p in remaining):
                    time.sleep(0.05)
                if any(same_process(read_process(p.pid), p) for p in remaining):
                    raise SwitchError('A desktop process refused to stop')
                return
            time.sleep(0.05)

    def ready(self, mode: str, home: Path) -> bool:
        try:
            if mode == 'pleamar':
                if self.run(['systemctl', '--user', 'is-active', '--quiet', 'pleamar.service'], check=False).returncode:
                    return False
                self.run(['pleamar', '--say', 'vitreus', 'get panel'])
                return self.run(['pleamar', '--say', 'lockscreen', 'get locked']).stdout.strip() in ('true', 'false')
            for config in (home / '.config/quickshell', home / '.local/share/ml4w-dock'):
                result = self.run(['qs', '-p', str(config), 'list', '-j'], check=False)
                if result.returncode or not json.loads(result.stdout):
                    return False
            names = {p.name for p in self.processes()}
            return {'walker', 'elephant', 'swaync', Path(POLKIT).name} <= names
        except (SwitchError, ValueError):
            return False


class StackManager:
    def __init__(self, home: Path, backend: Backend | None = None, *, wait_seconds: float = 25) -> None:
        self.home = home.absolute()
        self.backend = backend or Backend(self.home)
        self.mode_file = self.home / '.config/ml4w/settings/desktop-stack'
        self.state_dir = self.home / '.local/state/desktop-stack'
        self.wait_seconds = wait_seconds

    def selected(self) -> str:
        if not self.mode_file.exists() and not self.mode_file.is_symlink():
            return 'pleamar'
        if self.mode_file.is_symlink():
            raise SwitchError('Mode selection must not be a symlink')
        mode = self.mode_file.read_text().strip()
        if mode not in MODES:
            raise SwitchError(f'Invalid selected desktop stack: {mode!r}')
        return mode

    def write_mode(self, mode: str) -> None:
        if mode not in MODES or self.mode_file.is_symlink():
            raise SwitchError('Invalid mode or mode-file alias')
        self.mode_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.mode_file.parent.resolve().is_relative_to(self.home.resolve()):
            raise SwitchError('Mode directory escapes HOME')
        fd, name = tempfile.mkstemp(prefix='.desktop-stack-', dir=self.mode_file.parent)
        try:
            with os.fdopen(fd, 'w') as handle:
                handle.write(mode + '\n')
            os.replace(name, self.mode_file)
        finally:
            Path(name).unlink(missing_ok=True)

    def log(self, message: str) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(self.state_dir / 'operations.log', os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, 'w') as handle:
            handle.write(time.strftime('%Y-%m-%d %H:%M:%S ') + message + '\n')

    def script(self, process: Process, name: str) -> bool:
        candidates = {str(self.home / '.local/bin' / name),
                      str(self.home / '.config/pleamar/shells/vitreus/bin' / name),
                      str(self.home / '.config/ml4w/scripts' / name),
                      str(self.home / '.config/ml4w/listeners' / name)}
        return any(arg in candidates for arg in process.argv[:3])

    def members(self, mode: str, processes: list[Process]) -> list[Process]:
        if mode == 'pleamar':
            roots = [p for p in processes if p.name == 'pleamar' or any(self.script(p, name) for name in
                     ('vitreus-keep', 'vitreus-polkit-agent', 'vitreus-trial-status', 'vitreus-inhibit'))]
            return self.descendants(roots, processes)
        else:
            roots = [p for p in processes if p.name in {'qs', 'quickshell', 'walker', 'elephant', 'swaync', 'waybar', Path(POLKIT).name}
                     or self.script(p, 'ml4w-wallpaper-automation') or self.script(p, 'ml4w-autostart')]
            # A launcher may be the parent of an ordinary user application.
            # Only the wallpaper loop owns a wholly disposable job subtree.
            loops = [p for p in roots if self.script(p, 'ml4w-wallpaper-automation')]
            owned = {p.pid for p in self.descendants(loops, processes)} | {p.pid for p in roots}
            return [p for p in processes if p.pid in owned]

    @staticmethod
    def descendants(roots: list[Process], processes: list[Process]) -> list[Process]:
        found = {p.pid for p in roots}
        while True:
            expanded = found | {p.pid for p in processes if p.ppid in found}
            if expanded == found:
                return [p for p in processes if p.pid in found]
            found = expanded

    def preflight(self, mode: str) -> None:
        commands = ['systemctl', 'hyprctl', 'pleamar'] if mode == 'pleamar' else ['systemctl', 'hyprctl', 'qs', 'walker', 'elephant', POLKIT]
        files = ['.config/systemd/user/pleamar.service', '.local/bin/pleamar',
                 '.config/pleamar/shells/vitreus/vitreus.plm', '.config/pleamar/shells/vitreus/bin/vitreus-keep',
                 '.config/pleamar/shells/vitreus/lockscreen/lockscreen.plm'] if mode == 'pleamar' else [
                 '.config/quickshell/shell.qml', '.local/share/ml4w-dock/shell.qml', '.config/ml4w/scripts/ml4w-autostart']
        for command in commands:
            if not self.backend.has_command(command):
                raise SwitchError(f'Required command is missing: {command}')
        for name in files:
            if not (self.home / name).is_file():
                raise SwitchError(f'Required configuration is missing: {name}; recover the backup first')

    def unlocked(self) -> None:
        processes = self.backend.processes()
        if any(p.name == 'hyprlock' for p in processes):
            raise SwitchError('Unlock the session before switching desktops')
        if any(p.name == 'pleamar' and any(Path(arg).name == 'lockscreen.plm' for arg in p.argv) for p in processes):
            result = self.backend.run(['pleamar', '--say', 'lockscreen', 'get locked'], check=False)
            if result.returncode or result.stdout.strip() != 'false':
                raise SwitchError('Native lock is active or its state is unavailable; unlock before switching')

    def unit_exists(self, unit: str) -> bool:
        result = self.backend.run(['systemctl', '--user', 'show', unit, '-p', 'LoadState', '--value'], check=False)
        return result.returncode == 0 and result.stdout.strip() not in ('', 'not-found')

    def stop(self, mode: str) -> None:
        processes = self.backend.processes()
        members = self.members(mode, processes)
        night = [p for p in processes if p.name == 'hyprsunset']
        if night:
            self.backend.run(['hyprctl', 'hyprsunset', 'identity'], check=False)
        if mode == 'pleamar':
            keepers = [p for p in members if self.script(p, 'vitreus-keep')]
            self.backend.signal(keepers)
            self.backend.run(['systemctl', '--user', 'stop', 'pleamar.service'])
            self.backend.signal([p for p in members if p not in keepers])
            # A real file in ~/.config/systemd/user cannot be masked in place.
            # Its installed ExecCondition prevents activation in Quickshell mode.
        else:
            # Stop restart owners before their children; retain the slideshow preference.
            owners = [p for p in members if self.script(p, 'ml4w-wallpaper-automation') or self.script(p, 'ml4w-autostart')]
            self.backend.signal(owners)
            for unit in QS_UNITS:
                if self.unit_exists(unit):
                    self.backend.run(['systemctl', '--user', 'stop', unit])
                    self.backend.run(['systemctl', '--user', 'mask', unit])
            self.backend.signal([p for p in members if p not in owners])
        self.backend.signal(night)
        self.backend.wait_stopped(members + night)

    def refresh_listener(self) -> None:
        processes = self.backend.processes()
        listeners = [p for p in processes if self.script(p, 'gtk-theme-switcher.sh')]
        if listeners:
            owned = self.descendants(listeners, processes)
            self.backend.signal(owned)
            self.backend.wait_stopped(owned)
            self.backend.spawn([str(self.home / '.config/ml4w/listeners/gtk-theme-switcher.sh')])

    def start(self, mode: str) -> None:
        self.backend.run(['systemctl', '--user', 'daemon-reload'])
        if mode == 'pleamar':
            self.backend.run(['systemctl', '--user', 'unmask', 'pleamar.service'])
            self.backend.run(['systemctl', '--user', 'start', 'pleamar.service'])
            source = self.home / '.config/pleamar/shells/vitreus'
            self.backend.spawn([str(source / 'bin/vitreus-keep'), str(source / 'lockscreen/lockscreen.plm'),
                                str(self.home / '.local/share/pleamar/vitreus/lockscreen.log')],
                               {'DRI_PRIME': '1', 'VK_DRIVER_FILES': '/usr/share/vulkan/icd.d/radeon_icd.json', 'PLEAMAR_SWAPCHAIN': '1'})
        else:
            for unit in QS_UNITS:
                if self.unit_exists(unit):
                    self.backend.run(['systemctl', '--user', 'unmask', unit])
            self.backend.spawn([str(self.home / '.config/ml4w/scripts/ml4w-autostart')])
            self.backend.spawn(['elephant'])
            self.backend.spawn(['walker', '--gapplication-service'])
            self.backend.run(['systemctl', '--user', 'start', 'swaync.service'])
            self.backend.spawn([POLKIT])

    def wait_ready(self, mode: str) -> None:
        deadline = time.monotonic() + self.wait_seconds
        while not self.backend.ready(mode, self.home):
            if time.monotonic() >= deadline:
                raise SwitchError(f'{mode} did not become ready; inspect {self.state_dir}/operations.log')
            time.sleep(0.2)

    def switch(self, mode: str) -> None:
        if mode not in MODES:
            raise SwitchError('Unknown desktop stack')
        self.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not self.state_dir.resolve().is_relative_to(self.home.resolve()):
            raise SwitchError('State directory escapes HOME')
        with (self.state_dir / 'switch.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise SwitchError('A desktop switch is already running') from error
            previous = self.selected()
            other = 'pleamar' if mode == 'quickshell' else 'quickshell'
            if mode == previous and self.backend.ready(mode, self.home) and not self.members(other, self.backend.processes()):
                return
            self.backend.validate_context()
            self.preflight(mode)
            self.unlocked()
            self.log(f'Switch requested: {previous} -> {mode}')
            try:
                # Guards must see the requested mode during activation. Failure restores it.
                self.write_mode(mode)
                self.stop(other)
                self.refresh_listener()
                self.backend.run(['hyprctl', 'reload'])
                if not self.backend.ready(mode, self.home):
                    self.start(mode)
                self.wait_ready(mode)
                if self.members(other, self.backend.processes()):
                    raise SwitchError('The inactive stack still has running processes')
                self.log(f'Switch complete: {mode}')
            except Exception as error:
                self.log(f'Switch failed: {error}')
                self.write_mode(previous)
                try:
                    self.stop(mode)
                    self.backend.run(['hyprctl', 'reload'])
                    self.start(previous)
                    self.wait_ready(previous)
                except Exception as rollback:
                    self.log(f'Rollback failed: {rollback}')
                    raise SwitchError(f'{error}; rollback failed: {rollback}') from error
                raise SwitchError(f'{error}; previous stack restored') from error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('switch', 'resume', 'is', 'status'))
    parser.add_argument('mode', nargs='?', choices=MODES)
    args = parser.parse_args(argv)
    manager = StackManager(Path.home())
    try:
        if args.action == 'is':
            return 0 if args.mode == manager.selected() else 1
        if args.action == 'status':
            print(json.dumps({'selected': manager.selected(), 'ready': manager.backend.ready(manager.selected(), manager.home)}))
        else:
            if args.action == 'switch' and args.mode is None:
                parser.error('switch requires a mode')
            manager.switch(args.mode if args.action == 'switch' else manager.selected())
        return 0
    except (SwitchError, OSError) as error:
        print(f'Desktop switch failed: {error}', file=sys.stderr)
        if args.action not in ('is', 'status') and manager.backend.has_command('notify-send'):
            manager.backend.run(['notify-send', '-u', 'critical', 'Desktop switch failed', str(error)], check=False)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
