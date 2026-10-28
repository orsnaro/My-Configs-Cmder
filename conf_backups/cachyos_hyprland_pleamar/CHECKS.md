# Verification record — 2026-10-28

No live desktop stack was switched, no individual widget was disabled, and no
real lock/unlock or reboot/login cycle was performed. Installation was
file-only and did not invoke desktop/service activation commands.

| Current check | Result |
| --- | --- |
| Exported scene Python suite | 205 passed |
| Exported standalone scene Lua | 24 correctly parameterized invocations passed |
| Exported Hyprland Lua fixtures | 8 passed |
| Existing Hyprland shell/isolated QML harnesses | 8 passed; no live window input |
| Desktop switch/installer/recovery fixtures | 36 passed |
| Existing migration suite, including restore-cache regressions | 51 passed |
| Public overlay restore fixtures | 13 passed |
| Retained Kitty suite | 51 passed; 1 existing focused-GUI test skipped |
| Exported shell syntax | 57 entrypoints/harnesses passed |
| Retained Fish syntax / prompt formats | 14 Fish checks / 5 JSON/TOML parses passed |
| `pleamar --check vitreus.plm` | accepted: 45980 properties, 136507 instructions, 14768 rules, 8887 zones |
| Actual live-config copy: installer apply in temporary home | 23 updates; 18 syntax/launcher checks passed; repeat installation had zero changes |
| Actual Hyprland entrypoint with fully stubbed modules | both mode-specific binding/style branches passed; shared geometry stays loaded |
| Actual private snapshot: restore in temporary home | 1099 actions; zero remaining byte/mode/alias differences, including current terminal config |
| Exact runtime / private TV pairing key | executable bit / 0600 permissions verified after isolated restore |
| Actual public overlay: preview and apply in temporary home | manifest verified; preview wrote nothing; apply restored the shared mode helper |
| Installed `.desktop` validation | both launcher files accepted |
| Installed state (read-only) | selected `pleamar`, ready `true`; installer preview reports zero pending changes |
| Unrelated backup preservation | all 523 original file/link fingerprints unchanged |
| Private storage | parent/root 0700; all 937 payload files 0600; private directory Git-ignored |
| Public credential-pattern audit | no private-key/OAuth-token/known credential-prefix matches; private file types excluded |

Tests ran with Python `-B` and explicit suite directories. Lua VRR/tray runners
require named cases; they were run with every case from their Python callers.
The manual-wallpaper loader test used the explicit slideshow-off fixture below;
the user's actual slideshow preference was not changed. The isolated QML
workspace harness starts only its headless fixture, not the QS desktop stack.

Inline review added RED→GREEN regressions ensuring ordinary applications
launched by Walker are not treated as disposable background children, and
Python/Bash/Lua mode readers agree on whitespace and invalid multiline input.
The coordinator also refuses to stop its own managed-service cgroup; native
Vitreus application launches were checked to dispatch through Hyprland.

The current local snapshot is selected by
`../.private/pleamar-current.json`; the verified final bundle contains 1065
private/excluded manifest entries (7 cache/build exclusions). The earlier
pre-install snapshot and original curated-export archive remain available.
Normal mode switching never restores these snapshots over newer preferences.

Independent task review was attempted but the configured free-model quota was
reached. Review continued inline; no other model was selected. A real stack
switch, reboot, lock/unlock and focused scratch Kitty input remain untested.
ShellCheck is not installed. Do not present fixture checks as live acceptance.

`git diff --cached --check` reports seven pre-existing whitespace notices in
newly captured upstream/source files (trailing spaces/blank EOF lines). These
bytes are deliberately retained for exact backup parity. Authored switcher,
installer, recovery and test code passes the whitespace check; this is not a
claim that the complete copied-source diff is whitespace-clean.

## Historical verification record — 2026-10-25–26 refresh

Everything below describes the older export, not new October 28 results.

Run commands from this export unless otherwise specified. No real restore,
desktop switch, lock/unlock, or focused-window input was run on the live home.

| Check | Result |
| --- | --- |
| `python3 -B -m unittest discover -s source/vitreus/tests -p 'test_*.py'` | 156 passed |
| `python3 -B -m unittest discover -s config/kitty/tests -p 'test_*.py'` | 51 passed; 1 existing GUI test skipped |
| `python3 -B -m unittest discover -s tests -p 'test_*.py'` | 12 restore safety/checkout-portability tests passed |
| Scene standalone Lua harnesses | 10 passed; manual-wallpaper test uses explicit fixture below |
| Hyprland Lua harnesses | 8 passed with HOME mapped to a temporary config fixture |
| Legacy `config/hypr/tests/*.sh` harnesses | 8 passed against existing ML4W/local helpers, with temporary command fixtures |
| `fish --no-execute <file>` for exported `.fish` files | 14 passed |
| Python JSON/TOML parsing of `config/ohmyposh/*` | 5 passed |
| Oh My Posh rendering with exported `screenshot.omp.json` | Rendered successfully using installed 31.3.0 |
| `sh -n` / `bash -n` for captured `.sh` entry points and harnesses | 30 passed; no load/unload action executed |
| `pleamar --check vitreus.plm` from `source/vitreus/` | Accepted: 13932 properties, 40009 instructions, 4567 rules, 2683 zones |
| Local repository migration suite | 48 passed; local tools/tests intentionally not published in this snapshot |

