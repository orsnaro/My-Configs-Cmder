#!/usr/bin/env bash
# Re-backup live Hyprland ML4W configs into this folder. Idempotent.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
DOT="$REPO_DIR/dotfiles/.config"
LOC="$REPO_DIR/local/.local"
mkdir -p "$DOT" "$LOC/bin" "$LOC/share/applications"
mkdir -p "$DOT/ml4w/scripts" "$DOT/ml4w/settings" "$DOT/ml4w/listeners"

# Hyprland's on-demand launcher is source-backed; rebuild its ABI-specific plugin on restore.
if [[ -f "$HOME/.local/bin/rofi-trial" ]]; then
    cp -L -- "$HOME/.local/bin/rofi-trial" "$LOC/bin/rofi-trial"
    mkdir -p "$LOC/lib/rofi-trial"
    rsync -aL --exclude='*.so' --exclude='dismiss-guard' --exclude='.*' --exclude='__pycache__/' --exclude='*.pyc' \
        "$HOME/.local/lib/rofi-trial/" "$LOC/lib/rofi-trial/"
fi
if [[ -f "$HOME/.config/ml4w/listeners/gtk-theme-switcher.sh" ]]; then
    cp -L -- "$HOME/.config/ml4w/listeners/gtk-theme-switcher.sh" "$DOT/ml4w/listeners/"
fi
for theme in glass modern transparent glass-walker modern-walker; do
    if [[ -f "$HOME/.config/ml4w/themes/$theme/theme.sh" ]]; then
        mkdir -p "$DOT/ml4w/themes/$theme"
        cp -L -- "$HOME/.config/ml4w/themes/$theme/theme.sh" "$DOT/ml4w/themes/$theme/"
    fi
done

# Excluded files already in a snapshot are protected, not silently deleted.
# Review and remove any old private artifacts separately before publication.
EXCLUDES=(
  --exclude='*.bak*' --exclude='*-bak' --exclude='backup-*/' --exclude='.git/' --exclude='.github/'
  --exclude='__pycache__/' --exclude='*.pyc' --exclude='.pytest_cache/'
  --exclude='.cache/' --exclude='.superpowers/' --exclude='.opencode/'
  --exclude='.venv/' --exclude='venv/' --exclude='node_modules/'
  --exclude='.env' --exclude='.env.*' --exclude='credentials.json'
  --exclude='token.json' --exclude='tokens.json' --exclude='client_secret*.json'
  --exclude='fish_variables' --exclude='wallpapers/'
)

backup_tree() { # $1=source $2=destination, optional rsync filters follow
  local src="$1" dest="$2"
  shift 2
  mkdir -p "$dest"
  rsync -aL --delete "${EXCLUDES[@]}" "$@" "$src/" "$dest/"
}
optional_tree() {
  if [[ -d "$1" ]]; then backup_tree "$@"; fi
}
backup_file() {
  if [[ -f "$1" ]]; then rsync -aL "$1" "$2/"; fi
}

for name in hypr kitty quickshell waybar rofi swaync ml4w; do
  backup_tree "$HOME/.config/$name" "$DOT/$name"
done
for name in ml4w-dock ml4w-statusbar fastfetch fish matugen walker elephant ohmyposh hyprland-kde-overrides; do
  optional_tree "$HOME/.config/$name" "$DOT/$name"
done
optional_tree "$HOME/.config/sherlock" "$DOT/sherlock"
mkdir -p "$DOT/systemd/user" "$DOT/glaze-mail/eval/stylesets" \
  "$DOT/glaze-mail/terminal/config/aerc" "$DOT/glaze-mail/terminal/data/konsole"
backup_file "$HOME/.config/systemd/user/sherlock.service" "$DOT/systemd/user"
backup_file "$HOME/.local/bin/sherlock-launch" "$LOC/bin"
optional_tree "$HOME/.local/share/sherlock-integration" "$LOC/share/sherlock-integration" \
  --exclude='target/' --exclude='*.tar.gz' --exclude='Cargo.lock.upstream'
