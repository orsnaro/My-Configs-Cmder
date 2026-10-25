# Pleamar Configuration Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish an up-to-date, privacy-reviewed backup of the current Pleamar, Kitty, and Fish/Oh My Posh setup in a PR targeting `main`.

**Architecture:** Refresh the existing curated export under `conf_backups/cachyos_hyprland_pleamar/` from live files, without installing or changing live settings. Add terminal configuration to the same export, document restoration and exclusions, and regenerate its inventory. This is a snapshot update, not a redesign or a new backup subsystem.

**Tech Stack:** Existing Pleamar/Lua/Python tests, Fish syntax checks, Python standard-library hashing, Git, GitHub CLI.

**Spec:** User-approved bounded design in this session: refresh only the current Pleamar export, include current Kitty/Fish/Oh My Posh configuration, exclude private/runtime data, preserve older backups and unrelated work, and create a PR against `main`.

## Global Constraints

- Branch: `chore/refresh-pleamar-config-backup`, created from the current branch without discarding any working files.
- Do not change anything in the live home configuration, restart desktop processes, install packages, or apply Kitty patches.
- Preserve `conf_backups/cachyos_hyprland_ml4w/`, `conf_backups/cachyos_hyprland_pre_pleamar_20261019-172818/`, and pre-existing unrelated changes.
- Exclude credentials, SSH functions with private connection details, notification/calendar/task data, history, logs, caches, backup copies, generated previews, and private migration payloads.
- Do not stage unrelated untracked migration tools/tests/docs or pre-Pleamar metadata. Clearly describe local-only rollback prerequisites rather than implying they ship with this PR.
- Publish only the current Pleamar export and this plan. Do not merge the PR.
- Git push requires explicit confirmation as part of the publication approval.

## Review Focus

- Live config roots are symlinks: copy inspected resolved bytes; record source mappings rather than publishing broken absolute links.
- Prompt restoration needs both Fish customization and its Oh My Posh theme, not merely a theme filename.
- Kitty custom mappings depend on helper scripts, their version-specific patch files, and the ML4W cursor-trail include.
- Persistent Pleamar display/theme settings must be distinguished from runtime histories and sensitive location data.
- Existing manifest validation records are historical: retain their date and do not present them as fresh visual or performance acceptance.

## Task 1: Refresh the desktop snapshot

**Files:** `conf_backups/cachyos_hyprland_pleamar/source/vitreus/**`, `config/hypr/**`, selected `data/*`, `bin/pleamar-start`, `systemd/pleamar.service`.

**Interfaces:** Consume live `~/.config/pleamar/shells/vitreus`, `~/.config/hypr`, `~/.local/share/pleamar/vitreus`, and the existing GPU wrapper/service. Produce a matching curated export; no new runtime interfaces.

- [ ] Preserve a private baseline of the existing export and fingerprints of unrelated changes before overwriting any backup file.
- [ ] Run byte-parity checks to confirm the known stale source/Hyprland/wallpaper files fail before synchronization.
- [ ] Review changed/new source files and safe persistent settings; copy current source and its tests, complete Hyprland configuration dependencies, and an explicit persistent-settings allowlist. Do not copy histories, private settings, caches, or backups.
- [ ] Run exported scene Python tests with `python3 -B -m unittest discover -s source/vitreus/tests -p 'test_*.py'` and all standalone scene Lua harnesses with `lua5.4`. Run Hyprland harnesses in their expected fixture environment, never against the live compositor.
- [ ] Verify byte parity for every selected live-source mapping and review the update against the private baseline.

## Task 2: Include the current terminal and prompt

**Files:** New `config/kitty/**`, `config/fish/**`, `config/ohmyposh/*`, and required `config/ml4w/settings/kitty-cursor-trail.conf` within the Pleamar export.

**Interfaces:** Consume active Kitty configuration/helper/patch/test files and active Fish configuration plus safe functions and Oh My Posh themes. Produce an overlay restored to `~/.config/`; exclude `fish_variables`, SSH functions, caches, and dated backups.

- [ ] Confirm parity checks fail because the terminal/prompt export is currently absent.
- [ ] Copy Kitty configuration and required helpers/tests/patch diffs, excluding patch backup payloads. Copy Fish config/conf.d and safe non-SSH functions; copy audited non-backup Oh My Posh themes and the cursor-trail include.
- [ ] Run `python3 -B -m unittest discover -s config/kitty/tests -p 'test_*.py'`, Fish `--no-execute` checks for each `.fish` file, and JSON parsing for every prompt theme.
- [ ] Verify the exported Fish customization loads the included `screenshot.omp.json`; compare all selected terminal files with live bytes.

## Task 3: Verify and publish the curated export

**Files:** `conf_backups/cachyos_hyprland_pleamar/README.md`, `RESTORE.md`, `manifest.json`, `versions/pleamar.txt`, `RESTORE.sh`, and `tests/test_restore_script.py`; dedicated current-overlay restore instructions in the same directory.

**Interfaces:** Consume the copied payload and verification results. Produce an exact manifest, truthful restore instructions, and one scoped PR against `main`.

- [ ] Update the export date, current behavior notes, terminal dependencies, source mappings, privacy exclusions, and safe current-overlay restoration instructions. Qualify historical results and local-only rollback dependencies.
- [ ] User-approved follow-up: add a Pleamar-specific `RESTORE.sh` with dry-run as the default and an explicit `--apply`. Verify the manifest and destination boundaries before writes, back up existing resolved content and symlink metadata privately before merging, preserve unrelated destination files, and recreate source helper links. Never install packages, patch Kitty, start/stop services, reload Hyprland, or run upstream install/uninstall. Test these properties in isolated temporary homes, starting with failing tests. Document unloading through the reviewed rollback guide; leave old snapshot scripts untouched.
- [ ] Regenerate hashes, modes, sizes, inventory, and the documented source-tree digest without hashing the manifest itself. Pin binary hashes/version metadata without copying binaries.
- [ ] Run all available relevant export tests, the existing migration suite as a preservation check, manifest coverage/hash validation, live parity checks, and a secret/private-file audit. Record skips honestly; investigate failures rather than hiding them.
- [ ] Review the complete candidate diff inline because the configured free-model agents are unavailable. Verify unrelated files still match their initial fingerprints.
- [ ] Stage only the current Pleamar export and this plan, inspect the staged path list and whitespace checks, and create a commit. Do not include unrelated dirty files.
- [ ] After explicit push confirmation, push only `chore/refresh-pleamar-config-backup`, create a GitHub PR with `--base main`, and verify its URL, head/base, and file scope. Leave the PR unmerged.
