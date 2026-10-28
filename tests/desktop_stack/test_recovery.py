"""Sandboxed recovery tests for the private Pleamar snapshot wrapper.

Every fixture root lives under /tmp/opencode.  Recovery must only touch the
explicit destination home and an owner-private checkpoint; it never activates a
desktop stack or calls service/process commands.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from typing import Any
from unittest import mock

from tools.pleamar_migration.snapshot import snapshot, verify_snapshot

try:
    import tools.pleamar_recovery as recovery
except ImportError as error:
    if "pleamar_recovery" not in str(error):
        raise
    recovery = None


REPO_ROOT = Path(__file__).resolve().parents[2]


class RecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertIsNotNone(recovery, "recovery wrapper does not exist")
        self.temporary = tempfile.TemporaryDirectory(
            prefix="pleamar-recovery-", dir="/tmp/opencode"
        )
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.source_home = self.base / "source-home"
        self.destination = self.base / "destination-home"
        self.bundle = self.base / "snapshot"
        self.private = self.bundle / "private"
        self.public = self.bundle / "public"
        self.pointer = self.base / "pleamar-current.json"
        self.checkpoints = self.base / "checkpoints"
        self.source_home.mkdir()
        self.source_mode = 0o600

    # -- fixture helpers -------------------------------------------------
    def write_source(
        self, name: str, data: bytes, mode: int = 0o600
    ) -> Path:
        path = self.source_home / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(mode)
        return path

    def capture(self, *names: str) -> None:
        snapshot(
            self.source_home,
            [Path(name) for name in names],
            self.public,
            self.private,
        )

    def write_destination(
        self, name: str, data: bytes, mode: int = 0o600
    ) -> Path:
        path = self.destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(mode)
        return path

    def write_pointer(self, snapshot_root: Any, companion_root: Any) -> Path:
        self.pointer.write_text(
            json.dumps(
                {
                    "snapshot_root": snapshot_root,
                    "companion_root": companion_root,
                }
            )
        )
        self.pointer.chmod(0o600)
        return self.pointer

    def recover(self, *, apply: bool = False, **overrides: Any) -> dict[str, Any]:
        arguments: dict[str, Any] = {
            "snapshot": self.bundle,
            "home": self.destination,
            "apply": apply,
            "pointer": self.pointer,
            "repo_root": self.base,
            "checkpoint_parent": self.checkpoints,
        }
        arguments.update(overrides)
        return recovery.recover(**arguments)

    # -- tests -----------------------------------------------------------
    def test_default_preview_writes_nothing(self) -> None:
        self.write_source(".config/pleamar/scene.json", b"original scene\n")
        self.capture(".config/pleamar")
        live = self.write_destination(".config/pleamar/scene.json", b"later edit\n")

        result = self.recover(apply=False)

        self.assertFalse(result["applied"])
        self.assertIsNone(result["checkpoint"])
        self.assertTrue(result["actions"])
        self.assertEqual(live.read_bytes(), b"later edit\n")
        self.assertFalse(self.checkpoints.exists())
        self.assertEqual(sorted(p.name for p in self.destination.iterdir()), [".config"])

    def test_missing_pointer_rejects_without_writes(self) -> None:
        self.write_source(".config/pleamar/scene.json", b"original scene\n")
        self.capture(".config/pleamar")
        live = self.write_destination(".config/pleamar/scene.json", b"later edit\n")

        with self.assertRaises(recovery.RecoveryError):
            self.recover(snapshot=None, apply=True)

        self.assertEqual(live.read_bytes(), b"later edit\n")
        self.assertFalse(self.checkpoints.exists())

    def test_pointer_rejects_absolute_and_traversal_roots(self) -> None:
        for snapshot_root, companion_root in (
            (str(self.private), "snapshot/public"),
            ("../outside/private", "snapshot/public"),
            ("snapshot/private", "/tmp/outside/public"),
            ("snapshot/../private", "snapshot/public"),
        ):
            with self.subTest(snapshot_root=snapshot_root):
                self.write_pointer(snapshot_root, companion_root)
                with self.assertRaises(recovery.RecoveryError):
                    recovery.load_pointer(self.pointer, self.base)

    def test_default_pointer_supplies_repository_relative_roots(self) -> None:
        self.write_source(".config/pleamar/scene.json", b"original scene\n")
        self.capture(".config/pleamar")
        self.write_destination(".config/pleamar/scene.json", b"later edit\n")
        self.write_pointer("snapshot/private", "snapshot/public")

        result = self.recover(snapshot=None, apply=False)

        self.assertEqual(result["snapshot_root"], str(self.private))
        self.assertEqual(result["companion_root"], str(self.public))
        self.assertFalse(result["applied"])

    def test_corrupt_snapshot_rejects_before_checkpoint(self) -> None:
        self.write_source(".config/pleamar/scene.json", b"original scene\n")
        self.capture(".config/pleamar")
        live = self.write_destination(".config/pleamar/scene.json", b"later edit\n")
        manifest = json.loads((self.private / "manifest.json").read_text())
        payload = next(entry["payload"] for entry in manifest["entries"] if "payload" in entry)
        (self.private / payload).write_bytes(b"tampered payload\n")

        with self.assertRaises(recovery.RecoveryError):
            self.recover(apply=True)

        self.assertEqual(live.read_bytes(), b"later edit\n")
        self.assertFalse(self.checkpoints.exists())

    def test_missing_snapshot_rejects_without_writes(self) -> None:
        self.destination.mkdir()
        missing = self.base / "missing-snapshot"
        with self.assertRaises(recovery.RecoveryError):
            self.recover(snapshot=missing, apply=True)
        self.assertEqual(list(self.destination.iterdir()), [])
        self.assertFalse(self.checkpoints.exists())

    def test_apply_restores_and_checkpoints_changed_bytes(self) -> None:
        self.write_source(".config/pleamar/scene.json", b"original scene\n", 0o640)
        self.capture(".config/pleamar")
        live = self.write_destination(".config/pleamar/scene.json", b"later edit\n", 0o600)

        result = self.recover(apply=True, checkpoint_parent=None)

        self.assertTrue(result["applied"])
        checkpoint = Path(result["checkpoint"])
        self.assertEqual(checkpoint.parent, self.checkpoints)
        self.assertTrue(checkpoint.is_dir())
        self.assertEqual(live.read_bytes(), b"original scene\n")
        self.assertEqual(stat.S_IMODE(live.stat().st_mode), 0o640)

        checkpoint_private = checkpoint / "private"
        self.assertEqual(verify_snapshot(checkpoint_private), [])
        manifest = json.loads((checkpoint_private / "manifest.json").read_text())
        entry = next(
            record
            for record in manifest["entries"]
            if record["logical_path"] == ".config/pleamar/scene.json"
        )
        payload = checkpoint_private / entry["payload"]
        self.assertEqual(payload.read_bytes(), b"later edit\n")
        self.assertEqual(stat.S_IMODE(checkpoint.stat().st_mode), 0o700)

    def test_apply_checkpoints_through_a_symlinked_config_root(self) -> None:
        target = self.source_home / ".dotfiles/app"
        target.mkdir(parents=True)
        original = target / "main.conf"
        original.write_bytes(b"original through alias\n")
        original.chmod(0o600)
        alias = self.source_home / ".config/app"
        alias.parent.mkdir()
        alias.symlink_to(target)
        self.capture(".config/app")

        destination_target = self.destination / ".dotfiles/app"
        destination_target.mkdir(parents=True)
        live = destination_target / "main.conf"
        live.write_bytes(b"later edit through alias\n")
        live.chmod(0o600)
        (self.destination / ".config").mkdir()
        (self.destination / ".config/app").symlink_to(destination_target)

        result = self.recover(apply=True, checkpoint_parent=None)

        self.assertTrue(result["applied"])
        self.assertEqual(live.read_bytes(), b"original through alias\n")
        self.assertTrue((self.destination / ".config/app").is_symlink())
        checkpoint_private = Path(result["checkpoint"]) / "private"
        manifest = json.loads((checkpoint_private / "manifest.json").read_text())
        entry = next(
            record
            for record in manifest["entries"]
            if record["logical_path"] == ".dotfiles/app/main.conf"
        )
        self.assertEqual(
            (checkpoint_private / entry["payload"]).read_bytes(),
            b"later edit through alias\n",
        )

    def test_checkpoint_skips_home_and_never_recurses_into_itself(self) -> None:
        self.destination.mkdir()
        live = self.write_destination(".config/pleamar/scene.json", b"live bytes\n")
        parent = self.destination / "checkpoints"
        actions = [
            {
                "path": str(self.destination),
                "operation": "chmod",
                "expected": {"kind": "dir", "mode": 0o700},
                "desired": {"kind": "dir", "mode": 0o700},
            },
            {
                "path": str(live),
                "operation": "write",
                "expected": {
                    "kind": "file",
                    "mode": 0o600,
                    "sha256": "0" * 64,
                },
                "desired": {"kind": "file", "mode": 0o600, "sha256": "0" * 64},
            },
        ]

        checkpoint = recovery.create_checkpoint(actions, self.destination, parent)

        self.assertTrue(checkpoint.is_relative_to(parent))
        manifest = json.loads((checkpoint / "private/manifest.json").read_text())
        logical = {entry["logical_path"] for entry in manifest["entries"]}
        self.assertEqual(logical, {".config/pleamar/scene.json"})
        self.assertFalse(any("checkpoints" in path for path in logical))

    def test_apply_preserves_runtime_helper_modes_and_private_pairing(self) -> None:
        helper = b"#!/bin/sh\nexit 0\n"
        runtime = b"runtime bytes\n"
        pairing = b'{"pairing":"fixture-private-value"}\n'
        self.write_source(".config/pleamar/bin/helper", helper, 0o755)
        self.write_source(".config/pleamar/runtime/vitreus", runtime, 0o750)
        self.write_source(".config/pleamar/integration/pairing.json", pairing, 0o600)
        self.capture(".config/pleamar")

        result = self.recover(apply=True)

        self.assertTrue(result["applied"])
        expected = {
            ".config/pleamar/bin/helper": (helper, 0o755),
            ".config/pleamar/runtime/vitreus": (runtime, 0o750),
            ".config/pleamar/integration/pairing.json": (pairing, 0o600),
        }
        for name, (data, mode) in expected.items():
            restored = self.destination / name
            self.assertEqual(restored.read_bytes(), data, name)
            self.assertEqual(stat.S_IMODE(restored.stat().st_mode), mode, name)
        checkpoint = Path(result["checkpoint"])
        self.assertTrue(checkpoint.is_dir())
        self.assertEqual(verify_snapshot(checkpoint / "private"), [])
        self.assertEqual(
            json.loads((checkpoint / "checkpoint.json").read_text())["source_count"],
            0,
        )

    def test_no_desktop_command_executes(self) -> None:
        self.write_source(".config/pleamar/scene.json", b"original scene\n")
        self.capture(".config/pleamar")
        self.write_destination(".config/pleamar/scene.json", b"later edit\n")

        def forbidden(*args: Any, **kwargs: Any) -> None:
            raise AssertionError("recovery must not activate or control a desktop")

        with mock.patch("subprocess.run", side_effect=forbidden), mock.patch(
            "subprocess.Popen", side_effect=forbidden
        ), mock.patch("os.system", side_effect=forbidden), mock.patch(
            "os.execv", side_effect=forbidden
        ), mock.patch(
            "os.spawnv", side_effect=forbidden
        ):
            result = self.recover(apply=True)

        self.assertTrue(result["applied"])

    def test_cli_defaults_to_preview_and_writes_nothing(self) -> None:
        self.write_source(".config/pleamar/scene.json", b"original scene\n")
        self.capture(".config/pleamar")
        live = self.write_destination(".config/pleamar/scene.json", b"later edit\n")
        environment = dict(os.environ, TMPDIR="/tmp/opencode", PYTHONDONTWRITEBYTECODE="1")

        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(REPO_ROOT / "tools/pleamar_recovery.py"),
                "--snapshot",
                str(self.bundle),
                "--home",
                str(self.destination),
            ],
            cwd=REPO_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertFalse(json.loads(completed.stdout)["applied"])
        self.assertEqual(live.read_bytes(), b"later edit\n")
        self.assertFalse(self.checkpoints.exists())


if __name__ == "__main__":
    unittest.main()
