"""Exercise the restore entry point only against tiny isolated snapshot/home fixtures."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'RESTORE.sh'


class RestoreScriptTests(unittest.TestCase):
    def test_export_modes_are_git_checkout_portable(self) -> None:
        manifest = json.loads((SCRIPT.parent / 'manifest.json').read_text())
        for entry in manifest['files']:
            if entry['kind'] == 'file':
                with self.subTest(path=entry['path']):
                    self.assertIn(entry['mode'], {'0644', '0755'},
                                  'Git only stores the executable bit: manifest modes must survive a fresh checkout')

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix='pleamar-restore-test-', dir='/tmp/opencode')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.snapshot = self.root / 'snapshot'
        self.home = self.root / 'home'
        self.snapshot.mkdir()
        self.home.mkdir()
        self.env = {**os.environ, 'HOME': str(self.home), 'TMPDIR': str(self.root)}

    def prepare(self) -> None:
        self.assertTrue(SCRIPT.is_file(), 'Pleamar needs its own safe RESTORE.sh entry point')
        shutil.copy2(SCRIPT, self.snapshot / 'RESTORE.sh')
        files: dict[str, str] = {
            'config/hypr/hyprland.lua': '-- restored fixture\n',
            'config/kitty/kitty.conf': 'font_size 12\n',
            'config/fish/conf.d/20-customization.fish': 'echo screenshot.omp.json\n',
            'config/ohmyposh/screenshot.omp.json': '{"version": 3}\n',
            'config/ml4w/settings/kitty-cursor-trail.conf': 'cursor_trail 1\n',
            'config/ml4w/scripts/desktop-stack-mode': 'desktop_stack_is_qs() { return 1; }\n',
            'source/vitreus/vitreus.plm': '// fixture scene\n',
            'source/vitreus/bin/vitreus-example': '#!/bin/sh\nexit 0\n',
            'data/glass.json': '{"obsidian": true}\n',
            'systemd/pleamar.service': '[Service]\nExecStart=/fixture\n',
            'bin/pleamar-start': '#!/bin/sh\nexit 0\n',
        }
        for name, text in files.items():
            path = self.snapshot / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            path.chmod(0o755 if name.startswith(('bin/', 'source/vitreus/bin/')) else 0o644)
        (self.snapshot / 'source/vitreus/alias.plm').symlink_to('vitreus.plm')
        entries: list[dict[str, object]] = []
        for path in sorted(self.snapshot.rglob('*')):
            if path.is_symlink():
                entries.append({'path': path.relative_to(self.snapshot).as_posix(), 'kind': 'symlink', 'target': os.readlink(path)})
            elif path.is_file():
                entries.append({'path': path.relative_to(self.snapshot).as_posix(), 'kind': 'file', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'mode': '0755' if path.stat().st_mode & 0o100 else '0644', 'size': path.stat().st_size})
        (self.snapshot / 'manifest.json').write_text(json.dumps({'files': entries}))

    def run_restore(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(['bash', str(self.snapshot / 'RESTORE.sh'), *args], env=self.env, capture_output=True, text=True, timeout=20)

    def test_default_and_explicit_preview_do_not_write_to_home(self) -> None:
        self.prepare()
        for args in ((), ('--dry-run',)):
            with self.subTest(args=args):
                result = self.run_restore(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('DRY-RUN', result.stdout)
                self.assertIn('ohmyposh', result.stdout)
                self.assertIn('pleamar.service', result.stdout)
                self.assertEqual(list(self.home.iterdir()), [])

    def test_unknown_or_conflicting_modes_fail_without_writes(self) -> None:
        self.prepare()
        for args in (('--uninstall',), ('--apply', '--dry-run'), ('--apply', '--unknown')):
            with self.subTest(args=args):
                result = self.run_restore(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(list(self.home.iterdir()), [])

    def test_apply_backs_up_and_preserves_root_symlink_and_unrelated_data(self) -> None:
        self.prepare()
        target = self.home / '.mydotfiles/hypr'
        target.mkdir(parents=True)
        (target / 'hyprland.lua').write_text('keep original\n')
        (self.home / '.config').mkdir()
        (self.home / '.config/hypr').symlink_to(target, target_is_directory=True)
        data = self.home / '.local/share/pleamar/vitreus'
        data.mkdir(parents=True)
        (data / 'notification-history.json').write_text('private history stays\n')
        result = self.run_restore('--apply')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.home / '.config/hypr').is_symlink())
        self.assertEqual((target / 'hyprland.lua').read_text(), '-- restored fixture\n')
        self.assertEqual((data / 'notification-history.json').read_text(), 'private history stays\n')
        backup = next((self.home / '.local/state/pleamar-restore').iterdir())
        self.assertEqual(backup.stat().st_mode & 0o777, 0o700)
        self.assertEqual((backup / 'payload/.config/hypr/hyprland.lua').read_text(), 'keep original\n')
        self.assertTrue((backup / 'original/.config/hypr').is_symlink())
        helper = self.home / '.local/bin/vitreus-example'
        self.assertTrue(helper.is_symlink())
        self.assertTrue(os.access(helper, os.X_OK))
        alias = self.home / '.config/pleamar/shells/vitreus/alias.plm'
        self.assertEqual(os.readlink(alias), 'vitreus.plm')

    def test_corrupt_payload_is_rejected_before_any_home_write(self) -> None:
        self.prepare()
        (self.snapshot / 'config/kitty/kitty.conf').write_text('corrupt\n')
        result = self.run_restore('--apply')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('manifest', result.stderr.lower())
        self.assertEqual(list(self.home.iterdir()), [])

    def test_apply_restores_stack_mode_hook_not_only_ml4w_settings(self) -> None:
        self.prepare()
        result = self.run_restore('--apply')
        self.assertEqual(result.returncode, 0, result.stderr)
        helper = self.home / '.config/ml4w/scripts/desktop-stack-mode'
        self.assertTrue(helper.is_file(), 'saved startup/theme guards require their shared mode helper')

    def test_unrecorded_payload_is_rejected(self) -> None:
        self.prepare()
        (self.snapshot / 'config/kitty/unreviewed.conf').write_text('unreviewed\n')
        result = self.run_restore('--apply')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_mode_drift_is_rejected_before_any_home_write(self) -> None:
        self.prepare()
        (self.snapshot / 'bin/pleamar-start').chmod(0o644)
        result = self.run_restore('--apply')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('manifest', result.stderr.lower())
        self.assertEqual(list(self.home.iterdir()), [])

    def test_private_checkout_umask_does_not_break_valid_preview(self) -> None:
        self.prepare()
        for path in self.snapshot.rglob('*'):
            if path.is_file() and not path.is_symlink() and not path.stat().st_mode & 0o100:
                path.chmod(0o600)
        result = self.run_restore('--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('DRY-RUN', result.stdout)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_backup_location_cannot_overlap_a_restored_directory(self) -> None:
        self.prepare()
        target = self.home / '.config/hypr'
        target.mkdir(parents=True)
        (target / 'marker').write_text('untouched\n')
        state = self.home / '.local/state'
        state.mkdir(parents=True)
        (state / 'pleamar-restore').symlink_to(target, target_is_directory=True)
        result = self.run_restore('--dry-run')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(target.iterdir()), [target / 'marker'])

    def test_destination_symlink_escaping_home_is_rejected(self) -> None:
        self.prepare()
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'marker').write_text('untouched\n')
        (self.home / '.config').symlink_to(outside, target_is_directory=True)
        result = self.run_restore('--apply')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(outside.iterdir()), [outside / 'marker'])
        self.assertFalse((self.home / '.local').exists())

    def test_backup_failure_does_not_overwrite_configuration(self) -> None:
        self.prepare()
        dest = self.home / '.config/kitty'
        dest.mkdir(parents=True)
        (dest / 'kitty.conf').write_text('original\n')
        tools = self.root / 'tools'
        tools.mkdir()
        (tools / 'cp').write_text('#!/bin/sh\nexit 71\n')
        (tools / 'cp').chmod(0o755)
        self.env['PATH'] = f'{tools}:{os.environ["PATH"]}'
        result = self.run_restore('--apply')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((dest / 'kitty.conf').read_text(), 'original\n')

    def test_apply_never_invokes_desktop_or_privileged_commands(self) -> None:
        self.prepare()
        tools = self.root / 'tools'
        tools.mkdir()
        log = self.root / 'forbidden.log'
        for command in ('systemctl', 'hyprctl', 'pkill', 'sudo', 'pacman', 'curl', 'git'):
            path = tools / command
            path.write_text(f'#!/bin/sh\necho "{command}" >> "{log}"\nexit 99\n')
            path.chmod(0o755)
        self.env['PATH'] = f'{tools}:{os.environ["PATH"]}'
        result = self.run_restore('--apply')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(log.exists(), 'restore must not restart, uninstall, download or install anything')


if __name__ == '__main__':
    unittest.main()
