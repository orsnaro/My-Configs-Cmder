-- Personal GlazeWM-style additions. Loaded after ML4W's own bindings.
-- Workspace layout (numeric IDs: this fork's Lua dispatcher only takes numbers).
-- Display names live in quickshell StatusbarApp/WorkspacesModule.qml.
-- Center (DP-2): 1 main + 9 gaming. Left Samsung (HDMI-A-2): 2 work .. 7 others.
-- Right (DP-1): 8 terminals. Nothing is routed to 1:main by default.
local workspaces = {
    { id = 1, monitor = "DP-2",     key = "grave" }, -- grave is just the back-tick '`'
    { id = 2, monitor = "HDMI-A-2", key = "1" },
    { id = 3, monitor = "HDMI-A-2", key = "2" },
    { id = 4, monitor = "HDMI-A-2", key = "3" },
    { id = 5, monitor = "HDMI-A-2", key = "4" },
    { id = 6, monitor = "HDMI-A-2", key = "5" },
    { id = 7, monitor = "HDMI-A-2", key = "F1" },
    { id = 8, monitor = "DP-1",     key = "F2" },
    { id = 9, monitor = "DP-2",     key = "F3" },
}

for _, ws in ipairs(workspaces) do
    hl.workspace_rule({ workspace = tostring(ws.id), monitor = ws.monitor })
    hl.bind("ALT + " .. ws.key, hl.dsp.focus({ workspace = ws.id }),
        { description = "Focus workspace " .. ws.id })
    hl.bind("ALT + SHIFT + " .. ws.key,
        hl.dsp.window.move({ workspace = ws.id, follow = true }),
        { description = "Move window and follow to workspace " .. ws.id })
end
hl.bind("ALT + D", hl.dsp.focus({ workspace = "previous" }),
    { description = "Focus previous workspace" })

hl.bind("ALT + X", hl.dsp.window.fullscreen({ mode = "maximized", action = "toggle" }),
    { description = "Toggle maximize without hiding the bar" })
hl.unbind("SUPER + Q")
hl.bind("CTRL + SHIFT + W", hl.dsp.exec_cmd("~/.config/hypr/scripts/killactive.sh"),
    { description = "Close focused window" })
hl.unbind("SUPER + F")
hl.bind("ALT + F", hl.dsp.window.fullscreen({ mode = "fullscreen", action = "toggle" }),
    { description = "Toggle fullscreen" })
hl.bind("ALT + SHIFT + SPACE", hl.dsp.window.float({ action = "toggle" }),
    { description = "Toggle tiled/floating window" })
hl.bind("ALT + M", hl.dsp.exec_cmd("~/.local/bin/glaze-minimize hide"),
    { description = "Hide active window" })
hl.bind("ALT + SHIFT + M", hl.dsp.exec_cmd("~/.local/bin/glaze-minimize restore-all"),
    { description = "Restore all minimized windows to their original workspaces" })

-- Alt+J/K/L/I everywhere: Kitty panes own these keys when a Kitty
-- window is focused (original event passes through, no reinjection); otherwise they focus
-- Hyprland windows first, then adjacent monitors (including empty desktops).
-- Stop at the outer monitor edge instead of cycling.
local function visible_workspaces()
    local mons = hl.get_monitors()
    if mons == nil then return nil end
    local vis = {}
    for _, m in ipairs(mons) do
        local ok, ws = pcall(function() return m.active_workspace end)
        if ok and ws ~= nil then
            local ok2, id = pcall(function() return ws.id end)
            if ok2 and id ~= nil then vis[id] = true end
        end
    end
    return vis
end
local function window_in_direction(from, letter)
    local fx = from.at.x + from.size.x / 2
    local fy = from.at.y + from.size.y / 2
    local vis = visible_workspaces()
    if vis == nil then return true end
    local windows = hl.get_windows()
    if windows == nil then return true end
    for _, c in ipairs(windows) do
        local ok, found = pcall(function()
            if vis[c.workspace.id] ~= true then return false end
            local cx = c.at.x + c.size.x / 2
            local cy = c.at.y + c.size.y / 2
            local x_overlap = c.at.x < from.at.x + from.size.x
                and c.at.x + c.size.x > from.at.x
            local y_overlap = c.at.y < from.at.y + from.size.y
                and c.at.y + c.size.y > from.at.y
            if letter == "J" then
                return cx < fx and y_overlap
            elseif letter == "L" then
                return cx > fx and y_overlap
            elseif letter == "I" then
                return cy < fy and x_overlap
            else
                return cy > fy and x_overlap
            end
        end)
        if ok and found then return true end
    end
    return false
end
-- Single gate for outward moves (Hyprland binds and kitty's edge
-- fallthrough alike): windows first, adjacent monitors second, never cycle.
function checked_focus(direction, expected_pid, expected_address)
    local letters = { left = "J", right = "L", up = "I", down = "K" }
    local monitor_directions = { left = "l", right = "r", up = "u", down = "d" }
    local letter = letters[direction]
    if letter == nil then return end
    local w = hl.get_active_window()
    if expected_pid ~= nil then
        if w == nil or w.pid ~= expected_pid then return end
        if w.class ~= "kitty" and w.class ~= "quake-kitty" then return end
    end
    if expected_address ~= nil and (w == nil or w.address ~= expected_address) then return end
    if w ~= nil and window_in_direction(w, letter) then
        hl.dispatch(hl.dsp.focus({ direction = direction }))
        return
    end
    -- Native directional lookup returns nil at the edge; it never wraps.
    local monitor = hl.get_monitor(monitor_directions[direction])
    if monitor ~= nil then
        hl.dispatch(hl.dsp.focus({ monitor = monitor.id }))
    end
end
for _, pair in ipairs({
    { "J", "left" }, { "L", "right" }, { "I", "up" }, { "K", "down" },
}) do
    local letter, direction = pair[1], pair[2]
    hl.bind("ALT + " .. direction, hl.dsp.focus({ direction = direction }),
        { description = "Focus window " .. direction })
    -- ALT+letters: Kitty panes own them while a Kitty window is focused
    -- (original event passes through, no reinjection, so pane move + edge fallthrough apply);
    -- anywhere else they focus Hyprland windows, stopping at the edge.
    local opts = { description = "Focus window " .. direction .. " (Kitty panes first)" }
    hl.bind("ALT + " .. letter, function()
        local w = hl.get_active_window()
        if w ~= nil and (w.class == "kitty" or w.class == "quake-kitty") then
            return { pass_event = true }
        end
        checked_focus(direction)
    end, opts)
    -- SHIFT+ALT letters move; SHIFT+ALT arrows still focus.
    hl.bind("ALT + SHIFT + " .. letter,
        hl.dsp.exec_cmd("~/.local/bin/glaze-move-window " .. direction),
        { description = "Move window " .. direction })
    hl.bind("ALT + SHIFT + " .. direction, hl.dsp.focus({ direction = direction }),
        { description = "Focus window " .. direction })
    -- CTRL+ALT+SHIFT (letters only): focus Hyprland windows.
    hl.bind("CTRL + ALT + SHIFT + " .. letter, hl.dsp.focus({ direction = direction }),
        { description = "Focus window " .. direction })
end
-- NOTE: ALT+J/K/L/I are bound above as focus-with-Kitty-passthrough
-- (not free); no CTRL+ALT+SHIFT+arrow binds (quad focus is letters-only
-- by request). CTRL+ALT+J/K/L/I (no SHIFT) stays free for in-terminal
-- pane resize.

for _, spec in ipairs({
    { "U", "width", -2 }, { "P", "width", 2 },
    { "O", "height", 2 }, { "H", "height", -2 },
}) do
    hl.bind("ALT + SHIFT + " .. spec[1],
        hl.dsp.exec_cmd("~/.local/bin/glaze-resize-window " .. spec[2] .. " " .. spec[3]),
        { description = "Resize window " .. spec[2] .. " by " .. spec[3] .. "%" })
end

hl.bind("ALT + SHIFT + R", hl.dsp.exec_cmd("~/.local/bin/glaze-reset"),
    { description = "Reload and return assigned apps to their workspaces" })
hl.bind("SUPER + grave", hl.dsp.exec_cmd("~/.local/bin/glaze-quake"),
    { description = "Toggle Quake terminal on pointer monitor" })
-- Window picker alias: SUPER+Tab stays in default.lua; ALT+Tab runs the same toggle.
hl.bind("ALT + Tab", hl.dsp.exec_cmd("~/.local/bin/qs-lazy-toggle ~/.local/share/quickshell-overview overview toggle"),
    { description = "Open Select Window Menu" })

-- Preserve ML4W's statusbar focus action under a new key.
hl.unbind("SUPER + SPACE")
hl.bind("SUPER + CTRL + SPACE", hl.dsp.exec_cmd("qs ipc call statusbar focus"),
    { description = "Focus the statusbar" })
hl.bind("SUPER + R", hl.dsp.exec_cmd("rofi -show run -i -replace"),
    { description = "Run a command" })
hl.bind("SUPER + SUPER_L", hl.dsp.exec_cmd("~/.config/hypr/scripts/launcher.sh"),
    { release = true, description = "Open app list with bare Super" })
hl.bind("SUPER + period", hl.dsp.exec_cmd("rofimoji --action type copy"),
    { description = "Emoji picker (Win-style)" })

-- Keyboard layout switch: SUPER+Space toggles us/ara (SHIFT+SPACE freed:
-- it fired while typing and is problematic).
-- Uses hyprctl switchxkblayout so ALT+SHIFT+keys (move/resize) keep working.
-- XKB group toggles would eat those combos or hijack Caps Lock, so input.lua leaves kb_options empty.
-- SUPER+RETURN restored to terminal (default); layout moved to SUPER+SPACE, rofi run moved to SUPER+R.
hl.unbind("SHIFT + SPACE") -- keep old layout switch freed
hl.unbind("SUPER + RETURN") -- clear default.lua duplicate, single terminal below
hl.bind("SUPER + SPACE", hl.dsp.exec_cmd("~/.local/bin/hypr-switch-xkblayout"),
    { description = "Switch keyboard layout us/ara (Super+Space)" })
hl.bind("SUPER + RETURN", hl.dsp.exec_cmd("~/.config/ml4w/settings/terminal.sh"),
    { description = "Open the terminal" })
hl.bind("ALT + RETURN", hl.dsp.exec_cmd("~/.config/ml4w/settings/terminal.sh"),
    { description = "Open the terminal" })

-- One destination map is shared with the manual reset. Exact class matching
-- deliberately excludes Quake, ML4W helper terminals and application dialogs.
local apps = assert(io.open(os.getenv("HOME") .. "/.config/hypr/glaze-apps.tsv", "r"))
for line in apps:lines() do
    local class, workspace = line:match("^([^#\t][^\t]*)\t([1-9])$")
    if class then
        -- IDs in this map use only letters, digits, dots and hyphens; in a
        -- regex hyphens outside brackets are already literal.
        local escaped = class:gsub("%.", "\\.")
        hl.window_rule({
            name = "glaze-app-" .. class,
            match = { class = "^" .. escaped .. "$", modal = false, float = false },
            workspace = workspace .. " silent",
        })
    end
end
apps:close()

hl.window_rule({
    name = "glaze-quake",
    match = { class = "^quake-kitty$" },
    workspace = "special:quake silent",
    float = true,
    size = { "monitor_w*0.8", "monitor_h*0.54" },
    move = { "monitor_w*0.1", "80" },
})

-- PrtSc screenshots (no modifier needed)
-- Disable slide/fade for slurp "selection" layer, else grim captures
-- the teardown animation as a translucent band (2/3 overlay on small areas).
hl.layer_rule({ name = "noanim-selection", match = { namespace = "^selection$" }, no_anim = true })
hl.bind("PRINT", hl.dsp.exec_cmd("~/.config/hypr/scripts/screenshot.sh --instant-area"),
    { description = "PrtSc: instant area screenshot" })
hl.bind("SHIFT + PRINT", hl.dsp.exec_cmd("~/.config/hypr/scripts/screenshot.sh --instant"),
    { description = "Shift+PrtSc: instant fullscreen screenshot" })

-- Float file managers and small utilities (Hyprland-only, survives ML4W updates)
hl.window_rule({ name = "float-dolphin", match = { class = "^(dolphin|org.kde.dolphin)$" }, float = true, center = true, size = "1100 700" })
hl.window_rule({ name = "float-nautilus", match = { class = "^(nautilus|org.gnome.Nautilus)$" }, float = true, center = true, size = "1100 700" })
hl.window_rule({ name = "float-ark", match = { class = "^(ark|org.kde.ark)$" }, float = true, center = true, size = "800 600" })
hl.window_rule({ name = "float-fileroller", match = { class = "^(file-roller|org.gnome.FileRoller)$" }, float = true, center = true, size = "800 600" })
-- Brave Task Manager reports no window class; match its title instead.
hl.window_rule({ name = "float-brave-task-manager", match = { title = "^Task Manager - Brave$" }, float = true, center = true })
-- Brave Google OAuth popup shares brave-browser class with main windows.
-- Static float evaluates once at open when title==initialTitle==Untitled,
-- so matching final "Sign in" title can never fire. Untitled initialTitle
-- distinguishes popups from main windows (New Tab - Brave).
hl.window_rule({ name = "float-brave-google-signin", match = { class = "^brave-browser$", initial_title = "^Untitled - Brave$" }, float = true, center = true, size = "600 700" })
-- Steam Settings dialog shares the main client's "steam" class; match its title instead.
hl.window_rule({ name = "float-steam-settings", match = { class = "^steam$", title = "Settings$" }, float = true, center = true })
-- Obsidian Settings shares the main client's class; float it on the current
-- workspace/monitor instead of dragging it to workspace 4 with the main window.
hl.window_rule({ name = "float-obsidian-settings", match = { class = "^(obsidian|md.obsidian.Obsidian)$", title = "Settings" }, float = true, center = true, size = "1000 700" })

-- Hyprland-only boot apps (NOT ~/.config/autostart, so KDE is unaffected).
-- Workspace routing comes from glaze-apps.tsv silent rules.
hl.on("hyprland.start", function()
    hl.exec_cmd("kitty")
    hl.exec_cmd("~/.local/bin/glaze-obsidian-notes")
    hl.exec_cmd("~/.local/bin/glaze-discord")
    hl.exec_cmd("~/.local/bin/albion-data-watch")
end)

-- Focus overrides: later rules win over the silent TSV ones above.
-- Code and Kate jump to work (2) + focus; everything else opens silently
-- except the retargeted browser/terminal/notes overrides below.
hl.window_rule({ name = "focus-code", match = { class = "^(code|code-oss)$" }, workspace = "2" })
hl.window_rule({ name = "focus-kate", match = { class = "^(kate|org.kde.kate)$" }, workspace = "2" })
hl.window_rule({ name = "focus-browser", match = { class = "^(brave-browser|firefox)$" }, workspace = "3" })
hl.window_rule({ name = "focus-term", match = { class = "^(kitty|konsole|org.kde.konsole|Alacritty)$" }, workspace = "8" })
hl.window_rule({ name = "focus-notes", match = { class = "^(obsidian|md.obsidian.Obsidian)$", modal = false, float = false }, workspace = "4" })
hl.window_rule({ name = "focus-vortex", match = { class = "^vortex\\.exe$"}, workspace = "9", float = true, size = "1600 900", center = true })

-- Lutris / Wine / Proton games (workspace 9 = gaming).
-- Every Windows exe reports its window class as "<name>.exe" (verified
-- with winecfg.exe), so one pattern covers all 40+ Wine Lutris titles
-- without listing each game. Steam game windows use class steam_app_<id>.
-- Games take focus (plain "9", not silent) and float so windowed games
-- are never force-tiled.
hl.window_rule({ name = "gaming-wine-exe", match = { class = "\\.exe$" }, workspace = "9", float = true })
hl.window_rule({ name = "gaming-steam-app", match = { class = "^steam_app_" }, workspace = "9", float = true })
hl.window_rule({ name = "gaming-cemu", match = { class = "^[Cc]emu$" }, workspace = "9", float = true })

-- Focus follows mouse, mouse doesn't follow focus
hl.config({ cursor = { no_warps = true } })
