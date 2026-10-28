# Lightweight QS metrics, title and palette

Approved bounded design: the user requested GPU%, VRAM and focused-window title
on the main QS bar, followed by wallpaper-responsive Walker/Kitty colors, with
minimal changes and low resource use. They approved the proposed approach with
"then do next steps" after the previous switching/recovery PR was created.

## Scope

- Extend the existing CPU metrics pill with `GPU 12%` and `VRAM 1.2 GiB` fields.
  Reuse `hypr-sysinfo`'s existing `gpu.usage` and `gpu.vram_used_gb` cache fields
  and the existing three-second fetch cadence. Show an em dash for unavailable
  values; zero is valid. Do not add a collector, process or recurring timer.
- Add the focused-window title after workspaces on the main bar only. Read
  Quickshell's event-driven `ToplevelManager.activeToplevel.title`; use plain
  text, elide long titles, cap at 220 pixels, and collapse on an empty desktop.
  Keep the clock centered and avoid overlap with metrics; no title polling or
  per-window subprocesses. Preserve the two secondary bars.
- Walker already imports Matugen's generated `colors.css`. Map its remaining
  hard-coded normal/accent/error colors to generated palette roles, preserving
  its layout, opacity and providers. Reuse existing mode-gated reload hooks.
- Kitty already includes `colors-matugen.conf`; Matugen already signals it to
  reload. Verify that behavior and leave its configuration unchanged if it
  works. Do not add another palette generator, watcher or daemon.

## Safety and verification

Work on `feat/lightweight-qs-metrics-and-palette`; do not change PR #10. Preserve
unrelated dirty legacy dock backups, README and manifest. Checkpoint live files
before editing and retain config-root symlinks. Mirror changed files into the
existing backup layout, adding only the Walker theme files needed for recovery.
Record exact file paths separately rather than staging the user's dirty legacy
manifest. No broad backup refresh or theme redesign.

Use real offscreen QML behavior tests for unavailable/zero metrics, long/plain
Unicode window titles, title changes/empty desktop and layout constraints.
Test stylesheet palette references and existing reload mode guards. After the
plan is reviewed, perform one controlled QS live check, compare resource use
with the prior short sample, and return to Pleamar unless the user redirects.
Keep screenshots/private evidence out of Git. No automatic push of this new
feature branch; previous push approval concerned the completed switcher PR.

API reference: https://quickshell.org/docs/v0.2.1/types/Quickshell.Wayland/ToplevelManager/
is corroborated by installed Quickshell 0.3.2 QML type metadata (activeToplevel,
title and their change signals). Local collector/template/config files define
the existing metrics and palette contracts.
