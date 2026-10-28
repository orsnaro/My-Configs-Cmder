"""Rebuild the missing deployment journal for restore.py from the live state.

The permanent cutover predates journaled deployment (plan task O4), so
restore.py has no record of the installed hashes and refuses to replace any
path whose live bytes changed since the snapshot.  This tool replays the
planner instead of duplicating its mapping rules: every refused path is
recorded with its CURRENT state as authorized for replacement, and the planner
is re-run until the whole home is accepted.  Review the printed list before
writing the journal with ``--write``; anything edited after authorization is
still detected by restore.py's plan/apply preconditions.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Sequence

from . import restore

# Must stay in sync with restore.py's conflict wording (guarded by tests).
_CHANGED_PREFIX = "destination changed since snapshot: "
_MAX_ROUNDS = 5000


def authorize_journal(
    snapshot_root: Path,
    destination_home: Path,
    companion_root: Path | None = None,
) -> tuple[dict[str, Any], list[dict[str, str]], list[dict[str, Any]]]:
    """Return (journal, reviewed paths, planned actions) for the live home.

    ``reviewed`` holds one record per difference the planner refused before
    authorization; ``actions`` is the clean plan once the journal covers all
    of them.  Nothing on disk is modified.
    """
    home = Path(os.path.abspath(destination_home))
    installed: dict[str, Any] = {}
    reviewed: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix="pleamar-authorize-") as scratch:
        journal_path = Path(scratch) / "journal.json"
        for _ in range(_MAX_ROUNDS):
            journal = {"home": str(home), "installed": dict(installed), "created": []}
            journal_path.write_text(json.dumps(journal))
            try:
                actions = restore.plan_restore(
                    snapshot_root, home, journal_path, companion_root=companion_root
                )
            except restore.RestoreConflict as error:
                message = str(error)
                if not message.startswith(_CHANGED_PREFIX):
                    raise
                blocked = Path(message[len(_CHANGED_PREFIX):])
                relative = blocked.relative_to(home).as_posix()
                state = restore._state(blocked)  # same-package state reader
                if state is None:
                    raise restore.RestoreConflict(
                        f"live path vanished while authorizing: {blocked}"
                    )
                if relative in installed:
                    raise restore.RestoreConflict(
                        f"authorization did not clear the conflict: {blocked}"
                    )
                installed[relative] = state
                reviewed.append(
                    {
                        "path": relative,
                        "kind": state["kind"],
                        "summary": state.get("sha256", state.get("link_target", ""))[:16],
                    }
                )
                continue
            return journal, reviewed, actions
    raise restore.RestoreConflict(f"still blocked after {_MAX_ROUNDS} rounds")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-root", required=True, type=Path)
    parser.add_argument("--companion-root", type=Path)
    parser.add_argument("--home", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path, help="journal destination")
    parser.add_argument(
        "--write",
        action="store_true",
        help="write the journal to --out (default: review only)",
    )
    args = parser.parse_args(argv)
    try:
        journal, reviewed, actions = authorize_journal(
            args.snapshot_root, args.home, companion_root=args.companion_root
        )
        out = Path(os.path.abspath(args.out))
        if args.write:
            if out.is_symlink():
                raise restore.RestoreConflict("journal must not be a symlink")
            out.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(prefix=".authorize-", dir=out.parent)
            try:
                with os.fdopen(descriptor, "w") as stream:
                    json.dump(journal, stream, indent=2)
                os.chmod(temporary, 0o600)
                os.replace(temporary, out)
            finally:
                Path(temporary).unlink(missing_ok=True)
    except (restore.RestoreConflict, OSError, ValueError) as error:
        parser.exit(1, f"Authorize blocked: {error}\n")
    print(
        json.dumps(
            {
                "home": journal["home"],
                "reviewed_paths": reviewed,
                "planned_actions": [
                    {"operation": action["operation"], "path": action["path"]}
                    for action in actions
                ],
                "journal_written": str(out) if args.write else None,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
