"""Immutable, privacy-aware filesystem snapshot for the Pleamar migration (R1).

Capture is explicit (a caller-supplied allowlist), never an unrestricted home
crawl. Every enumerated path is inspected with ``lstat``; symlinks keep their
original destination *and* their dereferenced bytes; nested links that escape
the home tree or point into credential directories, plus traversal and cycles,
fail closed. Payloads are staged in fresh temporary siblings and published only
after every recorded byte verifies.

Classification defaults to PRIVATE. A file becomes public only when its exact
home-relative logical path *and* its content SHA-256 appear in the manually
supplied ``public_audit`` mapping (``Mapping[logical_path, sha256]``). Automated
name/field checks can only downgrade a file to private; they are never used to
claim that a file is safe. The private root and its payloads are stored 0600
(root 0700); public payloads drop privilege bits. Neither root is marked
``complete`` until both data roots are published, and the verifier refuses
incomplete snapshots.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = 2

# -- classification tables -------------------------------------------------
CACHE_DIR_NAMES = frozenset(
    {
        "__pycache__",
        ".cache",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        "node_modules",
        ".git",
        ".venv",
        "venv",
        "target",
        "build",
        "dist",
        "Cache",
        "GPUCache",
        "CachedData",
    }
)
CACHE_SUFFIXES = (".pyc", ".pyo", ".pyd", ".o", ".obj", ".so", ".class")

HISTORY_DIR_PARTS = frozenset(
    {"cliphist", "clipboard-history", "clipboard_history", "clipman", "history"}
)

# Nested symlinks resolved into one of these directories are refused before
# their bytes are read or staged.
SENSITIVE_DIR_NAMES = frozenset(
    {
        ".ssh",
        ".gnupg",
        ".password-store",
        ".aws",
        ".docker",
        ".kube",
        "gcloud",
        ".private",
        "keyrings",
        ".local/share/keyrings",
    }
)

PRIVATE_BASENAMES = frozenset(
    {
        ".netrc",
        ".env",
        ".envrc",
        ".git-credentials",
        "credentials",
        "credentials.json",
        "secrets.json",
        "cookies.sqlite",
        "id_rsa",
        "id_ed25519",
        "authorized_keys",
        "known_hosts",
    }
)
SECRET_NAME_TOKENS = (
    "token",
    "secret",
    "password",
    "passwd",
    "credential",
    "api_key",
    "apikey",
    "api-key",
    "access_key",
    "access-key",
    "private_key",
    "private-key",
    "client_secret",
    "refresh_token",
    "session",
    "cookie",
    "keyring",
    "kwallet",
    "gnupg",
    "netrc",
)

STRUCTURED_SUFFIXES = frozenset({".json", ".toml"})
TEXT_SUFFIXES = frozenset(
    {
        ".conf",
        ".cfg",
        ".ini",
        ".yaml",
        ".yml",
        ".qml",
        ".lua",
        ".sh",
        ".bash",
        ".zsh",
        ".desktop",
        ".service",
        ".txt",
        ".js",
        ".md",
        ".xml",
        ".plm",
        ".theme",
    }
)

# Downgrade-only heuristics: their only job is to demote a file to private.
_SECRET_KEYWORDS = (
    "token",
    "secret",
    "password",
    "passwd",
    "credential",
    "api_key",
    "apikey",
    "api-key",
    "access_key",
    "access-key",
    "private_key",
    "private-key",
    "client_secret",
    "refresh_token",
    "authorization",
    "bearer",
    "cookie",
    "auth",
)
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)(?:" + "|".join(re.escape(key) for key in _SECRET_KEYWORDS) + r")[\"']?\s*[=:]"
)
_SECRET_FIELD_HINTS = _SECRET_KEYWORDS
_MAX_AUDIT_BYTES = 1_000_000
_SHA256_RE = re.compile(r"[0-9a-fA-F]{64}")


class SnapshotError(RuntimeError):
    """Raised when a snapshot cannot be captured and safely published."""


# -- low-level helpers -----------------------------------------------------
def _read_bytes(path: Path) -> bytes:
    with open(path, "rb") as handle:
        return handle.read()


def _write_payload(dest: Path, data: bytes, mode: int) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as handle:
        handle.write(data)
    os.chmod(dest, mode)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _normalize_audit(public_audit: Mapping[str, str] | None) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in (public_audit or {}).items():
        name = str(key).replace("\\", "/")
        while name.startswith("./"):
            name = name[2:]
        normalized[name] = value
    return normalized


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _relative_parts(path: Path, home: Path) -> tuple[str, ...]:
    if _is_within(path, home):
        return path.relative_to(home).parts
    return path.parts


def _logical_path(path: Path, home: Path) -> str:
    rel = os.path.relpath(str(path), str(home))
    if rel == ".":
        return "."
    parts = Path(rel).parts
    if parts and parts[0] == "..":
        raise SnapshotError(f"source escapes home: {path}")
    return Path(rel).as_posix()


# -- classification --------------------------------------------------------
def _has_secret_field(tree: Any) -> bool:
    if isinstance(tree, dict):
        for key, value in tree.items():
            low = str(key).lower()
            if any(hint in low for hint in _SECRET_FIELD_HINTS):
                return True
            if _has_secret_field(value):
                return True
    elif isinstance(tree, (list, tuple)):
        return any(_has_secret_field(item) for item in tree)
    return False


def _text_has_secret(text: str) -> bool:
    return _SECRET_ASSIGNMENT.search(text) is not None


def _scan_reason(path: Path, data: bytes) -> str | None:
    """Downgrade-only scan. Never used to declare a file safe."""
    suffix = path.suffix.lower()
    if suffix in STRUCTURED_SUFFIXES:
        if len(data) > _MAX_AUDIT_BYTES:
            return "oversized structured file (private by default)"
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return "unreadable structured file (private by default)"
        if suffix == ".json":
            try:
                tree = json.loads(text)
            except ValueError:
                return "invalid JSON (private by default)"
        else:
            try:
                tree = tomllib.loads(text)
            except tomllib.TOMLDecodeError:
                return "invalid TOML (private by default)"
        if _has_secret_field(tree):
            return "secret field in structured config"
        return None
    if suffix in TEXT_SUFFIXES:
        if len(data) > _MAX_AUDIT_BYTES:
            return "oversized text file (private by default)"
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return "unreadable text file (private by default)"
        if _text_has_secret(text):
            return "secret-looking assignment in text config"
    return None


def _name_is_sensitive(name: str) -> bool:
    low = name.lower()
    if low in PRIVATE_BASENAMES:
        return True
    return any(token in low for token in SECRET_NAME_TOKENS)


# -- entry construction ----------------------------------------------------
def _entry(
    logical: str,
    resolved_source: str,
    kind: str,
    mode: int,
    classification: str,
    *,
    link_target: str | None = None,
    sha256: str | None = None,
    payload: str | None = None,
    payload_mode: int | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "logical_path": logical,
        "resolved_source": resolved_source,
        "kind": kind,
        "mode": mode,
        "classification": classification,
    }
    if link_target is not None:
        record["link_target"] = link_target
    if sha256 is not None:
        record["sha256"] = sha256
    if payload is not None:
        record["payload"] = payload
        record["payload_mode"] = payload_mode
    if reason is not None:
        record["reason"] = reason
    return record


class _Capture:
    def __init__(
        self,
        home: Path,
        public_tmp: Path,
        private_tmp: Path,
        audit: Mapping[str, str],
    ) -> None:
        self.home = home
        self.home_real = Path(os.path.realpath(home))
        self.public_tmp = public_tmp
        self.private_tmp = private_tmp
        self.audit = audit
        self.entries: list[dict[str, Any]] = []
        self.pre_stats: dict[str, tuple[int, int, int]] = {}
        self.source_paths: dict[str, Path] = {}
        self.link_targets: dict[str, str] = {}
        self.target_ids: dict[str, tuple[int, int]] = {}
        self._ancestors: list[Path] = []
        self._source_parent = home
        self._source_real_parent = self.home_real

    def run(self, sources: Sequence[Path]) -> None:
        for src in sources:
            path = self._resolve(src)
            self._source_parent = path.parent
            self._source_real_parent = Path(os.path.realpath(path)).parent
            try:
                st = os.lstat(path)
            except FileNotFoundError as exc:
                raise SnapshotError(f"source missing: {path}") from exc
            self._walk(path, _logical_path(path, self.home), st, top_level=True)

    def _resolve(self, src: Path) -> Path:
        path = Path(src)
        if not path.is_absolute():
            path = self.home / path
        path = Path(os.path.abspath(path))
        if _logical_path(path, self.home) == ".":
            raise SnapshotError("source must be a child of home, not home itself")
        return path

    def _walk(
        self, path: Path, logical: str, st: os.stat_result, *, top_level: bool
    ) -> None:
        if stat.S_ISLNK(st.st_mode):
            self._walk_symlink(path, logical, st, top_level=top_level)
        elif stat.S_ISDIR(st.st_mode):
            self._walk_dir(path, logical, st)
        elif stat.S_ISREG(st.st_mode):
            self._walk_file(path, logical, st)
        else:
            raise SnapshotError(f"unsupported file type: {logical}")

    # -- classification of a file's bytes ---------------------------------
    def _classify(
        self, logical: str, path: Path, data: bytes, *, target_name: str | None = None
    ) -> tuple[str, str | None]:
        if _name_is_sensitive(path.name) or (
            target_name is not None and _name_is_sensitive(target_name)
        ):
            return "private", "known sensitive file name"
        scan = _scan_reason(path, data)
        if scan is not None:
            return "private", scan
        audited = self.audit.get(logical)
        if audited is None:
            return "private", "not in public audit allowlist"
        if not _is_sha256(audited):
            return "private", "invalid public-audit digest"
        if audited.lower() != _sha256(data):
            return "private", "public-audit digest mismatch (stale)"
        return "public", None

    # -- symlinks ----------------------------------------------------------
    def _walk_symlink(
        self, path: Path, logical: str, st: os.stat_result, *, top_level: bool
    ) -> None:
        link_target = os.readlink(path)
        target_real = Path(os.path.realpath(path))
        if not target_real.exists():
            raise SnapshotError(f"symlink target missing: {logical} -> {link_target}")
        if not top_level:
            if not _is_within(target_real, self.home_real):
                raise SnapshotError(
                    f"external link rejected: {logical} -> {link_target}"
                )
            if any(
                part in SENSITIVE_DIR_NAMES
                for part in _relative_parts(target_real, self.home_real)
            ):
                raise SnapshotError(
                    f"nested link into credentials rejected: {logical} -> {link_target}"
                )
        tst = os.stat(path)
        target_parts = _relative_parts(target_real, self.home_real)
        if stat.S_ISDIR(tst.st_mode):
            reason = self._excluded_reason(
                path, logical, is_dir=True, extra_parts=target_parts
            )
            if reason:
                self._record_excluded(logical, path, "symlink", st, reason)
                return
            if any(target_real == seen for seen in self._ancestors):
                raise SnapshotError(f"symlink cycle detected: {logical}")
            self._remember_link(logical, path, link_target, tst, entry_real=str(target_real))
            self.entries.append(
                _entry(
                    logical,
                    str(target_real),
                    "symlink",
                    stat.S_IMODE(tst.st_mode),
                    "private",
                    link_target=link_target,
                )
            )
            self._ancestors.append(target_real)
            try:
                for name in sorted(os.listdir(path)):
                    child = path / name
                    self._walk(
                        child,
                        f"{logical}/{name}",
                        os.lstat(child),
                        top_level=False,
                    )
            finally:
                self._ancestors.pop()
            return
        if stat.S_ISREG(tst.st_mode):
            reason = self._excluded_reason(
                path, logical, is_dir=False, extra_parts=target_parts
            )
            if reason:
                self._record_excluded(logical, path, "symlink", st, reason)
                return
            data = _read_bytes(path)
            digest = _sha256(data)
            classification, reason = self._classify(
                logical, path, data, target_name=target_real.name
            )
            payload, payload_mode = self._stage(
                logical, data, stat.S_IMODE(tst.st_mode), classification
            )
            self._remember_link(logical, path, link_target, tst, entry_real=str(target_real))
            self.pre_stats[logical] = (tst.st_mtime_ns, tst.st_size, tst.st_ino)
            self.entries.append(
                _entry(
                    logical,
                    str(target_real),
                    "symlink",
                    stat.S_IMODE(tst.st_mode),
                    classification,
                    link_target=link_target,
                    sha256=digest,
                    payload=payload,
                    payload_mode=payload_mode,
                    reason=reason,
                )
            )
            return
        raise SnapshotError(f"unsupported symlink target type: {logical}")

    def _remember_link(
        self,
        logical: str,
        path: Path,
        link_target: str,
        tst: os.stat_result,
        *,
        entry_real: str,
    ) -> None:
        self.source_paths[logical] = path
        self.link_targets[logical] = link_target
        self.target_ids[logical] = (tst.st_dev, tst.st_ino)

    # -- directories -------------------------------------------------------
    def _walk_dir(self, path: Path, logical: str, st: os.stat_result) -> None:
        reason = self._excluded_reason(path, logical, is_dir=True)
        if reason:
            self._record_excluded(logical, path, "dir", st, reason)
            return
        real = Path(os.path.realpath(path))
        if any(real == seen for seen in self._ancestors):
            raise SnapshotError(f"directory cycle detected: {logical}")
        self.entries.append(
            _entry(
                logical,
                str(real),
                "dir",
                stat.S_IMODE(st.st_mode),
                "private",
            )
        )
        self._ancestors.append(real)
        try:
            for name in sorted(os.listdir(path)):
                child = path / name
                self._walk(
                    child, f"{logical}/{name}", os.lstat(child), top_level=False
                )
        finally:
            self._ancestors.pop()

    # -- regular files -----------------------------------------------------
    def _walk_file(self, path: Path, logical: str, st: os.stat_result) -> None:
        reason = self._excluded_reason(path, logical, is_dir=False)
        if reason:
            self._record_excluded(logical, path, "file", st, reason)
            return
        original_mode = stat.S_IMODE(st.st_mode)
        data = _read_bytes(path)
        classification, reason = self._classify(logical, path, data)
        payload, payload_mode = self._stage(
            logical, data, original_mode, classification
        )
        self.source_paths[logical] = path
        self.pre_stats[logical] = (st.st_mtime_ns, st.st_size, st.st_ino)
        self.entries.append(
            _entry(
                logical,
                str(Path(os.path.realpath(path))),
                "file",
                original_mode,
                classification,
                sha256=_sha256(data),
                payload=payload,
                payload_mode=payload_mode,
                reason=reason,
            )
        )

    # -- exclusions --------------------------------------------------------
    def _excluded_reason(
        self, path: Path, logical: str, *, is_dir: bool, extra_parts: Sequence[str] = ()
    ) -> str | None:
        parts = [p for p in Path(logical).parts if p != "."] + list(extra_parts)
        name = path.name
        # A deliberately selected checkout can live under ~/.cache; exclude
        # caches inside that source, not ancestors outside its selected scope.
        cache_parts = _relative_parts(path, self._source_parent) + _relative_parts(
            Path(os.path.realpath(path)), self._source_real_parent
        )
        if is_dir and any(part in CACHE_DIR_NAMES for part in cache_parts):
            return "build/runtime cache"
        if is_dir and (
            any(part in HISTORY_DIR_PARTS for part in parts)
            or name.startswith("history")
            or name.endswith("history")
        ):
            return "clipboard/shell history content"
        if not is_dir and name.endswith(CACHE_SUFFIXES):
            return "build artifact"
        if not is_dir and (
            name.startswith("history")
            or name.endswith("history")
            or any(part in HISTORY_DIR_PARTS for part in parts)
        ):
            return "clipboard/shell history content"
        return None

    def _record_excluded(
        self, logical: str, path: Path, kind: str, st: os.stat_result, reason: str
    ) -> None:
        self.entries.append(
            _entry(
                logical,
                str(Path(os.path.realpath(path))),
                kind,
                stat.S_IMODE(st.st_mode),
                "excluded",
                reason=reason,
            )
        )

    # -- staging -----------------------------------------------------------
    def _stage(
        self, logical: str, data: bytes, original_mode: int, classification: str
    ) -> tuple[str | None, int | None]:
        if classification == "public":
            root = self.public_tmp
            payload_mode = original_mode & 0o777
        elif classification == "private":
            root = self.private_tmp
            payload_mode = 0o600
        else:
            return None, None
        rel = Path("payload") / Path(logical)
        _write_payload(root / rel, data, payload_mode)
        return rel.as_posix(), payload_mode

    # -- post-capture source re-check -------------------------------------
    def verify_sources_unchanged(self) -> None:
        for entry in self.entries:
            logical = entry["logical_path"]
            source = self.source_paths.get(logical)
            digest = entry.get("sha256")
            if digest and source is not None:
                try:
                    st = os.stat(source)
                    data = _read_bytes(source)
                except OSError as exc:
                    raise SnapshotError(
                        f"source unreadable during verification: {logical}"
                    ) from exc
                if _sha256(data) != digest:
                    raise SnapshotError(f"source changed during capture: {logical}")
                previous = self.pre_stats.get(logical)
                if previous is not None and (
                    st.st_mtime_ns,
                    st.st_size,
                    st.st_ino,
                ) != previous:
                    raise SnapshotError(f"source changed during capture: {logical}")
            if entry["kind"] == "symlink" and source is not None:
                if os.readlink(source) != self.link_targets.get(logical):
                    raise SnapshotError(
                        f"symlink retargeted during capture: {logical}"
                    )
                if str(Path(os.path.realpath(source))) != entry["resolved_source"]:
                    raise SnapshotError(
                        f"symlink retargeted during capture: {logical}"
                    )
                st2 = os.stat(source)
                expected_id = self.target_ids.get(logical)
                if expected_id is not None and (st2.st_dev, st2.st_ino) != expected_id:
                    raise SnapshotError(
                        f"symlink retargeted during capture: {logical}"
                    )


def _finalize_directory_classification(entries: list[dict[str, Any]]) -> None:
    for entry in entries:
        if entry["kind"] != "dir" or entry["classification"] == "excluded":
            continue
        prefix = entry["logical_path"].rstrip("/") + "/"
        descendants = [
            other
            for other in entries
            if other is not entry and other["logical_path"].startswith(prefix)
        ]
        if any(
            other["classification"] in ("private", "excluded")
            for other in descendants
        ):
            entry["classification"] = "private"
            entry.setdefault("reason", "directory containing non-public entries")
        else:
            entry["classification"] = "public"


# -- publication helpers ---------------------------------------------------
def _write_manifest(
    root: Path,
    home: Path,
    entries: list[dict[str, Any]],
    *,
    complete: bool,
    withheld: list[dict[str, Any]],
    mode: int,
) -> None:
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "complete": complete,
        "created": datetime.now(timezone.utc).isoformat(),
        "home": str(home),
        "entry_count": len(entries),
        "entries": entries,
        "withheld": withheld,
    }
    _write_payload(
        root / "manifest.json",
        json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8"),
        mode,
    )


def _load_manifest(root: Path) -> dict[str, Any]:
    return json.loads((root / "manifest.json").read_text())


def _verify_payloads(root: Path, manifest: Mapping[str, Any]) -> list[str]:
    problems: list[str] = []
    listed: set[str] = set()
    for entry in manifest.get("entries", []):
        if not isinstance(entry, dict):
            problems.append("invalid manifest entry")
            continue
        logical = entry.get("logical_path")
        if not isinstance(logical, str) or not logical or Path(logical).is_absolute() or any(
            part in (".", "..") for part in logical.split("/")
        ):
            problems.append("invalid logical path")
            continue
        payload = entry.get("payload")
        if not payload:
            continue
        if not isinstance(payload, str) or payload != "payload/" + logical:
            problems.append(f"unsafe payload path for {logical}")
            continue
        if payload in listed:
            problems.append(f"duplicate payload: {payload}")
            continue
        listed.add(payload)
        payload_path = root / payload
        ancestors = [root.joinpath(*Path(payload).parts[:i]) for i in range(1, len(Path(payload).parts) + 1)]
        if any(path.is_symlink() for path in ancestors):
            problems.append(f"symlink payload rejected: {payload}")
            continue
        if not payload_path.is_file():
            problems.append(f"missing payload: {payload}")
            continue
        digest = entry.get("sha256")
        if not _is_sha256(digest):
            problems.append(f"invalid payload digest: {payload}")
            continue
        try:
            if _sha256(_read_bytes(payload_path)) != digest:
                problems.append(f"hash mismatch: {payload}")
        except OSError:
            problems.append(f"unreadable payload: {payload}")
            continue
        stored_mode = entry.get("payload_mode")
        if type(stored_mode) is int and 0 <= stored_mode <= 0o777:
            actual_mode = stat.S_IMODE(payload_path.stat().st_mode)
            if actual_mode != stored_mode:
                problems.append(f"payload mode mismatch: {payload}")
        else:
            problems.append(f"invalid payload mode: {payload}")
    payload_dir = root / "payload"
    if payload_dir.is_dir():
        for found in payload_dir.rglob("*"):
            if found.is_symlink():
                problems.append(f"symlink in payload tree: {found.relative_to(root)}")
            elif found.is_file():
                rel = found.relative_to(root).as_posix()
                if rel not in listed:
                    problems.append(f"unlisted payload: {rel}")
    return problems


# -- public API ------------------------------------------------------------
def snapshot(
    home: Path,
    sources: Sequence[Path],
    public_root: Path,
    private_root: Path,
    *,
    public_audit: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Capture ``sources`` (relative to ``home``) into two immutable roots.

    ``public_audit`` maps exact home-relative logical file paths to the SHA-256
    of manually audited bytes; only matching files may become public. Returns a
    summary dict describing the published manifests. Raises
    :class:`SnapshotError` on any unsafe condition; on failure nothing is
    published and all staging directories are removed.
    """
    home = Path(os.path.abspath(home))
    public_root = Path(os.path.abspath(public_root))
    private_root = Path(os.path.abspath(private_root))
    audit = _normalize_audit(public_audit)
    if not home.is_dir():
        raise SnapshotError(f"home is not a directory: {home}")
    if public_root == private_root:
        raise SnapshotError("public and private roots must differ")

    for root in (public_root, private_root):
        if root.is_symlink():
            raise SnapshotError(f"destination must not be a symlink: {root}")
        if root.exists():
            if not root.is_dir():
                raise SnapshotError(f"destination exists and is not a directory: {root}")
            if any(root.iterdir()):
                raise SnapshotError(f"destination is not empty: {root}")

    public_root.parent.mkdir(parents=True, exist_ok=True)
    private_root.parent.mkdir(parents=True, exist_ok=True)
    public_tmp = Path(tempfile.mkdtemp(prefix=public_root.name + ".tmp-", dir=public_root.parent))
    private_tmp = Path(tempfile.mkdtemp(prefix=private_root.name + ".tmp-", dir=private_root.parent))

    try:
        capture = _Capture(home, public_tmp, private_tmp, audit)
        capture.run(list(sources))
        _finalize_directory_classification(capture.entries)
        capture.verify_sources_unchanged()

        public_entries = [e for e in capture.entries if e["classification"] == "public"]
        private_entries = [
            e for e in capture.entries if e["classification"] in ("private", "excluded")
        ]
        withheld = [
            {
                "logical_path": e["logical_path"],
                "classification": e["classification"],
                "reason": e.get("reason") or "withheld (no public audit entry)",
            }
            for e in capture.entries
            if e["classification"] in ("private", "excluded")
        ]

        # Set storage permissions before publication, inside the handled path.
        os.chmod(public_tmp, 0o755)
        os.chmod(private_tmp, 0o700)
        _write_manifest(public_tmp, home, public_entries, complete=False, withheld=withheld, mode=0o644)
        _write_manifest(private_tmp, home, private_entries, complete=False, withheld=[], mode=0o600)

        for staged in (public_tmp, private_tmp):
            problems = _verify_payloads(staged, _load_manifest(staged))
            if problems:
                raise SnapshotError(
                    "staged snapshot failed verification: " + "; ".join(problems)
                )

        os.replace(public_tmp, public_root)
        os.replace(private_tmp, private_root)

        # Mark complete only after BOTH data roots are published.
        _write_manifest(public_root, home, public_entries, complete=True, withheld=withheld, mode=0o644)
        _write_manifest(private_root, home, private_entries, complete=True, withheld=[], mode=0o600)
    except SnapshotError:
        shutil.rmtree(public_tmp, ignore_errors=True)
        shutil.rmtree(private_tmp, ignore_errors=True)
        raise
    except Exception as exc:  # noqa: BLE001 - convert to a fail-closed error
        shutil.rmtree(public_tmp, ignore_errors=True)
        shutil.rmtree(private_tmp, ignore_errors=True)
        raise SnapshotError(str(exc)) from exc

    return {
        "schema_version": SCHEMA_VERSION,
        "complete": True,
        "home": str(home),
        "public_root": str(public_root),
        "private_root": str(private_root),
        "public_manifest": str(public_root / "manifest.json"),
        "private_manifest": str(private_root / "manifest.json"),
        "entries": capture.entries,
        "public_entry_count": len(public_entries),
        "private_entry_count": len(private_entries),
        "excluded_entry_count": sum(
            1 for e in capture.entries if e["classification"] == "excluded"
        ),
        "withheld_count": len(withheld),
    }


