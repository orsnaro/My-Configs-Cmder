# Compact QS Dock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Configured free-agent quota is exhausted; no model escalation. Track checkboxes.

**Goal:** Restore the dock's visibility and reclaim space using only the five user-approved preferences.

**Architecture:** The dock process and IPC already work; `dock.enabled=false` keeps its LazyLoader inactive. Change preferences, then send its existing reload IPC. No dock/QS restart, switcher rewrite or QML production edit.

**Tech Stack:** Existing ML4W Dock JSON, Quickshell singleton/IPC, Python unittest and offscreen QML fixture.

**Spec:** User selected Enable + compact: enabled=true, iconSize22→20, spacing6→5, pill.padding8→6, marginBottom11→6; preserve pins, autohide=false and DP-2. Subsequent keep 1.2 instruction applies only to Copilot's TLS minimum, not this dock task.

## Global Constraints

- Isolated branch `fix/compact-qs-dock` from local `fix/qs-walker-launcher-routing` (`ed9d38e`); do not publish or merge automatically.
- Live config `/home/narol/.config/ml4w-dock/config.json`; mirror under `conf_backups/cachyos_hyprland_ml4w/dotfiles/.config/ml4w-dock/config.json` in this worktree only. The original checkout's dirty dock backup differs from live: do not overwrite it or other dirty work.
- Preserve current six pins/order, launcher, monitor, colors, autohide, other preferences and all QML/scripts. No application launch/close/reorder, screenshot or clipboard capture during testing.
- Leave TLS/Copilot, Code OSS, Pleamar and all other QS components unchanged; do not restart the main shell. Reload only the dock via existing IPC.
- Before changing live preferences, checkpoint them privately and record core PIDs, monitor geometry and unrelated file fingerprints. Refresh/verify the existing owner-private recovery snapshot afterward.

## Review Focus

Disabled flag must become visible without restart; current pins survive export; actual DockSettings consumer accepts values; reserved strip is 48px rather than old configured59px; unrelated original dirty dock files stay intact. Each is verified below.

### Task 1: Apply and verify compact enabled preferences

**Files:** Modify the mapped live/backup JSON only. Create `tests/qs_lightweight/test_dock_config.py` and `tests/qs_lightweight/dock_settings.qml`; save a scoped verification report in `docs/superpowers/reports/2026-10-28-compact-qs-dock.md`.

**Interfaces:** Existing DockSettings singleton consumes HOME/.config/ml4w-dock/config.json. Existing `ml4w-dock reload` re-reads it without restarting. Tests consume the real saved singleton (or `DOCK_TEST_SOURCE` override), using temporary HOME/offscreen Qt; never instantiate desktop windows in that fixture.

- [x] Privately checkpoint live config, its unrelated keys/pins, original checkout dirty fingerprints and live core PIDs/monitor reservations.
- [x] Add `test_real_dock_settings_loads_enabled_compact_preferences`: load the real DockSettings singleton in isolated QML; assert enabled=true, iconSize20, spacing5, padding6, marginBottom6, DP-2 and autohide=false. Run against live old config using `ML4W_TEST_HOME=/home/narol`; expect RED on disabled/old-size preferences, not a fixture/import error.
- [x] Change precisely the five approved values in live JSON, preserving other bytes; save exact resulting config to this worktree's backup counterpart, preserving current pins rather than reverting to its historical pins.
- [x] Re-run the fixture on saved and live configs; run full QS/desktop-stack suites and existing dock preview/isolated gesture tests where safe. Report any failures/skips explicitly; no unrelated fixes.
- [x] Send `ml4w-dock reload`; wait for the dock layer on DP-2 and bottom reservation48px. Confirm dock/main QS PIDs unchanged, no other monitor reservation changes, pins and unrelated settings unchanged. User can confirm visual compactness without submitting a screenshot.
- [x] Verify source/backup parity and all unrelated fingerprints. Refresh the existing Git-ignored private snapshot and sandbox-restore it, verifying the compact config and zero remaining differences.
- [x] Inline scoped review under the approved quota fallback; record limitations, then commit only the config/test/fixture/report/plan on this local branch. No push, TLS changes or original dirty-backup overwrite.
