# Desktop Stack Switching and Pleamar Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement task-by-task. Steps use checkbox tracking.

**Goal:** Preserve the current Pleamar setup and install two reliable, launcher-visible, mutually exclusive whole-desktop switches.

**Architecture:** Reuse the existing snapshot/restore modules and curated export. A single Python coordinator owns mode persistence and stop/start logic; two shell scripts select the mode. A separate installer backs up and mode-gates existing live hooks without activating a switch.

**Tech Stack:** Python standard library (fully annotated), Bash, Hyprland Lua, existing systemd user services, existing QS/ML4W/Pleamar scripts, unittest fixtures.

**Spec:** `docs/superpowers/specs/2026-10-28-desktop-stack-recovery-design.md` (user approved).

## Global Constraints

- Work on `fix/pleamar-backup-and-stack-switch`; preserve unrelated dirty/untracked work. No push.
- Keep all configured Pleamar scenes/widgets; no partial widget optimization.
- Exactly two launcher entries: **Switch to QS** and **Switch to Pleamar**.
- Remember the last successfully selected stack; initial mode remains Pleamar.
- Do not perform a live switch or real lock/unlock during installation/testing.
- Affect only the inactive desktop stack, not unrelated services or applications.
- Private snapshots remain owner-private and Git-ignored under `conf_backups/.private/`.
- Keep `conf_backups/cachyos_hyprland_pleamar/RESTORE.sh` file-only and dry-run-first.
- Use existing installed binaries; no sudo, downloads or package changes.

## Review Focus

1. Locked session or unreadable native-lock state: refuse a switch before termination.
2. GTK/wallpaper/lazy hooks: never cold-start the inactive stack, including after a theme change.
3. Concurrent/repeated clicks and failed startup: serialize, avoid duplicates, preserve/roll back the remembered mode.
4. Symlinked config roots and private keys: preserve bytes, executable modes, aliases and private permissions; reject corrupt payloads before writes.
5. Shared processes and slideshow preferences: leave unrelated apps/services alive and retain the QS slideshow preference while pausing its loop.

---

### Task 1: Reusable recovery using the existing snapshot engine

**Files:** Modify `tools/pleamar_migration/restore.py`; extend `tests/pleamar_migration/test_restore.py`; create `tools/pleamar_recovery.py`, `tests/desktop_stack/test_recovery.py`, `tools/recover-pleamar.sh`.

**Interfaces:** Existing `snapshot.snapshot`, `snapshot.verify_snapshot`, `restore.plan_restore`, `restore.apply_restore`, and `authorize.authorize_journal`. New recovery CLI: `python3 tools/pleamar_recovery.py [--dry-run | --apply] [--snapshot PATH] [--home PATH]`. Default snapshot comes from private `conf_backups/.private/pleamar-current.json`; applying creates a private pre-write checkpoint and prints its location. Recovery restores files only; activation remains the coordinator's responsibility.

- [x] Preserve the old curated export and create/verify an owner-private snapshot of current source, data, binary, helpers, wallpapers and integration settings. Existing checkpoint: `conf_backups/.private/pleamar-current-20261028T111415Z/`.
- [ ] Add a regression test asserting that `apply_restore` validates each unique snapshot root once per preflight, while still rejecting per-file tampering before/during writes. Run it red, then cache only the whole-root validation within one call; retain existing file/hash/state checks.
- [ ] Add recovery fixture tests: default preview writes nothing; corrupt/missing snapshot rejects; apply checkpoints changed destination bytes before replacement; runtime/helper modes and private pairing data survive; no desktop command executes. All fixture roots stay under `/tmp/opencode`.
- [ ] Implement the recovery wrapper using existing authorize/plan/apply functions, not a new copy/manifest format. Refuse overwriting without explicit `--apply`; use the original private snapshot paths/mode metadata and a verified checkpoint of affected existing destination sources.
- [ ] Run `python3 -B -m unittest discover -s tests/pleamar_migration -p 'test_*.py'` and `python3 -B -m unittest discover -s tests/desktop_stack -p 'test_recovery.py'`; require zero failures. Review task diff.

### Task 2: Whole-stack coordinator

**Files:** Create `tools/desktop_stack.py`, `tests/desktop_stack/test_switch.py`.

**Interfaces:** CLI `desktop_stack.py switch {quickshell,pleamar}`, `resume`, `is {quickshell,pleamar}`, `status`. Mode file `~/.config/ml4w/settings/desktop-stack`; absent defaults to `pleamar`, malformed values fail closed. `resume` selects the persisted mode. Injectable command/process backend for tests; production backend reads only same-user `/proc` processes and uses exact known executable/script matches. No test touches the real session.

- [ ] Write tests for both directions, idempotence, missing dependencies before stop, lock rejection/unavailable native lock query, readiness failure/rollback, concurrent invocation, and remembered selection after success only. Assert fake unrelated processes are never signaled and keepers stop before scenes.
- [ ] Run new tests red. Implement the coordinator with a runtime `flock`, bounded subprocess timeouts, owner-private logging and explicit startup verification. Restore the previous mode/stack on failure; surface rollback failure separately.
- [ ] QS startup: existing `ml4w-autostart`, `elephant`, `walker --gapplication-service`, SwayNC and GNOME polkit agent. QS main config already supplies main and secondary bars; `ml4w-autostart` supplies the dock. Do not introduce a second waybar.
- [ ] Pleamar startup: unmask/start `pleamar.service` and the existing lock keeper command with `DRI_PRIME=1`, `VK_DRIVER_FILES=/usr/share/vulkan/icd.d/radeon_icd.json`, `PLEAMAR_SWAPCHAIN=1`. Let the main scene start its configured desktop companions. Verify notification ownership/readiness where available.
- [ ] QS shutdown: stop owned wallpaper-automation loop without changing its saved slideshow preference, stop all same-user QS/Walker/Elephant processes and QS notification/auth helpers. Pleamar shutdown: stop keeper owners first, stop managed service and remaining known scenes, clear the night-mode transform before its daemon is stopped.
- [ ] Stop/mask only identified opposing stack units; never blanket-disable services. Leave awww, hypridle, cliphist, portals, network/audio, tray applets and user applications untouched.
- [ ] Run `python3 -B -m unittest discover -s tests/desktop_stack -p 'test_switch.py'`. Review spec compliance then code quality.

