# CachyOS Hyprland — current Pleamar / Vitreus configuration

Refreshed from the live setup on **2026-10-25–26**. This is a curated configuration
overlay, not a complete home-directory or operating-system image. No live settings
were applied and no desktop processes were restarted during this refresh.

| Component | Recorded version |
| --- | --- |
| Pleamar | 0.4.18 · language 0.4, pinned binary hash in `versions/pleamar.txt` |
| Hyprland | 0.56.2, Lua configuration |
| Kitty | 0.49.2, local native `resize_divider` action present |
| Fish | 4.9.3, the user's login shell |
| Oh My Posh | 31.3.0, binary hash in `versions/terminal.txt` |

## What is now current

- **Kitty:** current colors, split/focus/resize mappings, helper scripts, patch
  diffs, and regression tests. Alt+arrows alias pane focus with compositor
  fallthrough; Ctrl+Alt+arrows alias absolute divider resizing. The cursor-trail
  include under `config/ml4w/settings/` is included too.
- **Prompt:** Fish loads `ohmyposh/screenshot.omp.json`, not the former
  `zen-box.toml`. The two-line prompt includes the user, adaptive-width path,
  Git branch/status/remote, virtual environment, execution time, and contextual
  right-side system/language information. Fish's resize hook and the theme are
  backed up together. Earlier non-backup themes remain available.
- **Pleamar:** the installed scene and all its current tests, including the
  side-monitor volume/mixer/output dropdowns, workspace styling, screenshot
  output/geometry handling, launcher click-away/focus handling, and read-only
  calendar/task display logic. No OAuth token, events, or task data is exported.
- **Hyprland:** the complete current config tree rather than only the original
  handful of cutover files. This includes the changed default bindings, custom
  rules, startup, monitors, idle/lock config, scripts, effects, and test harnesses.
- **Lock startup:** current autostart launches the separate native lock scene
  using `vitreus-keep`, the AMD GPU environment, and `PLEAMAR_SWAPCHAIN=1`.
  The shared lock helper retains its Hyprlock fallback. This is a file snapshot,
  not a claim that a real lock/unlock cycle was tested during the refresh.
- **Saved settings:** main bar on DP-2 with Frame/top/solid-obsidian settings;
  current display, palette, Iris, night, tray, sound, and generated settings.
  The wallpaper collection remains `~/.config/ml4w/wallpapers` and the **current
  slideshow is ON every 15 minutes**. The old October 20 "slideshow off" note
  is historical, not the setting in this snapshot.

## Layout and live destinations

| Export path | Restore destination |
| --- | --- |
| `source/vitreus/` | `~/.config/pleamar/shells/vitreus/` |
| `config/hypr/` | `~/.config/hypr/` |
| `config/kitty/` | `~/.config/kitty/` |
| `config/fish/` | `~/.config/fish/` |
| `config/ohmyposh/` | `~/.config/ohmyposh/` |
| `config/ml4w/settings/` | `~/.config/ml4w/settings/` (cursor include only) |
| `data/` | `~/.local/share/pleamar/vitreus/` (merge; never delete other data) |
| `systemd/pleamar.service` | `~/.config/systemd/user/pleamar.service` |
| `bin/pleamar-start` | `~/.local/bin/pleamar-start` |

The live Hyprland, Kitty, Fish, and Oh My Posh roots are links into
`~/.mydotfiles/com.ml4w.dotfiles.stable/`. The export contains their resolved
configuration bytes; `manifest.json` records the logical/resolved mappings.
The scene's internal relative `desktopmenu_hypr.luau` alias is preserved.
Public payload permissions are normalized to Git's portable **0644/0755** modes,
so a fresh checkout passes manifest validation. Original live permission modes
remain recorded in `source_mappings`; live permissions were not changed.
The restore verifier checks Git's executable bit, allowing tighter checkout umasks.

## Restore / load / unload

Use **[RESTORE-CURRENT.md](RESTORE-CURRENT.md)** for this profile:

```bash
cd conf_backups/cachyos_hyprland_pleamar
bash RESTORE.sh                 # preview only; verifies the manifest first
bash RESTORE.sh --dry-run       # explicit equivalent
# After reviewing the instructions and saving your work:
bash RESTORE.sh --apply         # private backup first, then merge files only
```

The script does **not** restart services, reload Hyprland, install dependencies,
apply Kitty patches, delete unrelated files, or switch desktops. It backs up both
existing symlink metadata and resolved content before the first config write.
Existing ML4W root-directory links are preserved.

**Do not use these for the current profile:**

