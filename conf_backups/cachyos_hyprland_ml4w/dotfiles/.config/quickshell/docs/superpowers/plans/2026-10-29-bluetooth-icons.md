# Bluetooth Icons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Blueman's glossy badge and restore its missing dropdown icons.

**Architecture:** A shell-local icon overlay inherits Breeze Dark. Seven
icon aliases reuse installed monochrome Breeze assets; the existing tray
renderer and native menu remain untouched.

**Tech Stack:** Quickshell 0.3.2, QML, freedesktop icon themes, Bash.

**Spec:** `2026-10-29-bluetooth-icons-design.md` in this directory.

## Global Constraints

- Preserve desktop theme, bar layout, other tray apps, and Bluetooth behavior.
- No package installation, Bluetooth toggling, unrelated fixes, or Git initialization.
- Existing dotfiles are not in a Git repository; branch/commit steps do not apply.
- Restart only the main shell, not the dock or Bluetooth applet.

## Review Focus

- Test normal/active/disabled Blueman icon names without changing Bluetooth state.
- Test every icon name exported by the live Blueman menu, not only the three warnings.
- Ensure SVGs render real pixmaps, not just successful name lookups.
- Check unrelated network, Steam, and KDE Connect icons remain available.
- Check existing theme registration before creating a symlink; never overwrite user files.

## Task 1: Add and verify the shell-local icon overlay

**Files:**
- Create: `StatusbarApp/tests/tray_icons.sh` and `StatusbarApp/tests/tray_icons.qml`.
- Create: `shared/icons/ml4w-quickshell/index.theme` and `scalable/status/` aliases.
- Register: `~/.local/share/icons/ml4w-quickshell` -> this overlay directory.
- Modify: `shell.qml:1-2`, adding `//@ pragma IconTheme ml4w-quickshell`.

**Interfaces:** Native `QIcon::fromTheme` and Quickshell `iconPath`/`hasThemeIcon`.

- [x] Write a headless Quickshell regression test that selects the shell's configured pragma, loads all Blueman tray/menu names into Images, checks `Image.Ready` and `hasThemeIcon`, and exits with nonzero status for missing icons or checkerboard warnings.
- [x] Run it before implementation; expect missing Bluetooth/plugin symbolic icons.
- [x] Create the overlay metadata (`Inherits=breeze-dark`, scalable 16–256px status directory).
- [x] Add symlinks: `blueman-tray` and `bluetooth-symbolic` -> Breeze `devices/16/network-bluetooth.svg`; `blueman-active` -> `status/22/network-bluetooth-activated.svg`; `blueman-disabled` and `bluetooth-disabled-symbolic` -> `status/22/network-bluetooth-inactive-symbolic.svg`; `application-x-addon-symbolic` -> `actions/16/plugins.svg`; `blueman-send-symbolic` -> `actions/16/document-send.svg`. Check every target exists first.
- [x] Register the theme and add the startup pragma; rerun the regression test and verify non-null rendered Images, inherited unrelated icons, and no missing-icon warnings.
- [x] Run all existing StatusbarApp tests, reporting pre-existing/environmental failures accurately.
- [x] Attempt independent spec/code review (blocked by configured model quota; completed self-review instead), restart only the main shell, and inspect fresh logs plus bar/dropdown screenshots without triggering Bluetooth actions.
- [x] Record verification results and summarize the exact changes.

## Verification result

24 checks passing (11 shell + 2 QML + 11 updates unit tests). Live main bar
and native Bluetooth dropdown visually verified. No desktop-theme, layout,
or Bluetooth-state changes. Verification record:
`/tmp/opencode/qs-bluetooth-sdd/task-1-report.md`.
