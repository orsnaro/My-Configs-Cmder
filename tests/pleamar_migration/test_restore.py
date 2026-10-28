"""Restore exercises real synthetic homes; no service/desktop operations."""
from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from typing import Any
from unittest import mock

from tools.pleamar_migration.snapshot import snapshot

try:
    restore = importlib.import_module("tools.pleamar_migration.restore")
except ModuleNotFoundError as error:
    if error.name != "tools.pleamar_migration.restore":
        raise
    restore = None


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class RestoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertIsNotNone(restore, "R2 restore implementation does not exist")
        self.temporary = tempfile.TemporaryDirectory(prefix="pleamar-restore-", dir="/tmp/opencode")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.home = self.base / "home"
        self.home.mkdir()
        self.destination = self.base / "restored-home"
        self.public = self.base / "public"
        self.private = self.base / "private"

    def write(self, name: str, data: bytes = b"original\n", mode: int = 0o640) -> Path:
        path = self.home / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(mode)
        return path

    def capture(self, *names: str, audit: dict[str, str] | None = None) -> None:
        snapshot(self.home, [Path(name) for name in names], self.public, self.private, public_audit=audit)

    def restore_private(self) -> None:
        actions = restore.plan_restore(self.private, self.destination)
        restore.apply_restore(actions, self.destination, apply=True)

    def test_default_is_read_only(self) -> None:
        self.write(".config/app/main.conf")
        self.capture(".config/app")
        actions = restore.plan_restore(self.private, self.destination)
        self.assertTrue(actions)
        restore.apply_restore(actions, self.destination)
        self.assertFalse(self.destination.exists())
        restore.apply_restore(actions, self.destination, apply=True)
        self.assertEqual((self.destination / ".config/app/main.conf").read_bytes(), b"original\n")

    def test_sandbox_restore_remaps_home_symlinks(self) -> None:
        source = self.write(".mydotfiles/app/main.conf")
        alias = self.home / ".config/app"
        alias.parent.mkdir()
        alias.symlink_to(source.parent)
        self.capture(".config/app")
        self.restore_private()
        restored_alias = self.destination / ".config/app"
        self.assertTrue(restored_alias.is_symlink())
        self.assertTrue(restored_alias.resolve().is_relative_to(self.destination))
        self.assertEqual((restored_alias / "main.conf").read_bytes(), b"original\n")
        self.assertEqual(stat.S_IMODE((restored_alias / "main.conf").stat().st_mode), 0o640)
        self.assertEqual(source.read_bytes(), b"original\n")

    def test_pair_restore_merges_alias_metadata_and_public_bytes(self) -> None:
        source = self.write(".mydotfiles/app/main.conf", b"safe=1\n")
        alias = self.home / ".config/app"
        alias.parent.mkdir()
        alias.symlink_to(source.parent)
        self.capture(".config/app", audit={".config/app/main.conf": digest(b"safe=1\n")})
        actions = restore.plan_restore(self.public, self.destination, companion_root=self.private)
        restore.apply_restore(actions, self.destination, apply=True)
        self.assertTrue((self.destination / ".config/app").is_symlink())
        self.assertEqual((self.destination / ".config/app/main.conf").read_bytes(), b"safe=1\n")

    def test_alias_target_directory_keeps_its_own_mode(self) -> None:
        target = self.home / ".mydotfiles/app"
        target.mkdir(parents=True)
        target.chmod(0o750)
        (target / "main.conf").write_bytes(b"alias contents\n")
        alias = self.home / ".config/app"
        alias.parent.mkdir()
        alias.symlink_to(target)
        self.capture(".config/app")

        # Restoring onto the unchanged live home must not chmod the target to
        # the symlink's own 0777 mode.
        actions = restore.plan_restore(
            self.private, self.home, companion_root=self.public
        )
        self.assertEqual(actions, [])
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o750)

    def test_alias_target_directory_mode_is_preserved_in_sandbox(self) -> None:
        target = self.home / ".mydotfiles/app"
        target.mkdir(parents=True)
        target.chmod(0o750)
        (target / "main.conf").write_bytes(b"alias contents\n")
        alias = self.home / ".config/app"
        alias.parent.mkdir()
        alias.symlink_to(target)
        self.capture(".config/app")
        self.restore_private()
        restored_target = self.destination / ".mydotfiles/app"
        # The snapshot records the target directory's mode, not the symlink's
        # own 0777 lstat mode; restoration must keep that real mode.
        self.assertEqual(stat.S_IMODE(restored_target.stat().st_mode), 0o750)
        self.assertEqual((restored_target / "main.conf").read_bytes(), b"alias contents\n")

    def test_post_snapshot_edit_is_a_conflict(self) -> None:
        self.write(".config/app/main.conf")
        self.capture(".config/app")
        self.restore_private()
        path = self.destination / ".config/app/main.conf"
        path.write_bytes(b"later user work\n")
        with self.assertRaises(restore.RestoreConflict):
            restore.plan_restore(self.private, self.destination)
        self.assertEqual(path.read_bytes(), b"later user work\n")

    def test_retargeted_alias_is_a_conflict(self) -> None:
        source = self.write(".mydotfiles/app/main.conf")
        alias = self.home / ".config/app"
        alias.parent.mkdir()
        alias.symlink_to(source.parent)
        self.capture(".config/app")
        self.restore_private()
        outside = self.base / "unrelated"
        outside.mkdir()
        restored = self.destination / ".config/app"
        restored.unlink()
        restored.symlink_to(outside)
        with self.assertRaises(restore.RestoreConflict):
            restore.plan_restore(self.private, self.destination)
        self.assertEqual(restored.resolve(), outside)

    def test_only_journal_created_files_can_be_removed(self) -> None:
        self.write(".config/app/main.conf")
        self.capture(".config/app")
        self.restore_private()
        old = self.destination / ".config/app/main.conf"
        old.write_bytes(b"installed version\n")
        new = self.destination / "migration-created.txt"
        new.write_bytes(b"owned creation\n")
        unrelated = self.destination / "user-work.txt"
        unrelated.write_bytes(b"keep me\n")
        journal = self.base / "journal.json"
        journal.write_text(json.dumps({
            "home": str(self.destination),
            "installed": {
                ".config/app/main.conf": {"kind": "file", "sha256": digest(b"installed version\n"), "mode": 0o640},
                "migration-created.txt": {"kind": "file", "sha256": digest(b"owned creation\n"), "mode": 0o644},
            },
            "created": ["migration-created.txt"],
        }))
        journal.chmod(0o600)
        actions = restore.plan_restore(self.private, self.destination, journal=journal)
        restore.apply_restore(actions, self.destination, apply=True)
        self.assertEqual(old.read_bytes(), b"original\n")
        self.assertFalse(new.exists())
        self.assertEqual(unrelated.read_bytes(), b"keep me\n")

    def test_corrupt_payload_rejects_before_any_writes(self) -> None:
        self.write(".config/app/first.conf")
        self.write(".config/app/last.conf")
        self.capture(".config/app")
        actions = restore.plan_restore(self.private, self.destination)
        manifest = json.loads((self.private / "manifest.json").read_text())
        files = [entry for entry in manifest["entries"] if "payload" in entry]
        (self.private / files[-1]["payload"]).write_bytes(b"tampered\n")
        with self.assertRaises(restore.RestoreConflict):
            restore.apply_restore(actions, self.destination, apply=True)
        self.assertFalse(self.destination.exists())

    def test_parent_symlink_rejects_before_any_writes(self) -> None:
        self.write(".config/app/main.conf")
        self.capture(".config/app")
        self.destination.mkdir()
        outside = self.base / "outside"
        outside.mkdir()
        (self.destination / ".config").symlink_to(outside)
        with self.assertRaises(restore.RestoreConflict):
            restore.plan_restore(self.private, self.destination)
        self.assertEqual(list(outside.iterdir()), [])

    def test_post_plan_changes_are_detected_at_apply(self) -> None:
        self.write(".config/app/main.conf")
        self.capture(".config/app")
        actions = restore.plan_restore(self.private, self.destination)
        self.destination.mkdir()
        sentinel = self.destination / "new-user-file"
        sentinel.write_bytes(b"later work")
        with self.assertRaises(restore.RestoreConflict):
            restore.apply_restore(actions, self.destination, apply=True)
        self.assertEqual(sentinel.read_bytes(), b"later work")

    def test_external_alias_is_sandboxed_without_writing_external_source(self) -> None:
        external = self.base / "shared-helper"
        external.write_bytes(b"helper\n")
        alias = self.home / ".local/bin/helper"
        alias.parent.mkdir(parents=True)
        alias.symlink_to(external)
        self.capture(".local/bin/helper")
        self.restore_private()
        restored = self.destination / ".local/bin/helper"
        self.assertTrue(restored.is_symlink())
        self.assertTrue(restored.resolve().is_relative_to(self.destination))
        self.assertEqual(restored.read_bytes(), b"helper\n")
        self.assertEqual(external.read_bytes(), b"helper\n")

    def test_capture_deploy_journal_restore_round_trip(self) -> None:
        app = self.home / ".config/app"
        (app / "sub").mkdir(parents=True)
        (app / "empty-dir").mkdir()
        for name, data, mode in (
            ("a.conf", b"alpha\n", 0o640),
            ("sub/b.conf", b"beta\n", 0o600),
        ):
            target = app / name
            target.write_bytes(data)
            target.chmod(mode)
        (app / "link.conf").symlink_to("a.conf")
        app.chmod(0o750)
        (app / "empty-dir").chmod(0o711)
        self.capture(".config/app")

        deployed = app / "a.conf"
        deployed.write_bytes(b"deployed alpha\n")
        deployed.chmod(0o600)
        created = app / "new-file"
        created.write_bytes(b"deployment artifact\n")
        created.chmod(0o644)
        (app / "sub/b.conf").unlink()
        journal = self.base / "journal.json"
        journal.write_text(json.dumps({
            "home": str(self.destination),
            "installed": {
                ".config/app/a.conf": {"kind": "file", "sha256": digest(b"deployed alpha\n"), "mode": 0o600},
                ".config/app/new-file": {"kind": "file", "sha256": digest(b"deployment artifact\n"), "mode": 0o644},
            },
            "created": [".config/app/new-file"],
        }))
        journal.chmod(0o600)

        # A complete backup is the public+private pair; empty directories
        # carry no secret and therefore live in the public manifest.
        actions = restore.plan_restore(
            self.private, self.destination, journal=journal, companion_root=self.public
        )
        restore.apply_restore(actions, self.destination, apply=True)

        manifest = json.loads((self.private / "manifest.json").read_text())
        restored_app = self.destination / ".config/app"
        self.assertFalse((restored_app / "new-file").exists())
        expected = {
            ".config/app/a.conf": (b"alpha\n", 0o640),
            ".config/app/sub/b.conf": (b"beta\n", 0o600),
        }
        for logical, (data, mode) in expected.items():
            restored = self.destination / logical
            self.assertEqual(restored.read_bytes(), data, logical)
            self.assertEqual(stat.S_IMODE(restored.stat().st_mode), mode, logical)
        self.assertEqual(os.readlink(restored_app / "link.conf"), "a.conf")
        self.assertEqual(stat.S_IMODE(restored_app.stat().st_mode), 0o750)
        self.assertEqual(stat.S_IMODE((restored_app / "empty-dir").stat().st_mode), 0o711)
        public_manifest = json.loads((self.public / "manifest.json").read_text())
        self.assertEqual(len(manifest["entries"]) + len(public_manifest["entries"]), 6)

    def test_apply_restore_validates_each_snapshot_root_once_per_call(self) -> None:
        for index in range(3):
            self.write(f".config/app/{index}.conf", f"value={index}\n".encode())
        self.capture(".config/app")
        actions = restore.plan_restore(self.private, self.destination)

        with mock.patch.object(
            restore, "verify_snapshot", wraps=restore.verify_snapshot
        ) as verify:
            restore.apply_restore(actions, self.destination)
            self.assertEqual(verify.call_count, 1)
            verify.reset_mock()
            restore.apply_restore(actions, self.destination, apply=True)
            self.assertEqual(verify.call_count, 1)

        self.assertTrue((self.destination / ".config/app/0.conf").is_file())

    def test_per_file_tamper_is_rejected_after_root_validation(self) -> None:
        self.write(".config/app/first.conf", b"first\n")
        self.write(".config/app/last.conf", b"last\n")
        self.capture(".config/app")
        actions = restore.plan_restore(self.private, self.destination)
        manifest = json.loads((self.private / "manifest.json").read_text())
        files = [entry for entry in manifest["entries"] if "payload" in entry]
        (self.private / files[-1]["payload"]).write_bytes(b"tampered\n")

        # Even if whole-root verification is cached/ok, the per-file digest
        # check must still reject tampered payloads before any destination
        # writes.
        with mock.patch.object(restore, "verify_snapshot", return_value=[]):
            with self.assertRaises(restore.RestoreConflict):
                restore.apply_restore(actions, self.destination, apply=True)
        self.assertFalse(self.destination.exists())

    def test_payload_tamper_during_writes_is_rejected(self) -> None:
        self.write(".config/app/main.conf", b"original\n")
        self.capture(".config/app")
        actions = restore.plan_restore(self.private, self.destination)
        write_action = next(
            action for action in actions if action["operation"] == "write"
        )
        source = Path(write_action["source"])
        real_read = Path.read_bytes
        reads = {"count": 0}

        def racing_read(path: Path) -> bytes:
            data = real_read(path)
            if path == source:
                reads["count"] += 1
                if reads["count"] == 2:
                    source.write_bytes(b"swapped during apply\n")
                    return real_read(source)
            return data

        with mock.patch.object(restore.Path, "read_bytes", racing_read):
            with self.assertRaises(restore.RestoreConflict):
                restore.apply_restore(actions, self.destination, apply=True)

        self.assertFalse((self.destination / ".config/app/main.conf").exists())

    def test_permission_modes_survive(self) -> None:
        source = self.write(".config/app/private.conf", b"private configuration\n", mode=0o750)
        source.parent.chmod(0o710)
        self.capture(".config/app")
        self.restore_private()
        restored = self.destination / ".config/app/private.conf"
        self.assertEqual(stat.S_IMODE(restored.stat().st_mode), 0o750)
        self.assertEqual(stat.S_IMODE(restored.parent.stat().st_mode), 0o710)
        self.assertEqual(restored.read_bytes(), source.read_bytes())


if __name__ == "__main__":
    unittest.main()
