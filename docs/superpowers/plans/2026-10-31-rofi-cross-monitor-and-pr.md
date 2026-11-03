# Cross-monitor Rofi dismissal and Rofi-only PR plan

> **For agentic workers:** Use executing-plans inline. The approved free subagent already failed on quota; do not escalate models.

**Goal:** Clicking another monitor cancels every Rofi picker without changing clipboard data; then push a clean PR targeting main.

**Architecture:** Extend the existing on-demand launcher bundle with one small native Wayland helper. It creates keyboard-unfocused transparent click surfaces only on the other outputs, using a shared 1×1 transparent buffer and viewport scaling. PID descriptors tie its lifetime and cancellation to the correct Rofi process. No resident helper or polling remains after the picker exits.

**Tech stack:** C11, wayland-client, wlr-layer-shell, viewporter, Linux pidfd; existing Python/Bash dispatcher and native Rofi plugin.

**Spec:** User approved the short in-chat click-based design and explicitly chose a Rofi-only PR from current main. Preserve the prior calculator, emoji grid, image preview, toggle, matching and ranking requirements.

## Global constraints

- Worktree `/home/narol/.local/share/opencode/worktree/df3a91/hyprland-rofi-main-pr`, branch `fix/hyprland-rofi-main-pr`, based on `origin/main` (6e128ea).
- Transfer only Rofi changes from the live checkout; omit seven earlier unrelated commits and dirty dock/Pleamar work.
- Clean main already fails `test_tv_tls.TvTlsTests.test_stricter_runtime_minimum_is_preserved`. User explicitly chose **keep out and disclose**: do not change TLS production code/tests or claim the whole suite is green.
- Clicking another monitor dismisses only; it does not activate the underlying application. Keyboard remains with Rofi. Moving the pointer alone must not dismiss.
- Guard startup/shutdown and normal app launching must leave no helper processes behind.
- Keep historical benchmark/recovery snapshots unchanged. Deploy only reviewed launcher files for live testing, with new safety snapshots and updated separate recovery metadata.
- No KDE wiring or global service changes. Push only the approved branch and create the PR to main; never merge automatically.

## Review focus

- Exclude the actual Rofi output so the transparent guard cannot cover the launcher.
- Reject foreign/reused PIDs; use pidfds, UID, executable and exact private PID-file arguments.
- Handle startup failure, normal cancellation, repeated toggles, output add/remove, and helper shutdown without idle polling or leftover overlays.
- Restore builds all native assets; compiled binaries, generated protocol artifacts, clipboard data and unrelated local files stay out of git.
- Preserve main's newer security changes and public manifest checksums.

### Task 1: Prepare the clean publication payload

Files: existing Rofi-targeted tools, backup payloads and tests from the prior task; shared README/manifest changes must exclude unrelated local dock changes.

- [x] Export only the prior Rofi diff against its recorded base plus its explicit new source/helper/theme/test files.
- [x] Apply that payload to current main; retain main's TLS source and test unchanged. Recompute only changed Pleamar manifest records and the publication checkout's public inventory.
- [x] Run affected coordinator/install/backup/search tests; compare and classify the known baseline failure separately.

### Task 2: Native cross-monitor click guard

Files: `conf_backups/cachyos_hyprland_ml4w/local/.local/lib/rofi-trial/{dismiss-guard.c,build-dismiss.sh,build-smart.sh,toggle.py,clipboard.py,files.py,protocols/wlr-layer-shell-unstable-v1.xml}`, `local/.local/bin/rofi-trial`, `tools/desktop_stack.py`, focused tests under `tests/desktop_stack/`.

Interfaces:
- `dismiss-guard PIDFILE EXCLUDED_OUTPUT OWNER_PID`: startup bounded by owner lifetime; once attached, block on Wayland events and Rofi pidfd. A pressed pointer button on a guard signals only verified Rofi and exits; Rofi exit destroys all guard surfaces.
- `toggle.py main(mode: str) -> int` keeps its stdout/exit-code interface; writes the focused monitor name to private runtime metadata for the dispatcher.
- Dispatcher consistently passes `-monitor` to every picker and starts the guard with stdout detached; file/clipboard helpers accept the monitor through the existing environment pattern.
- `build-smart.sh` also invokes `build-dismiss.sh`; builds from source, never relying on saved native binaries.

- [x] Add failing real-build/lifecycle tests: guard rejects a foreign process, exits with a dead owner, and builder produces both native assets. Add monitor-forwarding assertions to launcher tests.
- [x] Vendor the licensed wlr XML at commit d1598e82240d6e8ca57729495a94d4e11d222033. Generate viewporter/xdg-shell artifacts from installed wayland-protocols in a private temporary build directory.
- [x] Implement the guard and dispatcher/helper integration. Use one transparent pixel per helper, no keyboard grab, and no periodic work after startup.
- [x] Run all affected tests; check that only the untouched main TLS baseline test remains failing.

### Task 3: Live validation, backup parity and publication

Files: targeted runtime launcher files; relevant READMEs, manifests, tests and verification report.

- [x] Snapshot the current launcher helpers; build/deploy only the new reviewed bundle to the live user paths.
- [x] Use synthetic picker/clipboard data and the test-only virtual pointer to click on each other monitor for apps/emoji/clipboard. Verify actual painted guards, pointer-only behavior, no copy, and no remaining helper surfaces/processes after every close.
- [x] Re-run same-monitor dismissal, calculator, ranking and repeat-toggle checks. Measure guard PSS while open; do not relabel old benchmark numbers as new results.
- [x] Update backup/restore exclusions, dependencies and source payload inventory; refresh only changed public manifest checksums. Test in isolated HOME.
- [x] Run full publication-checkout suites, report the permitted pre-existing TLS failure by exact name, and review the complete PR diff for unrelated files, secrets, binaries and protocol license attribution.
- [ ] Commit only these changes on `fix/hyprland-rofi-main-pr`, push to origin, create a PR with `--base main`, then verify its URL/base/head. Preserve both worktrees and the live dirty branch.
