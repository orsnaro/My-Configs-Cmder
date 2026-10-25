#!/usr/bin/env bash
# Re-apply ORS native resize_divider patch to installed kitty (needs root).
# Idempotent: skips apply when already patched; aborts when dry-run is not clean.
set -euo pipefail

USER_HOME="${SUDO_USER_HOME:-}"
if [[ -z "$USER_HOME" && -n "${PKEXEC_UID:-}" ]]; then
  USER_HOME="$(getent passwd "$PKEXEC_UID" | cut -d: -f6)"
fi
if [[ -z "$USER_HOME" && -n "${SUDO_USER:-}" ]]; then
  USER_HOME="$(getent passwd "$SUDO_USER" | cut -d: -f6)"
fi
USER_HOME="${USER_HOME:-$HOME}"
PATCH_DIR="$USER_HOME/.config/kitty/patches"
TABS_DIFF="$PATCH_DIR/ors-resize-divider-kitty-0.49.1-tabs.diff"
UTILS_DIFF="$PATCH_DIR/ors-resize-divider-kitty-0.49.1-utils.diff"
TABS_PY="/usr/lib/kitty/kitty/tabs.py"
UTILS_PY="/usr/lib/kitty/kitty/options/utils.py"

if grep -q "def resize_divider" "$TABS_PY" && \
   grep -q "func_with_args('resize_divider')" "$UTILS_PY"; then
  echo "already patched, nothing to do"
  exit 0
fi

cd /usr/lib/kitty
patch --dry-run -p1 < "$TABS_DIFF"
patch --dry-run -p4 < "$UTILS_DIFF"

BACKUP="$PATCH_DIR/backup-$(date +%F-%H%M%S)"
mkdir -p "$BACKUP"
cp -a "$TABS_PY" "$BACKUP/tabs.py"
cp -a "$UTILS_PY" "$BACKUP/utils.py"
echo "backup: $BACKUP"

patch -p1 < "$TABS_DIFF"
patch -p4 < "$UTILS_DIFF"

rm -f /usr/lib/kitty/kitty/__pycache__/tabs.cpython-314*.pyc \
      /usr/lib/kitty/kitty/options/__pycache__/utils.cpython-314*.pyc

python3 -B - <<'EOF'
import sys
sys.path.insert(0, '/usr/lib/kitty')
from kitty.tabs import Tab
from kitty.options.utils import parse_key_action
assert callable(getattr(Tab, 'resize_divider', None)), 'tabs.py patch missing'
a = parse_key_action('resize_divider left')
assert (a.func, tuple(a.args)) == ('resize_divider', ('left',)), a
print('native patch verified')
EOF
