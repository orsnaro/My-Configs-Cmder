-- desktop-stack managed: shared display geometry stays independent of the shell.
local desktop_stack_mode = "pleamar"
local desktop_stack_file = io.open(os.getenv("HOME") .. "/.config/ml4w/settings/desktop-stack", "r")
if desktop_stack_file then
    desktop_stack_mode = (desktop_stack_file:read("*a") or ""):match("^%s*(.-)%s*$")
    desktop_stack_file:close()
end
--    __  _____  _____      __  ____  ____
--   /  |/  / / / / / | /| / / / __ \/ __/
--  / /|_/ / /_/_  _/ |/ |/ / / /_/ /\ \  
-- /_/  /_/____//_/ |__/|__/  \____/___/
--   
-- Advanced configuration for Hyprland

-- FUNCTIONS
require("functions")

-- MONITORS
require("monitors")
require("conf.monitor")

-- INPUT
require("input")

-- GESTURE
require("gestures")

-- AUTOSTART
require("conf.autostart")

-- COLORS
require("colors")

-- CONFIGURATION
require("conf.environment")
require("conf.window")
require("conf.decoration")
require("conf.layout")
require("conf.workspace")
require("conf.misc")
require("conf.keybinding")
require("conf.windowrule")
require("conf.animation")
require("conf.ml4w")

-- CUSTOM
local f = io.open(os.getenv("HOME") .. "/.config/hypr/custom.lua", "r")
if f then
    f:close()
    require("custom")
end

-- PLEAMAR VITREUS
local vitreus_binds = io.open(os.getenv("HOME") .. "/.config/hypr/hypr_vitreus.lua", "r")
if desktop_stack_mode == "pleamar" and vitreus_binds then
    vitreus_binds:close()
    require("hypr_vitreus")
end

-- HYPRMOD
require("hyprland-gui")

-- Vitreus's saved display, Hyprland and border settings. The display and
-- Hyprland files do not exist until Settings keeps something, hence pcall.
pcall(require, "vitreus_monitors")
if desktop_stack_mode == "pleamar" then pcall(require, "vitreus_hypr") end
if desktop_stack_mode == "pleamar" then pcall(require, "vitreus_colors") end
