# Native Rofi sessions and compositor dismissal implementation plan

> **For agentic workers:** Use executing-plans inline, as already chosen. The configured free agent failed on quota; do not escalate or push. Track the checkboxes and a plan-specific ledger.

**Goal:** Remove avoidable Python startup overhead from ordinary Rofi launch/toggle, and make fully rendered pickers dismiss on another-monitor clicks without a resident daemon.

**Architecture:** The existing native helper owns session identity, native toggle/monitor lookup and PID-fd lifetime watching. A small Hyprland Lua module receives verified session registration and enables only its own ordinary mouse callbacks while that session is open. Outside clicks are consumed before Hyprland's exclusive-layer routing and asynchronously cancel only the verified process.

**Tech stack:** C11, Linux pidfd/flock, json-c 0.19, Bash, Hyprland 0.56 Lua, existing Rofi/Qalculate plugin and Python picker helpers.

**Spec:** `docs/superpowers/specs/2026-11-01-rofi-compositor-dismissal-design.md`, including the user-approved Rofi-only fade and on-demand input-readiness updates.

## Global constraints

- Continue on `fix/rofi-startup-reliability`; preserve `0623ee1`, the original dirty checkout and current approved startup work. No automatic push, PR changes or merge.
- Keep Rofi on demand: no resident frontend, generic keyboard capture/replay, idle polling process, private Rofi/Hyprland binary, or compositor plugin.
- Retain the startup FD-9 handoff, caller umask, PID safety, arithmetic, matching/ranking/recency, emoji grid and clipboard previews.
- Use a Rofi-only fade with unchanged shared timings (currently 200 ms in, 1 s out), not a new 100 ms global animation setting. Keyboard input must not wait for fade completion.
- Mouse callbacks handle unmodified left/right/middle presses. Alt/Super drag/resize and other modified shortcuts stay untouched.
- Compositor callbacks perform only in-memory queries; no file reads, synchronous IPC, subprocess on ordinary clicks or action on pointer motion.
- Snapshot live changes, verify the bundle before deployment, and preserve historical recovery data. Backups contain source, not binaries or runtime data.
- Main's unrelated TLS test and stale TV-helper checksum remain unchanged/disclosed. No blanket green-suite or zero-delay claim.

## Review focus

1. Stale/reused PIDs, foreign Rofi instances, symlinks/FIFOs and non-private metadata must never cause an unintended signal or blocking compositor read.
2. Startup handoff, registration failure and close→reopen races must release all descriptors and never let old cleanup clear a new session.
3. Same-monitor and no-session clicks must pass through; outside clicks must be consumed without activating the underlying application.
4. Config reload during a picker must recover its genuine session without duplicate callbacks or adopting an unrelated Rofi.
5. Input tests must isolate pre-focus typing in an owned harmless sink, distinguish cold/warm focus latency from animation, and never capture normal user typing.

---

### Task 1: Native identity and toggle path

**Files:** create `conf_backups/cachyos_hyprland_ml4w/local/.local/lib/rofi-trial/session.h` and `session.c`; modify adjacent `dismiss-guard.c`, `build-dismiss.sh` and `../../bin/rofi-trial`; create `tests/desktop_stack/test_rofi_session.py`; update `tests/desktop_stack/test_rofi_dispatch.py` and `test_rofi_guard.py`.

**Interfaces:**
- `struct launcher_session { pid_t pid; int pidfd; char *pidfile; char *runtime; }` owns its descriptor/allocated strings.
- `session_from_pid(pid_t, struct launcher_session *)` and `session_from_pidfile(const char *, struct launcher_session *)`: return `0` valid, `1` absent/dead, `2` invalid; initialize outputs safely on every path.
- `session_close(struct launcher_session *)` releases owned resources.
- `session_toggle(const char *mode, const char *runtime)`: stdout is the absolute PID-file path and exit `10` for a new view; exit `0` after a deliberate same-mode close; exit `2` on a real failure. Preserve current mode/monitor metadata formats.
- `dismiss-guard --toggle MODE RUNTIME` delegates to that function. The existing lifetime CLI remains available until Task 2 replaces its internals.

