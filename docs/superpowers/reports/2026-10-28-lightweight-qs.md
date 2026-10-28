# Lightweight QS and palette verification — 2026-10-28

## Delivered

- Main-bar CPU pill also shows GPU% and used VRAM from the **existing**
  `hypr-sysinfo` sample. Missing sensors show `—`; zero remains valid.
- Focused-window title sits after workspaces, uses window-change signals,
  treats titles as plain text, elides at 220 px and collapses on desktop.
- Walker's five fixed color aliases now reference generated wallpaper colors;
  its layout, opacity, providers and existing reload hooks are unchanged.
- Kitty's existing Matugen include/SIGUSR1 hook worked. **No Kitty configuration
  edits, additional watchers, collectors, daemons or recurring timers.**

## Evidence

Real offscreen QML tests first failed on missing GPU/title behavior, then passed
against both saved and installed components. Native GTK accepted the Walker
stylesheet with two generated palettes. Live screenshots privately confirmed
GPU/VRAM, the title changing from `QS title test A` to `B`, an uncluttered centered
clock, and Walker following the alternate wallpaper palette. Scratch Kitty's
live foreground/background matched `colors-matugen.conf` after the normal
wallpaper hook. The prior QS wallpaper was restored; the scratch window closed.

The first scratch probes needed fixture corrections: Quake's workspace rule
opens new apps silently, so the scratch window needed explicit focus; Kitty's
`--title` permanently fixes its OS title, so the dynamic-title probe omitted it.
Neither required a production fix or input into the working terminal.

After acceptance, the full Pleamar stack was restored: seven scenes ready,
zero QS/scratch leftovers. Screenshots, logs and raw resource JSON are local,
Git-ignored/private. No real lock/unlock or reboot/login was performed.

## Resource check

Separate, uncontrolled ~3-second QS samples; **not a benchmark**:

| Stack | Before enhancements | After enhancements |
| --- | ---: | ---: |
| CPU, one-core scale | ~0% | ~0% |
| RAM PSS | 655.48 MiB | 653.75 MiB |
| RAM RSS | 953.68 MiB | 951.77 MiB |
| VRAM allocated | 193.83 MiB | 192.84 MiB |

Small differences are measurement noise, not claimed savings. The structural
resource guarantee is unchanged collector/timer counts and event-driven title
updates. Whole-system CPU was 1.12%, RAM used 3.09 GiB and AMD busy 2% in the new
sample; other processes and wallpaper differ from the earlier sample.

## Tests and known limitations

- Eight new unittest cases pass (real QML, layout/cache contracts, native GTK),
  including the two existing memory/panel-state QML fixtures inside a correct
  Quickshell config root. Direct invocation of those old fixtures with `qml`
  or as standalone QS config paths was not a valid harness; the wrapper keeps
  their original imports and code intact.
- Eleven existing updates-module behavioral tests pass.
- Nine current statusbar shell contracts pass; the live-only panel-log script
  skips when QS is stopped. The actual QS load was checked during acceptance.
- Two old layout assertions were updated for the intentionally inserted title.
  The installed night-control test was also stale from the earlier full-stack
  change; it now checks mode-routed resume/backend gating. The focused current
  contract is saved as `tests/qs_lightweight/night_mode.sh`; no night-mode
  production code changed here.
- Live logs still report warnings in unmodified `SlimBarWindow.visible` and
  duplicate `updates` IPC registration. Existing SwayNC CSS warnings from the
  original switcher verification remain outside this scoped change.
- Independent review remains unavailable after the configured free-model quota
  failure. Review is inline; no model escalation. One pre-existing Kitty GUI
  test remains skipped, not counted as passed.

## Backup and use

Saved counterparts of changed QML/layout files are under
`conf_backups/cachyos_hyprland_ml4w/dotfiles/.config/`:

- `quickshell/StatusbarApp/CpuModule.qml`
- `quickshell/StatusbarApp/FocusedTitleModule.qml`
- `quickshell/StatusbarApp/StatusbarWindow.qml`
- `quickshell/StatusbarApp/config.json`
- `quickshell/StatusbarApp/tests/media_module.sh`, `tests/volume_panel.sh`
- `ml4w-statusbar/config.json`
- `walker/themes/ml4w/style.css`

Only these scoped artifacts are refreshed, not the historical ML4W profile.
The user's dirty legacy README/manifest/dock files are deliberately untouched.
For manual overlay, copy the listed artifacts to corresponding HOME paths;
Walker needs the existing installed Matugen palette/config. Do **not** run the
legacy whole-profile restore for this small enhancement. The Git-ignored exact
snapshot is refreshed separately for full local recovery.

Use **Switch to QS** to see the changes. Switch scripts remain committed at
`tools/switch-to-qs.sh` and `tools/switch-to-pleamar.sh`. Original PR #10 is
unchanged; this enhancement is a separate, not-automatically-pushed branch:
`feat/lightweight-qs-metrics-and-palette`.
