#!/usr/bin/env bash
set -euo pipefail
root=$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")
exec python3 "$root/desktop_stack.py" switch quickshell "$@"
