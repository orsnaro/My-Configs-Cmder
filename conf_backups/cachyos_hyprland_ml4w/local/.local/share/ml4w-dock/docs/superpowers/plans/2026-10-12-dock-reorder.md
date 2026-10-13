# Pinned Dock Reordering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Track completed steps here.

**Goal:** Hold a pinned icon, drag horizontally, and release to save its new order without periodic background work.

**Architecture:** Reuse the existing MouseArea and settings writer. Keep delegates stationary during the gesture; indicate source/target using existing icon styling. Defer the single settings write until after release to avoid destroying the pointer owner mid-gesture.

**Tech Stack:** Quickshell 0.3.1, QtQuick/QtTest 6.12, shell/Python test utilities.

**Spec:** User-approved bounded design in this conversation, including acceptance of small event-driven overhead subject to a measured 1 MB added-memory budget.

## Global Constraints
- Pinned apps only; preserve stored IDs and other settings.
- No new recurring timers, polling, background processes, dependencies, or preview captures.
- Save once on a valid changed drop; no writes while moving or for canceled/unchanged gestures.
- Preserve all pre-existing uncommitted monitor and preview changes.
- Work on `feat/dock-hold-drag`; do not commit user work or push.
- Compare equivalent fresh baseline/patched instances; undo only this feature if repeatable added memory exceeds 1 MB.

## Review Focus
- Long holds and drops must never accidentally launch/activate the app.
- Drops outside the pinned strip, including above/below it, must cancel.
- Model/window changes mid-gesture must clear state without writing.
- Existing click, middle-click, context menu, and hover previews must remain usable.
- Resolve duplicate/alias IDs without confusing delegate indexes with stored pin indexes.

### Task 1: Behavioral tests and gesture implementation

**Files:** `DockApp/DockItem.qml`, `DockApp/DockWindow.qml`; new behavioral test/runner under `DockApp/tests/`.

**Interfaces:** `beginPinnedDrag(item)`, `updatePinnedDrag(item, x, y)`, `finishPinnedDrag(item, x, y)`, `cancelPinnedDrag()` owned by DockWindow. A named app Repeater provides coordinate targeting. The root owns source/target keys and a snapshot; DockItem owns click-suppression state. Existing `DockSettings.persistPinned(list)` remains the sole writer.

- [x] Write real Qt mouse-event tests against production QML in an isolated HOME; verify left/right moves, restart persistence, no-motion/out-of-bounds drops, running-only rejection, canceled/model-changing gestures, suppression of activation, and ordinary click/menu/hover behavior.
- [x] Run tests against unchanged production code and record a failure attributable to missing reorder support.
- [x] Implement in the two existing QML files. Stop tooltip/preview timers on pinned-left press, close popups, arm on left hold only, update the nearest valid pinned target, and defer persistence after release with a snapshot guard. Keep autohide revealed while dragging. Cancel on model replacement.
- [x] Run the existing preview test and all new tests; require no failures.
- [x] Obtain an independent spec and quality review; resolve substantive findings and rerun affected tests.

### Task 2: Resource and installed-dock validation

**Files:** Test-only measurement utilities/reports in `/tmp/opencode/`; no production instrumentation.

- [x] Compare fresh baseline and patched dock instances in alternating trials after identical warmup; record RSS, private memory including swapped pages, and CPU ticks across an idle interval.
- [x] Require repeatable additional private memory below 1 MB and no periodic work introduced. Undo only the feature on failure.
- [x] Restart the installed dock, inspect runtime logs, confirm final pins remain Dolphin before Brave, and rerun the complete test suite.
- [x] Save the measurement and behavioral-test evidence; mark this plan complete and report measured costs and usage.

### Task 3: User-requested backup update

**Files:** Dock settings/source/tests/docs and manifest within `/shared_across_des/repos/My-Configs-Cmder/conf_backups/cachyos_hyprland_ml4w/`.

- [x] Locate the existing backup, inspect its conventions, and create `chore/backup-dock-reorder` before editing.
- [x] Mirror the validated dock subtree without deleting unrelated files or copying git/scratch/cache artifacts.
- [x] Update its usage note and manifest; compare source/backup hashes and rerun the backed-up gesture tests.

### Task 4: User-requested 400 ms hold adjustment

**Files:** `DockApp/DockItem.qml`, `DockApp/tests/tst_dock_reorder.qml`, usage documentation and corresponding existing backup files.

**Scope:** On `feat/dock-hold-400ms`, add only `pressAndHoldInterval: 400` to the existing MouseArea; retain all gesture/click handling. This reuses Qt's existing hold timer. Backup branch: `chore/backup-dock-hold-400ms`.

- [x] Update the real-mouse hold helper: no drag at 350 ms, active by 450 ms; watch it fail with the old 800 ms interval.
- [x] Set the existing interval to 400 ms, run the complete gesture/restart and preview suites, and review the one-line production change.
- [x] Update current usage to 0.4 seconds; mirror existing backup files, check byte equality and runtime reload.

### Task 5: User-requested 250 ms hold adjustment

Change `pressAndHoldInterval: 400` to `250` in `DockApp/DockItem.qml`, align
future test timing/usage notes and mirror the existing backup. User explicitly
requested no full test workflow; use only a value/backup/reload check.
