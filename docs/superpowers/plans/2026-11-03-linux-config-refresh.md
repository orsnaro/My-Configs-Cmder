# Linux Config Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox syntax for tracking. The configured free subagents are quota-blocked; continue inline without model escalation.

**Goal:** Publish a safe, restorable snapshot of the final desktop configuration approved in the November 1–3 OpenCode sessions.

**Architecture:** Refresh existing backup payloads, not the live desktop. Retain the verified native Rofi fallback, add the current Sherlock integration and its source/provenance, and copy only explicit non-secret mail configuration/support assets. Both public Hyprland overlays must agree; manifests describe the actual payload.

**Tech Stack:** Bash/rsync, Hyprland Lua, Python unittest, C/C++, systemd user units, Sherlock TOML/CSS.

**Spec:** Bounded maintenance brief: existing user-approved desktop behavior is the source of truth. Sherlock is primary (apps, clipboard, emoji, toggle/outside dismissal), Rofi remains fallback; CasaOS/Jellyfin tile on workspace 8 without title bars; Kitty ANSI green is restored; mail keeps Konsole/Nano, current shortcuts, safe right-hand HTML previews and generated Gmail SMTP/header-cache settings. No browser migration, new media bridge, new daemons or live activation. External Pomo and Hyprlock upgrades are documented as prerequisites, not copied as binaries.

## Global Constraints
- Branch from current `origin/main`; preserve the original checkout and its dirty files.
- Do not copy credentials, account files, OAuth tokens, browser profiles, mail data, clipboard history, runtime state, build products or virtual environments.
- Do not change live configuration, reload Hyprland, restart services, send mail or launch GUI probes.
- User requested autonomous completion and PR publication; no merge or unrelated push.
- Preserve current TLS security changes on main; repair stale assertions only against verified behavior.

## Review Focus
- Restore into a fresh home: launcher helpers and unit must be present, binaries remain explicit prerequisites.
- Backup re-run must not ingest mail/browser state or compiled launcher artifacts.
- Hardcoded home paths in Sherlock must be rebased for the restoring user.
- Switching stacks must not resurrect Walker or orphan Sherlock; preserve ordinary launched apps.
- Manifest checksums must include updated files without masking unrelated security changes.

### Task 1: Carry forward verified native Rofi fallback
- [x] Import the seven unpublished commits through `fix/rofi-startup-reliability`, resolving only integration differences against main.
- [x] Preserve the TV TLS floor without lowering stricter defaults; regenerate the public Pleamar manifest from actual bytes.
- [x] Run `python -B -m unittest discover -s tests/desktop_stack -v` and record genuine failures.

### Task 2: Refresh approved Hyprland and terminal settings
**Files:** both `conf_backups/cachyos_hyprland_{ml4w,pleamar}/.../hypr/` payloads, ML4W and Pleamar Kitty `custom.conf`, `tests/desktop_stack/test_config_refresh.py`.
- [x] Exercise the missing app-routing rules before copying; add isolated snapshot/session/restore tests.
- [x] Compare live Hyprland files to the payload; copy coherent current source/tests, including `sherlock_session.lua` and app map/rules.
- [x] Sync Kitty `custom.conf`; do not refresh unrelated generated palettes.
- [x] Repair outdated Hyprland test mocks to model the actual `hl.bind` return contract; retain meaningful assertions.
- [x] Run all Hyprland Lua/shell tests in both exports and the new refresh tests.

### Task 3: Preserve Sherlock and safe mail support
**Files:** ML4W `dotfiles/.config/sherlock/`, selected `dotfiles/.config/glaze-mail/terminal/config/`, `local/.local/{bin,src,share}/`, backup/restore scripts, tests.
- [x] Add fixture coverage for backup exclusions, Sherlock payload restoration and alternate-home path rebasing.
- [x] Copy Sherlock config, wrapper, IPC helper, tests and provenance; retain pinned clipboard source without target/build output. Document pinned Sherlock/Tela installation rather than vendor binaries or thousands of theme assets.
- [x] Copy `~/.local/src/glaze-mail/` source/tests and explicit mail-local bindings/opener/pager/terminal config only; never copy the containing mutable mail tree or account/auth files.
- [x] Extend backup/restore allowlists for these assets. Restore copies files only and rebases Sherlock home paths; no service activation or automatic download.
- [x] Preserve current shared Sherlock Hyprland startup rather than introduce new stack ownership (ledger ruling); retain Rofi fallback preflight.
- [x] Run component tests in temporary homes with no live mail/browser access.

### Task 4: Verify and publish
**Files:** backup READMEs/manifests, `docs/superpowers/reports/2026-11-03-linux-config-refresh.md`.
- [x] Record dependency versions, external Pomo fix, Hyprlock 0.9.7, manual Brave Origin/site trust settings, exclusions and restoration instructions.
- [x] Run all discovered offline unittest groups, syntax validation, both isolated restore previews/applies, and privacy/generated-file checks. Record unavailable GUI checks honestly; do not claim a live/reboot test.
- [x] Review spec compliance, then code quality inline (independent reviewer quota blocked).
- [ ] Commit scoped changes, push only this branch, create PR to main and verify its URL/head/base/status.