- `../cachyos_hyprland_ml4w/RESTORE.sh` / `BACKUP.sh` target the older desktop.
  They were inspected but deliberately left unchanged.
- `source/vitreus/install.sh` is the captured upstream installer. Its
  `--stop`/`--uninstall` paths do not handle this profile's `pleamar.service`,
  custom Hyprland cutover, or masked SwayNC. They are not the load/unload path.
- `source/vitreus/pleamar-wm/install-session.sh` changes a separate compositor's
  system-wide login entry, not this Hyprland profile. Do not run it here.
- `config/hypr/scripts/loadconfig.sh` only calls `hyprctl reload`; it is current
  and needs no change, but does not restore files or restart the Pleamar service.

**Unload / return to the previous desktop:** see the historical, machine-local
**[RESTORE.md](RESTORE.md)** rollback guide. Its private checkpoint, public
metadata companion, and migration tools are **not included in this PR**. Use it
only when those exact local prerequisites exist; do not substitute upstream
uninstall or the legacy public restore script. Merely stopping the service is
temporary and does not remove the next login's Pleamar autostart hook.

## Dependencies and boundaries

This overlay assumes the existing CachyOS/ML4W base, its installed applications,
fonts, wallpaper collection, and local command helpers (for example
`glaze-*`, `hypr-switch-xkblayout`, and `qs-lazy-toggle`). Those are referenced by
the saved configs, not newly packaged or installed here. Fish's optional
`fastfetch`/`direnv` integrations likewise need their existing programs.

The Pleamar systemd unit is static: Hyprland starts it from `conf/autostart.lua`,
not a `WantedBy=` enablement. `pleamar-start` retains the AMD Vulkan/GPU wrapper.
The existing persistent SwayNC mask is external service state, not a copied unit;
check notification ownership before activating this overlay on another home.

The Kitty patch diffs retain their original **0.49.1 filenames**, while the live
package is **0.49.2** and its native-action tests pass. Do not apply these old
diffs blindly to another package version. The helper's non-native fallback remains
available; restoration never runs `apply-native-patch.sh` or `sudo`.

Generated `data/vitreus_monitors.lua` is retained as data. The live
`config/hypr/` currently has no file of that name, so this refresh does not invent
one or change which monitor settings the live entrypoint loads. Monitor names,
geometry, and absolute paths are machine-specific: review them before restoring
to a different machine. Display-Keep persistence and visual acceptance are not
newly certified by this export.

## Privacy

Only inspected source, configuration, tests, and version metadata are included.
No credentials, OAuth tokens, calendar/task caches, notification history, shell
history, clipboard data, logs, Fish universal-variable state, private SSH
functions, weather/location data, trial/checkpoint payloads, generated previews,
dated backup copies, Git metadata, bytecode, or compiled binaries are copied.
The restore script preserves unrelated private data already in the destination.
One named source exception is retained: `pleamar-wm/wm/session.plm.pre-rebase`
is the upstream README's documented historical compositor scene, not a personal
backup or runtime payload.

## Verification

See **[CHECKS.md](CHECKS.md)** for commands, results, and limitations:

- Scene: **156/156 Python tests pass**; **10 standalone Lua harnesses pass**.
- Hyprland: **8 Lua config harnesses pass** in an isolated fixture home.
- Legacy Hyprland/ML4W shell harnesses: **8 pass** against the existing local
  helper/ML4W/Quickshell dependencies; those dependencies are not repackaged here.
- Kitty: **51 pass, 1 skipped** out of 52 discovered tests. The skipped test
  requires a focused scratch GUI terminal and was not enabled on the live desktop.
- Restore entry point: **12/12 safety/checkout-portability tests pass**; restore
  applications are exercised only in temporary homes.
- Fish: **14 syntax checks pass**; all five prompt JSON/TOML files parse and
  the active prompt renders with the installed Oh My Posh binary.
- Pleamar parser: accepted, with the same six pre-existing naming notes.
- The existing local migration suite remains **48/48 passing**; it is not shipped
  as part of this snapshot.

Manifest coverage, hashes, sizes, modes, live-source parity, privacy exclusions,
and preservation of unrelated working files are checked separately. No new visual,
GPU/performance, real lock/unlock, or desktop-switch acceptance claim is made.
Independent review was unavailable because the configured free-model agents hit
their provider quota; this change received inline review instead.

The previous checkpoint README is preserved verbatim in
[HISTORY-2026-10-20.md](HISTORY-2026-10-20.md). Its dates, measurements, open
issues, and commands describe that earlier checkpoint only.
