from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock
import configparser
import shlex
import stat

import configure


class ConfigureTests(TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_one_account_uses_gmail_smtp_without_changing_incoming(self) -> None:
        parser = configparser.ConfigParser(interpolation=None)
        parser.read_string(configure.render_accounts(Path("/python with space"), Path("/source/oauth.py")))
        self.assertEqual(parser.sections(), ["Central Gmail - online evaluation"])
        account = parser[parser.sections()[0]]
        self.assertEqual(account["source"], "imaps+xoauth2://omar.rashad.dev%40gmail.com@imap.gmail.com:993")
        self.assertEqual(account["from"], "omar.rashad.dev@gmail.com")
        self.assertEqual(account["default"], "INBOX")
        for key, expected in {
            "outgoing": "smtps+xoauth2://omar.rashad.dev%40gmail.com@smtp.gmail.com:465",
            "outgoing-cred-cmd": account["source-cred-cmd"],
        }.items():
            with self.subTest(field=key):
                self.assertEqual(account.get(key), expected)
        self.assertTrue(account.getboolean("cache-headers"))
        self.assertEqual(account["check-mail"], "5m")
        self.assertEqual(shlex.split(account["source-cred-cmd"]), ["/usr/bin/timeout", "30s", "/python with space", "/source/oauth.py", "token"])
        for key in ("aliases", "folders", "folders-exclude", "check-mail-cmd", "password", "debug-log-path", "copy-to"):
            self.assertNotIn(key, account)

    def test_hook_uses_quoted_absolute_paths_without_shell_interpolation(self) -> None:
        parser = configparser.ConfigParser(interpolation=None)
        parser.read_string(configure.render_aerc(Path("/python with space"), Path("/source/toast's.py")))
        self.assertEqual(shlex.split(parser["hooks"]["mail-received"]), ["/python with space", "/source/toast's.py"])

    def test_message_list_shows_native_labels(self) -> None:
        parser = configparser.ConfigParser(interpolation=None)
        parser.read_string(configure.render_aerc(Path("/python"), Path("/source/toast.py")))
        self.assertEqual(parser["ui"].get("index-columns"), "flags:4,name<20%,labels<20%,subject,date>=")
        self.assertEqual(parser["ui"].get("column-labels"), '{{.Labels | join ", "}}')
        self.assertEqual(parser["ui"].get("column-separator"), '" │ "')
        self.assertEqual(parser["ui"].get("styleset-name"), "glaze")
        self.assertEqual(parser["ui"].get("stylesets-dirs"), str(Path.home()/".config/glaze-mail/eval/stylesets"))
        self.assertTrue(parser["ui"].getboolean("mouse-enabled"))
        self.assertFalse(parser["ui"].getboolean("new-message-bell"))
        self.assertEqual(parser.sections(), ["ui", "hooks", "viewer", "compose", "openers", "filters"])
        self.assertEqual(parser["hooks"]["mail-received"], "/python /source/toast.py")

    def test_mail_local_pager_uses_custom_keys_without_global_less_changes(self) -> None:
        parser = configparser.ConfigParser(interpolation=None)
        parser.read_string(configure.render_aerc(Path("/python"), Path("/source/toast.py")))
        self.assertIn("viewer", parser)
        self.assertEqual(shlex.split(parser["viewer"]["pager"]), [
            "/usr/bin/less", "-Rc", "--lesskey-src=/home/narol/.config/glaze-mail/eval/lesskey",
        ])
        self.assertEqual(set(parser["viewer"]), {"pager", "alternatives", "html-inline-images"})

    def test_compose_uses_nano_without_changing_standalone_plain_text_opener(self) -> None:
        parser = configparser.ConfigParser(interpolation=None)
        parser.read_string(configure.render_aerc(Path("/python"), Path("/source/toast.py")))
        self.assertIn("compose", parser)
        self.assertIn("openers", parser)
        self.assertEqual(shlex.split(parser["compose"]["editor"]), ["/usr/bin/nano"])
        self.assertEqual(shlex.split(parser["openers"]["text/plain"]), ["/usr/bin/gnome-text-editor", "--standalone"])
        self.assertEqual(set(parser["compose"]), {"editor"})
        self.assertEqual(set(parser["openers"]), {"text/plain", "text/html"})

    def test_plain_text_has_a_native_filter_so_the_pager_can_display_the_body(self) -> None:
        parser = configparser.ConfigParser(interpolation=None)
        parser.read_string(configure.render_aerc(Path("/python"), Path("/source/toast.py")))
        self.assertIn("filters", parser)
        self.assertEqual(shlex.split(parser["filters"]["text/plain"]), ["/usr/lib/aerc/filters/colorize"])
        self.assertEqual(set(parser["filters"]), {"text/plain", "text/html"})

    def test_html_is_preferred_and_opened_through_fixed_safe_mode(self) -> None:
        parser = configparser.ConfigParser(interpolation=None)
        parser.read_string(configure.render_aerc(Path('/python'), Path('/source/toast.py')))
        self.assertEqual(parser['viewer'].get('alternatives'), 'text/html,text/plain')
        self.assertEqual(parser['viewer'].get('html-inline-images'), 'true')
        prefix = [str(Path.home()/'.local/share/glaze-mail/preview-venv/bin/python'),
                  str(Path(configure.__file__).resolve().parent/'preview.py')]
        self.assertEqual(shlex.split(parser['filters']['text/html']), prefix + ['text'])
        self.assertEqual(shlex.split(parser['openers']['text/html']), prefix + ['open-html', '--aerc-export'])

    def test_generation_is_private_and_idempotent(self) -> None:
        directory = self.root / "eval"
        files = {"accounts.conf": "account-content", "aerc.conf": "ui-content"}
        configure.write_new_config(directory, files)
        configure.write_new_config(directory, files)
        self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
        for name, content in files.items():
            self.assertEqual((directory/name).read_text(), content)
            self.assertEqual(stat.S_IMODE((directory/name).stat().st_mode), 0o600)

    def test_differing_existing_file_is_not_overwritten(self) -> None:
        directory = self.root / "eval"
        directory.mkdir()
        (directory/"accounts.conf").write_text("user work")
        with self.assertRaises(FileExistsError):
            configure.write_new_config(directory, {"accounts.conf":"new", "aerc.conf":"new"})
        self.assertEqual((directory/"accounts.conf").read_text(), "user work")
        self.assertFalse((directory/"aerc.conf").exists())

    def test_symlink_and_path_traversal_cannot_overwrite_other_files(self) -> None:
        directory = self.root/"eval"
        directory.mkdir()
        victim = self.root/"victim"
        victim.write_text("untouched")
        (directory/"accounts.conf").symlink_to(victim)
        with self.assertRaises(ValueError):
            configure.write_new_config(directory, {"accounts.conf":"new", "aerc.conf":"new"})
        with self.assertRaises(ValueError):
            configure.write_new_config(directory, {"../victim":"new", "aerc.conf":"new"})
        self.assertEqual(victim.read_text(), "untouched")

    def test_existing_calendar_and_aerc_directories_are_forbidden(self) -> None:
        with mock.patch.object(Path, "home", return_value=self.root):
            for suffix in (".config/aerc", ".config/gcal"):
                directory = self.root/suffix
                with self.assertRaises(ValueError):
                    configure.write_new_config(directory, {"accounts.conf":"x", "aerc.conf":"x"})
                self.assertFalse(directory.exists())

    def test_relative_or_multiline_credential_commands_are_rejected(self) -> None:
        for python in (Path("relative/python"), Path("/path\nwith-newline")):
            with self.assertRaises(ValueError):
                configure.render_accounts(python, Path("/source/oauth.py"))
