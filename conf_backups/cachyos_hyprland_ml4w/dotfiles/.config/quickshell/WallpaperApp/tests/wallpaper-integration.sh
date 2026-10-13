#!/usr/bin/env bash
set -euo pipefail
# Login-resume + gamemode integration contracts for the slideshow.
autostart="$HOME/.config/ml4w/scripts/ml4w-autostart"
gamemode="$HOME/.config/hypr/scripts/gamemode.sh"
wallpaper_script="$HOME/.config/ml4w/scripts/ml4w-wallpaper"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
need() { grep -q -- "$2" "$1" || fail "$3"; }

need "$autostart" "wallpaper-slideshow" "autostart must consult the persisted slideshow setting"
need "$autostart" "ml4w-wallpaper-automation --start" "autostart must resume the slideshow when enabled"
need "$autostart" "ml4w-wallpaper-automation --status" "autostart must guard against duplicate loops"
need "$autostart" "BEGIN slideshow resume" "resume block must be delimited for testing"
need "$gamemode" "ml4w-wallpaper-automation --stop" "gamemode enter must pause via --stop"
need "$gamemode" "ml4w-wallpaper-automation --start" "gamemode exit must resume via --start"
need "$gamemode" "restart-wpauto" "gamemode must preserve restart intent"

# ---- Isolated login simulation: extract the delimited block and run it ----
sandbox() {
    local home; home=$(mktemp -d /tmp/opencode/wallpaper-login-test-XXXXXX)
    mkdir -p "$home/.config/ml4w/settings" "$home/.config/ml4w/scripts"
    cat > "$home/.config/ml4w/scripts/ml4w-wallpaper-automation" <<'STUB'
#!/usr/bin/env bash
printf 'AUTO %s\n' "$*" >> "$AUDIT_LOG"
exit "${AUTO_STATUS:-1}"
STUB
    chmod +x "$home/.config/ml4w/scripts/ml4w-wallpaper-automation"
    printf '%s' "$home"
}

run_resume_block() {
    # $1 = sandbox home; runs the production resume block with stubbed helpers
    local home="$1"
    sed -n '/# BEGIN slideshow resume/,/# END slideshow resume/p' "$autostart" > "$home/resume.sh"
    : > "$home/calls.log"
    HOME="$home" PATH="/usr/bin:/bin" AUDIT_LOG="$home/calls.log" \
        AUTO_STATUS="${AUTO_STATUS:-1}" bash -c '
            info() { printf "INFO %s\n" "$*" >> "$AUDIT_LOG"; }
            source "$1"
        ' _ "$home/resume.sh" >>"$home/calls.log" 2>&1 || true
    /bin/sleep 0.2
}

# Case 1: enabled + not running -> --status probe then background --start.
h=$(sandbox); printf 'true' > "$h/.config/ml4w/settings/wallpaper-slideshow"
AUTO_STATUS=1 run_resume_block "$h"
grep -q '^AUTO --status$' "$h/calls.log" || fail "resume must probe --status first"
grep -q '^AUTO --start$' "$h/calls.log" || fail "enabled slideshow must resume at login"

# Case 2: disabled -> no automation calls at all.
h=$(sandbox); printf 'false' > "$h/.config/ml4w/settings/wallpaper-slideshow"
AUTO_STATUS=1 run_resume_block "$h"
grep -q '^AUTO ' "$h/calls.log" && fail "disabled slideshow must not launch at login"

# Case 3: enabled + already running -> probe only, no duplicate start.
h=$(sandbox); printf 'true' > "$h/.config/ml4w/settings/wallpaper-slideshow"
AUTO_STATUS=0 run_resume_block "$h"
grep -q '^AUTO --status$' "$h/calls.log" || fail "resume must probe --status first"
grep -q '^AUTO --start$' "$h/calls.log" && fail "running slideshow must not start a duplicate"

effect="$HOME/.config/hypr/effects/wallpaper/grain-heavy"
listener="$HOME/.config/ml4w/listeners/gtk-theme-switcher.sh"
effects_dir="$HOME/.config/hypr/effects/wallpaper"
need "$effect" '"$IMAGE_PATH"' "effect must quote image paths (spaced filenames)"
need "$effect" '"$ORIG"' "effect must quote the source path"
need "$listener" '"$(cat' "listener must quote the cached wallpaper path"
need "$wallpaper_script" "waybar-disabled" "waybar reload must respect the disabled marker"
need "$wallpaper_script" "warn" "quickshell reload must warn instead of claiming success on IPC failure"

