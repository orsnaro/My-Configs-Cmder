# CachyOS Hyprland ML4W configs — backup 2026-10-06

Base: CachyOS + ML4W dotfiles stable 2.16 + kitty 0.49.2
Repo: https://github.com/orsnaro/My-Configs-Cmder.git, folder `cachyos_hyprland_ml4w/`

Source live paths are symlinks:
`~/.config/hypr|kitty|waybar|quickshell|rofi|swaync` -> `~/.mydotfiles/com.ml4w.dotfiles.stable/.config/...`

Layout here mirrors $HOME:
- `dotfiles/.config/...` (hypr, kitty, quickshell, waybar, rofi, swaync, ml4w/scripts+settings, ml4w-dock, ml4w-statusbar, fastfetch, fish)
- `local/.local/bin/...` (hypr-*, qs-lazy-toggle; cemu-mousepad.py excluded)
- `local/.local/share/...` (ml4w-dock QML source, quickshell-overview, ml4w-dotfiles-settings, applications/quake-kitty.desktop)

Excluded: `ml4w/wallpapers/` (209M), `__pycache__/`, `*.pyc`, `kitty/patches/backup-*/` full copies.

Kitty source patch: `dotfiles/.config/kitty/patches/*.diff` + `apply-native-patch.sh`, requires sudo, version-pinned 0.49.2. See `KITTY_PATCH_STATE.txt`.

Dock QML (`local/.local/share/ml4w-dock/`) + quickshell QML are user-space source (plain copy, no sudo). Only kitty needs sudo re-patch.

Matugen regen (do not fight): `hypr/colors.conf`, `hypr/colors.lua`, `kitty/colors-matugen.conf`, `ml4w-dock/colors.json`.

Restore: `./RESTORE.sh [--dry-run]` — copies back, `chmod +x *.sh/*.py`, prompts for kitty sudo patch, then `hyprctl reload`.
Re-backup: `./BACKUP.sh`

### Dock update — 2026-10-12

- Dolphin is pinned before Brave.
- Hold a pinned icon with the left mouse button for ~0.25 s, drag horizontally
  onto another pinned icon, and release to persist its order. Dropping outside
  the pinned icons cancels; running-only apps are unchanged.
- No new polling, recurring timers or processes. Controlled post-use
  comparisons measured +256–580 KiB private memory and zero sampled idle CPU ticks.
- Source, isolated Qt gesture tests and validation report are backed up under
  `local/.local/share/ml4w-dock/`. See its
  `docs/superpowers/reports/2026-10-12-dock-reorder.md` for test/resource details
  and the pre-existing Quickshell/Qt version warning.

## Caveats

### Rofi launcher — permanent Hyprland selection, 2026-10-31

- Bare **Super**: app search and inline arithmetic (`2+2` → `4`; Enter copies).
  **Super+R** runs commands, **Super+.** opens the 6×6 emoji grid, and
  **Super+V** opens clipboard history with image previews. Repeat a shortcut to
  close that menu; Escape or clicking the transparent area outside also cancels.
- Emoji uses contiguous keyword matching (`heart` no longer matches scattered
  letters in unrelated descriptions). Other menus retain fuzzy abbreviations.
  Search results use fzf relevance ranking; empty clipboard searches keep recency.
- The executable retains its compatible name `~/.local/bin/rofi-trial`; this is
  no longer session-only. The QS coordinator in `tools/desktop_stack.py` starts
  neither Walker/Elephant nor a resident Rofi process. KDE configuration is untouched.
- The ML4W clipboard button forwards to the same preview/toggle helper. Visual
  theme presets preserve the selected launcher rather than resetting it to Walker.
- Runtime packages on CachyOS/Arch: `rofi`, `rofi-calc`, `rofimoji`, `libqalculate`,
  `wl-clipboard`, `cliphist`, `fd`, and an installed `xdg-open` provider. Plugin build:
  `gcc`, `pkgconf`, `glib2`, `cairo`, `pango`, `libqalculate`, and Rofi development headers.
  This payload was tested with Rofi 2.0.0 and Qalculate 5.13.2.
- `BACKUP.sh` includes launcher helpers/source and the guarded GTK listener.
  `RESTORE.sh --dry-run` never builds or launches anything; actual restore builds
  `smart.so` against the installed Rofi/Qalculate ABI and fails visibly on build errors.
  No compiled plugin or clipboard database/history is published in this backup.
- Restore ML4W files first. For the existing QS/Pleamar setup, then run repository-root
  `python3 tools/install_desktop_stack.py --dry-run`, followed by `--apply`, to install
  coordinator/switch links and mode guards. Keep the repository at that path afterward.
  `tools/switch-to-qs.sh` checks Rofi assets before stopping the current stack.

Original full-stack **PSS** baseline (MiB), retained without remeasurement:

| View | Walker/Elephant | Original Rofi trial |
| --- | ---: | ---: |
| Closed | 214.74 | 0.22 |
| Apps | 257.22 | 29.93 |
| Emoji | 262.96 | 46.07 |
| Clipboard | 255.37 | 30.93 |

These are original measurements, **not a benchmark of the later smart-search
plugin/full-monitor theme**. Raw samples and recovery data remain at
`~/.local/state/launcher-trial/20261031T133150+0200/` on the original machine;
`followup/` records subsequent fixes and safe recovery checkpoints.

- Restore targets `$HOME` only (no alternate target dir); base required: CachyOS + ML4W dotfiles stable 2.16.
- `hypr/monitors.conf` + `custom.lua` workspaces hardcode a 3-monitor layout (DP-2/HDMI-A-2/DP-1) — adjust for single-display machines.
- Matugen overwrites `hypr/colors.*`, `kitty/colors-matugen.conf`, `ml4w-dock/colors.json` on theme change; these copies are a snapshot.
- `kitty/patches/ors-*-tabs-before-no-neighbors.diff` is a superseded single-hunk iteration, kept for reference; the applier uses `tabs.diff` + `utils.diff` only.
- Excluded on purpose: game/tool binaries (`albiondata-client`, `fetch`, `obsidian*`), `cemu-mousepad.py`, `*.bak` leftovers.
