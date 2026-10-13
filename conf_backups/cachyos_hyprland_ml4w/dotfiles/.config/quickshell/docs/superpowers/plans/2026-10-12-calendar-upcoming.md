# Calendar Upcoming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore a truthful, fresh Upcoming list while preserving the desktop layout and reducing duplicate background work.

**Architecture:** Keep the existing Python sync/reminder scripts and cache format. Update the existing QML panel to filter cached events, disclose stale/error state, and independently launch a sync that survives closing the popup. Only the center panel owns background timers; all panels observe cache changes.

**Tech Stack:** Installed Quickshell 0.3.1, QtQuick, Python standard-library regression runner; existing Google OAuth consent script.

**Spec:** User-approved bounded design in this conversation: two widget files only, plus offline regression tests; reconnect Google through the existing consent flow after verification.

## Global Constraints

- No new packages, daemons, faster timers, or cloud calendar/task writes.
- Keep the current card dimensions, colors, fonts, and overall layout.
- Existing background intervals remain 900000 ms for sync and 300000 ms for reminders.
- Do not modify any existing token/cache/reminder-state files during tests.
- This configuration tree is not a Git repository: back up modified source files; no Git branch, commits, or worktree.

## Review Focus

- Timed events ending at/before now disappear; an already-started event whose end is still future remains.
- All-day events use local date boundaries and an exclusive end date, not UTC date parsing.
- Invalid JSON preserves the last usable cache; malformed event timestamps do not surface bogus upcoming entries.
- Closing/reopening the popup during sync does not cancel or duplicate that panel's subprocess.
- Failed sync exposes cached/stale state; side-panel cache updates require no polling or extra background jobs.

### Task 1: Offline regression coverage

**Files:** Create `/home/narol/.config/gcal/tests/calendar_panel.py`.

**Interfaces:** Launch the real `CalendarPanel.qml` in a temporary Quickshell config using `QT_QPA_PLATFORM=offscreen` and `QT_QUICK_BACKEND=software`. Use a fixture HOME under `/tmp/opencode`; replace only external Google subprocess work with small fixture sync/reminder scripts. Exercise real QML functions, state, delegates, and subprocess lifecycle, not source-text matches.

- [ ] Write a typed standard-library unittest runner that generates disposable QML test cases and fixture data, with a process timeout and explicit assertion-failure reporting.
- [ ] Test expired/ongoing/future timed events, exclusive all-day ends, invalid timestamps/JSON, and stale-cache signaling using `panel.parseAgenda(JSON.stringify(fixture))` and observable `agendaEvents`/rendered labels.
- [ ] Test sync completes after opening then closing the panel, a failed subprocess surfaces an error, and two non-owner panels do not launch reminder jobs. Test file-change reload with a fixture atomic cache update.
- [ ] Test all-day labels include a date, six task rows have a 72 px viewport/24 px row height, and title tooltips retain full text.
- [ ] Run `python3 /home/narol/.config/gcal/tests/calendar_panel.py`; record expected behavioral failures against the original widget before changing source.

### Task 2: Minimal widget fix

**Files:** Modify `/home/narol/.config/quickshell/StatusbarApp/CalendarPanel.qml` and `/home/narol/.config/quickshell/StatusbarApp/StatusbarWindow.qml`.

**Interfaces:** Preserve `parseAgenda(src): void`, `agendaEvents`, `agendaTasks`, existing commands and cache keys. Add `property bool manageAgendaBackground: false`; set it true only on the central CalendarPanel. Add `refreshAgenda(): void` to update time/filter state using the retained raw cache.

- [ ] Back up both original files under `/tmp/opencode/calendar-upcoming-backup/` before modifying them.
- [ ] Keep raw cached events; filter on parse/open/existing timer triggers by event end. Parse all-day date-only ends as local midnight; retain ongoing events; reject invalid ends. Store the cache's `updated` timestamp and show a compact stale/error note (30-minute stale threshold).
- [ ] Enable `FileView.watchChanges` with reload on change. Remove `Process.running: panel.isOpen`; explicitly start sync on open only when not already running. Reload on successful exit and surface a failed sync, distinguishing `invalid_grant` if available without displaying raw stderr/secrets.
- [ ] Gate both existing background timers with `manageAgendaBackground`, keeping their intervals. Keep the reminder process/script otherwise unchanged. Set the central panel's owner property true.
- [ ] Include the date in all-day labels; attach hover-only full-title tooltips to event/task labels. Give task delegates a fixed 24 px height and the task viewport `Math.min(3, taskCount) * 24`, retaining scrolling and the six-task cap.
- [ ] Run all new regression tests; investigate failures before changing assertions. Run the existing reminder test with a disposable HOME and a copied real cache so its smoke test cannot mutate live notified.json.
- [ ] Have an independent reviewer check spec compliance and code quality; resolve any blocking issues and rerun tests.

### Task 3: Verify and reconnect

**Files:** No new production files; existing `/home/narol/.config/gcal/gcal-consent.py` and `gcal-sync.py` are executed unchanged.

- [ ] Confirm Quickshell accepted the hot reload and there are no new calendar-related QML load/runtime errors. Do not fix unrelated existing StatusbarWindow errors.
- [ ] Compare the original/current two-file diff and confirm no new timers/packages/process daemons were added.
- [ ] Start the existing consent script in the background and present/open its Google authorization URL for the user's browser approval. Do not overwrite/revoke unrelated Google MCP credentials or change Cloud Console settings.
- [ ] After successful consent, run the existing read-only sync once; verify cache timestamp/counts and absence of expired events in the displayed list. Never print token/client-secret values.
- [ ] Report verified results and any pending browser consent explicitly; do not claim live refresh is fixed before auth and sync succeed.

## Plan self-review

The three tasks cover the approved widget scope and authentication blocker. Tests use real QML and disposable external-service boundaries. No Python sync/refactoring or unrelated UI work is included. Browser consent remains a user action.

## Execution outcome

Main fix implemented and browser consent completed. Controller verification: 20/20 tests pass; native popup checked; live sync returns 17 events/17 tasks with no finished events. Original QML backups are retained in `/tmp/opencode/calendar-upcoming-backup/`. Execution/checklist evidence is in `/tmp/opencode/calendar-upcoming-sdd/progress.md`.

Final-review limitations disclosed: an open non-owner side panel refilters on reopening when prolonged offline use produces no cache writes; corrupted cache-generation metadata can prematurely clear a sync-error banner. Neither limitation affects the verified fresh production-cache path. No CPU/RAM benchmark or native-hover test is claimed.