# Mail's surrounding directories contain browser profiles, drafts and credentials.
# Only declarative preferences and reviewed source are public backup inputs.
optional_tree "$HOME/.local/src/glaze-mail" "$LOC/src/glaze-mail" \
  --include='/*.py' --include='/*.lua' --include='/Makefile' --include='/README.md' \
  --include='/requirements-preview.txt' --include='/assets/***' \
  --include='/tests/***' --include='/tests_preview/***' --exclude='*'
for name in aerc.conf lesskey; do
  backup_file "$HOME/.config/glaze-mail/eval/$name" "$DOT/glaze-mail/eval"
done
backup_file "$HOME/.config/glaze-mail/eval/stylesets/glaze" "$DOT/glaze-mail/eval/stylesets"
backup_file "$HOME/.config/glaze-mail/terminal/config/aerc/binds.conf" "$DOT/glaze-mail/terminal/config/aerc"
backup_file "$HOME/.config/glaze-mail/terminal/config/konsolerc" "$DOT/glaze-mail/terminal/config"
backup_file "$HOME/.config/glaze-mail/terminal/data/konsole/GlazeMail.colorscheme" "$DOT/glaze-mail/terminal/data/konsole"
for name in gtk-3.0 gtk-4.0; do
  optional_tree "$HOME/.config/$name" "$DOT/$name" \
    --include='/settings.ini' --include='/gtk.css' --include='/colors.css' --exclude='*'
done
# Never copy the entire calendar directory: tokens and agenda state are private.
optional_tree "$HOME/.config/gcal" "$DOT/gcal" \
  --include='/gcal-consent.py' --include='/gcal-sync.py' --include='/gcal-remind.py' \
  --include='/tests/' --include='/tests/***' --exclude='*'

for name in hypr-switch-xkblayout hypr-sysinfo hypr-weather hypr-current-xkblayout qs-lazy-toggle albion-data-watch albion-data-start; do
  backup_file "$HOME/.local/bin/$name" "$LOC/bin"
done
shopt -s nullglob
for file in "$HOME"/.local/bin/glaze-*; do backup_file "$file" "$LOC/bin"; done
rm -f "$LOC/bin/cemu-mousepad.py" 2>/dev/null || true
for name in ml4w-dock quickshell-overview ml4w-dotfiles-settings; do
  optional_tree "$HOME/.local/share/$name" "$LOC/share/$name"
done
backup_file "$HOME/.local/share/applications/quake-kitty.desktop" "$LOC/share/applications"
backup_file "$HOME/.local/share/applications/aerc-mail.desktop" "$LOC/share/applications"
for app in brave-kdcbgnonmmimiohkdebbbipakbegkkol-Default brave-cdbapkcndmkmbeiedikfcaeelndldoha-Default; do
  backup_file "$HOME/.local/share/applications/$app.desktop" "$LOC/share/applications"
  mkdir -p "$LOC/share/icons/hicolor/512x512/apps"
  backup_file "$HOME/.local/share/icons/hicolor/512x512/apps/$app.png" "$LOC/share/icons/hicolor/512x512/apps"
done

kitty --version > "$DOT/kitty/KITTY_PATCH_STATE.txt" 2>/dev/null || echo "kitty unknown" > "$DOT/kitty/KITTY_PATCH_STATE.txt"
echo "tabs.py resize_divider count: $(grep -c resize_divider /usr/lib/kitty/kitty/tabs.py 2>/dev/null || echo 0)" >> "$DOT/kitty/KITTY_PATCH_STATE.txt"
(cd "$DOT/kitty/patches" && ls *.diff) >> "$DOT/kitty/KITTY_PATCH_STATE.txt" 2>/dev/null || true

(cd "$REPO_DIR" && find dotfiles local -type f | LC_ALL=C sort > manifest.txt; wc -l manifest.txt; du -sh --exclude=wallpapers .)
echo BACKUP_OK
