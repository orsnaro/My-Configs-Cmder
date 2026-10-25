-- Permanent Vitreus key binds. Loaded from hyprland.lua after custom.lua, so
-- these win over the earlier bindings without touching unrelated keys.
--
-- Preserved on purpose:
--   SUPER + Space  -> your existing keyboard-layout switch (custom.lua)
--   SUPER + B      -> your existing Brave shortcut (custom.lua)
--   every other binding not named here
local say = 'PATH="$HOME/.local/bin:$PATH" pleamar --say vitreus'

-- Bare Meta opens Vitreus's own launcher.
hl.unbind("SUPER + SUPER_L")
hl.bind("SUPER + SUPER_L", hl.dsp.exec_cmd(say .. ' "emit launch_toggle"'),
    { description = "Open the Vitreus launcher", release = true })

-- Both window-picker shortcuts use Vitreus's overview, not the old Quickshell one.
hl.unbind("ALT + Tab")
hl.bind("ALT + Tab", hl.dsp.exec_cmd(say .. ' "emit ov_toggle"'),
    { description = "Open the Vitreus window picker" })
hl.unbind("SUPER + Tab")
hl.bind("SUPER + Tab", hl.dsp.exec_cmd(say .. ' "emit ov_toggle"'),
    { description = "Open the Vitreus window picker" })

-- Settings remains reachable with Shift; plain Super+Space is left alone.
hl.unbind("SUPER + SHIFT + Space")
hl.bind("SUPER + SHIFT + Space", hl.dsp.exec_cmd(say .. ' "emit settings_toggle"'),
    { description = "Open Vitreus Settings" })

hl.unbind("SUPER + W")
hl.bind("SUPER + W", hl.dsp.exec_cmd(say .. ' "emit wp_picker_toggle"'),
    { description = "Open or close the Vitreus wallpaper picker" })

-- Lock goes through the shared helper: the Vitreus lock scene when its socket is up, Hyprlock otherwise.
hl.unbind("SUPER + L")
hl.bind("SUPER + L", hl.dsp.exec_cmd("$HOME/.config/pleamar/shells/vitreus/bin/vitreus-lock"),
    { description = "Lock the session (Vitreus lock screen, Hyprlock fallback)" })

hl.unbind("SUPER + D")
hl.bind("SUPER + D", hl.dsp.exec_cmd(say .. ' "emit desk_toggle"'),
    { description = "Open or close the Vitreus Desk" })
hl.unbind("SUPER + SHIFT + D")
hl.bind("SUPER + SHIFT + D", hl.dsp.exec_cmd(say .. ' "emit dash_toggle"'),
    { description = "Open or close the Vitreus dashboard" })

hl.unbind("Print")
hl.bind("Print", hl.dsp.exec_cmd(say .. ' "emit shot 0"'),
    { description = "Capture a region" })
hl.unbind("SHIFT + Print")
hl.bind("SHIFT + Print", hl.dsp.exec_cmd(say .. ' "emit shot 1"'),
    { description = "Capture the whole screen" })
hl.unbind("SUPER + C")
hl.bind("SUPER + C", hl.dsp.exec_cmd(say .. ' "emit shot 0"'),
    { description = "Capture a region" })
hl.unbind("SUPER + SHIFT + C")
hl.bind("SUPER + SHIFT + C", hl.dsp.exec_cmd(say .. ' "emit rec_toggle"'),
    { description = "Start or stop a recording" })

hl.unbind("XF86MonBrightnessUp")
hl.bind("XF86MonBrightnessUp", hl.dsp.exec_cmd([[PATH="$HOME/.local/bin:$PATH"; f=$(brightnessctl -e4 -n2 -m set 5%+ | awk -F, '{printf "%.4f", $3/$5}'); pleamar --say vitreus "emit bright_key $f"]]), { locked = true, repeating = true })
hl.unbind("XF86MonBrightnessDown")
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd([[PATH="$HOME/.local/bin:$PATH"; f=$(brightnessctl -e4 -n2 -m set 5%- | awk -F, '{printf "%.4f", $3/$5}'); pleamar --say vitreus "emit bright_key $f"]]), { locked = true, repeating = true })

hl.unbind("SUPER + E")
hl.bind("SUPER + E", hl.dsp.exec_cmd("PATH=\"$HOME/.local/bin:$PATH\" vitreus-files"),
    { description = "Open the home folder" })