### Task 3: Installer, launchers and inactive-stack hook guards

**Files:** Create `tools/install_desktop_stack.py`, `tests/desktop_stack/test_install.py`, `tools/switch-to-qs.sh`, `tools/switch-to-pleamar.sh`; generated live links and two `.desktop` files. Live hook targets listed below are checkpointed before edits.

**Interfaces:** CLI `install_desktop_stack.py [--dry-run | --apply] [--home PATH]`. Installer is idempotent and file-only: never starts/stops services, reloads the compositor, or switches modes. Thin shell wrappers resolve their own repo path and exec Task 2. Generated links: `~/.local/bin/desktop-stack`, `switch-to-qs`, `switch-to-pleamar`; generated launcher files `~/.local/share/applications/switch-to-{qs,pleamar}.desktop`.

- [ ] Write red fixture tests for no-write preview, repeat installation, escaped/spaced repo paths, checkpoint creation, initial Pleamar mode, config-root symlink preservation, exact two visible launchers and zero service/process activation.
- [ ] Modify `~/.config/hypr/conf/autostart.lua` to invoke `desktop-stack resume` once while retaining its shared startup commands. Conditionalize loading `hypr_vitreus`/Vitreus generated appearance modules in `hyprland.lua`; preserve shared display/input/user-app configuration. Keep existing mode-aware locker fallback; reject switching while locked.
- [ ] Gate `~/.config/ml4w/scripts/ml4w-autostart`, `ml4w-wallpaper-automation` start/toggle, and `~/.local/bin/qs-lazy-toggle` against the selected mode. Gate Walker restarts in `ml4w-wallpaper` and both GTK theme-listener branches. GTK listener must also respect `settings/waybar-disabled`, so QS does not gain a duplicate Waybar.
- [ ] Gate QS-only dock/statusbar/wallpaper UI helpers; preserve non-UI wallpaper operations. Restore a QS-appropriate branch for `ml4w-toggle-hyprsunset` while retaining Pleamar's saved-night-mode path. Guard direct `pleamar.service` activation with the same mode choice. Avoid editing the Vitreus source or copying historical whole desktop profiles.
- [ ] Add tests executing transformed shell hooks with fake commands in both modes, asserting no inactive `qs`, `walker`, `waybar` or Pleamar start. Verify shell syntax and Lua fixture config loading. Verify the installer does not change slideshow settings.
- [ ] Run `python3 -B -m unittest discover -s tests/desktop_stack -p 'test_install.py'`; review diff. Before actual installation, create a branch in any separate live config Git repository being edited, preserve dirty content, then run installer preview/apply without running either switch launcher.

### Task 4: Refresh exports and verify recovery end-to-end in isolation

**Files:** Refresh existing `conf_backups/cachyos_hyprland_pleamar/source/vitreus/**`, `config/hypr/**`, safe `data/**`, `bin/pleamar-start`, `systemd/pleamar.service`, `versions/pleamar.txt`, `manifest.json`, `README.md`, `RESTORE-CURRENT.md`, `CHECKS.md`; include the new stack-tool entrypoints/integration instructions. Update private current-pointer JSON only after snapshot verification.

**Interfaces:** Existing public `manifest.json` file inventory/source mappings and private snapshot schema remain unchanged. Exact private recovery includes every scene's settings, not just Vitreus's `data/` subset. Public export excludes personal data. Normal switching does not invoke recovery.

- [ ] Confirm existing public payload drift fails source-parity checks; synchronize inspected current source/Hyprland/helpers and safe settings. Preserve historic files and existing unrelated Kitty/Fish content; do not publish OAuth/pairing credentials, private notes or histories.
- [ ] Regenerate manifest inventory/hashes/executable-bit modes/source mappings and record Pleamar `0.4.31` plus the current runtime SHA-256. Update recovery/switching instructions and prerequisites truthfully.
- [ ] Capture/verify a final private snapshot including new installed hooks/launchers, original/full Pleamar state, runtime and required QS configuration; atomically publish `conf_backups/.private/pleamar-current.json`. Keep previous snapshots.
- [ ] Restore the real private snapshot into an isolated temporary home and compare all restored payload bytes, executable modes and aliases against its manifest. Run public RESTORE.sh dry-run and fixture apply. Validate both launcher `.desktop` files if `desktop-file-validate` is installed.
- [ ] Run all new desktop-stack tests, the migration suite, public restore tests, exported scene Python tests, standalone Lua harnesses and applicable Hyprland/terminal suites. Current pre-change live scene baseline: **205 Python tests pass**. Report any skipped GUI/live acceptance rather than imply it happened.
- [ ] Compare the 523 recorded unrelated file/link fingerprints; require no changes. Run `git diff --check`, verify private roots are Git-ignored/0700 and private payloads 0600, inspect final diff and request independent review. Resolve critical findings before declaring completion.
- [ ] Record that live stack switching, a reboot/login cycle and real lock/unlock were not performed unless separately approved. Provide the two exact launcher names and recovery command; leave current desktop active and do not push.
