from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO, BytesIO, TextIOWrapper
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock
import importlib
import importlib.util
import os
import subprocess
import sys

from preview_files import PreviewContext, create_preview


class CliTests(TestCase):
    def setUp(self) -> None:
        self.assertIsNotNone(importlib.util.find_spec('preview'), 'Preview CLI is missing')
        self.module = importlib.import_module('preview')
        self.temp = TemporaryDirectory(prefix='preview-cli-', dir='/tmp/opencode')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.context = PreviewContext(self.root, '4' * 32, 'fixture.service')
        patcher = mock.patch.dict(os.environ, {'XDG_RUNTIME_DIR': str(self.root), 'INVOCATION_ID': '4' * 32,
                                             'GLAZE_MAIL_SERVICE_UNIT': 'fixture.service', 'TMPDIR': str(self.root)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def properties(self) -> dict[str, str]:
        return {'InvocationID': '4' * 32, 'ActiveState': 'active', 'ControlGroup': '/fixture.service',
                'ExecStopPost': '{ path=' + sys.executable + ' ; argv[]=' + sys.executable + ' ' +
                str(Path(self.module.__file__).resolve()) + ' cleanup ; ignore_errors=no ; }'}

    def test_active_context_rejects_stale_foreign_stopping_or_unhooked_unit(self) -> None:
        properties = self.properties()
        for changes, cgroup in [({}, '0::/fixture.service/child\n'),
                                ({'InvocationID': '5' * 32}, '0::/fixture.service\n'),
                                ({'ActiveState': 'deactivating'}, '0::/fixture.service\n'),
                                ({'ExecStopPost': ''}, '0::/fixture.service\n'),
                                ({'ControlGroup': '/'}, '0::/fixture.service\n'),
                                ({}, '0::/fixture.service-foreign\n')]:
            values = properties | changes
            output = '\n'.join(k + '=' + v for k, v in values.items())
            with self.subTest(changes=changes, cgroup=cgroup), \
                    mock.patch('preview.subprocess.run', return_value=subprocess.CompletedProcess([], 0, output, '')), \
                    mock.patch('preview.current_cgroup', return_value=cgroup):
                if not changes and cgroup == '0::/fixture.service/child\n':
                    self.module.require_active_context(self.context)
                else:
                    with self.assertRaises(ValueError):
                        self.module.require_active_context(self.context)

    def test_text_mode_is_network_free_and_bounded(self) -> None:
        for data, expected in [(b'<p>hello</p><script>bad()</script>', 'hello\n'),
                               ('<p>مرحبا ikIK</p>'.encode(), 'مرحبا ikIK\n')]:
            with mock.patch('sys.stdin', TextIOWrapper(BytesIO(data))), redirect_stdout(StringIO()) as out:
                self.assertEqual(self.module.main(['text']), 0)
                self.assertEqual(out.getvalue(), expected)
        with mock.patch('sys.stdin', TextIOWrapper(BytesIO(b'x' * (16 * 1024 * 1024 + 1)))), \
                redirect_stderr(StringIO()) as err, redirect_stdout(StringIO()) as out:
            self.assertEqual(self.module.main(['text']), 1)
            self.assertNotIn('xxxx', err.getvalue())
            self.assertEqual(out.getvalue(), '')

    def test_open_generates_then_hands_only_sanitized_file_and_discards_exact_export(self) -> None:
        directory = self.root / 'aerc-fixture'
        directory.mkdir(mode=0o700)
        export = directory / 'مرحبا;$(touch OWNED).not-html'
        export.write_bytes(b'<script>bad()</script><p>SYNTHETIC BODY</p>')
        received: list[Path] = []

        def opened(path: Path, context: PreviewContext) -> None:
            received.append(path)
            self.assertEqual(context, self.context)
            self.assertNotEqual(path, export)
            self.assertNotIn('bad()', path.read_text())
            self.assertIn('SYNTHETIC BODY', path.read_text())

        with mock.patch('preview.require_active_context'), mock.patch('preview_desktop.launch_preview', side_effect=opened):
            self.assertEqual(self.module.main(['open-html', '--aerc-export', str(export)]), 0)
        self.assertEqual(len(received), 1)
        self.assertTrue(received[0].exists())
        self.assertFalse(export.exists())
        self.assertFalse((self.root / 'OWNED').exists())

    def test_open_loads_https_images_by_default_and_keeps_block_images_toggle(self) -> None:
        directory = self.root / 'aerc-fixture'
        directory.mkdir(mode=0o700)
        export = directory / 'message.html'
        export.write_bytes(b'<p>Body</p><img src="https://images.example.invalid/pixel.png">'
                           b'<img src="http://images.example.invalid/insecure.png"><script>bad()</script>')
        received: list[tuple[Path, PreviewContext]] = []

        def opened(path: Path, context: PreviewContext) -> None:
            received.append((path, context))

        with mock.patch('preview.require_active_context'), mock.patch('preview.notify_failure'), \
                mock.patch('preview_desktop.launch_preview', side_effect=opened):
            self.assertEqual(self.module.main(['open-html', '--aerc-export', str(export)]), 0)
        self.assertEqual(len(received), 1)
        path, context = received[0]
        self.assertEqual(context, self.context)
        document = path.read_text()
        self.assertIn('src="https://images.example.invalid/pixel.png"', document)
        self.assertNotIn('insecure.png', document)
        self.assertNotIn('bad()', document)
        self.assertIn('Block images</a>', document)
        blocked = path.with_name('blocked.html')
        self.assertIn('href="' + blocked.as_uri() + '"', document)
        self.assertNotIn('src="https://images.example.invalid/pixel.png"', blocked.read_text())
        self.assertIn('Load images', blocked.read_text())
        self.assertFalse(export.exists())

    def test_failure_does_not_open_raw_retry_or_echo_private_values(self) -> None:
        directory = self.root / 'aerc-fixture'
        directory.mkdir(mode=0o700)
        export = directory / 'SECRET-FILENAME.html'
        export.write_bytes(b'<p>SECRET BODY</p>')
        with mock.patch('preview.require_active_context'), \
                mock.patch('preview_desktop.launch_preview', side_effect=TimeoutError('SECRET BODY')), \
                mock.patch('preview.notify_failure'), redirect_stderr(StringIO()) as err:
            self.assertEqual(self.module.main(['open-html', '--aerc-export', str(export)]), 1)
            self.assertNotIn('SECRET', err.getvalue())
        self.assertFalse(export.exists())

    def test_cleanup_runs_without_site_packages_or_active_service(self) -> None:
        page = create_preview(b'body', self.context)
        result = subprocess.run([sys.executable, '-S', str(Path(self.module.__file__)), 'cleanup'],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(page.exists())

    def test_untrusted_argument_errors_do_not_echo_values(self) -> None:
        with redirect_stderr(StringIO()) as err:
            self.assertEqual(self.module.main(['SECRET-ARGUMENT']), 1)
        self.assertNotIn('SECRET', err.getvalue())

    def test_oversized_native_export_is_refused_and_exact_raw_copy_disposed(self) -> None:
        directory = self.root / 'aerc-oversize'
        directory.mkdir(mode=0o700)
        export = directory / 'large.html'
        with export.open('wb') as stream:
            stream.truncate(16 * 1024 * 1024 + 1)
        with mock.patch('preview.require_active_context'), mock.patch('preview.notify_failure'), redirect_stderr(StringIO()):
            self.assertEqual(self.module.main(['open-html', '--aerc-export', str(export)]), 1)
        self.assertFalse(export.exists(), 'Rejected oversized HTML left a raw mail export behind')
        self.assertFalse(directory.exists())
