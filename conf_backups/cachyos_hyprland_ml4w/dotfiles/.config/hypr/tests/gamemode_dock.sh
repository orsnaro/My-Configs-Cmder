#!/usr/bin/env bash
set -euo pipefail

source_script="$HOME/.config/hypr/scripts/gamemode-dock.sh"
if [[ ! -f "$source_script" ]]; then
    echo 'FAIL: combined game-mode/dock toggle does not exist' >&2
    exit 1
fi
test_dir=$(mktemp -d "${TMPDIR:-/tmp/opencode}/gamemode-dock-test.XXXXXX")
trap 'rm -rf "$test_dir"' EXIT
real_home=$HOME
export HOME="$test_dir/home" XDG_RUNTIME_DIR="$test_dir/runtime"
export COMMAND_LOG="$test_dir/commands" DOCK_RUNNING="$test_dir/dock-running"
export PATH="$test_dir/bin:$PATH"
mkdir -p "$test_dir/bin" "$XDG_RUNTIME_DIR" "$HOME/.config/hypr/scripts" \
    "$HOME/.config/ml4w/settings" "$HOME/.config/ml4w/scripts" \
    "$HOME/.cache/ml4w/hyprland-dotfiles" "$HOME/.local/bin" \
    "$HOME/.local/share/ml4w-dock/bin"
cp "$source_script" "$HOME/.config/hypr/scripts/gamemode-dock.sh"
cp "$real_home/.config/hypr/scripts/gamemode.sh" "$HOME/.config/hypr/scripts/gamemode.sh"
cp "$real_home/.local/bin/ml4w-dock" "$HOME/.local/share/ml4w-dock/bin/ml4w-dock"
chmod +x "$HOME/.local/share/ml4w-dock/bin/ml4w-dock"
ln -s "$HOME/.local/share/ml4w-dock/bin/ml4w-dock" "$HOME/.local/bin/ml4w-dock"
printf 'notify_user() { :; }\n' > "$HOME/.config/ml4w/scripts/ml4w-notification-handler"
printf '#!/usr/bin/env bash\nexit 1\n' > "$HOME/.config/ml4w/scripts/ml4w-wallpaper-automation"
chmod +x "$HOME/.config/ml4w/scripts/ml4w-wallpaper-automation"

cat > "$test_dir/bin/hyprctl" <<'FAKE'
#!/usr/bin/env bash
set -euo pipefail
case "$*" in
    'eval activate_gamemode()'|'reload') printf 'hyprctl %s\n' "$*" >> "$COMMAND_LOG" ;;
    *) echo "Unexpected hyprctl: $*" >&2; exit 1 ;;
esac
FAKE
cat > "$test_dir/bin/qs" <<'FAKE'
#!/usr/bin/env bash
set -euo pipefail
expected="$HOME/.local/share/ml4w-dock"
case "$*" in
    "kill -p $expected")
        printf 'dock stop\n' >> "$COMMAND_LOG"
        rm -f "$DOCK_RUNNING"
        ;;
    "-n -p $expected")
        printf 'dock start\n' >> "$COMMAND_LOG"
        touch "$DOCK_RUNNING"
        # Model a long-lived dock process to expose an inherited toggle lock.
        if [[ ${HOLD_START:-0} == 1 ]]; then sleep 3; fi
        ;;
    *) echo "Unexpected qs (must target only the dock): $*" >&2; exit 1 ;;
esac
FAKE
chmod +x "$test_dir/bin/hyprctl" "$test_dir/bin/qs"
toggle="$HOME/.config/hypr/scripts/gamemode-dock.sh"
marker="$HOME/.config/ml4w/settings/gamemode-enabled"

wait_for_dock() {
    for ((attempt = 0; attempt < 100; attempt++)); do
        [[ -f "$DOCK_RUNNING" ]] && return 0
        sleep 0.02
    done
    echo 'FAIL: dock did not restart' >&2
    return 1
}

# Entry stops the dedicated dock, not any other Quickshell configuration.
touch "$DOCK_RUNNING"
bash "$toggle"
test -f "$marker"
test ! -f "$DOCK_RUNNING"
diff -u <(printf 'hyprctl eval activate_gamemode()\ndock stop\n') "$COMMAND_LOG"
echo 'PASS: game mode ON stops only the dock'

# Exit starts the dock without keeping the shortcut alive for its lifetime.
: > "$COMMAND_LOG"
export HOLD_START=1
timeout 1 bash "$toggle"
test ! -f "$marker"
wait_for_dock
diff -u <(printf 'hyprctl reload\ndock start\n') "$COMMAND_LOG"
echo 'PASS: game mode OFF restarts the dock in the background'

# Another press must work even while that background process is still alive.
timeout 1 bash "$toggle"
test -f "$marker"
test ! -f "$DOCK_RUNNING"
echo 'PASS: the restarted dock does not inherit the shortcut lock'
unset HOLD_START

# A failing game-mode transition must not change the dock's lifecycle.
printf '#!/usr/bin/env bash\nexit 42\n' > "$HOME/.config/hypr/scripts/gamemode.sh"
: > "$COMMAND_LOG"
if bash "$toggle"; then
    echo 'FAIL: game-mode failure was ignored' >&2
    exit 1
fi
test ! -s "$COMMAND_LOG"
echo 'PASS: game-mode failure leaves the dock untouched'