def verify_snapshot(root: Path) -> list[str]:
    """Return a list of problems with the snapshot at ``root`` (empty = ok)."""
    root = Path(root)
    problems: list[str] = []
    manifest_path = root / "manifest.json"
    if root.is_symlink() or manifest_path.is_symlink():
        return ["snapshot root and manifest must not be symlinks"]
    if not manifest_path.is_file():
        return [f"missing manifest: {manifest_path}"]
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, ValueError) as exc:
        return [f"unreadable manifest: {manifest_path}: {exc}"]
    if not isinstance(manifest, dict) or manifest.get("schema_version") != SCHEMA_VERSION:
        return ["invalid or unsupported snapshot schema"]
    entries = manifest.get("entries")
    if not isinstance(entries, list) or manifest.get("entry_count") != len(entries):
        return ["invalid snapshot entries or entry count"]
    withheld = manifest.get("withheld", [])
    if not isinstance(withheld, list) or any(not isinstance(record, dict) for record in withheld):
        return ["invalid withheld metadata"]
    if manifest.get("complete") is not True:
        problems.append("manifest is not marked complete")

    problems.extend(_verify_payloads(root, manifest))

    for record in withheld:
        leaked = set(record) - {"logical_path", "classification", "reason"}
        if leaked:
            problems.append(
                "withheld record leaks fields: " + ", ".join(sorted(leaked))
            )
    return problems