- [ ] Add native CLI tests using a small compiled ELF fixture named `rofi`, with real pidfiles/metadata and actual pidfd signals. Assert new-view exit 10/focused monitor, same-mode close exit 0, mode change close→new-view, stale PID recovery, foreign-process refusal, adjacent argument matching, wrong PID content, private-directory validation, and symlink/FIFO rejection without blocking.
- [ ] Add `test_apps_open_without_python_command`: an isolated PATH includes required native/core commands and test boundaries, but no `python` command. The wrapper must still open apps. Keep fake command interpreters' absolute shebangs independent of PATH; test the production dispatch decision, not their implementation.
- [ ] Run `python -m unittest discover -s tests/desktop_stack -p test_rofi_session.py -v` and the new dispatch test. Expect missing native subcommands / Python requirement failures before implementation.
- [ ] Implement strict session verification: pidfd first; same UID; executable basename `rofi`; exactly one adjacent `-pid ABSOLUTE_PATH`; owned private parent; regular non-symlink PID file named `rofi.pid` whose content equals PID; valid mode/monitor markers. Use no-follow, nonblocking, bounded file reads; never open a FIFO through stdio.
- [ ] Implement native toggle using json-c for `hyprctl -j monitors`, bounded child execution (3 s), and `poll(pidfd, 4000)` after SIGTERM. No shell command parsing. Close FD 9 in spawned IPC children. Write metadata only to verified regular owned files; preserve umask and paths with spaces.
- [ ] Update wrapper to require the compiled helper before using `--toggle`; require Python only in modes that need it. Retain exact guard handoff and nonblocking flock behavior. Update dispatcher fixtures to delegate native toggle to a real compiled helper while still controlling the watcher/picker boundary.
- [ ] Run all `test_rofi_*.py` and `test_switch.py`; expect no new failures. Commit only this task's sources/tests plus its ledger evidence, without staging unrelated pending work.

### Task 2: Compositor session and watcher lifecycle

**Files:** create identical `dotfiles/.config/hypr/rofi_session.lua` in the ML4W backup and `config/hypr/rofi_session.lua` in the Pleamar overlay; add `require("rofi_session").setup()` in both `custom.lua` files; update `session.h`, `session.c`, `dismiss-guard.c`, `build-dismiss.sh`; create `tests/desktop_stack/rofi_session.lua` and extend native session/guard/dispatch tests plus the existing Lua binding fixture.

**Interfaces:**
- `rofi_session.setup()` installs the module and `_G.rofi_trial_session` with `register(pid)` / `unregister(pid)`; unregister clears only an equal PID.
- Three initially disabled bindings use `mouse:272`, `mouse:273`, `mouse:274`, with normal modifier matching. Store each returned handle and toggle only that handle's enabled state; never broadly unbind another user's mouse bindings.
- Each callback finds a mapped `rofi` layer with the registered PID via `hl.get_layers({namespace="rofi"})`, compares its actual `layer.monitor.id` with `hl.get_monitor_at_cursor().id`, and either returns `{pass_event=true}` or requests cancellation and returns `{pass_event=false}`.
- `dismiss-guard --dismiss PID` verifies then signals only its pidfd, or safely does nothing for an invalid/dead/foreign target. `--adopt PID` verifies and registers only a genuine existing session for config-reload recovery.
- `session_ipc(const char *action, pid_t pid)` runs `hyprctl eval` with a fixed function name and integer PID only; validates success, times out after 3 s and reaps its own child. Fixed helper paths in Lua are shell-quoted.

- [ ] Add Lua behavioral tests for disabled/idle callbacks, inside/same-monitor pass-through, outside consume + exact PID cancellation, unrelated/unmapped layers, stale close events, old unregister after new registration, all three buttons, no mouse-movement subscription, and modified shortcuts not captured.
- [ ] Add config-reload tests: only mapped existing Rofi layers trigger one-shot `--adopt`, genuine identity is checked natively, and a closed picker launches no recovery process. Verify reload does not duplicate active callbacks.
- [ ] Run `lua tests/desktop_stack/rofi_session.lua`; expect failure before the module exists.
- [ ] Implement the module with no I/O in the click path. `layer.closed` unregisters a matching session. `config.reloaded` examines mapped Rofi layers and asynchronously asks the native helper to adopt them; invalid PID adoption never enables callbacks.
- [ ] Replace the guard's Wayland surfaces with validated PID attachment → Lua registration → startup FD close → blocking pidfd wait → PID-matched unregister. Preserve owner-bounded startup and old optional-FD CLI compatibility. Registration failure logs a clear reload/integration error, cancels only the already-verified picker, and releases all descriptors.
- [ ] Build the C watcher/core against json-c only. Keep old protocol assets untouched until the live replacement passes; no more Wayland overlays are created.
- [ ] Extend guard tests for successful registration/close/unregister, absent Lua integration, dead owner, IPC timeout, and no inherited lock after readiness. Run the focused Python and Lua suites; expect pass.
- [ ] Add `.config/hypr/rofi_session.lua` to coordinator required assets and document native/json-c requirements. Test refusal before stopping the current desktop when the module/helper is missing. Commit the task with evidence.

