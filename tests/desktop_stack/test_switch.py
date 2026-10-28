"""Whole-stack transitions with a deterministic, side-effect-free process backend."""
from __future__ import annotations

import fcntl
from pathlib import Path
import signal
import subprocess
import tempfile
import unittest
from unittest import mock

from tools import desktop_stack as stack


class FakeBackend:
    def __init__(self) -> None:
        self.events: list[tuple[str, ...]] = []
        self.items: list[stack.Process] = []
        self.healthy: set[str] = {'pleamar'}
        self.fail: set[str] = set()
        self.locked = 'false'
        self.missing: set[str] = set()
        self.unsafe_context = False
        self.late_process: stack.Process | None = None
        self.masked: set[str] = set()
        self.dbus_activation_race = False

    def validate_context(self) -> None:
        if self.unsafe_context:
            raise stack.SwitchError('Use the application launcher or an external terminal')

    def has_command(self, name: str) -> bool:
        return name not in self.missing

    def processes(self) -> list[stack.Process]:
        return self.items[:]

    def run(self, argv: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        self.events.append(tuple(argv))
        if argv == ['systemctl', '--user', 'mask', 'pleamar.service']:
            raise stack.SwitchError('Cannot mask an existing user unit file')
        output = ''
        if argv[:3] == ['systemctl', '--user', 'show']:
            output = 'loaded' if argv[3] in {'pleamar.service', 'swaync.service', 'waybar.service'} else 'not-found'
        if argv[:3] == ['systemctl', '--user', 'stop']:
            self.healthy.discard('pleamar' if argv[3] == 'pleamar.service' else 'quickshell')
            if self.dbus_activation_race and argv[3] == 'swaync.service' and argv[3] not in self.masked:
                self.items.append(stack.Process(4243, ('swaync',), 'dbus-restart'))
        if argv[:3] == ['systemctl', '--user', 'mask']:
            self.masked.add(argv[3])
        if argv[:3] == ['systemctl', '--user', 'unmask']:
            self.masked.discard(argv[3])
        if argv[:3] == ['systemctl', '--user', 'start'] and argv[3] == 'pleamar.service':
            if 'pleamar' not in self.fail:
                self.healthy.add('pleamar')
                if self.late_process is not None:
                    self.items.append(self.late_process)
        if '--say' in argv and 'lockscreen' in argv:
            output = self.locked
        return subprocess.CompletedProcess(argv, 0, output, '')

    def spawn(self, argv: list[str], env: dict[str, str] | None = None) -> None:
        self.events.append(('spawn', *argv))
        if argv[0].endswith('ml4w-autostart') and 'quickshell' not in self.fail:
            self.healthy.add('quickshell')

    def signal(self, processes: list[stack.Process], sig: int = signal.SIGTERM) -> None:
        for process in processes:
            self.events.append(('signal', str(process.pid), str(sig)))
        self.items = [item for item in self.items if item not in processes]

    def wait_stopped(self, processes: list[stack.Process]) -> None:
        self.events.append(('wait', *(str(item.pid) for item in processes)))

    def ready(self, mode: str, home: Path) -> bool:
        return mode in self.healthy


class StackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(dir='/tmp/opencode', prefix='stack-test-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.backend = FakeBackend()
        self.manager = stack.StackManager(self.home, self.backend, wait_seconds=0)
        for name in ('.config/quickshell/shell.qml', '.local/share/ml4w-dock/shell.qml',
                     '.config/ml4w/scripts/ml4w-autostart', '.config/systemd/user/pleamar.service',
                     '.local/bin/pleamar', '.config/pleamar/shells/vitreus/vitreus.plm',
                     '.config/pleamar/shells/vitreus/bin/vitreus-keep',
                     '.config/pleamar/shells/vitreus/lockscreen/lockscreen.plm'):
            path = self.home / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture')

    def process(self, pid: int, *args: str, ppid: int = 1) -> stack.Process:
        process = stack.Process(pid, tuple(args), 'start', ppid)
        self.backend.items.append(process)
        return process

    def test_switch_to_qs_stops_keepers_before_scenes_and_remembers(self) -> None:
        keeper = str(self.home / '.local/bin/vitreus-keep')
        self.process(10, '/bin/sh', keeper, 'scene.plm')
        self.process(11, '/home/bin/pleamar', '--scene', 'scene.plm', ppid=10)
        self.process(12, 'ffmpeg', ppid=11)
        self.process(99, 'obsidian')
        self.manager.switch('quickshell')
        self.assertEqual(self.manager.selected(), 'quickshell')
        self.assertLess(self.backend.events.index(('signal', '10', '15')),
                        self.backend.events.index(('systemctl', '--user', 'stop', 'pleamar.service')))
        self.assertIn(('signal', '12', '15'), self.backend.events)
        self.assertNotIn(('signal', '99', '15'), self.backend.events)
        self.assertTrue(any(event[0] == 'spawn' and 'elephant' in event for event in self.backend.events))

    def test_switch_to_pleamar_removes_entire_qs_stack_and_keeps_preference(self) -> None:
        self.manager.write_mode('quickshell')
        self.backend.healthy = {'quickshell'}
        pref = self.home / '.config/ml4w/settings/wallpaper-slideshow'
        pref.write_text('true\n')
        for pid, binary in enumerate(('qs', 'walker', 'elephant', 'swaync', 'waybar'), 10):
            self.process(pid, binary)
        self.process(20, 'bash', str(self.home / '.config/ml4w/scripts/ml4w-wallpaper-automation'), '--start')
        self.process(90, 'awww-daemon')
        self.process(91, 'hypridle')
        self.manager.switch('pleamar')
        self.assertEqual(self.manager.selected(), 'pleamar')
        self.assertEqual(pref.read_text(), 'true\n')
        self.assertEqual({item.pid for item in self.backend.items}, {90, 91})
        self.assertTrue(any('vitreus-keep' in event[1] for event in self.backend.events if event[0] == 'spawn'))

    def test_repeated_healthy_activation_does_not_restart(self) -> None:
        self.manager.switch('pleamar')
        self.assertEqual(self.backend.events, [])

    def test_external_apps_launched_by_walker_are_not_stack_background_jobs(self) -> None:
        self.manager.write_mode('quickshell')
        self.backend.healthy = {'quickshell'}
        self.process(10, 'walker')
        self.process(11, 'obsidian', ppid=10)
        self.process(12, 'kitty', ppid=10)
        self.process(13, 'fish', ppid=12)
        self.manager.switch('pleamar')
        self.assertEqual({p.pid for p in self.backend.items}, {11, 12, 13})

    def test_native_lock_and_unknown_lock_query_refuse_before_stop(self) -> None:
        for value in ('true', '', 'invalid'):
            with self.subTest(value=value):
                self.backend.events.clear()
                self.backend.locked = value
                self.backend.items = []
                self.process(15, 'pleamar', '--scene', str(self.home / '.config/pleamar/shells/vitreus/lockscreen/lockscreen.plm'))
                with self.assertRaises(stack.SwitchError):
                    self.manager.switch('quickshell')
                self.assertFalse(any(event[0] == 'signal' or 'stop' in event for event in self.backend.events))

    def test_hyprlock_refuses_switch(self) -> None:
        self.process(15, 'hyprlock')
        with self.assertRaises(stack.SwitchError):
            self.manager.switch('quickshell')

    def test_missing_dependency_does_not_stop_current_stack(self) -> None:
        self.backend.missing.add('walker')
        with self.assertRaises(stack.SwitchError):
            self.manager.switch('quickshell')
        self.assertEqual(self.backend.events, [])
        self.assertEqual(self.manager.selected(), 'pleamar')

    def test_switch_refuses_to_stop_its_own_managed_service_context(self) -> None:
        self.backend.unsafe_context = True
        with self.assertRaisesRegex(stack.SwitchError, 'external terminal'):
            self.manager.switch('quickshell')
        self.assertEqual(self.backend.events, [])
        self.assertEqual(self.manager.selected(), 'pleamar')

    def test_real_backend_detects_stack_service_cgroups(self) -> None:
        backend = stack.Backend(self.home)
        with mock.patch.object(stack.Path, 'read_text', return_value='0::/user.slice/app.slice/pleamar.service\n'):
            with self.assertRaises(stack.SwitchError):
                backend.validate_context()
        with mock.patch.object(stack.Path, 'read_text', return_value='0::/user.slice/session.slice/wayland-wm@hyprland.desktop.service\n'):
            backend.validate_context()

    def test_startup_failure_rolls_back_selection_and_old_stack(self) -> None:
        self.backend.fail.add('quickshell')
        with self.assertRaisesRegex(stack.SwitchError, 'previous stack restored'):
            self.manager.switch('quickshell')
        self.assertEqual(self.manager.selected(), 'pleamar')
        self.assertIn('pleamar', self.backend.healthy)

    def test_rollback_failure_is_reported(self) -> None:
        self.backend.fail.update(('quickshell', 'pleamar'))
        with self.assertRaisesRegex(stack.SwitchError, 'rollback failed'):
            self.manager.switch('quickshell')
        self.assertEqual(self.manager.selected(), 'pleamar')

    def test_inactive_survivor_error_identifies_the_process(self) -> None:
        self.manager.write_mode('quickshell')
        self.backend.healthy = {'quickshell'}
        self.backend.late_process = stack.Process(4242, ('walker',), 'late')
        with self.assertRaisesRegex(stack.SwitchError, r'walker.*4242'):
            self.manager.switch('pleamar')

    def test_dbus_cannot_reactivate_swaync_between_stop_and_mask(self) -> None:
        self.manager.write_mode('quickshell')
        self.backend.healthy = {'quickshell'}
        self.backend.dbus_activation_race = True
        self.process(10, 'swaync')
        self.manager.switch('pleamar')
        self.assertFalse(self.manager.members('quickshell', self.backend.processes()))
        self.assertEqual(self.manager.selected(), 'pleamar')

    def test_readiness_rejects_notification_owner_from_other_stack(self) -> None:
        backend = stack.Backend(self.home)
        for owner, expected in (('swaync', False), ('pleamar', True), ('', False)):
            with self.subTest(owner=owner):
                def run(argv: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
                    if argv[0] == 'busctl':
                        return subprocess.CompletedProcess(argv, 0 if owner else 1, f'PID=44\nExe=/usr/bin/{owner}\n', '')
                    return subprocess.CompletedProcess(argv, 0, 'false\n', '')
                with mock.patch.object(backend, 'run', side_effect=run):
                    self.assertEqual(backend.ready('pleamar', self.home), expected)

    def test_concurrent_switch_is_rejected(self) -> None:
        self.manager.state_dir.mkdir(parents=True)
        with (self.manager.state_dir / 'switch.lock').open('w') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(stack.SwitchError, 'already'):
                self.manager.switch('quickshell')
        self.assertEqual(self.backend.events, [])

    def test_invalid_mode_fails_closed(self) -> None:
        self.manager.mode_file.parent.mkdir(parents=True, exist_ok=True)
        self.manager.mode_file.write_text('garbage\n')
        with self.assertRaises(stack.SwitchError):
            self.manager.selected()

    def test_process_identity_survives_parent_exit_without_signaling_reused_pid(self) -> None:
        original = stack.Process(1234, ('ffmpeg',), 'start', 22)
        orphan = stack.Process(1234, ('ffmpeg',), 'start', 1)
        backend = stack.Backend(self.home)
        with mock.patch.object(stack, 'read_process', return_value=orphan), mock.patch.object(stack.os, 'kill') as kill:
            backend.signal([original])
            kill.assert_called_once_with(1234, signal.SIGTERM)
        with mock.patch.object(stack, 'read_process', return_value=stack.Process(1234, ('obsidian',), 'new', 1)), mock.patch.object(stack.os, 'kill') as kill:
            backend.signal([original])
            kill.assert_not_called()

    def test_running_gtk_listener_and_owned_pipeline_are_refreshed_only_on_switch(self) -> None:
        script = self.home / '.config/ml4w/listeners/gtk-theme-switcher.sh'
        script.parent.mkdir(parents=True)
        script.write_text('#!/bin/bash\n')
        self.process(60, 'bash', str(script))
        self.process(61, 'inotifywait', ppid=60)
        self.process(62, 'bash', str(self.home / '.config/ml4w/listeners/low-bat-notification.sh'))
        self.manager.switch('quickshell')
        self.assertIn(('signal', '60', '15'), self.backend.events)
        self.assertIn(('signal', '61', '15'), self.backend.events)
        self.assertNotIn(('signal', '62', '15'), self.backend.events)
        self.assertIn(('spawn', str(script)), self.backend.events)


if __name__ == '__main__':
    unittest.main()
