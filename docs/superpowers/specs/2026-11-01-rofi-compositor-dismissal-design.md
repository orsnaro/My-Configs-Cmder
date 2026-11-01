# Rofi cross-monitor dismissal through Hyprland

## Agreed outcome

The user chose Hyprland callbacks rather than a privately patched Rofi binary.
This extends the already approved startup-reliability work: both shortcuts should
open one responsive picker, deliberate repeated shortcuts should close it, and
an outside click must dismiss a **fully rendered** picker on another monitor.
Keyboard focus remains with Rofi; pointer movement alone must not dismiss it.
There must be no additional permanent daemon or global desktop animation change.
Keep arithmetic, relevance/recency, the emoji grid, clipboard previews and safe
cancellation intact. Test only with synthetic clipboard data and intercepted copy.

## Why the existing approach is invalid

Installed Hyprland is 0.56.2, commit
`efb50993780079460b0cbed1363e2166a2de1d9f`. Its input manager checks exclusive
keyboard layer surfaces before ordinary pointer-only overlays and falls back to
the exclusive surface even outside its output. Rofi 2.0 requests exclusive
keyboard interactivity unconditionally. Therefore the transparent helper cannot
reliably receive another-monitor clicks once Rofi is actually mapped.

Wayland traces confirmed a click going to Rofi with negative local coordinates,
with no pointer-enter/button event delivered to the guard. A controlled probe
using the **original** saved wrapper, original guard and original animations also
failed after the menu was fully rendered. Earlier fast cross-monitor tests clicked
before exclusive input became active and gave false confidence; preserve that
correction rather than weakening the strengthened tests.

