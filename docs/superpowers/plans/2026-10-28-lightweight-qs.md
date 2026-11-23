# Lightweight QS Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task; prior configured free-model delegation failed with a quota limit. Do not escalate models. Steps use checkbox tracking.

**Goal:** Display GPU%, used VRAM and focused title on the main QS bar, and complete lightweight wallpaper-responsive Walker/Kitty theming.

**Architecture:** Extend the existing CPU pill's already-sampled data rather than create a new GPU process. Add a reactive title component and palette-map Walker's existing stylesheet; retain Kitty's working Matugen integration.

**Tech Stack:** Existing Quickshell 0.3.2/QML, JavaScript format helper, GTK CSS, Matugen, Python unittest and offscreen QML fixtures. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-10-28-lightweight-qs-design.md` (approved bounded in-chat design, captured for implementation).

## Global Constraints

- No new daemon, collector, recurring metrics timer or focused-title polling.
- GPU uses existing three-second sample; missing values display `—`, zero is valid.
- Title after workspaces, main bar only, plain text, maximum 220 px, empty-desktop collapse.
- Preserve clock centering, secondary bars, settings, providers and unrelated dirty files.
- Work on `feat/lightweight-qs-metrics-and-palette`; PR #10 stays unchanged; no automatic push.
- Checkpoint live files privately; preserve aliases; screenshots/keys/raw evidence never committed.

**Preflight before Task 1:** privately checkpoint all mapped live files and
record unrelated dirty-path fingerprints before the first code edit. Confirm
the original PR head remains `9c3e77a`; implementation commits belong only to
this new feature branch. The later acceptance task reuses this checkpoint.

## Review Focus

1. Missing/malformed GPU cache must not display fake zero or blank the main bar (Task 1).
2. Zero metrics must remain valid, including VRAM=0 (Task 1).
3. Long, Unicode, markup-looking and rapidly changing titles must elide safely and collapse on desktop (Task 2).
4. Wide workspace/media content and large right-side metrics must not overlap the centered clock (Task 2).
5. Wallpaper reload in Pleamar mode must not resurrect Walker/QS; existing Kitty settings remain intact (Tasks 3–4).

## Exact file mapping

Live QS root: `/home/narol/.config/quickshell/StatusbarApp/`.
Backup QS root: `conf_backups/cachyos_hyprland_ml4w/dotfiles/.config/quickshell/StatusbarApp/`.
Patch corresponding files in both roots. Existing backup differs from live
`StatusbarWindow.qml` by one pre-existing `manageAgendaBackground: true` line;
retain that line in live and mirror it when updating the backup.

Live layout: `/home/narol/.config/ml4w-statusbar/config.json`; backup:
`conf_backups/cachyos_hyprland_ml4w/dotfiles/.config/ml4w-statusbar/config.json`.
Live Walker style: `/home/narol/.config/walker/themes/ml4w/style.css`; new saved
copy: `conf_backups/cachyos_hyprland_ml4w/dotfiles/.config/walker/themes/ml4w/style.css`.
Do not edit the pre-existing dirty legacy `README.md`, `manifest.txt` or dock files.

### Task 1: GPU and VRAM in the existing metrics pill

**Files:** Modify both mapped `CpuModule.qml` files; create `tests/qs_lightweight/test_bar.py` and `tests/qs_lightweight/metrics.qml`.

**Interfaces:** Existing `CpuModule.parseSys(src: string): void`; add nullable `gpuPct` and `vramUsed` properties. Consume `gpu.usage` and `gpu.vram_used_gb`, format memory using existing `SystemMetricFormat.js`. Keep all existing CPU/panel signals.

- [ ] Add offscreen real-QML assertions for parsed `12`/`1.2`, valid zero, missing `gpu`, malformed JSON retaining previous data, and em-dash missing display. Assert no new Process/Timer beyond the original collector/cadence.
- [ ] Run `python3 -B -m unittest discover -s tests/qs_lightweight -p 'test_bar.py'` and observe GPU assertions fail before editing production.
- [ ] Extend existing parser/text row with compact GPU/VRAM labels; retain CPU clock and hover/click panel behavior. No collector or extra cache reader.
- [ ] Re-run the tests; require all pass. Commit only scoped tests and CPU files.

### Task 2: Event-driven focused-window title

**Files:** Create both mapped `FocusedTitleModule.qml` files; modify both mapped `StatusbarWindow.qml`, documented `config.json`, and mapped live/backup layout; extend `tests/qs_lightweight/test_bar.py`; create `tests/qs_lightweight/focused_title.qml`.

**Interfaces:** `FocusedTitleModule` consumes `ToplevelManager.activeToplevel`; `property var toplevel` defaults to that value, enabling a real QtObject fixture. Expose `readonly property bool collapsed` for no title; cap text at 220 px; no action or mouse handler. Register module key `title` and insert it after `workspaces` in defaults and installed layout.

- [ ] Add real-QML tests for live title-property changes, empty/null toplevel, Unicode and `<b>literal</b>` plain text, width<=220 and ellipsis. Include a layout fixture demonstrating no overlap with the centered group when side content grows.
- [ ] Run Task 1's command and observe title tests fail before implementation.
- [ ] Implement component and minimal registry/left-loader layout constraints; allow title to shrink/hide first. Do not restructure other bar components or modify secondary bars.
- [ ] Run all bar fixtures, existing sysinfo/slim-bar tests and syntax checks; require zero failures. Commit exact mapped files, not entire backup trees.

### Task 3: Complete existing palette wiring

**Files:** Modify live Walker style and its new saved copy; create `tests/qs_lightweight/test_palette.py`. Record verification in `docs/superpowers/reports/2026-10-28-lightweight-qs.md`. Kitty files stay unchanged unless a reproducible failure requires a separately tested narrow fix.

**Interfaces:** Existing generated palette provides `surface`, `on_surface`, `primary`, `on_primary`, `primary_container`, `error` and `on_error`. Existing `ml4w-wallpaper`/GTK listener regenerate colors and restart Walker only in QS mode. Kitty consumes generated `colors-matugen.conf` and its existing SIGUSR1 hook.

- [ ] Add failing tests that all Walker color aliases resolve to generated roles rather than fixed hex, while imports/layout/providers stay unchanged; reuse desktop-stack guard tests for inactive-mode suppression.
- [ ] Map remaining static text/accent/error definitions, without changing sizing/opacity/provider configuration. Do not install new watchers or dependencies.
- [ ] Run `python3 -B -m unittest discover -s tests/qs_lightweight -p 'test_*.py'` and `python3 -B -m unittest discover -s tests/desktop_stack -p 'test_*.py'`; require all pass.
- [ ] Verify Kitty palette/reload in a scratch terminal, not by typing into the working terminal. If it works, document zero Kitty configuration changes. Commit scoped files/tests/report.

### Task 4: Controlled live acceptance and scoped backup

**Files:** Update the report; refresh Git-ignored exact snapshot through existing recovery tooling. No broad legacy manifest/README refresh.

- [ ] Privately checkpoint live files before any edits; save fingerprints of unrelated dirty paths. Use existing file-only recovery mechanisms, not broad Git restore/reset operations.
- [ ] Run all new tests, all existing QS statusbar fixtures that apply, desktop-stack/migration/curated-restore suites and parser checks. Mark legitimate live-only skips explicitly; never treat a skip as a pass.
- [ ] With prior live-test authorization, switch to QS once; verify main/secondary bars, GPU/VRAM against the same cache and title changes on real focus events. Inspect logs/screenshots privately.
- [ ] Trigger one controlled wallpaper/theme change through the existing hook, verify Walker and scratch Kitty update, then restore selected wallpaper/theme preferences. Confirm no extra resident processes. Record a short resource sample with the same limitations as earlier measurements.
- [ ] Return to Pleamar, verify seven scenes/zero QS leftovers and unchanged saved preferences. Refresh/verify the current private snapshot and isolated recovery; preserve earlier snapshots.
- [ ] Confirm only the explicitly mapped changes are committed, original PR unchanged, unrelated dirty fingerprints unchanged, and no private evidence staged. Independent review remains unavailable unless the configured quota is restored; report inline review honestly.
