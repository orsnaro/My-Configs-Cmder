# Walker-only QS Launcher Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Configured free-model delegation previously exhausted its quota; no model escalation. Steps use checkbox tracking.

**Goal:** Restore QS Meta+V and use Walker consistently for existing launcher/picker functions.

**Architecture:** Reuse the existing helper branches. Set the shared launcher preference to `walker` and prevent three theme presets from changing it to missing Rofi. Apps, runner, symbols, keybinding help, screenshot/OCR and wallpaper effects already use Walker.

**Tech Stack:** Existing Bash/ML4W settings, Walker/Elephant (clipboard provider confirmed installed), Python unittest. No packages, new services or collectors.

**Spec:** User's explicit Walker-only direction; bounded design recorded below. Security-bot feedback is reviewed separately in `docs/superpowers/reports/2026-10-28-pr10-security-review.md`; no security-source changes belong in this fix.

## Design and global constraints

- Change four live configuration values only: `/home/narol/.config/ml4w/settings/launcher`, plus the launcher-setting line in `/home/narol/.config/ml4w/themes/{glass,modern,transparent}/theme.sh`.
- Mirror the same relative paths under `conf_backups/cachyos_hyprland_ml4w/dotfiles/`. Do not rewrite clipboard/history storage or change installed launcher helpers that already support Walker.
- Preserve current selected themes and QS mode. Do not activate theme presets, switch desktops, install Rofi, add a process, wipe history, select a clipboard entry or publish clipboard contents.
- Leave Pleamar's native launcher/keybindings and QS power/calendar/sidebar panels untouched.
- Work on `fix/qs-walker-launcher-routing`; preserve previous feature commits and unrelated dirty backups. No push, PR dismissal, GitHub comment or TLS/network policy change without approval.

## Review Focus

Missing Rofi must never be invoked on the active route; clipboard provider flags must be forwarded intact; all three presets must retain Walker; fake theme execution must not touch live daemons; no clipboard contents enter logs/screenshots. Each case belongs to the regression fixture below.

### Task 1: Route existing pickers consistently

**Files:** Four mapped live/backup configuration paths above; create `tests/qs_lightweight/test_launcher.py`.

**Interfaces:** `ml4w-cliphist` reads `settings/launcher` and calls `~/.config/walker/launch.sh -m clipboard -N -H`. Theme selector uses the same preference. No new API.

- [x] Checkpoint affected live files privately. Record unrelated dirty fingerprints.
- [x] Write fixture tests asserting the saved preference is `walker`, the real clipboard helper forwards the expected flags to a fake Walker and never invokes fake Rofi, and isolated execution of each preset leaves `launcher=walker`. All external theme commands are log-only fakes; never read live clipboard history.
- [x] Run `python3 -B -m unittest discover -s tests/qs_lightweight -p 'test_launcher.py'`; observe failures on old Rofi preference/preset resets. RED used `ML4W_TEST_HOME=/home/narol` because the saved presets did not exist yet; all five expected failures reproduced.
- [x] Apply the four small configuration changes and save exact counterparts. Preserve the remaining preset bytes and selected appearance.
- [x] Re-run the regression tests and full QS/desktop-stack suites. Require zero failures; review exact diff and commit only scoped paths/tests. Fresh QS/desktop-stack runs pass 11/39 cases; broader legacy log-check limitation is recorded in the report.

### Task 2: Live acceptance and backup

**Files:** Create `docs/superpowers/reports/2026-10-28-walker-routing.md`; refresh the Git-ignored exact snapshot using existing tools.

- [x] In the user's current QS session, open/dismiss the clipboard UI through the actual Meta+V route. Verify only its layer/process presence, not history text; do not select/copy/delete anything. If synthetic key input is unavailable, verify the bound helper directly and ask for the physical-key check explicitly. User confirmed physical Meta+V opens correctly after the helper-layer check.
- [x] Confirm app/runner/symbol routes still point to Walker, no Rofi process appeared and launcher-setting changes require no compositor/service restart. Keep QS active.
- [x] Verify saved/live parity, unchanged theme bytes except the launcher preference, unrelated dirty fingerprints and private exclusion. Record limitations honestly. Refresh and sandbox-verify exact recovery; do not push this branch automatically.
