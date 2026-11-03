from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase, mock
import importlib
import importlib.util
import json
import os
import subprocess
import sys
import time

from preview_files import PreviewContext, create_preview


class DesktopTests(TestCase):
    def setUp(self) -> None:
        self.assertIsNotNone(importlib.util.find_spec('preview_desktop'), 'Normal desktop browser handoff is missing')
        self.module = importlib.import_module('preview_desktop')
        self.temp = TemporaryDirectory(prefix='preview-desktop-', dir='/tmp/opencode')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.context = PreviewContext(self.root, '3' * 32, 'fixture.service')
        self.path = create_preview(b'<p>synthetic</p>', self.context)

    def environment(self) -> dict[str, str]:
        env = {'HOME': str(self.root), 'XDG_RUNTIME_DIR': str(self.root),
               'DBUS_SESSION_BUS_ADDRESS': os.environ['DBUS_SESSION_BUS_ADDRESS'],
               'WAYLAND_DISPLAY': os.environ.get('WAYLAND_DISPLAY', 'fixture'),
               'XDG_CONFIG_HOME': '/isolated/mail/config', 'UNRELATED_SECRET': 'must-not-forward'}
        for name, value in self.module.capture_desktop_paths({}, self.root).items():
            env['GLAZE_MAIL_DESKTOP_' + name] = value
        return env

    def test_desktop_paths_restore_real_context_not_mail_isolation(self) -> None:
        paths = self.module.capture_desktop_paths({'XDG_CONFIG_HOME': '/normal config'}, Path('/home/test'))
        self.assertEqual(paths, {'XDG_CONFIG_HOME': '/normal config', 'XDG_DATA_HOME': '/home/test/.local/share',
                                 'XDG_CACHE_HOME': '/home/test/.cache', 'XDG_STATE_HOME': '/home/test/.local/state'})
        environment = self.module.desktop_environment(self.environment())
        self.assertEqual(environment['XDG_CONFIG_HOME'], str(self.root / '.config'))
        self.assertNotIn('UNRELATED_SECRET', environment)
        self.assertNotIn('BROWSER', environment)
        for value in ('relative', '/bad\npath', ''):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.module.capture_desktop_paths({'XDG_DATA_HOME': value}, self.root)
        with self.assertRaises(ValueError):
            self.module.desktop_environment({'HOME': str(self.root)})

    def test_browser_command_uses_independent_collected_service_and_no_profile_override(self) -> None:
        argv = self.module.build_browser_command(self.path, self.context, self.environment())
        self.assertEqual(argv[:2], ['/usr/bin/systemd-run', '--user'])
        for flag in ('--collect', '--service-type=exec', '--property=ExitType=cgroup', '--property=Restart=no'):
            self.assertIn(flag, argv)
        self.assertIn('--setenv=XDG_CONFIG_HOME=' + str(self.root / '.config'), argv)
        self.assertIn(str(self.path), argv)
        self.assertIn(self.context.invocation_id, argv)
        self.assertNotIn('must-not-forward', '\n'.join(argv))
        for forbidden in ('--user-data-dir', '--no-sandbox', '--disable-web-security', 'BindsTo=', 'Requires='):
            self.assertNotIn(forbidden, '\n'.join(argv))
        with self.assertRaises(ValueError):
            self.module.build_browser_command(self.root / 'raw.html', self.context, self.environment())

    def test_native_gio_chooses_https_handler_not_text_html_editor(self) -> None:
        normal = self.module.capture_desktop_paths({}, self.root)
        for directory in normal.values():
            Path(directory).mkdir(parents=True, exist_ok=True)
        apps = Path(normal['XDG_DATA_HOME']) / 'applications'
        apps.mkdir()
        receiver = self.root / 'receiver.py'
        log = self.root / 'opened.json'
        receiver.write_text('import json,sys\nfrom pathlib import Path\nPath(' + repr(str(log)) + ').write_text(json.dumps(sys.argv[1:]))\n')
        for name, role, mime in [('fixture-browser', 'browser', 'x-scheme-handler/https'), ('wrong-editor', 'editor', 'text/html')]:
            (apps / (name + '.desktop')).write_text(f'[Desktop Entry]\nType=Application\nName={name}\nExec={sys.executable} {receiver} {role} %u\nTerminal=false\nMimeType={mime};\n')
        (Path(normal['XDG_CONFIG_HOME']) / 'mimeapps.list').write_text('[Default Applications]\nx-scheme-handler/https=fixture-browser.desktop\ntext/html=wrong-editor.desktop\n')
        env = os.environ.copy() | normal
        result = subprocess.run([sys.executable, str(Path(self.module.__file__)), 'open', str(self.path),
                                 '--runtime', str(self.root), '--mail-invocation', self.context.invocation_id,
                                 '--mail-unit', self.context.unit_name], env=env, capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        deadline = time.monotonic() + 5
        while not log.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertTrue(log.exists(), 'Native GIO did not launch the controlled HTTPS handler')
        received = json.loads(log.read_text())
        self.assertEqual(received[0], 'browser')
        self.assertEqual(len(received), 2)
        self.assertIn(received[1], (str(self.path), self.path.as_uri()))

    def test_app_gio_preserves_existing_arguments_and_escapes_percent_encoded_uri(self) -> None:
        self.assertTrue(hasattr(self.module, 'app_browser'), 'Preview needs a tabless app window')
        import gi
        gi.require_version('GioUnix', '2.0')
        from gi.repository import GioUnix
        log = self.root/'new-window.json'
        receiver = self.root/'receive.py'
        receiver.write_text('import json,sys\nfrom pathlib import Path\nPath(' + repr(str(log)) + ').write_text(json.dumps(sys.argv[1:]))\n')
        desktop = self.root/'browser.desktop'
        desktop.write_text(f'[Desktop Entry]\nType=Application\nName=fixture\nExec={sys.executable} {receiver} --existing-flag "value with space" %U\n')
        browser = GioUnix.DesktopAppInfo.new_from_filename(str(desktop))
        runtime = self.root / 'runtime % "quote" space'
        runtime.mkdir(mode=0o700)
        page = create_preview(b'<p>synthetic</p>', PreviewContext(runtime, '5' * 32, 'fixture.service'))
        preview_browser = self.module.app_browser(browser, page)
        self.assertTrue(preview_browser.launch_uris([], None))
        deadline = time.monotonic() + 5
        while not log.exists() and time.monotonic() < deadline:
            time.sleep(.02)
        self.assertTrue(log.exists())
        received = json.loads(log.read_text())
        self.assertEqual(received[:2], ['--existing-flag', 'value with space'])
        self.assertEqual(received, ['--existing-flag', 'value with space', '--app=' + page.as_uri()])

    def test_mail_workspace_requires_matching_active_owner_and_window_pid(self) -> None:
        self.assertTrue(hasattr(self.module, 'workspace_snapshot'), 'Mail workspace lookup is missing')
        clients = [{'address': '0xaaa', 'pid': 123, 'class': 'aerc-mail', 'workspace': {'id': 6}},
                   {'address': '0xbbb', 'pid': 456, 'class': 'brave-browser', 'workspace': {'id': 3}}]
        properties = 'MainPID=123\nActiveState=active\nInvocationID=' + self.context.invocation_id + '\n'
        with mock.patch('preview_desktop.subprocess.run', return_value=subprocess.CompletedProcess([], 0, properties, '')), \
                mock.patch('preview_desktop.window_clients', return_value=clients):
            self.assertEqual(self.module.workspace_snapshot(self.context), (6, {'0xaaa', '0xbbb'}, '0xaaa'))
        for values in (properties.replace('MainPID=123', 'MainPID=999'), properties.replace('active', 'inactive'),
                       properties.replace(self.context.invocation_id, '4' * 32)):
            with mock.patch('preview_desktop.subprocess.run', return_value=subprocess.CompletedProcess([], 0, values, '')), \
                    mock.patch('preview_desktop.window_clients', return_value=clients):
                self.assertIsNone(self.module.workspace_snapshot(self.context))

    def test_placement_verifies_only_new_exact_preview_without_moving_browser_or_webapps(self) -> None:
        self.assertTrue(hasattr(self.module, 'place_preview'), 'Exact preview workspace placement is missing')
        marker = 'aerc Mail preview ' + self.path.parent.name
        app_class = 'brave-__private_' + self.path.parent.name + '_blocked.html-Default'
        windows = [{'address': '0xaaa', 'class': app_class, 'title': marker, 'workspace': {'id': 3}},
                   {'address': '0xbbb', 'class': 'brave-open.spotify.com__-Default', 'title': marker, 'workspace': {'id': 8}},
                   {'address': '0xccc', 'class': 'brave-browser', 'title': 'Unrelated browser', 'workspace': {'id': 3}},
                   {'address': '0xeee', 'class': 'aerc-mail', 'workspace': {'id': 6},
                    'at': [0, 0], 'size': [500, 800], 'floating': False},
                   {'address': '0xddd', 'class': app_class, 'title': marker, 'workspace': {'id': 6},
                    'at': [600, 0], 'size': [500, 800], 'floating': False}]
        with mock.patch('preview_desktop.window_clients', return_value=windows), \
                mock.patch('preview_desktop.subprocess.run', side_effect=AssertionError('No post-open dispatch')):
            self.assertTrue(self.module.place_preview(self.path, (6, {'0xaaa', '0xeee'}, '0xeee')))
        self.assertEqual([w['workspace']['id'] for w in windows[:-1]], [3, 8, 3, 6])

    def test_wrong_initial_placement_is_reported_without_post_open_corrections(self) -> None:
        marker = 'aerc Mail preview ' + self.path.parent.name
        mail = {'address': '0xaaa', 'class': 'aerc-mail', 'workspace': {'id': 6},
                'at': [600, 0], 'size': [500, 800], 'floating': False}
        preview = {'address': '0xbbb', 'class': 'brave-__private_' + self.path.parent.name + '_blocked.html-Default',
                    'title': marker, 'workspace': {'id': 6}, 'at': [0, 0], 'size': [500, 800], 'floating': False}
        for changes in ({}, {'at': [600, 900]}, {'workspace': {'id': 3}},
                        {'floating': True}, {'fullscreen': 2, 'fullscreenClient': 2}):
            with self.subTest(changes=changes), \
                    mock.patch('preview_desktop.window_clients', return_value=[mail, preview | changes]), \
                    mock.patch('preview_desktop.subprocess.run', side_effect=AssertionError('No post-open correction')):
                self.assertFalse(self.module.place_preview(self.path, (6, {'0xaaa'}, '0xaaa')))

    def test_already_right_preview_is_not_rearranged(self) -> None:
        marker = 'aerc Mail preview ' + self.path.parent.name
        windows = [{'address': '0xaaa', 'class': 'aerc-mail', 'workspace': {'id': 6},
                    'at': [0, 0], 'size': [500, 800], 'floating': False},
                   {'address': '0xbbb', 'class': 'brave-__private_' + self.path.parent.name + '_blocked.html-Default',
                    'title': marker, 'workspace': {'id': 6}, 'at': [600, 0], 'size': [500, 800], 'floating': False}]
        with mock.patch('preview_desktop.window_clients', return_value=windows), \
                mock.patch('preview_desktop.subprocess.run', side_effect=AssertionError('Do not move an already-right preview')):
            self.assertTrue(self.module.place_preview(self.path, (6, {'0xaaa'}, '0xaaa')))

    def test_placement_refuses_missing_mail_and_ambiguous_preview_without_moving(self) -> None:
        marker = 'aerc Mail preview ' + self.path.parent.name
        app_class = 'brave-__private_' + self.path.parent.name + '_blocked.html-Default'
        preview = {'address': '0xbbb', 'class': app_class, 'title': marker, 'workspace': {'id': 6}}
        mail = {'address': '0xaaa', 'class': 'aerc-mail', 'workspace': {'id': 6}}
        duplicate = preview | {'address': '0xccc'}
        for windows in ([preview], [mail, preview, duplicate]):
            with self.subTest(windows=windows), \
                    mock.patch('preview_desktop.window_clients', return_value=windows), \
                    mock.patch('preview_desktop.subprocess.run', side_effect=AssertionError('Unsafe movement')):
                self.assertFalse(self.module.place_preview(self.path, (6, {'0xaaa'}, '0xaaa')))

    def test_late_fullscreen_change_is_reported_without_overriding_user_state(self) -> None:
        marker = 'aerc Mail preview ' + self.path.parent.name
        mail = {'address': '0xaaa', 'class': 'aerc-mail', 'workspace': {'id': 6},
                'at': [0, 0], 'size': [500, 800], 'floating': False}
        preview = {'address': '0xbbb', 'class': 'brave-__private_' + self.path.parent.name + '_blocked.html-Default',
                   'title': marker, 'workspace': {'id': 6}, 'at': [600, 0], 'size': [500, 800],
                   'floating': False, 'fullscreen': 0, 'fullscreenClient': 0}
        queries = 0
        clock = 0.0
        def clients() -> list[dict[str, object]]:
            nonlocal queries
            queries += 1
            if queries == 2:
                preview.update(at=[0, 0], size=[1100, 800], fullscreen=2, fullscreenClient=2)
            return [mail, preview]
        def now() -> float:
            nonlocal clock
            clock += .1
            return clock
        with mock.patch('preview_desktop.window_clients', side_effect=clients), \
                mock.patch('preview_desktop.subprocess.run', side_effect=AssertionError('Do not override fullscreen')), \
                mock.patch('preview_desktop.time.monotonic', side_effect=now), \
                mock.patch('preview_desktop.time.sleep'):
            self.assertFalse(self.module.place_preview(self.path, (6, {'0xaaa'}, '0xaaa')))
        self.assertGreater(queries, 1)

    def test_startup_hook_is_ready_before_launch_or_browser_is_not_opened(self) -> None:
        self.assertTrue(hasattr(self.module, 'prepare_preview'), 'Before-layout preparation is missing')
        target = (6, {'0xaaa'}, '0xaaa')
        for ready in (True, False):
            operations: list[str] = []
            browser = SimpleNamespace(get_id=lambda: 'brave-browser.desktop')
            app = SimpleNamespace(launch_uris=lambda *args: operations.append('launch') or True)
            gi = SimpleNamespace(require_version=lambda *args: None)
            repository = SimpleNamespace(Gio=SimpleNamespace(AppInfo=SimpleNamespace(
                get_default_for_uri_scheme=lambda scheme: browser)))
            def prepare(*args: object) -> bool:
                operations.append('prepare')
                return ready
            def verify(*args: object) -> bool:
                operations.append('verify')
                return True
            with self.subTest(ready=ready), mock.patch.dict(sys.modules, {'gi': gi, 'gi.repository': repository}), \
                    mock.patch('preview_desktop.workspace_snapshot', return_value=target), \
                    mock.patch('preview_desktop.prepare_preview', side_effect=prepare), \
                    mock.patch('preview_desktop.app_browser', return_value=app), \
                    mock.patch('preview_desktop.place_preview', side_effect=verify):
                if ready:
                    self.module.open_in_desktop(self.path, self.context)
                    self.assertEqual(operations, ['prepare', 'launch', 'verify'])
                else:
                    with self.assertRaises(ValueError):
                        self.module.open_in_desktop(self.path, self.context)
                    self.assertEqual(operations, ['prepare'])

    def test_startup_rejects_untrusted_identity_or_failed_lua_without_opening(self) -> None:
        self.assertTrue(hasattr(self.module, 'prepare_preview'), 'Before-layout preparation is missing')
        for target in ((6, {'0xaaa'}, '0xaaa"'), (0, {'0xaaa'}, '0xaaa'), (6, set(), '0xaaa')):
            with self.subTest(target=target), \
                    mock.patch('preview_desktop.subprocess.run', side_effect=AssertionError('Unsafe Lua input')):
                self.assertFalse(self.module.prepare_preview(self.path, target))
        with mock.patch('preview_desktop.subprocess.run', return_value=subprocess.CompletedProcess([], 0, 'error: hook failed\n', '')):
            self.assertFalse(self.module.prepare_preview(self.path, (6, {'0xaaa'}, '0xaaa')))

    def test_runtime_startup_hook_scopes_splits_and_expires_without_moving_windows(self) -> None:
        self.assertTrue(hasattr(self.module, 'prepare_preview'), 'Before-layout preparation is missing')
        run = subprocess.run
        fixture = Path(__file__).with_name('startup_fixture.lua')
        def compositor(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            self.assertEqual(argv[:2], ['/usr/bin/hyprctl', 'eval'])
            result = run(['/usr/bin/lua', str(fixture), argv[2]], capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            return subprocess.CompletedProcess(argv, 0, 'ok\n', '')
        with mock.patch('preview_desktop.subprocess.run', side_effect=compositor):
            self.assertTrue(self.module.prepare_preview(self.path, (6, {'0xaaa'}, '0xaaa')))
