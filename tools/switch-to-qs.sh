#!/usr/bin/env bash
set -euo pipefail
# The coordinator validates the restored on-demand Rofi payload; no launcher daemon.
root=$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")
exec python3 "$root/desktop_stack.py" switch quickshell "$@"
