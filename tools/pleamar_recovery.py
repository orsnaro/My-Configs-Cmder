"""File-only Pleamar recovery from the owner-private desktop snapshot.

The wrapper deliberately reuses the existing snapshot, authorize and restore
machinery.  It never starts, stops or reconfigures a desktop component; after a
successful file restore the coordinator still owns activation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POINTER = REPO_ROOT / "conf_backups/.private/pleamar-current.json"

# Running `python3 tools/pleamar_recovery.py` makes `tools/` importable but not
# the repository root that contains the `tools` package.
if not __package__ and str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.pleamar_migration import authorize, restore  # noqa: E402
from tools.pleamar_migration.snapshot import snapshot, verify_snapshot  # noqa: E402


class RecoveryError(RuntimeError):
    """Recovery prerequisites are missing, unsafe or inconsistent."""


def _within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _repository_path(value: Any, key: str, repo_root: Path) -> Path:
    if not isinstance(value, str) or not value:
        raise RecoveryError(f"pointer {key} must be a non-empty string")
    relative = Path(value)
    if relative.is_absolute() or any(
        part in ("", ".", "..") for part in relative.parts
    ):
        raise RecoveryError(f"pointer {key} must stay inside the repository")
    candidate = Path(os.path.abspath(repo_root / relative))
    if not _within(candidate, Path(os.path.abspath(repo_root))):
        raise RecoveryError(f"pointer {key} escapes the repository")
    return candidate


def load_pointer(pointer: Path, repo_root: Path) -> tuple[Path, Path]:
    """Load and validate the private pointer's repository-relative roots."""
    pointer = Path(os.path.abspath(pointer))
    repo_root = Path(os.path.abspath(repo_root))
    if pointer.is_symlink():
        raise RecoveryError(f"recovery pointer must not be a symlink: {pointer}")
    if not pointer.is_file():
        raise RecoveryError(f"missing recovery pointer: {pointer}")
    try:
        saved = json.loads(pointer.read_text())
    except (OSError, ValueError) as error:
        raise RecoveryError(f"unreadable recovery pointer: {error}") from error
    if not isinstance(saved, dict):
        raise RecoveryError("recovery pointer must be a JSON object")
    private_root = _repository_path(saved.get("snapshot_root"), "snapshot_root", repo_root)
    companion_root = _repository_path(
        saved.get("companion_root"), "companion_root", repo_root
    )
    if private_root == companion_root:
        raise RecoveryError("snapshot and companion roots must differ")
    return private_root, companion_root


def resolve_snapshot(
    snapshot_path: Path | None, pointer: Path, repo_root: Path
) -> tuple[Path, Path | None]:
    """Map an explicit snapshot bundle/root or the default pointer to roots."""
    if snapshot_path is None:
        private_root, companion_root = load_pointer(pointer, repo_root)
        return private_root, companion_root

    candidate = Path(os.path.abspath(snapshot_path))
    if not candidate.is_dir():
        raise RecoveryError(f"snapshot path is not a directory: {candidate}")
    if (candidate / "private/manifest.json").is_file():
        companion = candidate / "public"
        return candidate / "private", companion if companion.is_dir() else None
    if (candidate / "manifest.json").is_file():
        if candidate.name == "public":
            private = candidate.parent / "private"
            if (private / "manifest.json").is_file():
                return private, candidate
        companion = candidate.parent / "public"
        return candidate, companion if (companion / "manifest.json").is_file() else None
    raise RecoveryError(f"snapshot contains no manifest: {candidate}")


def _validate_roots(private_root: Path, companion_root: Path | None) -> None:
    if companion_root is not None and private_root == companion_root:
        raise RecoveryError("snapshot and companion roots must differ")
    for label, root in (("private", private_root), ("companion", companion_root)):
        if root is None:
            continue
        problems = verify_snapshot(root)
        if problems:
            raise RecoveryError(
                f"invalid {label} snapshot: " + "; ".join(problems[:5])
            )


def _destination_home(home: Path | None, private_root: Path) -> Path:
    if home is not None:
        destination = Path(os.path.abspath(home))
    else:
        try:
            manifest = json.loads((private_root / "manifest.json").read_text())
        except (OSError, ValueError) as error:
            raise RecoveryError(f"cannot read snapshot home: {error}") from error
        recorded = manifest.get("home") if isinstance(manifest, dict) else None
        if not isinstance(recorded, str) or not Path(recorded).is_absolute():
            raise RecoveryError("snapshot has no absolute original home; pass --home")
        destination = Path(os.path.abspath(recorded))
    if destination == Path(destination.anchor):
        raise RecoveryError("refusing the filesystem root as a recovery home")
    if destination.is_symlink():
        raise RecoveryError(f"recovery home must not be a symlink: {destination}")
    return destination


