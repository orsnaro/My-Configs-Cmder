"""Exercise the active GTK4 theme, including collapsed-stack rendering."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
import subprocess
import warnings

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gtk


STYLE = Path(__file__).resolve().parents[1] / "style.css"


class ThemeTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        Gtk.init()
        cls.provider = Gtk.CssProvider()
        cls.diagnostics: list[str] = []
        cls.provider.connect("parsing-error", cls._on_error)
        cls.provider.load_from_path(str(STYLE))
        display = Gdk.Display.get_default()
        if display is None:
            raise RuntimeError("GTK4 theme tests need a display")
        Gtk.StyleContext.add_provider_for_display(display, cls.provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

    @staticmethod
    def _on_error(_provider: Gtk.CssProvider, section: Gtk.CssSection, error: object) -> None:
        ThemeTests.diagnostics.append(f"{section.get_start_location().lines + 1}: {error}")

    def test_imported_theme_has_no_gtk4_diagnostics(self) -> None:
        self.assertEqual(self.diagnostics, [])

    def test_normal_and_critical_cards_have_padding_and_border(self) -> None:
        for urgency in ("normal", "critical"):
            with self.subTest(urgency=urgency):
                root = Gtk.Box(css_classes=["control-center"])
                row = Gtk.Box(css_classes=["notification-row"])
                background = Gtk.Box(css_classes=["notification-background"])
                card = Gtk.Box(css_classes=["notification", urgency])
                root.append(row)
                row.append(background)
                background.append(card)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", DeprecationWarning)
                    context = card.get_style_context()
                    self.assertGreaterEqual(context.get_padding().top, 10)
                    self.assertGreaterEqual(context.get_border().left, 1)

    def test_group_heading_has_readable_font_size(self) -> None:
        header = Gtk.Box(css_classes=["notification-group-headers"])
        label = Gtk.Label(label="Mail")
        header.append(label)
        self.assertGreater(label.get_pango_context().get_font_description().get_size(), 0)

    def test_only_lower_collapsed_card_contents_are_hidden(self) -> None:
        # Render actual GTK nodes: removing the collapsed selector reveals LOWER;
        # making it unconditional also hides LOWER in the expanded fixture.
        for action_class in ("notification-default-action", "notification-action"):
            for collapsed in (True, False):
                with self.subTest(collapsed=collapsed, action_class=action_class):
                    node = self._render_group(collapsed, action_class)
                    self.assertEqual(node.count("text {"), 1 if collapsed else 2, node)

    def _render_group(self, collapsed: bool, action_class: str) -> str:
        classes = '<class name="collapsed"/>' if collapsed else ""
        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<interface>
  <object class="GtkBox" id="group">
    <property name="orientation">vertical</property>
    <style><class name="notification-group"/>{classes}</style>
    <child><object class="GtkBox">
      <style><class name="notification-row"/></style>
      <child><object class="GtkLabel">
        <property name="label">LOWER</property>
        <style><class name="{action_class}"/></style>
      </object></child>
    </object></child>
    <child><object class="GtkBox">
      <style><class name="notification-row"/></style>
      <child><object class="GtkLabel">
        <property name="label">FRONT</property>
        <style><class name="{action_class}"/></style>
      </object></child>
    </object></child>
  </object>
</interface>'''
        with TemporaryDirectory(prefix="swaync-theme-test-", dir="/tmp/opencode") as temporary:
            fixture = Path(temporary) / "group.ui"
            fixture.write_text(xml)
            result = subprocess.run(
                ["gtk4-builder-tool", "render", "--node", "--id=group", f"--css={STYLE}", str(fixture)],
                capture_output=True, text=True, timeout=15, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            return fixture.with_suffix(".node").read_text()