# -- CLI -------------------------------------------------------------------
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="snapshot",
        description=(
            "Immutable privacy-aware snapshot. Never prints file bodies; "
            "only manually audited paths are public, everything else is private."
        ),
    )
    parser.add_argument("--home", type=Path)
    parser.add_argument("--public", type=Path)
    parser.add_argument("--private", type=Path)
    parser.add_argument("--sources-file", type=Path)
    parser.add_argument("--public-audit", type=Path, metavar="JSON")
    parser.add_argument("--verify", type=Path, metavar="ROOT")
    args = parser.parse_args(argv)

    if args.verify is not None:
        problems = verify_snapshot(args.verify)
        for problem in problems:
            print(f"problem: {problem}")
        if not problems:
            print(f"OK: {args.verify}")
        return 1 if problems else 0

    missing = [
        name
        for name, value in (
            ("--home", args.home),
            ("--public", args.public),
            ("--private", args.private),
            ("--sources-file", args.sources_file),
        )
        if value is None
    ]
    if missing:
        parser.error("required for capture: " + ", ".join(missing))

    audit: Mapping[str, str] | None = None
    if args.public_audit is not None:
        try:
            loaded = json.loads(args.public_audit.read_text())
        except (OSError, ValueError) as exc:
            parser.error(f"--public-audit is not valid JSON: {exc}")
        if not isinstance(loaded, dict):
            parser.error("--public-audit must be a JSON object mapping path -> sha256")
        audit = loaded

    sources = [
        Path(line.strip())
        for line in args.sources_file.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    result = snapshot(args.home, sources, args.public, args.private, public_audit=audit)
    summary = {k: v for k, v in result.items() if k != "entries"}
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
