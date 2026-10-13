"""Exercise the real backup/restore scripts with disposable homes and rsync."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class BackupRestoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="config-backup-", dir="/tmp/opencode")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.snapshot = self.root / "snapshot"
        self.snapshot.mkdir()
        (self.snapshot / "dotfiles/.config/ml4w").mkdir(parents=True)
        for name in ("BACKUP.sh", "RESTORE.sh"):
            shutil.copy2(ROOT / name, self.snapshot / name)
        self.home = self.root / "source-home"
        self.home.mkdir()
        for relative in (
            "hypr", "kitty/patches", "quickshell", "waybar", "rofi", "swaync",
            "ml4w/scripts", "ml4w/settings", "ml4w-dock", "ml4w-statusbar",
            "fastfetch", "fish",
        ):
            self.write(self.home / ".config" / relative / "fixture.conf", "current\n")
        self.write(self.home / ".config/kitty/patches/native.diff", "patch\n")
        self.write(self.home / ".local/bin/glaze-quake", "#!/bin/sh\nexit 0\n")
        self.write(self.home / ".local/share/applications/quake-kitty.desktop", "[Desktop Entry]\n")
        for name in ("ml4w-dock", "quickshell-overview", "ml4w-dotfiles-settings"):
            self.write(self.home / ".local/share" / name / "fixture.qml", "source\n")
        self.commands = self.root / "commands"
        self.commands.mkdir()
        kitty = self.commands / "kitty"
        self.write(kitty, "#!/bin/sh\nprintf 'kitty fixture\\n'\n")
        kitty.chmod(0o755)

    @staticmethod
    def write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def run_script(self, name: str, home: Path, *args: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ | {
            "HOME": str(home),
            "PATH": f"{self.commands}:{os.environ['PATH']}",
            "TMPDIR": str(self.root),
        }
        result = subprocess.run(
            ["bash", str(self.snapshot / name), *args],
            env=environment, input="N\n", capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_backup_includes_wallpaper_and_dolphin_dependencies(self) -> None:
        dependencies = (
            "ml4w/listeners.sh", "ml4w/themes/default.conf", "ml4w/assets/logo.svg",
            "ml4w/colors/colors.json", "ml4w/version.json", "ml4w/bin/settings",
            "ml4w/listeners/gtk-theme-switcher.sh",
            "matugen/config.toml",
            "matugen/templates/kitty-colors.conf",
            "hyprland-kde-overrides/dolphinrc",
            "walker/config.toml", "elephant/desktopapplications.toml",
            "ohmyposh/custom.omp.json", "gtk-3.0/settings.ini", "gtk-4.0/gtk.css",
            "gcal/gcal-consent.py", "gcal/gcal-sync.py", "gcal/gcal-remind.py",
            "gcal/tests/test_sync.py",
        )
        for relative in dependencies:
            self.write(self.home / ".config" / relative, f"dependency {relative}\n")
        self.run_script("BACKUP.sh", self.home)
        for relative in dependencies:
            with self.subTest(path=relative):
                self.assertTrue((self.snapshot / "dotfiles/.config" / relative).is_file())
                self.assertEqual(
                    (self.snapshot / "dotfiles/.config" / relative).read_text(),
                    f"dependency {relative}\n",
                )

    def test_restore_includes_wallpaper_and_dolphin_dependencies(self) -> None:
        dependencies = (
            "ml4w/listeners.sh", "ml4w/themes/default.conf", "ml4w/assets/logo.svg",
            "ml4w/colors/colors.json", "ml4w/version.json", "ml4w/bin/settings",
            "ml4w/listeners/gtk-theme-switcher.sh", "matugen/config.toml",
            "matugen/templates/kitty-colors.conf", "hyprland-kde-overrides/dolphinrc",
            "walker/config.toml", "elephant/desktopapplications.toml",
            "ohmyposh/custom.omp.json", "gtk-3.0/settings.ini", "gtk-4.0/gtk.css",
            "gcal/gcal-consent.py", "gcal/gcal-sync.py", "gcal/gcal-remind.py",
            "gcal/tests/test_sync.py",
        )
        for relative in dependencies:
            self.write(self.snapshot / "dotfiles/.config" / relative, "restored\n")
        destination = self.root / "restored-home"
        self.run_script("RESTORE.sh", destination)
        for relative in dependencies:
            with self.subTest(path=relative):
                self.assertTrue((destination / ".config" / relative).is_file())
                self.assertEqual((destination / ".config" / relative).read_text(), "restored\n")

    def test_backup_excludes_secrets_caches_and_scratch_but_keeps_patch_sources(self) -> None:
        artifacts = (
            "settings.bak", "settings.bak-20261012", "config.jsonc.pre-gif-bak", "backup-old/config",
            ".superpowers/sdd/progress.md", ".opencode/plan.md", ".git/config",
            "__pycache__/module.pyc", ".pytest_cache/results", ".cache/data",
            ".env", ".env.local", "credentials.json", "token.json",
            "client_secret_fixture.json", "node_modules/module/index.js", ".venv/bin/python",
        )
        trees = (
            (self.home / ".config/hypr", self.snapshot / "dotfiles/.config/hypr"),
            (self.home / ".config/kitty", self.snapshot / "dotfiles/.config/kitty"),
            (self.home / ".local/share/ml4w-dock", self.snapshot / "local/.local/share/ml4w-dock"),
        )
        for source, _ in trees:
            for relative in artifacts:
                self.write(source / relative, "must not publish\n")
        self.run_script("BACKUP.sh", self.home)
        for _, destination in trees:
            for relative in artifacts:
                with self.subTest(tree=destination.name, path=relative):
                    self.assertFalse((destination / relative).exists())
        self.assertEqual(
            (self.snapshot / "dotfiles/.config/kitty/patches/native.diff").read_text(), "patch\n",
        )

    def test_restore_dry_run_does_not_create_a_missing_home(self) -> None:
        self.run_script("BACKUP.sh", self.home)
        destination = self.root / "dry-home"
        self.run_script("RESTORE.sh", destination, "--dry-run")
        self.assertFalse(destination.exists())

    def test_restore_merges_without_removing_unrelated_files(self) -> None:
        self.run_script("BACKUP.sh", self.home)
        destination = self.root / "restored-home"
        self.write(destination / ".config/hypr/unrelated.conf", "preserve\n")
        self.run_script("RESTORE.sh", destination)
        self.assertEqual((destination / ".config/hypr/unrelated.conf").read_text(), "preserve\n")
        self.assertEqual((destination / ".config/hypr/fixture.conf").read_text(), "current\n")

    def test_backup_regenerates_manifest_from_current_snapshot(self) -> None:
        self.write(self.snapshot / "dotfiles/.config/hypr/obsolete.conf", "stale\n")
        self.run_script("BACKUP.sh", self.home)
        manifest = (self.snapshot / "manifest.txt").read_text().splitlines()
        self.assertIn("dotfiles/.config/hypr/fixture.conf", manifest)
        self.assertIn("local/.local/bin/glaze-quake", manifest)
        self.assertNotIn("dotfiles/.config/hypr/obsolete.conf", manifest)
        actual = sorted(
            str(file.relative_to(self.snapshot))
            for directory in ("dotfiles", "local")
            for file in (self.snapshot / directory).rglob("*") if file.is_file()
        )
        self.assertEqual(manifest, actual)

    def test_calendar_and_gtk_backup_only_capture_reviewed_sources(self) -> None:
        for relative in (
            "gcal/token.json", "gcal/cache.json", "gcal/notified.json", "gcal/agenda.txt",
            "gcal/.venv/bin/python", "gtk-3.0/bookmarks", "gtk-4.0/servers",
            "fish/fish_variables",
        ):
            self.write(self.home / ".config" / relative, "private state\n")
        self.run_script("BACKUP.sh", self.home)
        for relative in (
            "gcal/token.json", "gcal/cache.json", "gcal/notified.json", "gcal/agenda.txt",
            "gcal/.venv/bin/python", "gtk-3.0/bookmarks", "gtk-4.0/servers", "fish/fish_variables",
        ):
            with self.subTest(path=relative):
                self.assertFalse((self.snapshot / "dotfiles/.config" / relative).exists())

    def test_restore_dry_run_previews_bin_and_desktop_files(self) -> None:
        self.run_script("BACKUP.sh", self.home)
        destination = self.root / "restored-home"
        (destination / ".config").mkdir(parents=True)
        (destination / ".local/share/applications").mkdir(parents=True)
        (destination / ".local/bin").mkdir()
        result = self.run_script("RESTORE.sh", destination, "--dry-run")
        self.assertIn("glaze-quake", result.stdout)
        self.assertIn("quake-kitty.desktop", result.stdout)
        self.assertFalse((destination / ".local/bin/glaze-quake").exists())

    def test_restore_does_not_chmod_unrelated_bin_files(self) -> None:
        self.run_script("BACKUP.sh", self.home)
        destination = self.root / "restored-home"
        unrelated = destination / ".local/bin/data.txt"
        self.write(unrelated, "keep mode\n")
        unrelated.chmod(0o600)
        self.run_script("RESTORE.sh", destination)
        self.assertEqual(unrelated.stat().st_mode & 0o777, 0o600)

    def test_restored_dock_entrypoint_is_a_portable_link(self) -> None:
        self.write(self.home / ".local/share/ml4w-dock/bin/ml4w-dock", "#!/bin/sh\nexit 0\n")
        self.run_script("BACKUP.sh", self.home)
        destination = self.root / "restored-home"
        self.run_script("RESTORE.sh", destination)
        entrypoint = destination / ".local/bin/ml4w-dock"
        self.assertTrue(entrypoint.is_symlink())
        self.assertEqual(entrypoint.resolve(), destination / ".local/share/ml4w-dock/bin/ml4w-dock")


if __name__ == "__main__":
    unittest.main()