### Task 3: Live deployment, settled-menu clicks and early typing

**Files:** targeted live wrapper/helper/module/config paths; update `tests/desktop_stack/live_rofi_monitors.py`; create `tests/desktop_stack/live_rofi_input.py` and a test-only GTK entry sink fixture if needed.

- [ ] Snapshot every newly changed live path into the existing private `followup/startup-reliability/` area, without overwriting earlier snapshots. Build the full source bundle in a temporary directory. Install the Lua module/config and use config-only reload, then deploy the matched native helper/wrapper bundle after verifying no concurrent edits.
- [ ] Replace guard-surface assumptions in the explicit live test: expect only the owned Rofi layer, no helper overlays; locate the one watcher via its executable/argv/owner and check that it exits afterward. Align pointer and monitor before launch, wait for the owned painted border, and verify it stays open before clicking.
- [ ] Exercise all six apps/emoji/clipboard × other-output cases after full rendering, all three mouse buttons, motion-only behavior, same-monitor cancellation and no underlying-app activation. Use synthetic history and a fake wl-copy. Repeat with a config-only reload during an open picker.
- [ ] Re-run thirty open/close cycles, including ten overlapping starts, with no duplicate picker, lock warning, clipboard write, surviving helper, or disabled normal mouse button after closing.
- [ ] Build a short-lived GTK entry sink using the installed Python GI/GTK runtime. Focus and verify that owned sink before each pre-focus trial so no synthetic text can reach a user's application. Test a harmless numeric expression against an isolated desktop-app fixture and intercepted wl-copy. Sweep delays 0/30/60/120 ms and separately test immediately after the observed Wayland keyboard-enter event. Post-focus queries must arrive intact; pre-focus losses are measured and reported, not relabeled as passing or buffered silently.
- [ ] Capture native Timing-domain traces for the startup path without letting debug output reach the real clipboard. Compare native toggle overhead and launch-to-focus times to the recorded Python ~27 ms and 73–76 ms warm focus / 668 ms first-focus sample. Preserve raw cold/outlier results; no zero-latency claim.
- [ ] If any new live safety/behavior check fails, diagnose it before parity or completion. Once settled clicks pass, remove only the obsolete public `protocols/wlr-layer-shell-unstable-v1.xml` and its protocol README; retain all private historical artifacts and original branch sources.

### Task 4: Parity, review and final local result

**Files:** ML4W inventory/README, changed Pleamar manifest records (including the new Lua module), dated verification report, and the separate private permanent recovery manifest's expected-current fields.

- [ ] Verify targeted live source parity without replacing later user custom.lua edits. Refresh only changed public checksums/inventory; native binaries, private logs and clipboard data remain excluded. Retain the explicit correction to earlier false-positive cross-monitor claims.
- [ ] Preserve original recovery targets/snapshots; update only authorized expected-current hashes after checking that changes equal the approved edits. Run `rollback.py --manifest followup/permanent-manifest.json --check` with no writes.
- [ ] Run all six active Python suite directories explicitly: `tests/desktop_stack`, `tests/pleamar_migration`, `tests/qs_lightweight`, curated Pleamar tests, Vitreus tests and Kitty tests. Run both Lua suites, native builds, isolated ML4W dry-run/real restore, Python/shell parsing and `git diff --check`.
- [ ] Expected baseline exceptions remain exactly the unchanged TLS minimum-version test, existing Kitty GUI skip, and real Pleamar TV-helper checksum failure. Report them by name; every other new failure blocks completion.
- [ ] Perform whole-diff inline review under the approved quota fallback; check PID reuse, special files, descriptor lifetime, callback pass-through/consumption, reload/mode-switch races and privacy. Commit verified changes locally, preserve both worktrees and all evidence, and do not push.