# Post-review findings: (1) every effect must quote IMAGE_PATH, (2) automation
# start must be lock-serialized, (3) QML thumbnail path must escape quotes.
bad=""
for f in "$effects_dir"/*; do
    hit=$(awk '/\$IMAGE_PATH/ && !/"\$IMAGE_PATH"/ {print FNR": "$0}' "$f" || true)
    [[ -n "$hit" ]] && bad="$bad$(basename "$f") $hit; "
done
[[ -z "$bad" ]] || fail "effects with unquoted IMAGE_PATH: $bad"
need "$HOME/.config/ml4w/scripts/ml4w-wallpaper-automation" "flock" "automation start must be serialized with flock"

qml_file="$HOME/.config/quickshell/WallpaperApp/WallpaperWindow.qml"
grep -qF "replace(/'" "$qml_file" || fail "thumbnail path must escape single quotes before bash -c"

# Real-magick reproduction: the effect snippet must handle spaced filenames.
fx=$(mktemp -d /tmp/opencode/wallpaper-effect-test-XXXXXX)
magick -size 4x4 xc:black "$fx/orig file.png" || fail "test setup could not create image"
printf '%s' "$fx/orig file.png" > "$fx/current_wallpaper"
CACHE_FILE="$fx/current_wallpaper" IMAGE_PATH="$fx/processed file.png" \
    bash -c 'source "$1"' _ "$effect" || fail "effect snippet must succeed on spaced filenames"
[[ -f "$fx/processed file.png" ]] || fail "effect must write the spaced output file"
# apply_effect copies the source to the cached name before sourcing snippets
# without a pristine-restore header (blur1, blur2, blackwhite*, negate*).
cp "$fx/orig file.png" "$fx/processed blur.png"
CACHE_FILE="$fx/current_wallpaper" IMAGE_PATH="$fx/processed blur.png" \
    bash -c 'source "$1"' _ "$effects_dir/blur1" || fail "blur1 must succeed on spaced filenames"
[[ -f "$fx/processed blur.png" ]] || fail "blur1 must write the spaced output file"
CACHE_FILE="$fx/current_wallpaper" IMAGE_PATH="$fx/processed noise.png" \
    bash -c 'cp "$(cat "$CACHE_FILE")" "$IMAGE_PATH"; source "$1"' _ "$effects_dir/glass-noise" \
    || fail "glass-noise must succeed on spaced filenames"
[[ -f "$fx/processed noise.png" ]] || fail "glass-noise must write the spaced output file"

# Stubbed pipeline run: disabled waybar + failing qs must not claim success.
px=$(mktemp -d /tmp/opencode/wallpaper-reload-test-XXXXXX)
mkdir -p "$px/.config/ml4w/settings" "$px/.config/gtk-3.0" "$px/bin"
printf 'simple' > "$px/.config/ml4w/settings/wallpaper-transition-effect"
printf 'off' > "$px/.config/ml4w/settings/wallpaper-effect"
printf 'true' > "$px/.config/ml4w/settings/wallpaper-theming"
printf '0x0' > "$px/.config/ml4w/settings/blur.sh"
touch "$px/.config/ml4w/settings/waybar-disabled"
printf '[Settings]\ngtk-application-prefer-dark-theme=1\n' > "$px/.config/gtk-3.0/settings.ini"
touch "$px/input.png"
for name in awww matugen magick swaync-client walker pkill killall pgrep pywalfox notify-send nohup sleep; do
    cat > "$px/bin/$name" <<'STUB'
#!/usr/bin/env bash
printf '%s %s\n' "${0##*/}" "$*" >> "$AUDIT_LOG"
case "${0##*/}" in
  awww) [[ "$1" == "--version" ]] && echo "awww 0.12.1";;
  pgrep) [[ "$*" == *"-x qs"* ]] && exit 0; exit 1;;
  qs) exit 1;;
esac
exit 0
STUB
    chmod +x "$px/bin/$name"
done
: > "$px/calls.log"
HOME="$px" PATH="$px/bin:/usr/bin:/bin" AUDIT_LOG="$px/calls.log" \
    bash "$wallpaper_script" "$px/input.png" >"$px/out.log" 2>"$px/err.log" || true
grep -q "Waybar restarted" "$px/err.log" && fail "disabled waybar must not be reported as restarted"
grep -q "nohup" "$px/calls.log" && fail "disabled waybar must not be launched"
grep -q "Quickshell theme updated" "$px/err.log" && fail "failed IPC must not be reported as updated"

printf 'PASS: slideshow login resume and gamemode integration honored\n'
