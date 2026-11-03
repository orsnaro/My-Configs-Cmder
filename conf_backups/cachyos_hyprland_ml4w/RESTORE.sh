#!/usr/bin/env bash
# Merge into a fresh CachyOS + ML4W 2.16 install, preserving copied permissions.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
DOT="$REPO_DIR/dotfiles/.config"
LOC="$REPO_DIR/local/.local"
DRY_ARGS=()
if [[ "${1:-}" == "--dry-run" ]]; then DRY_ARGS=(--dry-run); fi

restore_one() { # $1=src $2=dest
  if [[ -d "$1" ]]; then
    rsync -aL --mkpath --itemize-changes --exclude='.git/' "${DRY_ARGS[@]}" "$1/" "$2/"
  fi
}
for name in hypr kitty quickshell waybar rofi swaync ml4w ml4w-dock ml4w-statusbar fastfetch fish matugen walker elephant ohmyposh hyprland-kde-overrides gtk-3.0 gtk-4.0 gcal sherlock; do
  restore_one "$DOT/$name" "$HOME/.config/$name"
done
restore_one "$DOT/glaze-mail" "$HOME/.config/glaze-mail"
if [[ -f "$DOT/systemd/user/sherlock.service" ]]; then
  rsync -aL --mkpath --itemize-changes "${DRY_ARGS[@]}" "$DOT/systemd/user/sherlock.service" "$HOME/.config/systemd/user/"
fi
restore_one "$LOC/bin" "$HOME/.local/bin"
restore_one "$LOC/lib/rofi-trial" "$HOME/.local/lib/rofi-trial"
restore_one "$LOC/src/glaze-mail" "$HOME/.local/src/glaze-mail"
for name in ml4w-dock quickshell-overview ml4w-dotfiles-settings applications sherlock-integration icons; do
  restore_one "$LOC/share/$name" "$HOME/.local/share/$name"
done
# Recreate the launcher without embedding this machine's absolute HOME path.
if [[ -f "$LOC/share/ml4w-dock/bin/ml4w-dock" && ! -e "$HOME/.local/bin/ml4w-dock" && ! -L "$HOME/.local/bin/ml4w-dock" ]]; then
  if [[ ${#DRY_ARGS[@]} -gt 0 ]]; then
    echo 'Would create ~/.local/bin/ml4w-dock -> ../share/ml4w-dock/bin/ml4w-dock'
  else
    mkdir -p "$HOME/.local/bin"
    ln -s ../share/ml4w-dock/bin/ml4w-dock "$HOME/.local/bin/ml4w-dock"
  fi
fi

if [[ ${#DRY_ARGS[@]} -eq 0 ]]; then
  # Sherlock's native config/CSS use absolute paths. Rebase only copied files;
  # never rewrite browser/mail runtime state or another user's credentials.
  python3 - "$HOME" "$DOT" "$LOC" <<'PY'
from pathlib import Path
import sys

home = Path(sys.argv[1])
config_source, local_source = Path(sys.argv[2]), Path(sys.argv[3])
for name in ('config.toml', 'main.css'):
    path = home / '.config/sherlock' / name
    if (config_source / 'sherlock' / name).is_file():
        path.write_text(path.read_text().replace('/home/narol/', str(home) + '/'))
mail = home / '.config/glaze-mail'
for relative in ('eval/aerc.conf', 'eval/lesskey', 'eval/stylesets/glaze',
                 'terminal/config/aerc/binds.conf', 'terminal/config/konsolerc',
                 'terminal/data/konsole/GlazeMail.colorscheme'):
    path = mail / relative
    if (config_source / 'glaze-mail' / relative).is_file():
        path.write_text(path.read_text().replace('/home/narol/', str(home) + '/'))
        path.chmod(0o600)
        for parent in path.parents:
            if parent == mail.parent:
                break
            parent.chmod(0o700)
source = home / '.local/src/glaze-mail'
if (local_source / 'src/glaze-mail').is_dir():
    source.chmod(0o700)
    for original in (*(local_source / 'src/glaze-mail').glob('*.py'),
                     *(local_source / 'src/glaze-mail').glob('*.lua')):
        (source / original.name).chmod(0o600)
for name in ('aerc-mail.desktop',
             'brave-kdcbgnonmmimiohkdebbbipakbegkkol-Default.desktop',
             'brave-cdbapkcndmkmbeiedikfcaeelndldoha-Default.desktop'):
    if (local_source / 'share/applications' / name).is_file():
        path = home / '.local/share/applications' / name
        text = path.read_text().replace('/home/narol/', str(home) + '/')
        if name == 'aerc-mail.desktop':
            executable = str(home / '.local/bin/glaze-mail')
            for character in ('\\', '"', '`', '$'):
                executable = executable.replace(character, '\\' + character)
            executable = executable.replace('%', '%%')
            text = '\n'.join('Exec="' + executable + '"' if line.startswith('Exec=') else line
                             for line in text.splitlines()) + '\n'
        path.write_text(text)
PY
  if [[ -f "$HOME/.local/lib/rofi-trial/build-smart.sh" ]]; then
    echo "Building the on-demand Rofi plugin and cross-monitor guard..."
    bash "$HOME/.local/lib/rofi-trial/build-smart.sh" || {
      echo "Rofi native build failed; install the documented build dependencies before activating QS." >&2
      exit 1
    }
  fi
  echo "--- kitty system patch (needs sudo, kitty 0.49.2) ---"
  cat "$DOT/kitty/KITTY_PATCH_STATE.txt" 2>/dev/null || true
  read -r -p "Re-apply kitty patch with sudo now? [y/N] " ans || ans="N"
  if [[ "$ans" == [yY]* ]]; then sudo bash ~/.config/kitty/apply-native-patch.sh; fi
  echo "Done. Run: hyprctl reload (then relog for dock/quickshell)."
else
  echo "DRY-RUN done, no changes made."
fi
