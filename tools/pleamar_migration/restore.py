"""Conflict-aware, dry-run-by-default restoration of migration snapshots."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
from typing import Any, Mapping, Sequence

from .snapshot import verify_snapshot


class RestoreConflict(RuntimeError):
    """A restore cannot proceed without overriding unapproved state."""


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _relative(name: str) -> Path:
    if not isinstance(name, str) or not name or Path(name).is_absolute() or any(
        part in ("", ".", "..") for part in name.split("/")
    ):
        raise RestoreConflict("invalid home-relative path")
    return Path(name)


def _safe_parents(path: Path, home: Path) -> None:
    try:
        relative = path.relative_to(home)
    except ValueError as error:
        raise RestoreConflict(f"path escapes destination home: {path}") from error
    if any(part in (".", "..") for part in relative.parts) or home.is_symlink():
        raise RestoreConflict(f"unsafe destination: {path}")
    parent = home
    for part in relative.parts[:-1]:
        parent /= part
        if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
            raise RestoreConflict(f"unsafe destination parent: {parent}")


def _state(path: Path) -> dict[str, Any] | None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(info.st_mode):
        return {"kind": "symlink", "link_target": os.readlink(path)}
    mode = stat.S_IMODE(info.st_mode)
    if stat.S_ISDIR(info.st_mode):
        return {"kind": "dir", "mode": mode}
    if stat.S_ISREG(info.st_mode):
        return {"kind": "file", "mode": mode, "sha256": _hash(path.read_bytes())}
    raise RestoreConflict(f"unsupported destination type: {path}")


def plan_restore(
    snapshot_root: Path,
    destination_home: Path,
    journal: Path | None = None,
    *,
    companion_root: Path | None = None,
) -> list[dict[str, Any]]:
    """Validate both snapshots and produce actions without creating anything."""
    home = Path(os.path.abspath(destination_home))
    roots = [Path(snapshot_root)] + ([Path(companion_root)] if companion_root else [])
    entries: dict[str, tuple[dict[str, Any], Path]] = {}
    original_home: Path | None = None
    for root in roots:
        problems = verify_snapshot(root)
        if problems:
            raise RestoreConflict("invalid snapshot: " + "; ".join(problems[:5]))
        manifest = json.loads((root / "manifest.json").read_text())
        recorded_home = Path(manifest["home"])
        if not recorded_home.is_absolute() or (original_home is not None and original_home != recorded_home):
            raise RestoreConflict("snapshot roots disagree about original home")
        original_home = recorded_home
        for entry in manifest["entries"]:
            name = entry["logical_path"]
            _relative(name)
            if entry["classification"] == "excluded":
                continue
            if name in entries and entries[name][0] != entry:
                raise RestoreConflict(f"conflicting snapshot entries: {name}")
            entries[name] = entry, root
    if original_home is None:
        raise RestoreConflict("missing original home")

    installed: Mapping[str, Any] = {}
    created: list[str] = []
    if journal is not None:
        if journal.is_symlink():
            raise RestoreConflict("journal must not be a symlink")
        saved = json.loads(journal.read_text())
        if saved.get("home") != str(home) or not isinstance(saved.get("installed"), dict) or not isinstance(saved.get("created", []), list):
            raise RestoreConflict("invalid deployment journal")
        installed = saved["installed"]
        created = saved.get("created", [])

    def mapped_target(entry: Mapping[str, Any]) -> Path:
        source = Path(entry["resolved_source"])
        if not source.is_absolute():
            raise RestoreConflict("alias target must be absolute in snapshot metadata")
        if source.is_relative_to(original_home):
            return home / source.relative_to(original_home)
        if home == original_home:
            return source  # External targets are checked, never written below.
        tag = _hash(str(source).encode())[:16]
        return home / ".pleamar-recovery" / "external" / tag / source.name

    aliases = {
        name: mapped_target(entry)
        for name, (entry, _) in entries.items()
        if entry["kind"] == "symlink" and "payload" not in entry
    }

    def physical(name: str) -> Path:
        _relative(name)
        for alias in sorted(aliases, key=len, reverse=True):
            if name.startswith(alias + "/"):
                return aliases[alias] / Path(name).relative_to(alias)
        return home / name

    actions: dict[Path, dict[str, Any]] = {}
    desired: dict[Path, dict[str, Any]] = {}

    def add(path: Path, wanted: dict[str, Any], operation: str, **details: Any) -> None:
        _safe_parents(path, home)
        if path in desired:
            if desired[path] != wanted:
                raise RestoreConflict(f"conflicting restore targets: {path}")
            return
        desired[path] = wanted
        current = _state(path)
        if current == wanted:
            return
        relative = path.relative_to(home).as_posix()
        if current is not None and current != installed.get(relative):
            raise RestoreConflict(f"destination changed since snapshot: {path}")
        actions[path] = {
            "operation": operation, "path": str(path), "expected": current,
            "desired": wanted, **details,
        }

    def directory(path: Path, mode: int | None = None) -> None:
        _safe_parents(path, home)
        if path != home:
            directory(path.parent)
        current = _state(path)
        if current is not None and current["kind"] != "dir":
            raise RestoreConflict(f"directory target is not a directory: {path}")
        if current is not None and mode is None:
            return
        wanted = {"kind": "dir", "mode": mode if mode is not None else 0o700}
        if path in desired and mode is None:
            return
        if path in desired and desired[path]["kind"] == "dir" and mode is not None:
            desired.pop(path)
            actions.pop(path, None)
        add(path, wanted, "mkdir" if current is None else "chmod")

    def file(path: Path, entry: Mapping[str, Any], root: Path) -> None:
        wanted = {"kind": "file", "mode": entry["mode"], "sha256": entry["sha256"]}
        if not path.is_relative_to(home):
            if _state(path) != wanted:
                raise RestoreConflict(f"external alias target requires explicit recovery: {path}")
            return
        directory(path.parent)
        add(path, wanted, "write", source=str(root / entry["payload"]), source_root=str(root))

    for name, (entry, root) in sorted(entries.items(), key=lambda item: (item[0].count("/"), item[0])):
        path = physical(name)
        mode = entry.get("mode")
        if type(mode) is not int or not 0 <= mode <= 0o7777:
            raise RestoreConflict(f"invalid original mode: {name}")
        if entry["kind"] == "dir":
            directory(path, mode)
        elif entry["kind"] == "file":
            file(path, entry, root)
        elif entry["kind"] == "symlink":
            target = mapped_target(entry)
            if target == path or target.is_relative_to(path):
                raise RestoreConflict(f"cyclic alias target: {name}")
            if "payload" in entry:
                file(target, entry, root)
            elif target.is_relative_to(home):
                directory(target, mode)
            elif not target.is_dir():
                raise RestoreConflict(f"external alias directory unavailable: {name}")
            directory(path.parent)
            raw_target = entry["link_target"] if home == original_home else (
                str(target) if Path(entry["link_target"]).is_absolute() else os.path.relpath(target, path.parent)
            )
            add(path, {"kind": "symlink", "link_target": raw_target}, "symlink")
        else:
            raise RestoreConflict(f"unsupported entry kind: {name}")

    for name in created:
        path = home / _relative(name)
        if name in entries or path in desired:
            continue
        _safe_parents(path, home)
        expected = installed.get(name)
        current = _state(path)
        if current is None:
            continue
        if not isinstance(expected, dict) or current != expected or current["kind"] == "dir":
            raise RestoreConflict(f"cannot remove changed or unowned creation: {path}")
        actions[path] = {"operation": "remove", "path": str(path), "expected": current, "desired": None}

    priority = {"mkdir": 0, "write": 1, "symlink": 2, "chmod": 3, "remove": 4}
    return sorted(actions.values(), key=lambda action: (priority[action["operation"]], len(Path(action["path"]).parts)))


def apply_restore(
    actions: Sequence[dict[str, Any]], destination_home: Path, *, apply: bool = False
) -> None:
    """Preflight every action/payload; never force a later edit or recurse-delete."""
    home = Path(os.path.abspath(destination_home))
    verified_roots: set[str] = set()
    for action in actions:
        path = Path(action["path"])
        _safe_parents(path, home)
        if _state(path) != action["expected"]:
            raise RestoreConflict(f"destination changed after restore planning: {path}")
        if action["operation"] == "write":
            root = Path(action["source_root"])
            root_key = str(root)
            if root_key not in verified_roots:
                if verify_snapshot(root):
                    raise RestoreConflict("snapshot changed after restore planning")
                verified_roots.add(root_key)
            source = Path(action["source"])
            _safe_parents(source, root)
            if source.is_symlink() or _hash(source.read_bytes()) != action["desired"]["sha256"]:
                raise RestoreConflict("payload changed after restore planning")
    if not apply:
        return
    for action in actions:
        path = Path(action["path"])
        _safe_parents(path, home)
        if _state(path) != action["expected"]:
            raise RestoreConflict(f"destination changed during restore: {path}")
        operation, wanted = action["operation"], action["desired"]
        if operation == "mkdir":
            path.mkdir(mode=wanted["mode"])
            path.chmod(wanted["mode"])
        elif operation == "chmod":
            path.chmod(wanted["mode"])
        elif operation == "write":
            data = Path(action["source"]).read_bytes()
            if _hash(data) != wanted["sha256"]:
                raise RestoreConflict("payload changed during restore")
            descriptor, temporary = tempfile.mkstemp(prefix=".pleamar-restore-", dir=path.parent)
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(data)
                os.chmod(temporary, wanted["mode"])
                os.replace(temporary, path)
            finally:
                Path(temporary).unlink(missing_ok=True)
        elif operation == "symlink":
            if path.is_symlink():
                path.unlink()
            path.symlink_to(wanted["link_target"])
        elif operation == "remove":
            path.unlink()
        else:
            raise RestoreConflict("unknown restore operation")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-root", required=True, type=Path)
    parser.add_argument("--companion-root", type=Path)
    parser.add_argument("--home", required=True, type=Path)
    parser.add_argument("--journal", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        actions = plan_restore(args.snapshot_root, args.home, args.journal, companion_root=args.companion_root)
        apply_restore(actions, args.home, apply=args.apply)
    except (RestoreConflict, OSError, ValueError) as error:
        parser.exit(1, f"Restore blocked: {error}\n")
    print(json.dumps({"applied": args.apply, "actions": [{"operation": action["operation"], "path": action["path"]} for action in actions]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
