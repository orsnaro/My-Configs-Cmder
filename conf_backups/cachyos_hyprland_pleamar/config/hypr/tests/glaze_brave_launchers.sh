#!/usr/bin/env bash
set -euo pipefail

test_dir=$(mktemp -d)
trap 'rm -rf "$test_dir"' EXIT
cat > "$test_dir/brave" <<'FAKE'
#!/usr/bin/env bash
printf '%s\n' "$@"
FAKE
chmod +x "$test_dir/brave"

for spec in \
    'gmail|https://mail.google.com/' \
    'discord|https://discord.com/channels/@me' \
    'spotify|https://open.spotify.com/'; do
    name=${spec%%|*}
    url=${spec#*|}
    args=$(env -u HYPRLAND_INSTANCE_SIGNATURE PATH="$test_dir:$PATH" "$HOME/.local/bin/glaze-$name")
    grep -Fx -- "--app=$url" <<< "$args" >/dev/null
    if grep -q -- '^--class=' <<< "$args"; then
        echo "FAIL: $name sets the shared Brave process class" >&2
        exit 1
    fi
done

echo 'PASS: Brave apps use unique app URLs without setting a shared process class'
