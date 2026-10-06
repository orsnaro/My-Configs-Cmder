#!/usr/bin/env bash
set -euo pipefail

# Run the real indicator data source with controlled Hyprland device responses.
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cat > "$tmp/hyprctl" <<'EOF'
#!/usr/bin/env bash
[[ "$1" == devices && "$2" == -j ]] || exit 2
printf '%s\n' "$KEYBOARD_FIXTURE"
EOF
chmod +x "$tmp/hyprctl"
export PATH="$tmp:$PATH"
indicator="$HOME/.local/bin/hypr-current-xkblayout"

expect() {
    local want=$1 got
    got=$($indicator)
    [[ "$got" == "$want" ]] || { printf 'wanted %s, got %s\n' "$want" "$got" >&2; exit 1; }
}

# The main keyboard wins even if another one still has a different layout.
export KEYBOARD_FIXTURE='{"keyboards":[{"main":false,"active_layout_index":1},{"main":true,"active_layout_index":0}]}'
expect us
export KEYBOARD_FIXTURE='{"keyboards":[{"main":false,"active_layout_index":0},{"main":true,"active_layout_index":1}]}'
expect ar
# No keyboard should never claim that US is selected.
export KEYBOARD_FIXTURE='{"keyboards":[]}'
expect --
printf 'PASS: indicator reflects the main keyboard and handles no keyboard\n'
