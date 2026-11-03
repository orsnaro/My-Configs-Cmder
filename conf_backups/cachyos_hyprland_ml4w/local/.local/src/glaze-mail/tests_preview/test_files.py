from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock
import importlib
import importlib.util
import os
import subprocess
import sys


class FileTests(TestCase):
    def setUp(self) -> None:
        self.assertIsNotNone(importlib.util.find_spec('preview_files'), 'Private preview ownership is missing')
        self.module = importlib.import_module('preview_files')
        self.temp = TemporaryDirectory(prefix='preview-files-', dir='/tmp/opencode')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.context = self.module.PreviewContext(self.root, '1' * 32, 'fixture.service')

    def test_context_rejects_untrusted_ids_paths_and_unit_names(self) -> None:
        valid = {'XDG_RUNTIME_DIR': str(self.root), 'INVOCATION_ID': '1' * 32}
        self.assertEqual(self.module.context_from_environment(valid).unit_name, 'glaze-mail-eval.service')
        for key, value in [('INVOCATION_ID', '../escape'), ('INVOCATION_ID', ''), ('XDG_RUNTIME_DIR', 'relative'),
                           ('GLAZE_MAIL_SERVICE_UNIT', '--unit=escape'), ('GLAZE_MAIL_SERVICE_UNIT', 'bad\n.service')]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.module.context_from_environment(valid | {key: value})
        self.root.chmod(0o755)
        with self.assertRaises(ValueError):
            self.module.context_from_environment(valid)

    def test_preview_files_are_private_and_remain_after_creator_returns(self) -> None:
        path = self.module.create_preview(b'<p>private body</p>', self.context)
        self.assertEqual(path.name, 'blocked.html')
        self.assertRegex(path.parent.name, r'^[0-9a-f]{32}$')
        self.assertTrue(path.is_relative_to(self.root / 'glaze-mail-preview' / ('1' * 32)))
        for file in (path, path.with_name('images.html')):
            self.assertEqual(file.stat().st_mode & 0o777, 0o600)
            self.assertIn('private body', file.read_text())
        for directory in (path.parent, path.parent.parent, path.parent.parent.parent):
            self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
        self.assertEqual(self.module.validate_preview_path(path, self.context), path)

    def test_cleanup_is_idempotent_and_preserves_other_invocations(self) -> None:
        self.module.cleanup(self.context)
        first = self.module.create_preview(b'first', self.context)
        other = self.module.create_preview(b'other', self.module.PreviewContext(self.root, '2' * 32, 'other.service'))
        first.with_name('images.html').unlink()
        self.module.cleanup(self.context)
        self.module.cleanup(self.context)
        self.assertFalse(first.exists())
        self.assertIn('other', other.read_text())

    def test_planted_file_symlink_is_not_followed(self) -> None:
        path = self.module.create_preview(b'body', self.context)
        victim = self.root / 'victim'
        victim.write_text('preserve')
        path.unlink()
        path.symlink_to(victim)
        with self.assertRaises(ValueError):
            self.module.validate_preview_path(path, self.context)
        self.module.cleanup(self.context)
        self.assertEqual(victim.read_text(), 'preserve')

    def test_cleanup_rejects_foreign_entries_or_changed_owner_marker(self) -> None:
        path = self.module.create_preview(b'body', self.context)
        unexpected = path.parent / 'user-work.txt'
        unexpected.write_text('do not delete')
        with self.assertRaises(ValueError):
            self.module.cleanup(self.context)
        self.assertEqual(unexpected.read_text(), 'do not delete')
        unexpected.unlink()
        marker = path.parent.parent / '.owner'
        marker.write_text('not this invocation')
        with self.assertRaises(ValueError):
            self.module.cleanup(self.context)
        self.assertTrue(path.exists())

    def test_directory_symlink_never_reaches_another_tree(self) -> None:
        path = self.module.create_preview(b'body', self.context)
        other = self.root / 'foreign'
        other.mkdir(mode=0o700)
        victim = other / 'blocked.html'
        victim.write_text('preserve')
        path.unlink()
        path.with_name('images.html').unlink()
        path.parent.rmdir()
        path.parent.symlink_to(other, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.module.cleanup(self.context)
        self.assertEqual(victim.read_text(), 'preserve')

    def test_only_own_generated_html_can_be_launched(self) -> None:
        path = self.module.create_preview(b'body', self.context)
        for bad in (self.root / 'raw.html', path.parent.parent / 'other.html', path.with_name('.owner')):
            with self.subTest(path=bad), self.assertRaises(ValueError):
                self.module.validate_preview_path(bad, self.context)
        path.chmod(0o644)
        with self.assertRaises(ValueError):
            self.module.validate_preview_path(path, self.context)

    def test_native_export_is_read_and_only_exact_copy_disposed(self) -> None:
        export_dir = self.root / 'aerc-native-fixture'
        export_dir.mkdir(mode=0o700)
        path = export_dir / 'معاينة;$(touch OWNED).html'
        path.write_bytes(b'<p>body</p>')
        with mock.patch.dict(os.environ, {'TMPDIR': str(self.root)}):
            export = self.module.read_aerc_export(path)
            self.assertEqual(export.data, b'<p>body</p>')
            self.module.discard_export(export)
        self.assertFalse(path.exists())
        self.assertFalse(export_dir.exists())
        self.assertFalse((self.root / 'OWNED').exists())

    def test_arbitrary_symlink_hardlink_and_changed_exports_are_preserved(self) -> None:
        directory = self.root / 'aerc-fixture'
        directory.mkdir(mode=0o700)
        victim = self.root / 'user.html'
        victim.write_text('preserve')
        path = directory / 'copy.html'
        with mock.patch.dict(os.environ, {'TMPDIR': str(self.root)}):
            with self.assertRaises(ValueError):
                self.module.read_aerc_export(victim)
            path.symlink_to(victim)
            with self.assertRaises(ValueError):
                self.module.read_aerc_export(path)
            path.unlink()
            os.link(victim, path)
            with self.assertRaises(ValueError):
                self.module.read_aerc_export(path)
            path.unlink()
            path.write_text('original')
            export = self.module.read_aerc_export(path)
            path.unlink()
            path.symlink_to(victim)
            with self.assertRaises(ValueError):
                self.module.discard_export(export)
        self.assertEqual(victim.read_text(), 'preserve')

    def test_native_export_fifo_is_rejected_without_blocking(self) -> None:
        directory = self.root / 'aerc-fifo'
        directory.mkdir(mode=0o700)
        path = directory / 'fifo.html'
        os.mkfifo(path, 0o600)
        code = ('from pathlib import Path\nfrom preview_files import read_aerc_export\n'
                'try: read_aerc_export(Path(' + repr(str(path)) + '))\n'
                'except ValueError: raise SystemExit(0)\nraise SystemExit(1)\n')
        with mock.patch.dict(os.environ, {'TMPDIR': str(self.root)}):
            try:
                result = subprocess.run([sys.executable, '-c', code], capture_output=True, timeout=2)
            except subprocess.TimeoutExpired:
                self.fail('Non-regular native export blocked the preview helper')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(path.exists())
