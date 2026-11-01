# Permanent Hyprland Rofi — 2026-10-31

## Outcome

- Main Search handles arithmetic (`2+2` → `4`) and normal desktop applications.
- Repeating a menu command toggles it closed; outside-panel clicks on any
  connected monitor cancel without copying a selection. Pointer motion alone
  does not dismiss it. Transparent other-output guards are pointer-only and
  consume about 228–238 KiB PSS while a picker is open; none remain afterward.
- The 6×6 emoji grid and clipboard image preview remain intact.
- User chose **substring matching only for emoji**; other menus retain fuzzy
  abbreviations. User approved fzf relevance sorting across these menus. Actual
  smart app search ranks/launches a harmless ARC Raiders fixture above a loose match.
- Hyprland QS startup no longer starts or requires Walker/Elephant daemons.
  Rofi remains on demand. KDE configuration/global service enablement is unchanged.
- ML4W clipboard buttons use the same preview/toggle wrapper. Five visual presets
  preserve launcher choice instead of forcing Walker back on.

The user-requested order was retained: runtime fixes, then startup, then targeted
repository backup/shell updates. Existing dock/Pleamar work was preserved.
Publication branch: `fix/hyprland-rofi-main-pr`, based directly on `origin/main`
at `6e128ea`. Only the Rofi payload is included; seven earlier unrelated commits
and the original checkout's dirty dock/Pleamar work are excluded and preserved.
The user approved pushing this branch and opening a PR to `main`, not merging it.

## Files and restore workflow

- `tools/desktop_stack.py`: on-demand launcher readiness/preflight/startup.
- `tools/install_desktop_stack.py`: fresh/already-managed theme restart guards.
- `tools/switch-to-qs.sh`: still a thin coordinator wrapper, now using the new startup.
- `conf_backups/cachyos_hyprland_ml4w/`: themes, wrapper, helper/plugin sources,
  clipboard entry point, theme guards/presets and backup/restore integration.
- `conf_backups/cachyos_hyprland_pleamar/`: matching launcher bindings and updated
  manifest records so restoring that overlay does not undo Rofi routing.

The stable executable remains `~/.local/bin/rofi-trial` for binding compatibility.
Actual ML4W restore rebuilds `smart.so` and `dismiss-guard` from source; dry-run
never builds or launches anything. Build failure is reported before desktop activation. Dependency/restore
instructions are in the ML4W backup README. No clipboard database is published.

## Publication verification (2026-11-01)

All active Python suite directories in the publication checkout were explicitly
run with `python -m unittest discover -s <directory> -v`:

| Suite/check | Result |
| --- | --- |
| `tests/desktop_stack` | 60 passed, 1 existing TLS failure |
| `tests/pleamar_migration` | 17 passed |
| `tests/qs_lightweight` | 5 passed |
| Vitreus | 205 passed |
| Curated restore fixtures | 13 passed |
| Kitty | 51 passed, 1 existing focused-Kitty GUI skip |
| Live arithmetic, relevance, safe app launch and repeated toggles | 6 passed |
| Same-monitor outside click | apps, emoji and clipboard passed |
| Other-monitor outside click | all 6 mode/output combinations passed; no clipboard writes or surviving helpers |
| Actual ML4W payload restore in isolated HOME | dry-run made no writes; real restore rebuilt both native assets |
| Lua bindings / shell syntax / Python parsing / whitespace | passed |
| Public ML4W inventory | 624 source/config files; no native binaries |
| Deployed Rofi source/theme parity | wrapper, themes and helper sources match byte-for-byte |

Publication Python total: **351 passed, 1 failed, 1 skipped** (353 tests).
The full suite is **not green**. The user explicitly approved keeping these
pre-existing `main` problems outside the Rofi PR and disclosing them:

- `test_tv_tls.TvTlsTests.test_stricter_runtime_minimum_is_preserved`: unchanged
  TV TLS code lowers a TLS 1.3 minimum to TLS 1.2. Neither production code nor
  its test is changed here.
- Actual Pleamar `RESTORE.sh --dry-run` refuses with
  `manifest content mismatch: source/vitreus/bin/vitreus-tvremote`. The stale
  record is unchanged from `main`; no destination writes occurred. The 13 green
  restore **fixture** tests do not mean this real restore passed.