Sources checked against the installed versions:
- [Hyprland input routing](https://github.com/hyprwm/Hyprland/blob/efb50993780079460b0cbed1363e2166a2de1d9f/src/managers/input/InputManager.cpp#L454-L465)
- [Hyprland mouse binds and callback results](https://github.com/hyprwm/Hyprland/blob/efb50993780079460b0cbed1363e2166a2de1d9f/src/managers/KeybindManager.cpp)
- [Lua layer properties](https://github.com/hyprwm/Hyprland/blob/efb50993780079460b0cbed1363e2166a2de1d9f/src/config/lua/objects/LuaLayerSurface.cpp)
- [Lua binding options](https://github.com/hyprwm/Hyprland/blob/efb50993780079460b0cbed1363e2166a2de1d9f/src/config/lua/bindings/LuaBindingsToplevel.cpp)
- [Rofi keyboard interactivity](https://github.com/davatorium/rofi/blob/2.0.0/source/wayland/display.c)

## Chosen architecture

### 1. Short compositor-side callbacks

A small reusable Hyprland Lua module installs disabled left/right/middle mouse
button callbacks. They are enabled only for a session registered by the verified
launcher helper. Existing modified mouse shortcuts (Alt/Super drag/resize, etc.)
are left untouched; these callbacks handle ordinary unmodified clicks.

On a button press, query `hl.get_layers({namespace="rofi"})` and
`hl.get_monitor_at_cursor()` in memory. Find a mapped layer with the registered
PID. If its actual monitor differs from the pointer's monitor, consume this
click and asynchronously request PID-checked cancellation. Otherwise return
`{pass_event=true}` so Rofi selection and ordinary mouse behavior work normally.

Do not read files, run shell commands, poll, or do synchronous IPC inside the
common compositor callback path. An outside cancellation launches one short-lived
helper; no process starts for ordinary clicks, clicks inside Rofi, or movement.
Do not alter keyboard interactivity, focus monitors, or activate an underlying app.

### 2. Verified session registration and cancellation

Keep the existing small native helper, but replace its ineffective transparent
surfaces with session registration and PID-descriptor lifetime watching. Once it
has validated the exact launcher PID, it registers that numeric PID through one
Hyprland Lua IPC call and releases the inherited startup lock. It then blocks on
the Rofi pidfd without periodic polling. On exit it unregisters only that same PID,
so a late cleanup cannot clear a newer session.

`layer.closed` also clears the matching Lua session promptly. On config reload,
inspect existing mapped Rofi layers and run the one-shot identity helper to re-register
only genuine launcher instances. No reload-time process is needed when Rofi is
closed. The native helper remains on-demand and leaves no process after closing.

The identity helper used for cancellation/re-registration must:
- Accept only an integer PID greater than one; open its pidfd before inspection.
- Verify process UID and executable name `rofi`.
- Require adjacent `-pid` and absolute PID-file arguments in `/proc/PID/cmdline`.
- Verify the PID file is a regular non-symlink named `rofi.pid`, in an owned
  private directory; its content must equal the supplied PID. Read without
  following symlinks or blocking on special files.
- Require the launcher's valid mode/monitor metadata so an unrelated Rofi is not
  adopted just because it uses a PID file.
- Signal through the verified pidfd only. Stale, foreign, invalid or already-dead
  instances are a safe no-op, never a reason to launch or kill another process.

Only validated integer PIDs appear in shell/IPC commands. Do not interpolate query
text, clipboard data or application names into commands. Quote fixed helper paths.

### 3. Retained startup and animation work

Retain the tested nonblocking startup-lock handoff. Requests overlapping startup
return promptly rather than competing for Rofi's PID file; after readiness a
deliberate repeated shortcut still closes it. Preserve the caller's umask.

Retain the measured Rofi-only no-animation rule. Its crossed five-pair A/B test
reduced median stable center-border appearance from 237.2 ms to 113.4 ms. This is
not an assertion that every cold launch is fast: an initial 3794.6 ms baseline
sample and a 729.7 ms sample in the later 30-cycle test remain recorded. Do not
silently add stale application caches, remove fonts, or change power settings.

## Integration and recovery

- Use branch `fix/rofi-startup-reliability`; preserve publication commit `0623ee1`
  and the original dirty checkout. No automatic push, PR change or merge.
- Install the Lua module via both restoring Hyprland overlays without replacing
  later user rules. Backups carry source only and rebuild the native helper.
- Retire only the now-unused public Wayland guard/protocol build assets after the
  replacement works. Original private recovery snapshots and benchmarks remain.
- Snapshot newly changed live paths before deployment. Update only the separate
  permanent recovery manifest's expected-current fields, preserving restore
  targets and original snapshots; run its read-only preflight.
- Keep main's unrelated TLS production/test and stale TV-helper checksum unchanged
  and disclosed. Do not claim the entire repository/real Pleamar restore is green.

## Acceptance tests

1. Unit/Lua tests for inactive pass-through, same-monitor pass-through, mapped
   owned PID + other-monitor consume/cancel, foreign/stale PID no-op, and cleanup
   of an older session without clearing a newer one. Test callback enable/disable
   and config-reload recovery, including no process on idle clicks.
2. Native/process tests for PID identity, startup FD handoff, owner exit,
   registration failure, descriptor cleanup, and no inherited lock in the picker.
3. Live cross-monitor tests must wait for the owned picker's painted border and
   then confirm it remains open before clicking. Cover apps, emoji and clipboard
   against both other outputs, with pointer-only movement leaving it open. Check
   keyboard focus/typing still reaches Rofi after pointer movement.
4. Verify left/right/middle outside clicks, same-monitor cancellation, deliberate
   toggle close, rapid starts, safe app launching, arithmetic and image preview.
   No click may activate an underlying application or write to the real clipboard.
5. After every close: no picker/helper surfaces or running helpers; mouse buttons
   work normally. Exercise config reload while open, mode changes and failed
   startup. Do not label virtual-pointer/command tests as physical keyboard tests.
6. Run all active repository suites, native builds, Lua tests, isolated restores,
   changed-source parsing, inventories and whitespace checks. Report the accepted
   baseline TLS failure and existing GUI skip separately from new failures.

## Non-goals and review limits

No privately patched Rofi/Hyprland binary, input plugin, global mouse remapping,
hover dismissal, resident event reader, KDE changes or unrelated security fixes.
Hardware hotplug/reboot and physical global shortcuts are not automatically
claimed tested. Inline review is the approved fallback after the configured free
subagent's quota failure; it is not an independent review.
