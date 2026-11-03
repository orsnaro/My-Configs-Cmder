from __future__ import annotations

from pathlib import Path
from unittest import TestCase
import configparser
import shlex


ASSETS = Path(__file__).resolve().parents[1] / "assets"


def parse_ini(text: str) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read_string(text)
    return parser


class PreferencesTests(TestCase):
    def bindings(self) -> configparser.ConfigParser:
        asset = ASSETS / "binds.conf"
        self.assertTrue(asset.is_file(), "Mail-local navigation/search bindings are missing")
        return parse_ini("[global]\n" + asset.read_text())

    def test_desktop_entry_uses_managed_launcher_without_changing_defaults(self) -> None:
        asset = ASSETS / "aerc-mail.desktop"
        self.assertTrue(asset.is_file(), "The searchable managed desktop entry is missing")
        entry = parse_ini(asset.read_text())["Desktop Entry"]
        self.assertEqual(entry["Type"], "Application")
        self.assertEqual(entry["Name"], "aerc Mail")
        for key in ("Exec", "TryExec"):
            self.assertEqual(shlex.split(entry[key]), ["/home/narol/.local/bin/glaze-mail"])
        self.assertFalse(entry.getboolean("Terminal"))
        self.assertFalse(entry.getboolean("StartupNotify"))
        self.assertFalse(entry.getboolean("NoDisplay", False))
        self.assertFalse(entry.getboolean("Hidden", False))
        self.assertEqual(entry["StartupWMClass"], "aerc-mail")
        self.assertEqual(entry["Icon"], "internet-mail")
        self.assertEqual(entry["Categories"], "Network;Email;")
        self.assertTrue({"aerc", "mail", "email", "Gmail", "Glaze", "Inbox"}.issubset(entry["Keywords"].split(";")))
        self.assertNotIn("MimeType", entry)

    def test_navigation_is_context_local(self) -> None:
        bindings = self.bindings()
        for key, command in {"i": "prev", "k": "next", "I": "prev-folder", "K": "next-folder"}.items():
            self.assertEqual(bindings["messages"].get(key), f":{command}<Enter>")
        for key, command in {"I": "prev", "K": "next"}.items():
            self.assertEqual(bindings["view"].get(key), f":{command}<Enter>")
        for section in ("messages", "view"):
            self.assertEqual(bindings[section].get("j"), ":prev-tab<Enter>")
            self.assertEqual(bindings[section].get("l"), ":next-tab<Enter>")
            self.assertNotIn("J", bindings[section])
        for section in ("global", "compose", "compose::editor", "terminal"):
            for key in ("i", "k", "I", "K"):
                self.assertNotIn(key, bindings[section])

    def test_tab_keys_work_in_review_but_remain_literal_while_typing(self) -> None:
        bindings = self.bindings()
        self.assertEqual(bindings["compose::review"].get("j", "").split(" #", 1)[0], ":prev-tab<Enter>")
        self.assertEqual(bindings["compose::review"].get("l", "").split(" #", 1)[0], ":next-tab<Enter>")
        for section in ("global", "compose", "compose::editor", "view::passthrough", "terminal"):
            with self.subTest(section=section):
                self.assertNotIn("j", bindings[section])
                self.assertNotIn("l", bindings[section])
                if section != "global":
                    self.assertEqual(bindings[section]["$noinherit"], "true")

    def test_search_replaces_page_and_tab_bindings_only_in_mail_contexts(self) -> None:
        bindings = self.bindings()
        self.assertEqual(bindings["messages"].get("<C-f>"), ":search -a<space>")
        self.assertEqual(bindings["view"].get("<C-f>"), ":toggle-key-passthrough<Enter>/")
        for section, prefix in (("messages", ""), ("view", ":close<Enter>")):
            command = bindings[section].get("<C-p>", "")
            self.assertTrue(command.startswith(prefix + ':{{if eq .Folder "[Gmail]/All Mail"}}echo'))
            self.assertIn("{{else}}cf '[Gmail]/All Mail'{{end}}<Enter>:prompt 'Search All Mail: ' search ", command)
            self.assertIn("--all-mail-still-loading-retry-ctrl-p", command)
            self.assertIn('{{if eq .Folder "[Gmail]/All Mail"}}-a{{else}}', command)
            self.assertNotIn(":exec", command)
            self.assertNotIn("sleep", command)
        self.assertEqual(bindings["global"]["<C-PgUp>"], ":prev-tab<Enter>")
        self.assertEqual(bindings["messages"]["<PgDn>"], ":next 100%<Enter>")
        self.assertEqual(bindings["view::passthrough"]["<Esc>"], ":toggle-key-passthrough<Enter>")

    def test_pager_keys_do_not_remap_line_editing(self) -> None:
        asset = ASSETS / "lesskey"
        self.assertTrue(asset.is_file(), "Mail-local pager keys are missing")
        self.assertEqual(asset.read_text().splitlines(), ["#command", "i back-line", "k forw-line"])

    def test_unrelated_bindings_and_o_are_preserved(self) -> None:
        bindings = self.bindings()
        baseline = parse_ini("[global]\n" + Path("/usr/share/aerc/binds.conf").read_text())
        self.assertEqual(bindings.sections(), baseline.sections())
        changed = {"messages": {"i", "k", "I", "K", "j", "l", "J", "<C-f>", "<C-p>"},
                   "view": {"I", "K", "j", "l", "J", "<C-f>", "<C-p>"},
                   "compose::review": {"j", "l"}}
        for section in baseline.sections():
            excluded = changed.get(section, set())
            self.assertEqual({key: value for key, value in bindings[section].items() if key not in excluded},
                             {key: value for key, value in baseline[section].items() if key not in excluded})
        for key in ("o", "O"):
            self.assertEqual(bindings["view"][key], ":open<Enter>")