The parser retains six pre-existing naming notes: `palette-live.plm:13`,
`desk.plm:651`, `bar.plm:79`, `bar.plm:80`, `osd_drawer.plm:50`, and
`osd_drawer.plm:104`. These are not newly fixed or hidden by the refresh.

The skipped Kitty test is
`AbsoluteResizeTest.test_down_moves_divider_down_from_top_without_losing_focus`
in `config/kitty/tests/test_absolute_resize.py`. It requires explicit
`KITTY_TEST_PID`/`KITTY_TEST_TO` for a focused scratch terminal and sends input.
Do not point it at an ordinary working terminal merely to remove the skip.
The native-action tests emit their expected invalid-direction diagnostic.
ShellCheck is not installed; shell syntax checks are not a claim of ShellCheck validation.

## Standalone Lua tests

From `source/vitreus/`, run `lua5.4 tests/<name>.lua` for `bar_monitors`,
`bar_position`, `hypr_persistence`, `palette_push`, `settings_safety`, `test_gcal`,
`trial_policy`, `trial_status`, and `trial_tray`. These use synthetic boundaries.

The historical `wallpaper_config.lua` harness asserts **manual mode**, whereas
the current saved slideshow is **on**. It originally failed when pointed at the
current `data/`; that mismatch was investigated, not "fixed" by changing the
user's settings or weakening the test. Run the unchanged manual-mode harness
with an explicit fixture:

```bash
# From source/vitreus/; no current saved setting is changed.
fixture=$(mktemp -d "${TMPDIR:-/tmp/opencode}/pleamar-manual-test.XXXXXX")
cp ../../data/wallpaper-dir.json "$fixture/"
printf '{"slideshow":false,"minutes":5}\n' > "$fixture/wallpaper.json"
lua5.4 tests/wallpaper_config.lua "$fixture"
# Remove only this named temporary fixture when finished.
```

This verifies the manual-mode loader contract, not the live enabled slideshow.

Hyprland's eight `.lua` tests stub its API. For tests that read `$HOME`, point
HOME at a temporary fixture with `.config/hypr` linked to this exported
`config/hypr`, and run them from `config/hypr/`. Do not evaluate actual config
files against the live compositor as a substitute for those harnesses.
The eight legacy `.sh` harnesses were run successfully against their existing
ML4W/local-helper/Quickshell dependencies, with `TMPDIR=/tmp/opencode` and the
harnesses' synthetic command boundaries. They are captured unchanged, with those
external dependencies described in `README.md`; this is not a standalone-fresh-home
test. Shell syntax was checked separately, without activating load/unload scripts.

## Integrity and scope

- `manifest.json` covers every public payload file except itself, including
  relative aliases, hashes, modes, and sizes. It records 380 selected live-source
  mappings and the current source-tree digest.
- The 380 copied live-source files were compared byte-for-byte with their live
  originals; config-root links were resolved for capture, not replaced live.
- The restore entry point rejects missing/unrecorded/corrupt payloads and mode
  drift before writing to HOME. Safety tests use tiny isolated snapshot/home
  fixtures, preserve unrelated runtime history, and intercept forbidden commands.
- Public file modes are normalized to Git-portable 0644/0755. The regression
  check first rejected three original 0600 manifest entries that Git cannot
  reproduce on checkout; normalized payloads now validate without changing live
  permissions. Original live modes remain recorded as source-mapping metadata.
  A second regression ensures a valid checkout with private 0600 permissions
  still previews successfully; validation checks Git's stored executable bit,
  not permission bits that Git cannot preserve.
- A private baseline preserved the original export. Fingerprints of 728
  unrelated working files verify the legacy snapshots/tools/docs were not altered.
- No credentials, private SSH functions, logs, caches, runtime histories, private
  rollback payloads, or compiled binaries are staged.
- The specifically allowlisted `source/vitreus/pleamar-wm/wm/session.plm.pre-rebase`
  is documented upstream source history, not an incidental personal backup.
- Independent agent review was unavailable due to the configured free-model
  quota. Review was performed inline; live GUI acceptance remains pending.
