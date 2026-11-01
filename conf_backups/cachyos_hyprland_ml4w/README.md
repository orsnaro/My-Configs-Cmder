# CachyOS Hyprland ML4W configs — refreshed 2026-10-13

Base: CachyOS + ML4W dotfiles stable 2.16 + kitty 0.49.2
Repo: https://github.com/orsnaro/My-Configs-Cmder.git, folder `conf_backups/cachyos_hyprland_ml4w/`

Source live paths are symlinks:
`~/.config/hypr|kitty|waybar|quickshell|rofi|swaync` -> `~/.mydotfiles/com.ml4w.dotfiles.stable/.config/...`

Layout here mirrors $HOME:
- `dotfiles/.config/...` (hypr, kitty, quickshell, waybar, rofi, swaync, ML4W source/settings/listeners/themes/assets/colors, ml4w-dock, ml4w-statusbar, fastfetch, declarative fish configuration)
- Appearance/launcher dependencies: matugen configuration/templates, walker, elephant, ohmyposh, hyprland-kde-overrides; GTK 3/4 `settings.ini`, `gtk.css`, and `colors.css` only.
- Calendar: `gcal-consent.py`, `gcal-sync.py`, `gcal-remind.py`, and tests only.
- `local/.local/bin/...` (hypr-*, glaze-*, qs-lazy-toggle, albion-data-watch/start; cemu-mousepad.py excluded)
- `local/.local/share/...` (ml4w-dock QML source, quickshell-overview, ml4w-dotfiles-settings, applications/quake-kitty.desktop)

Excluded: wallpapers, backup leftovers (`*.bak*`, `*-bak`, `backup-*/`), Python caches, `.git/`, `.github/`, private `.superpowers/`/`.opencode/` scratch, virtual environments, node_modules, `.env*`, OAuth credentials/tokens, and Fish's mutable `fish_variables` store. Intentional dock `docs/superpowers/` reports/plans and tests remain included. Calendar caches, notification state, GTK bookmarks and personal agenda data are not allowlisted.

Kitty source patch: `dotfiles/.config/kitty/patches/*.diff` + `apply-native-patch.sh`, requires sudo, version-pinned 0.49.2. See `KITTY_PATCH_STATE.txt`.

Dock QML (`local/.local/share/ml4w-dock/`) + quickshell QML are user-space source (plain copy, no sudo). Only kitty needs sudo re-patch.

Matugen regen (do not fight): `hypr/colors.conf`, `hypr/colors.lua`, `kitty/colors-matugen.conf`, `ml4w-dock/colors.json`.

Restore: `./RESTORE.sh [--dry-run]` — merges files without deleting unrelated destination files, preserves copied permissions, recreates the dock launcher link if absent, and prompts for the Kitty sudo patch. It **prints** the reload/relogin instruction; it does not reload the desktop automatically. Dry-run previews config, bin, and desktop-entry copies without writing files. Requires Bash and rsync with `--mkpath` support.
Re-backup: `./BACKUP.sh` — refreshes the allowlisted snapshot and manifest. Missing optional directories are skipped; real copy failures stop the script. Exclusions protect existing excluded snapshot files: review/remove old artifacts explicitly rather than using `--delete-excluded`.

## Current behavior

- Quake Kitty stays open and visible when GUI windows launch. The native `quake-apps-to-normal-workspace` rule sends non-Quake windows initially mapped on `special:quake` to `m+0 silent` (the normal workspace underneath); no wrapper, daemon, or polling.
- Mouse-follow focus remains enabled with `special_fallthrough = true`; `hide_special_on_workspace_change = false` keeps Quake visible while normal workspaces change.
- Dock press/hold reordering uses the current 250 ms threshold; gesture regressions and the implementation report are included.
- Includes current Kitty resize mappings, wallpaper automation/theming, calendar panel/helpers, Fastfetch network-usage query, and Walker/Elephant configuration.
- The Quickshell updates button uses Cachy Update (`arch-update`): its count includes system, AUR, and Flatpak entries from `${XDG_STATE_HOME:-$HOME/.local/state}/arch-update/last_updates_check`. It watches that cache and reloads it every 30 minutes without launching another update checker. The existing Cachy Update timer owns scheduled checks; clicking the button opens its interactive updater in the configured ML4W terminal. Updates remain manual, with no package-age delay.

## Restore prerequisites

- Install the applications/tools referenced by the configs separately (including Walker/Elephant, Matugen, Quickshell, Oh My Posh, and the Albion data client if used). This is a config/source backup, not a binary or package backup.
- The updates button requires Cachy Update (`arch-update`) and the terminal configured in `~/.config/ml4w/settings/terminal.sh`. Keep Cachy Update's check timer enabled for fresh counts; its cache is runtime state and is not backed up.
- Fish expects `~/.local/bin/oh-my-posh`; the Pomo module expects `~/.local/bin/pomo`. Install these separately or recreate their links; the current Pomo binary lives in an external repo.
- Calendar helpers require a fresh `~/.config/gcal/.venv` with `google-api-python-client`, `google-auth`, and `google-auth-oauthlib`. Supply your own `client_secret_*.json`, then run `~/.config/gcal/.venv/bin/python ~/.config/gcal/gcal-consent.py` to consent. Tokens, caches, and virtual environments are intentionally not restored.
- Obsidian's mounted vault and browser profiles are external and are not backed up here.

