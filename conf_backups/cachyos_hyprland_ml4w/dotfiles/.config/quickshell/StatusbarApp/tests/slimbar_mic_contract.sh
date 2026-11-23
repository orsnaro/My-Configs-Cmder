#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
slim="$root/StatusbarApp/SlimBarWindow.qml"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
need() { grep -Fq -- "$1" "$2" || fail "$3"; }

need 'MicModule {' "$slim" "slim bar must include MicModule"
need 'pillHeight: 26' "$slim" "slim mic should use compact pillHeight"
need 'iconSize: 16' "$slim" "slim mic should use compact iconSize"

# Placement: keyboard layout, then mic, then volume.
awk '
  /KeyboardLayoutModule \{/ { k=NR }
  /MicModule \{/ { m=NR }
  /VolumeModule \{/ { v=NR }
  END {
    if (!(k && m && v)) exit 1;
    if (!(k < m && m < v)) exit 1;
  }
' "$slim" || fail "MicModule must be placed between KeyboardLayoutModule and VolumeModule"

printf 'PASS: slim bars include mic module contract\n'
