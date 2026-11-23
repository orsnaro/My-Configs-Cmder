-- qBittorrent's main window must stay tiled while every subwindow floats.
-- All qBittorrent windows share the app_id org.qbittorrent.qBittorrent, so the
-- split is title-based: the main window is "qBittorrent v<version>" (possibly
-- prefixed by [PAUSED] or [D: ...]), every other title is a dialog. The
-- add-torrent dialog is titled with the torrent name and is unparented when
-- launched from outside, so its title cannot be listed explicitly.
local root = os.getenv("HOME") .. "/.config/hypr/"
local rules = {}
local function operation(name)
    return function(arg) return { name = name, arg = arg } end
end

hl = {
    bind = function() end,
    unbind = function() end,
    on = function() end,
    env = function() end,
    exec_cmd = operation("exec"),
    workspace_rule = function() end,
    window_rule = function(rule) rules[rule.name] = rule end,
    layer_rule = function(...) end,
    config = function(...) end,
    dsp = {
        exec_cmd = operation("exec"),
        focus = operation("focus"),
        window = {
            move = operation("move"),
            float = operation("float"),
            fullscreen = operation("fullscreen"),
            resize = operation("resize"),
        },
        workspace = { toggle_special = operation("toggle_special") },
    },
}
dofile(root .. "custom.lua")

local class = "^org\\.qbittorrent\\.qBittorrent$"
local version = ".*qBittorrent v[0-9]+(\\.[0-9]+)+.*"

local main = assert(rules["qbit-main-tiled"],
    "qBittorrent's main window needs an explicit tiled rule")
assert(main.float == false, "the main qBittorrent window must not float")
assert(main.match.class == class,
    "the rule must target the observed Wayland app_id, not the desktop name")
assert(main.match.title == version,
    "the main rule must match 'qBittorrent v<version>', with room for [PAUSED]/speed prefixes")

local dialogs = assert(rules["float-qbit-dialogs"],
    "qBittorrent subwindows need a floating rule")
assert(dialogs.float == true and dialogs.center == true,
    "qBittorrent subwindows should float and center")
assert(dialogs.match.class == class, "the dialog rule must stay scoped to qBittorrent")
assert(dialogs.match.title == ("negative:" .. version),
    "the dialog rule must float every title that is not the main window")

-- Guard against regressing to a class-only float, which would un-tile the main window.
for name, rule in pairs(rules) do
    if rule.match.class == class and rule.float == true then
        assert(rule.match.title ~= nil, name .. " floats the main window too")
    end
end

print("PASS: qBittorrent subwindows float while the main window stays tiled")