## Backup-script tests

`python3 -m unittest discover -s tests -v` runs both scripts against disposable homes under `/tmp/opencode` with real rsync. Component regressions live in their respective `tests/` directories; some GUI integrations require a dedicated session/terminal.

`python3 dotfiles/.config/quickshell/StatusbarApp/tests/updates.py` exercises the real updates module offscreen with disposable cache/terminal fixtures, without checking repositories or installing updates. The volume-panel layout regression includes the existing microphone module; no layout change is needed for the updater integration.

Snapshot validation on 2026-10-13 (historical snapshot, not a current status): backup/restore fixtures, Hyprland, Kitty unit tests, wallpaper tests and offline calendar tests passed then. **The full suite was not green at that time:** the statusbar module-order assertion predated the microphone module, Fastfetch's historical baseline fixture was external/missing, and dock Wayland long-hold/timing checks failed. The statusbar/volume-panel assertion has since been corrected for the 2026-10-17 updater change; the unrelated historical Fastfetch external-fixture and dock GUI failures are **not** claimed fixed. These are reported for separate investigation, not silently skipped; the backup PR is a draft.

## Directional navigation

Physical keys: J=left, L=right, I=up, K=down (US and Arabic layouts).

- `Alt+J/L/I/K`: Kitty panes first; at a pane edge, focus desktop windows, then adjacent monitors, including empty active workspaces. At the outer monitor edge, stop without wrapping.
- `Shift+Alt+J/L/I/K`: move desktop windows.
- `Ctrl+Shift+Alt+J/L/I/K`: focus desktop windows.
- `Ctrl+Alt+J/L/I/K`: resize Kitty panes; native resize mappings and the Python fallback remain unchanged.
- `Shift+Alt+arrows`: desktop window focus, unchanged.

Kitty receives the original event, not a synthetic forwarded shortcut. Its no-UI `smart-focus.py` focuses pane groups in-process and uses bounded local Hyprland IPC only at an edge. `checked_focus` also handles empty desktops; PID/address guards reject stale Kitty requests. No watcher, polling, parity filter or navigation subprocess is needed.

## Caveats

### Rofi launcher — permanent Hyprland selection, 2026-10-31

- Bare **Super**: app search and inline arithmetic (`2+2` → `4`; Enter copies).
  **Super+R** runs commands, **Super+.** opens the 6×6 emoji grid, and
  **Super+V** opens clipboard history with image previews. Repeat a shortcut to
  close that menu; Escape or clicking outside on **any connected monitor** also
  cancels. Moving the pointer alone does not close it.
  Overlapping requests during startup are ignored until the guard verifies the
  picker PID; a later press still closes it. The wrapper needs `flock` from
  `util-linux`. App/run/calculator launch and toggle use the native helper,
  without starting Python. A namespace-scoped fade rule preserves Rofi's open/close animation
  without a slide. The approved shared layer fade-out is now **150 ms**, down
  from 1 second: fading panels/notifications also close faster. Opening remains
  200 ms; window/workspace animations are unchanged. The native watcher creates
  no overlay surfaces and registers only ordinary left/right/middle click callbacks
  during the verified picker session; modified mouse shortcuts stay unchanged.
  **Correction and replacement:** settled-menu testing found that Hyprland's
  exclusive input routing bypasses the transparent guards. The earlier
  cross-monitor checks clicked before that routing became active; do not treat
  them as proof that the original guard worked. Its compositor-callback replacement
  now passes all 18 settled-menu cases (three pickers × two other outputs × three
  buttons), including reloads while open, with no underlying click or clipboard write.
  See `docs/superpowers/reports/2026-11-01-rofi-native-session.md` at repository root.
  Warm keyboard-focus probes were roughly 46–58 ms, with a 669 ms initial sample.
  Pre-focus characters can still go to the previous application; no zero-delay or
  physical-shortcut guarantee, resident frontend, or input buffering is added.
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
  `gcc`, `pkgconf`, `glib2`, `cairo`, `pango`, `libqalculate`, `wayland`,
  `json-c`, and Rofi development headers.
  This payload was tested with Rofi 2.0.0 and Qalculate 5.13.2.
- `BACKUP.sh` includes launcher helpers/source and the guarded GTK listener.
  `RESTORE.sh --dry-run` never builds or launches anything; actual restore builds
  `smart.so` and the native session watcher against the installed ABI, and
  fails visibly on build errors. The watcher verifies Rofi identity, registers
  session-scoped Hyprland callbacks and blocks on its process descriptor; it
  creates no surfaces and exits after the picker. The old guard PSS of
  228–238 KiB is historical, not a measurement of this watcher. No compiled binaries, generated protocol code, or
  clipboard database/history are published in this backup.
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
