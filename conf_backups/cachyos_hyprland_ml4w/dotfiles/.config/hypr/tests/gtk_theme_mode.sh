#!/usr/bin/env bash
set -euo pipefail

real_home=$HOME
hook="$real_home/.config/matugen/post-hook-scripts/gtk-themes-reload.sh"
toggle="$real_home/.config/ml4w/scripts/ml4w-toggle-theme"
test_dir=$(mktemp -d "${TMPDIR:-/tmp/opencode}/gtk-theme-test.XXXXXX")
trap 'rm -rf "$test_dir"' EXIT
mkdir -p "$test_dir/bin" "$test_dir/home/.config/gtk-3.0" "$test_dir/home/.config/gtk-4.0"
cat > "$test_dir/bin/gsettings" <<'FAKE'
#!/usr/bin/env bash
case "$1" in
    get) printf "'%s'\n" "${CURRENT_SCHEME:-prefer-light}" ;;
    set) printf '%s\n' "$*" >> "$SETTINGS_LOG" ;;
    *) exit 2 ;;
esac
FAKE
chmod +x "$test_dir/bin/gsettings"
export HOME="$test_dir/home" PATH="$test_dir/bin:$PATH" SETTINGS_LOG="$test_dir/writes"

write_settings() {
    for version in 3 4; do
        printf '[Settings]\ngtk-application-prefer-dark-theme=%s\ngtk-icon-theme-name=keep-me\n' "$1" > "$HOME/.config/gtk-$version.0/settings.ini"
    done
    : > "$SETTINGS_LOG"
}

expect_scheme() {
    local expected="set org.gnome.desktop.interface color-scheme $1"
    local actual
    actual=$(< "$SETTINGS_LOG")
    if [[ $actual != "$expected" ]]; then
        printf 'FAIL: expected one preference write: %s\nActual:\n%s\n' "$expected" "$actual" >&2
        exit 1
    fi
}

# Catch inverted hooks and transient writes of the opposite preference.
for spelling in true 1; do
    write_settings "$spelling"
    CURRENT_SCHEME=prefer-light bash "$hook"
    expect_scheme prefer-dark
done
for spelling in false 0; do
    write_settings "$spelling"
    CURRENT_SCHEME=prefer-dark bash "$hook"
    expect_scheme prefer-light
done
for file in "$HOME/.config/gtk-"{3,4}'.0/settings.ini'; do
    printf '[Settings]\ngtk-icon-theme-name=keep-me\n' > "$file"
done
: > "$SETTINGS_LOG"
CURRENT_SCHEME=prefer-light bash "$hook"
expect_scheme prefer-dark

# Run the actual toggle without any background wallpaper listener.
for spelling in true 1; do
    write_settings "$spelling"
    bash "$toggle" > /dev/null
    expect_scheme prefer-light
    grep -Eq '^gtk-application-prefer-dark-theme=(0|false)$' "$HOME/.config/gtk-3.0/settings.ini"
    grep -Eq '^gtk-application-prefer-dark-theme=(0|false)$' "$HOME/.config/gtk-4.0/settings.ini"
    : > "$SETTINGS_LOG"
    bash "$toggle" > /dev/null
    expect_scheme prefer-dark
    grep -Eq '^gtk-application-prefer-dark-theme=(1|true)$' "$HOME/.config/gtk-3.0/settings.ini"
    grep -Eq '^gtk-application-prefer-dark-theme=(1|true)$' "$HOME/.config/gtk-4.0/settings.ini"
    for version in 3 4; do
        grep -Fxq 'gtk-icon-theme-name=keep-me' "$HOME/.config/gtk-$version.0/settings.ini"
    done
done
printf 'PASS: saved GTK preference, dark fallback, no preference flicker, and manual theme round trips\n'
