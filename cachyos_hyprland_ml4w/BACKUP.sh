#!/usr/bin/env bash
# Re-backup live Hyprland ML4W configs into this folder. Idempotent.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
DOT="$REPO_DIR/dotfiles/.config"
LOC="$REPO_DIR/local/.local"
mkdir -p "$DOT" "$LOC/bin" "$LOC/share/applications"

rsync -aL --delete --exclude='__pycache__/' ~/.config/hypr/ "$DOT/hypr/"
rsync -aL --delete --exclude='__pycache__/' --exclude='*.pyc' --exclude='backup-*/' ~/.config/kitty/ "$DOT/kitty/"
rsync -aL --delete ~/.config/quickshell/ "$DOT/quickshell/"
rsync -aL --delete ~/.config/waybar/ "$DOT/waybar/"
rsync -aL --delete ~/.config/rofi/ "$DOT/rofi/"
rsync -aL --delete ~/.config/swaync/ "$DOT/swaync/"
rsync -aL --delete --exclude='wallpapers/' ~/.config/ml4w/scripts/ "$DOT/ml4w/scripts/"
rsync -aL --delete --exclude='wallpapers/' ~/.config/ml4w/settings/ "$DOT/ml4w/settings/"
rsync -aL --delete ~/.config/ml4w-dock/ "$DOT/ml4w-dock/" 2>/dev/null || true
rsync -aL --delete ~/.config/ml4w-statusbar/ "$DOT/ml4w-statusbar/" 2>/dev/null || true
rsync -aL --delete ~/.config/fastfetch/ "$DOT/fastfetch/" 2>/dev/null || true
rsync -aL --delete ~/.config/fish/ "$DOT/fish/" 2>/dev/null || true

cp -a ~/.local/bin/hypr-switch-xkblayout ~/.local/bin/hypr-sysinfo ~/.local/bin/hypr-weather ~/.local/bin/hypr-current-xkblayout ~/.local/bin/qs-lazy-toggle "$LOC/bin/" 2>/dev/null || true
rsync -a --delete --exclude='.git/' ~/.local/share/ml4w-dock/ "$LOC/share/ml4w-dock/" 2>/dev/null || true
rsync -a --delete --exclude='.git/' ~/.local/share/quickshell-overview/ "$LOC/share/quickshell-overview/" 2>/dev/null || true
rsync -a --delete --exclude='.git/' ~/.local/share/ml4w-dotfiles-settings/ "$LOC/share/ml4w-dotfiles-settings/" 2>/dev/null || true
mkdir -p "$LOC/share/applications"
cp -a ~/.local/share/applications/quake-kitty.desktop "$LOC/share/applications/" 2>/dev/null || true

kitty --version > "$DOT/kitty/KITTY_PATCH_STATE.txt" 2>/dev/null || echo "kitty unknown" > "$DOT/kitty/KITTY_PATCH_STATE.txt"
echo "tabs.py resize_divider count: $(grep -c resize_divider /usr/lib/kitty/kitty/tabs.py 2>/dev/null || echo 0)" >> "$DOT/kitty/KITTY_PATCH_STATE.txt"
ls "$DOT/kitty/patches/"*.diff >> "$DOT/kitty/KITTY_PATCH_STATE.txt" 2>/dev/null || true

(cd "$REPO_DIR" && find dotfiles local -type f | sort > manifest.txt; wc -l manifest.txt; du -sh --exclude=wallpapers .)
echo BACKUP_OK
