-- Verify only the two local apps receive client-only fullscreen rules.
local root = os.getenv("HOME") .. "/.config/hypr/"
local rules = {}
local function operation(name)
    return function(arg) return { name = name, arg = arg } end
end

hl = {
    bind = function() return { set_enabled = function() end } end,
    unbind = function() end,
    on = function() end,
    env = function() end,
    exec_cmd = operation("exec"),
    workspace_rule = function() end,
    window_rule = function(rule) rules[rule.name] = rule end,
    layer_rule = function() end,
    config = function() end,
    animation = function() end,
    get_layers = function() return {} end,
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

local expected = {
    ["tiled-jellyfin-chromeless"] = "^brave-(kdcbgnonmmimiohkdebbbipakbegkkol|192\\.168\\.1\\.12__web_)-Default$",
    ["tiled-casaos-chromeless"] = "^brave-(cdbapkcndmkmbeiedikfcaeelndldoha|192\\.168\\.1\\.12__)-Default$",
}
for name, class in pairs(expected) do
    local rule = assert(rules[name], "missing app-only title-bar rule: " .. name)
    assert(rule.match.class == class, name .. " must match only its installed app and existing shortcut class")
    assert(rule.match.float == false and rule.match.modal == false,
        name .. " must exclude floating windows and modal dialogs")
    assert(rule.fullscreen_state == "0 2", name .. " must keep compositor tiling while full-screening only the client")
    assert(rule.sync_fullscreen == false, name .. " must keep compositor/client states separate")
    assert(rule.workspace == nil and rule.size == nil and rule.move == nil and rule.float == nil,
        name .. " must not override workspace, geometry, or floating mode")
end
-- Workspace routing: the shared TSV must send both installed Brave app IDs
-- and their legacy extension IDs to workspace 8 without forcing float.
local routing = {
    { class = "brave-192.168.1.12__web_-Default", regex = "^brave-192\\.168\\.1\\.12__web_-Default$" },
    { class = "brave-192.168.1.12__-Default", regex = "^brave-192\\.168\\.1\\.12__-Default$" },
    { class = "brave-kdcbgnonmmimiohkdebbbipakbegkkol-Default", regex = "^brave-kdcbgnonmmimiohkdebbbipakbegkkol-Default$" },
    { class = "brave-cdbapkcndmkmbeiedikfcaeelndldoha-Default", regex = "^brave-cdbapkcndmkmbeiedikfcaeelndldoha-Default$" },
}
for _, app in ipairs(routing) do
    local name = "glaze-app-" .. app.class
    local rule = assert(rules[name], "missing workspace route: " .. name)
    assert(rule.match.class == app.regex, name .. " must match one exact anchored class")
    assert(rule.match.float == false and rule.match.modal == false,
        name .. " must exclude floating windows and modal dialogs")
    assert(rule.workspace == "8 silent", name .. " must route to the others workspace silently")
    assert(rule.float == nil and rule.size == nil and rule.move == nil,
        name .. " must not force floating or override geometry")
end
local browser = assert(rules["glaze-app-brave-browser"], "missing ordinary Brave route")
assert(browser.match.class == "^brave-browser$", "ordinary Brave route must stay exact")
assert(browser.workspace == "3 silent", "ordinary Brave windows must keep routing to search")
local count = 0
for name, rule in pairs(rules) do
    if rule.fullscreen_state == "0 2" then
        assert(expected[name], "unexpected client-only fullscreen rule affecting another app: " .. name)
        count = count + 1
    end
end
assert(count == 2, "exactly CasaOS and Jellyfin should receive client-only fullscreen")
print("PASS: CasaOS/Jellyfin route to others; only their title bars hidden; tiling and dialog behavior preserved")