The main-preserving integration retains newer navigation/screenshot behavior,
private backup exclusions, optional config trees, restore permissions and dry-run
handling. Two regression tests reproduced the initial transfer's backup/restore
regressions before the integration correction and passed afterward.
The saved GTK listener was also executed for both light/dark preferences with
both launcher selections; it restarts Walker only when explicitly selected.
The final review is inline because the configured free subagent failed on quota;
there is no independent-review claim. Hardware hotplug, reboot/relogin and a new
full-stack roundtrip were not tested.

## Historical live-checkout verification

The following counts belong to the earlier, differently based live checkout,
not the publication branch or a newly green full suite:

| Suite/check | Result |
| --- | --- |
| Launcher trial unit suite | 32 passed |
| Desktop coordinator/install/backup/build | 51 passed |
| Migration/recovery | 51 passed |
| QS lightweight/routing/palette | 12 passed |
| Vitreus suite | 205 passed |
| Pleamar curated restore suite | 13 passed |
| Kitty suite | 51 passed, 1 existing focused-scratch-GUI skip |
| Live calculator/toggle/ranking/safe app launch | 6 passed |
| Live outside-click check | passed for apps, emoji and clipboard on both other monitors |
| Dock Qt gesture/restart E2E | 22 + 2 passed, no failures/skips |
| Dock preview contract | passed |
| Backed-up Hyprland Lua binding suite | passed |
| Shell syntax / changed Python parsing / diff whitespace | passed |
| Backup payload | 17 relevant live files match byte-for-byte; 536-file inventory verified |
| Permanent recovery preflight | 12 integration files verified; no writes |
| Live desktop status / Hyprland config errors | QS ready; no config errors |

Historical Python suites totaled **415 passes, one existing skip**. Bare unittest discovery at
`tests/` returns “NO TESTS RAN” because those folders are not packages; each actual
suite was explicitly executed, not counted as passing from empty discovery.
One previously failing night-mode suite consumed the live QS mode instead of
its intended Pleamar branch; it now uses an explicit fixture HOME. No production
night-mode behavior was changed.

Reproduction and full per-suite logs:
`~/.local/state/launcher-trial/20261031T133150+0200/followup/`:
`run_repository_checks.py`, `final-suites.json`, `final-live_checks.log`,
`final-outside_checks.log`, and cropped synthetic UI screenshots.
Dock E2E log: `/tmp/opencode/rofi-final-dock-e2e.log`.

The outside-click fixture originally sent timestamps 0/1 and treated layer
registration as finished rendering. Correct monotonic timestamps and waiting for
a known one-pixel panel border removed that test error; native geometry confirmed
the centered layout. No production layout workaround was piled onto that symptom.

## Recovery and original measurements

Original benchmark JSON, comparison files, snapshots and `manifest.json` are
untouched. The original full-stack PSS baseline was Walker closed **214.74 MiB**,
apps **257.22**, emoji **262.96**, clipboard **255.37**. Original Rofi trial figures
were closed **0.22**, apps **29.93**, emoji **46.07**, clipboard **30.93 MiB**.
These are **not measurements of the later smart plugin/full-monitor theme**.

Permanent recovery uses the existing guarded `rollback.py` with the separate
`followup/permanent-manifest.json` (pass `--check` first). Its 12-file inventory
includes the repository-backed coordinator and the six additional shell hooks.
It preserves later user mail startup/window rules, refuses subsequent unknown
edits, and leaves all historical baseline files and private snapshots intact.
The trial README contains the complete recovery commands.

## Rulings and review limitations

1. Update the Pleamar public overlay's launcher bindings too, because it restores
   the same Hyprland files. If undesired, revert only those targeted bindings.
2. Include clipboard-button forwarding and preset preservation: broad tests
   reproduced paths that bypassed the new UI or reset Walker. Recovery snapshots
   cover those six additional shell files.
3. Isolate night-mode test HOME rather than changing production behavior. The risk
   is missed mode-specific coverage; separate coordinator QS tests remain green.
4. Keep the historical manifest immutable and reconstruct a separate Walker
   recovery target around later mail edits. If reconstruction is wrong, rebuild
   that separate target, never overwrite the historical originals.

Final review was an inline self-review: the configured free subagent had already
failed on quota, and no model escalation was authorized. No blocking findings
remain in that review; self-review is weaker than an independent review.
No new full-session QS↔Pleamar roundtrip, reboot/relogin, real lock/unlock, or
physical-global-shortcut test is claimed. Live toggle checks invoke the exact
bound commands. The existing low-contrast tab styling was not redesigned.
