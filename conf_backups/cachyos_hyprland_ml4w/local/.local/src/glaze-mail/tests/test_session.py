from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock
import os
import subprocess

import session


class SessionTests(TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        patcher = mock.patch.dict(os.environ, {"DBUS_SESSION_BUS_ADDRESS": "unix:path=/synthetic/bus"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def prepared(self) -> tuple[Path, Path, Path]:
        binary = self.root/"aerc"
        binary.write_text("#!/bin/sh\nexit 0\n")
        binary.chmod(0o700)
        config = self.root/"config"
        config.mkdir()
        for name in ("accounts.conf", "aerc.conf"):
            (config/name).write_text("config")
            (config/name).chmod(0o600)
        styles = config/"stylesets"
        styles.mkdir(mode=0o700)
        (styles/"glaze").write_text("*.selected.bg=#34362e\n")
        (styles/"glaze").chmod(0o600)
        (config/"lesskey").write_text("#command\ni back-line\nk forw-line\n")
        (config/"lesskey").chmod(0o600)
        bindings = self.root/"terminal/config/aerc/binds.conf"
        bindings.parent.mkdir(parents=True, mode=0o700)
        bindings.write_text("[messages]\ni = :prev<Enter>\nk = :next<Enter>\n")
        bindings.chmod(0o600)
        scheme = self.root/"terminal/data/konsole/GlazeMail.colorscheme"
        scheme.parent.mkdir(parents=True, mode=0o700)
        scheme.write_text("[General]\nOpacity=0.9\n")
        scheme.chmod(0o600)
        konsole = self.root/"konsole"
        konsole.write_text("#!/bin/sh\nexit 0\n")
        konsole.chmod(0o700)
        patcher = mock.patch.object(session, "KONSOLE_BINARY", konsole, create=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        token = self.root/"oauth.json"
        token.write_text("{}")
        token.chmod(0o600)
        source = self.root/'source with space%'
        source.mkdir(mode=0o700)
        for name in ('preview.py', 'preview_files.py', 'preview_desktop.py', 'preview_html.py', 'preview_startup.lua'):
            (source/name).write_text('# synthetic fixture\n')
            (source/name).chmod(0o600)
        venv = self.root/'preview-venv'
        (venv/'bin').mkdir(parents=True, mode=0o700)
        venv.chmod(0o700)
        (venv/'bin/python').symlink_to('/usr/bin/python')
        (venv/'pyvenv.cfg').write_text('include-system-site-packages = true\n')
        for name, value in [('SOURCE_DIRECTORY', source), ('PREVIEW_PYTHON', venv/'bin/python')]:
            patcher = mock.patch.object(session, name, value, create=True)
            patcher.start()
            self.addCleanup(patcher.stop)
        return binary, config, token

    def test_launch_owns_terminal_and_children_in_one_non_restarting_cgroup(self) -> None:
        with mock.patch.dict(os.environ, {"WAYLAND_DISPLAY":"wayland-1", "XDG_RUNTIME_DIR":"/run/user/1000", "DBUS_SESSION_BUS_ADDRESS":"unix:path=/synthetic/bus", "UNRELATED_SECRET":"not-forwarded"}, clear=True):
            argv = session.build_launch_command(Path("/runtime/aerc"), Path("/eval"))
        self.assertEqual(argv[:2], ["/usr/bin/systemd-run", "--user"])
        for flag in ("--unit=glaze-mail-eval", "--collect", "--service-type=exec",
                     "--property=KillMode=control-group", "--property=Restart=no", "--property=TimeoutStopSec=5s"):
            self.assertIn(flag, argv)
        native = argv[argv.index("--")+1:]
        self.assertEqual(native[:5], ["/usr/bin/konsole", "--separate", "--builtin-profile", "--desktopfile", "aerc-mail"])
        for flag in ("--hide-menubar", "--hide-toolbars", "--hide-tabbar", "WordMode=true", "BidiRenderingEnabled=true",
                     "BidiLineLTR=true", "BidiTableDirOverride=true", "ScrollBarPosition=2", "ShowTerminalSizeHint=false",
                     "TerminalMargin=0", "Font=DejaVu Sans Mono,10,-1,5,400,0,0,0,1,0", "ColorScheme=GlazeMail"):
            self.assertIn(flag, native)
        self.assertEqual(native[native.index("-e")+1:], ["/usr/bin/env", "DBUS_SESSION_BUS_ADDRESS=unix:path=/synthetic/bus",
                         "/runtime/aerc", "-I", "-C", "/eval/aerc.conf", "-A", "/eval/accounts.conf"])
        self.assertIn("--setenv=DBUS_SESSION_BUS_ADDRESS=unix:path=/dev/null", argv)
        self.assertNotIn("--setenv=DBUS_SESSION_BUS_ADDRESS=unix:path=/synthetic/bus", argv)
        for key in ("CONFIG", "CACHE", "STATE", "DATA"):
            self.assertIn(f"--setenv=XDG_{key}_HOME=/terminal/{key.lower()}", argv)
        self.assertIn("--setenv=QT_WAYLAND_DISABLE_WINDOWDECORATION=1", argv)
        self.assertIn("--setenv=WAYLAND_DISPLAY=wayland-1", argv)
        self.assertNotIn("not-forwarded", " ".join(argv))

    def test_mail_terminal_disables_history_with_a_launch_scoped_profile_override(self) -> None:
        argv = session.build_launch_command(Path("/runtime/aerc"), Path("/eval"))
        native = argv[argv.index("--")+1:]
        terminal_options = native[:native.index("-e")]
        properties = [terminal_options[index+1] for index, value in enumerate(terminal_options) if value == "-p"]
        self.assertEqual([value for value in properties if value.startswith("HistoryMode=")], ["HistoryMode=0"])

    def test_missing_or_multiline_desktop_bus_is_rejected(self) -> None:
        for value in (None, "", "unix:path=/bad\nbus", "unix:path=/bad\rbus"):
            with self.subTest(value=value), mock.patch.dict(os.environ, {}, clear=True):
                if value is not None:
                    os.environ["DBUS_SESSION_BUS_ADDRESS"] = value
                with self.assertRaises(ValueError):
                    session.build_launch_command(Path("/runtime/aerc"), Path("/eval"))

    def test_normal_desktop_paths_and_cleanup_hook_are_preserved_before_isolation(self) -> None:
        with mock.patch.dict(os.environ, {'HOME': '/home/fixture', 'DBUS_SESSION_BUS_ADDRESS': 'unix:path=/bus',
                                         'XDG_CONFIG_HOME': '/normal config', 'UNRELATED_SECRET': 'hidden'}, clear=True):
            argv = session.build_launch_command(Path('/runtime/aerc'), Path('/eval'))
        self.assertIn('--setenv=GLAZE_MAIL_SERVICE_UNIT=glaze-mail-eval.service', argv)
        self.assertIn('--setenv=GLAZE_MAIL_DESKTOP_XDG_CONFIG_HOME=/normal config', argv)
        for key, suffix in [('DATA', '.local/share'), ('CACHE', '.cache'), ('STATE', '.local/state')]:
            self.assertIn(f'--setenv=GLAZE_MAIL_DESKTOP_XDG_{key}_HOME=/home/fixture/{suffix}', argv)
        self.assertNotIn('hidden', ' '.join(argv))
        hook = next((arg for arg in argv if arg.startswith('--property=ExecStopPost=')), '')
        self.assertIn('/preview.py" "cleanup"', hook)

    def test_preview_preflight_rejects_missing_or_public_assets_but_accepts_venv_link(self) -> None:
        binary, config, token = self.prepared()
        target = session.SOURCE_DIRECTORY/'preview.py'
        target.chmod(0o644)
        with mock.patch('subprocess.run') as run:
            with self.assertRaises(ValueError):
                session.launch(binary, config, token)
            run.assert_not_called()
        target.chmod(0o600)
        self.assertTrue(session.PREVIEW_PYTHON.is_symlink())
        with mock.patch('subprocess.run', return_value=subprocess.CompletedProcess([], 0)):
            session.launch(binary, config, token)

    def test_systemd_cleanup_escaping_is_not_shell_quoting(self) -> None:
        self.assertTrue(hasattr(session, 'systemd_command'), 'Cleanup needs systemd argument escaping')
        self.assertEqual(session.systemd_command(['/bin/python', '/a b/100%/$file".py', 'cleanup']),
                         '"/bin/python" "/a b/100%/$$file\\".py" "cleanup"')

    def test_startup_lua_is_required_and_private_before_any_launch(self) -> None:
        binary, config, token = self.prepared()
        startup = session.SOURCE_DIRECTORY/'preview_startup.lua'
        for mode in (0o644, 0o600):
            startup.chmod(mode)
            if mode == 0o600:
                startup.unlink()
            with self.subTest(mode=mode), mock.patch('subprocess.run') as run:
                with self.assertRaises(ValueError):
                    session.launch(binary, config, token)
                run.assert_not_called()
        startup.write_text('-- synthetic startup fixture\n')
        startup.chmod(0o600)
        with mock.patch('subprocess.run', return_value=subprocess.CompletedProcess([], 0)):
            session.launch(binary, config, token)

    def test_relative_or_multiline_paths_are_rejected(self) -> None:
        for binary, config in ((Path("relative"), Path("/eval")), (Path("/runtime/aerc"), Path("relative")),
                               (Path("/runtime\naerc"), Path("/eval")), (Path("/runtime/aerc"), Path("/eval\nconfig"))):
            with self.subTest(binary=binary, config=config), self.assertRaises(ValueError):
                session.build_launch_command(binary, config)

    def test_missing_or_nonexecutable_konsole_is_rejected_before_start(self) -> None:
        binary, config, token = self.prepared()
        terminal = session.KONSOLE_BINARY
        terminal.chmod(0o600)
        for exists in (True, False):
            if not exists:
                terminal.unlink()
            with self.subTest(exists=exists), mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0)) as run:
                with self.assertRaises((ValueError, FileNotFoundError)):
                    session.launch(binary, config, token)
                run.assert_not_called()

    def test_missing_or_symlinked_theme_assets_are_rejected(self) -> None:
        binary, config, token = self.prepared()
        for path in (config/"stylesets/glaze", self.root/"terminal/data/konsole/GlazeMail.colorscheme"):
            contents = path.read_text()
            path.unlink()
            with self.subTest(asset=path.name, kind="missing"), mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0)) as run:
                with self.assertRaises(ValueError):
                    session.launch(binary, config, token)
                run.assert_not_called()
            victim = self.root/(path.name+"-target")
            victim.write_text(contents)
            victim.chmod(0o600)
            path.symlink_to(victim)
            with self.subTest(asset=path.name, kind="symlink"), mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0)) as run:
                with self.assertRaises(ValueError):
                    session.launch(binary, config, token)
                run.assert_not_called()
            path.unlink()
            path.write_text(contents)
            path.chmod(0o600)

    def test_symlinked_terminal_config_directory_is_rejected(self) -> None:
        binary, config, token = self.prepared()
        (self.root/"terminal/config").rename(self.root/"original-config")
        outside = self.root/"outside"
        outside.mkdir()
        (self.root/"terminal/config").symlink_to(outside, target_is_directory=True)
        with mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0)) as run:
            with self.assertRaises(ValueError):
                session.launch(binary, config, token)
            run.assert_not_called()
        self.assertEqual(list(outside.iterdir()), [])

    def test_missing_or_unsafe_preference_assets_are_rejected_before_launch(self) -> None:
        binary, config, token = self.prepared()
        for path in (config/"lesskey", self.root/"terminal/config/aerc/binds.conf"):
            contents = path.read_text()
            for kind in ("missing", "symlink", "public"):
                path.unlink()
                if kind == "symlink":
                    target = self.root/(path.name+"-target")
                    target.write_text(contents)
                    target.chmod(0o600)
                    path.symlink_to(target)
                elif kind == "public":
                    path.write_text(contents)
                    path.chmod(0o644)
                with self.subTest(asset=path.name, kind=kind), mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0)) as run:
                    with self.assertRaises(ValueError):
                        session.launch(binary, config, token)
                    run.assert_not_called()
                if path.exists() or path.is_symlink():
                    path.unlink()
                path.write_text(contents)
                path.chmod(0o600)

    def test_terminal_owned_runtime_directories_are_private(self) -> None:
        binary, config, token = self.prepared()
        with mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0)):
            session.launch(binary, config, token)
        for name in ("config", "cache", "state"):
            directory = self.root/"terminal"/name
            self.assertTrue(directory.is_dir())
            self.assertEqual(directory.stat().st_mode & 0o777, 0o700)

    def test_missing_dependencies_fail_before_starting_any_process(self) -> None:
        binary, config, token = self.prepared()
        for path in (binary, config/"accounts.conf", config/"aerc.conf", token):
            contents, mode = path.read_bytes(), path.stat().st_mode & 0o777
            path.unlink()
            with self.subTest(missing=path.name), mock.patch("subprocess.run", side_effect=AssertionError("must not launch")):
                with self.assertRaises((ValueError, FileNotFoundError)):
                    session.launch(binary, config, token)
            path.write_bytes(contents)
            path.chmod(mode)

    def test_duplicate_service_failure_does_not_retry_or_open_second_window(self) -> None:
        binary, config, token = self.prepared()
        with mock.patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "systemd-run")) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                session.launch(binary, config, token)
        self.assertEqual(len(run.call_args_list), 1)

    def test_launch_is_checked_and_not_a_shell(self) -> None:
        binary, config, token = self.prepared()
        with mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([],0)) as run:
            session.launch(binary, config, token)
        self.assertTrue(run.call_args.kwargs["check"])
        self.assertFalse(run.call_args.kwargs["shell"])

    def test_symlinked_token_and_permissive_credentials_are_refused(self) -> None:
        binary, config, token = self.prepared()
        token.chmod(0o644)
        with self.assertRaises(ValueError):
            session.launch(binary, config, token)
        token.unlink()
        token.symlink_to(config/"accounts.conf")
        with self.assertRaises(ValueError):
            session.launch(binary, config, token)
