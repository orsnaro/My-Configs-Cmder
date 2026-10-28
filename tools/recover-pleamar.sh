#!/usr/bin/env bash
# File-only Pleamar recovery; activation stays with the desktop-stack coordinator.
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
exec python3 "$repo_root/tools/pleamar_recovery.py" "$@"
