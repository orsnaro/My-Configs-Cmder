# Rofi startup reliability implementation plan

> **For agentic workers:** Use executing-plans inline; the configured free subagent already failed on quota. No model escalation. Track each step below.

**Goal:** Both launcher shortcuts reliably open one picker during overlapping startup, retain deliberate second-press closing, and feel responsive without a daemon.

**Architecture:** Hold an advisory startup lock across the existing Bash→Python→Rofi handoff. The existing native dismiss guard inherits that descriptor and releases it once it has attached to the verified Rofi PID; later invocations can then toggle normally. Separately A/B-test a namespace-scoped Hyprland no-animation rule and retain it only if measured visual readiness improves.

**Tech stack:** Bash, Python 3, Linux flock/pidfd, existing C Wayland guard, Hyprland 0.56 Lua.

**Spec:** User-approved in-chat bounded design: fix overlapping requests, test the animation change before retaining it, update live paths and backups, retain normal toggles and recovery data; no automatic push.

## Global constraints

- Branch `fix/rofi-startup-reliability`, based on the preserved Rofi publication commit `0623ee1`; do not change the original dirty checkout.
- No shortcut changes, permanent daemon, global animation changes, or clipboard writes during testing.
- Runtime first, then matching backup/config and verification report. Snapshot every live path before deployment; retain prior snapshots and benchmarks.
- Keep PID identity checks, all-monitor dismissal, arithmetic, fuzzy/substring rules, emoji grid, image previews and relevance/recency behavior.
- Existing main TLS failure and stale TV-helper manifest record stay unchanged and disclosed. No green full-suite claim.
- No push or PR changes without a new explicit request.

## Review focus

- Lock acquired only inside an owned private runtime directory; no writes through an unsafe directory.
- Descriptor handoff has no gap between toggle decision and PID registration; guard failure/owner exit must release the lock.
- No inherited lock in Rofi, launched applications, or long-running clipboard/file helpers after startup.
- Repeated presses after readiness still close; stale PID files, quick cancellation and different-menu transitions recover.
- Rofi-only animation rules leave unrelated layers and all desktop animation settings unchanged.

### Task 1: Startup serialization

**Files:** `conf_backups/cachyos_hyprland_ml4w/local/.local/bin/rofi-trial`, `conf_backups/cachyos_hyprland_ml4w/local/.local/lib/rofi-trial/dismiss-guard.c`, `tests/desktop_stack/test_rofi_dispatch.py`, `tests/desktop_stack/test_rofi_guard.py`.

**Interfaces:** wrapper retains existing CLI/environment. Guard accepts optional fourth operand `STARTUP_FD` after `PIDFILE EXCLUDED_OUTPUT OWNER_PID`; old three-operand calls remain valid. FD 9 is reserved in this wrapper, inherited only by the guard, and closed by the wrapper before launching the picker. Native guard closes it after verified PID attachment; process exit closes it on failure.

- [ ] Add a command-boundary regression with the first picker paused before PID registration: overlapping calls must return promptly, start exactly one picker/guard, and not copy. Add recovery checks for missing assets/guard exit and unsafe runtime directories.
- [ ] Run `python -m unittest discover -s tests/desktop_stack -p test_rofi_dispatch.py -v`; expect the new overlap test to fail before implementation.
- [ ] Add private-directory validation and nonblocking flock acquisition before the toggle decision. Busy requests return success without waiting or spawning another picker. Hand FD 9 to the existing guard; never add a sleep/debounce timer or another watcher process.
- [ ] Validate/close the optional descriptor in the guard while preserving old CLI and pidfd checks. Add native argument/dead-owner checks with inherited descriptors.
- [ ] Run `python -m unittest discover -s tests/desktop_stack -p 'test_rofi_*.py' -v`; expect all focused tests to pass.

### Task 2: Scoped animation A/B and live regressions

**Files:** live `~/.config/hypr/custom.lua`, matching `conf_backups/cachyos_hyprland_ml4w/dotfiles/.config/hypr/custom.lua` and `conf_backups/cachyos_hyprland_pleamar/config/hypr/custom.lua`, associated Lua binding test, explicit live tests under `tests/desktop_stack/` if needed.

- [ ] Snapshot current wrapper, guard sources/binary and live custom.lua; build in a temporary directory and deploy only reviewed launcher changes.
- [ ] Measure repeated open/close/burst cycles with synthetic data and intercepted wl-copy. Confirm no PID-lock warnings, duplicate pickers, clipboard writes or surviving guards. Re-run arithmetic/toggles and six cross-monitor cases.
- [ ] A/B-test `hl.layer_rule({name="rofi-instant", match={namespace="^(rofi|rofi-dismiss-guard)$"}, no_anim=true})`. Measure time to stable center-panel border, not just layer registration. Retain only if faster; no global animation changes.
- [ ] Preserve physical-shortcut limits: synthetic virtual-keyboard attempts did not fire the modifier-only binding, so do not label command-level tests as physical key tests.

References: [layer rules](https://wiki.hypr.land/Configuring/Basics/Window-Rules/#layer-rules), [animation units/tree](https://wiki.hypr.land/Configuring/Advanced-and-Cool/Animations/). Installed animation settings currently include layers-in slide 3 ds, fade-in 2 ds, layers/fade-out 10 ds.

### Task 3: Backup parity, review and final verification

**Files:** changed curated manifest records; `conf_backups/cachyos_hyprland_ml4w/README.md`; new dated verification report.

- [ ] Refresh only changed curated checksums and verify public inventory/source-only exclusions. Confirm changed live wrapper/helper/config parity without overwriting later user rules.
- [ ] Run all six active publication Python suite directories explicitly, native build, Lua binding tests, shell syntax, and `git diff --check`. Expect only the accepted baseline TLS failure and existing Kitty GUI skip.
- [ ] Review the entire follow-up diff inline (approved quota fallback), record evidence and limitations, and leave the verified changes locally. Do not push.
