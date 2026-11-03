#!/usr/bin/env bash
set -euo pipefail
launcher="$HOME/.local/bin/glaze-mail"
tmp=$(mktemp -d /tmp/opencode/glaze-mail-launcher-test.XXXXXX)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/home/.config/gcal/.venv/bin" "$tmp/bin"
cat > "$tmp/home/.config/gcal/.venv/bin/python" <<'PYTHON'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$ARGUMENT_LOG"
PYTHON
cat > "$tmp/bin/alacritty" <<'TERMINAL'
#!/usr/bin/env bash
printf 'unsafe-old-launcher\n' > "$FORBIDDEN_LOG"
TERMINAL
chmod +x "$tmp/home/.config/gcal/.venv/bin/python" "$tmp/bin/alacritty"
export HOME="$tmp/home" ARGUMENT_LOG="$tmp/args" FORBIDDEN_LOG="$tmp/forbidden"
export PATH="$tmp/bin:$PATH"
timeout 5s bash "$launcher" --aerc-binary /test/runtime >/dev/null 2>"$tmp/stderr"
if [[ ! -f "$ARGUMENT_LOG" ]]; then
    echo "FAIL: mail launcher did not invoke the owned Python session launcher" >&2
    exit 1
fi
mapfile -t args < "$ARGUMENT_LOG"
[[ ${#args[@]} == 3 ]]
[[ ${args[0]} == "$HOME/.local/src/glaze-mail/session.py" ]]
[[ ${args[1]} == --aerc-binary && ${args[2]} == /test/runtime ]]
[[ ! -e "$FORBIDDEN_LOG" ]]
echo "PASS: mail entrypoint invokes only the owned session and preserves arguments"