def _checkpoint_sources(
    actions: Sequence[dict[str, Any]], home: Path, checkpoint_root: Path
) -> list[Path]:
    """Collect existing files/links whose bytes are about to be replaced."""
    sources: list[Path] = []
    seen: set[str] = set()
    for action in actions:
        expected = action.get("expected")
        if not isinstance(expected, dict) or expected.get("kind") not in (
            "file",
            "symlink",
        ):
            continue
        path = Path(action["path"])
        if path == home:
            continue
        try:
            relative = path.relative_to(home)
        except ValueError as error:
            raise RecoveryError(f"checkpoint source escapes home: {path}") from error
        if not relative.parts or any(
            part in ("", ".", "..") for part in relative.parts
        ):
            raise RecoveryError(f"unsafe checkpoint source: {path}")
        if _within(path, checkpoint_root) or path == checkpoint_root:
            raise RecoveryError("checkpoint cannot cover itself")
        if expected["kind"] == "symlink":
            target = Path(os.path.realpath(path))
            if target == home or _within(home, target):
                raise RecoveryError("refusing to checkpoint a home root through a symlink")
            if _within(target, checkpoint_root) or _within(checkpoint_root, target):
                raise RecoveryError("checkpoint overlaps a destination symlink target")
        key = relative.as_posix()
        if key not in seen:
            seen.add(key)
            sources.append(relative)
    return sources


def create_checkpoint(
    actions: Sequence[dict[str, Any]], home: Path, checkpoint_parent: Path
) -> Path:
    """Snapshot affected destination bytes into an owner-private checkpoint."""
    parent = Path(os.path.abspath(checkpoint_parent))
    if parent.is_symlink():
        raise RecoveryError("checkpoint parent must not be a symlink")
    if parent.exists() and not parent.is_dir():
        raise RecoveryError(f"checkpoint parent is not a directory: {parent}")
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    root = parent / stamp
    if root.exists():
        root = parent / f"{stamp}-{os.getpid()}"
    root.mkdir(mode=0o700)
    os.chmod(root, 0o700)

    sources = _checkpoint_sources(actions, home, root)
    if not sources:
        # No destination bytes are replaced.  Publish an empty, verifiable
        # snapshot pair anyway so every checkpoint has the same schema.
        with tempfile.TemporaryDirectory(
            prefix=".empty-checkpoint-", dir=parent
        ) as scratch:
            empty_home = Path(scratch) / "home"
            empty_home.mkdir(mode=0o700)
            snapshot(empty_home, [], root / "public", root / "private")
        metadata = {
            "created": datetime.now(timezone.utc).isoformat(),
            "home": str(home),
            "source_count": 0,
        }
        metadata_path = root / "checkpoint.json"
        metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True))
        os.chmod(metadata_path, 0o600)
        problems = verify_snapshot(root / "public") + verify_snapshot(root / "private")
        if problems:
            raise RecoveryError(
                "pre-write checkpoint failed verification: " + "; ".join(problems[:5])
            )
        return root

    public_root = root / "public"
    private_root = root / "private"
    snapshot(home, sources, public_root, private_root)
    problems = verify_snapshot(public_root) + verify_snapshot(private_root)
    if problems:
        raise RecoveryError(
            "pre-write checkpoint failed verification: " + "; ".join(problems[:5])
        )
    return root


def recover(
    *,
    snapshot: Path | None = None,
    home: Path | None = None,
    apply: bool = False,
    pointer: Path = DEFAULT_POINTER,
    repo_root: Path = REPO_ROOT,
    checkpoint_parent: Path | None = None,
) -> dict[str, Any]:
    """Preview or apply a file-only restore from the private snapshot engine."""
    repo_root = Path(os.path.abspath(repo_root))
    private_root, companion_root = resolve_snapshot(snapshot, pointer, repo_root)
    _validate_roots(private_root, companion_root)
    destination = _destination_home(home, private_root)

    _journal, reviewed, actions = authorize.authorize_journal(
        private_root, destination, companion_root=companion_root
    )

    result: dict[str, Any] = {
        "actions": [
            {"operation": action["operation"], "path": action["path"]}
            for action in actions
        ],
        "applied": False,
        "checkpoint": None,
        "companion_root": str(companion_root) if companion_root else None,
        "home": str(destination),
        "reviewed_paths": reviewed,
        "snapshot_root": str(private_root),
    }
    if not apply:
        return result

    restore.apply_restore(actions, destination, apply=False)
    parent = (
        checkpoint_parent
        if checkpoint_parent is not None
        else private_root.parent.parent / "checkpoints"
    )
    checkpoint = create_checkpoint(actions, destination, parent)
    try:
        restore.apply_restore(actions, destination, apply=True)
    except (restore.RestoreConflict, OSError, ValueError) as error:
        raise RecoveryError(
            f"restore failed; pre-write checkpoint retained at {checkpoint}: {error}"
        ) from error
    result["applied"] = True
    result["checkpoint"] = str(checkpoint)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="preview (default)")
    mode.add_argument("--apply", action="store_true", help="restore files")
    parser.add_argument("--snapshot", type=Path, help="snapshot bundle or private root")
    parser.add_argument("--home", type=Path, help="destination home")
    args = parser.parse_args(argv)
    try:
        result = recover(
            snapshot=args.snapshot,
            home=args.home,
            apply=args.apply,
        )
    except (
        RecoveryError,
        restore.RestoreConflict,
        OSError,
        ValueError,
    ) as error:
        parser.exit(1, f"Recovery blocked: {error}\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
