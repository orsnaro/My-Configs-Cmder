# QS Walker routing — 2026-10-28

## Result

The user physically confirmed **Meta/Super+V opens Walker correctly** in the
current QS session. Apps, runner, emoji/symbols, keybinding help, screenshot/OCR,
wallpaper-effects and preference-driven theme pickers use existing Walker
routes. QS power/calendar/sidebar panels and Pleamar's native launcher remain
unchanged. No launcher/package, clipboard collector, service or timer was added.

Only four live values changed from Rofi to Walker:

- `~/.config/ml4w/settings/launcher`
- `~/.config/ml4w/themes/glass/theme.sh` (launcher-setting line)
- `~/.config/ml4w/themes/modern/theme.sh` (launcher-setting line)
- `~/.config/ml4w/themes/transparent/theme.sh` (launcher-setting line)

Exact counterparts are saved under
`conf_backups/cachyos_hyprland_ml4w/dotfiles/` at the same relative paths. All
other preset bytes, including the original EOF, are preserved. Presets were
executed **only in isolated test homes with fake external commands**, never
activated in the live desktop. The clipboard helper itself was not rewritten.

## Verification

- New tests first reproduced the shared Rofi preference, clipboard helper's
  wrong branch and all three preset resets (five RED failures); all three
  unittest cases now pass against saved and live sources.
- Python suites: QS **11**, desktop-stack **39**, migration **51**, exported
  scene **205**, public restore **13**, Kitty **51 passed / 1 skipped**, existing
  QS updates **11**: **381 passed**, one existing GUI skip. The Pleamar scene
  suite runs in a restored sandbox HOME with Pleamar selected there only and
  the two existing file-manager desktop-entry overrides copied as dependencies.
  Running its Pleamar-only night-mode fixture against the live QS selection
  initially failed; the isolated rerun passes without production changes.
- Nine existing QS shell contracts and the current mode-routing contract pass.
  **One legacy live check does not pass:** `system_panel_load.sh` requires a
  `Reloading configuration` log marker, but this QS instance has only its
  initial `Configuration Loaded` marker. A direct initial-load check confirms
  loading and absence of all five system-panel error signatures. No live reload
  was performed just to satisfy that test; this is not an all-tests-green claim.
- `bash -n` accepts all three changed presets. QS remains selected and ready;
  Quickshell, notification, Elephant and polkit core PIDs are unchanged. Walker
  UI lifecycle and transient child PIDs are not treated as immutable core PIDs.
- The bound clipboard helper opened a Walker layer and `walker --close`
  dismissed it without selecting/copying/deleting an entry. No clipboard text
  or screenshots were captured. Synthetic keyboard/dispatcher attempts did not
  confirm binding activation; the user's physical-key confirmation is the
  acceptance evidence, not those unsuccessful probes.
- All **27** unrelated dirty/untracked fingerprints and **eight** live
  appearance/TV-helper fingerprints are unchanged. All four saved/live routing
  artifacts are byte-identical. No Rofi or Pleamar process appeared.

## Recovery and review

The Git-ignored, owner-private exact snapshot was refreshed separately. It has
**1066 entries**, seven cache/build exclusions and **938** protected payload
files. An isolated restore applied **1100 actions** with **zero remaining
byte/mode/alias differences**, including the four routing changes. Private
directory/payload modes and Git exclusion were verified. No private snapshot or
clipboard artifact belongs in the public commit.

Work remains local on `fix/qs-walker-launcher-routing`, based on `c483ccd`.
No push, merge or GitHub comment/dismissal is authorized by this fix. TV
TLS/certificate/pairing code is untouched; its separate assessment is in
`2026-10-28-pr10-security-review.md`.

### Execution decisions

- Continue in the approved fix branch/current checkout, not a new worktree
  mid-task; scoped staging and preserved fingerprints guard existing work.
- Run Pleamar-only IPC fixtures in a temporary Pleamar-selected HOME; this does
  not claim coverage of the live QS backend from those fixtures.
- Preserve the user's no-reload QS session and report the reload-only test
  limitation rather than manufacture its expected log marker.

The configured free reviewer was attempted but returned a usage-limit error;
no model escalation was used. Inline self-review checked the four-value scope,
exact mirrors, fixture isolation, clipboard flags and staged private-artifact
exclusion; no unresolved important issue was identified in this routing change.
This is **not an independent-review pass**. The legacy log-test limitation
above remains explicitly unresolved rather than being counted as passing.
