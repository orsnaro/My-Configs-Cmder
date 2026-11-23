-- Verify Firefox Taskbar Tab windows route to their intended workspaces.
-- Parallel to Brave rules; Brave rows are asserted unchanged as regression guards.
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

local function anchored(class)
    return "^" .. class:gsub("%.", "\\.") .. "$"
end

-- Firefox Taskbar Tabs get distinct WM classes (firefox.webapp-<id>), so the
-- shared TSV emits exact-class rules for them.
local taskbar = {
    { id = "firefox.webapp-0c68c6e0-91ba-41a6-9a44-3b8149802af5", ws = "6 silent", name = "Gmail" },
    { id = "firefox.webapp-72b06082-7cf0-4264-8d6b-e101ea94f466", ws = "5 silent", name = "Discord" },
    { id = "firefox.webapp-9e863039-c56e-4c31-a966-52960c83b83a", ws = "8 silent", name = "Jellyfin" },
    { id = "firefox.webapp-c2ce0393-a858-42a0-82f6-779b2ac8fd8f", ws = "8 silent", name = "Spotify" },
    { id = "firefox.webapp-e682f68e-eb4a-4f75-b5bd-ecd72f332d09", ws = "8 silent", name = "CasaOS" },
}
for _, app in ipairs(taskbar) do
    local name = "glaze-app-" .. app.id
    local rule = assert(rules[name], "missing taskbar-tab route: " .. name)
    assert(rule.match.class == anchored(app.id), name .. " must match one exact anchored class")
    assert(rule.match.float == false and rule.match.modal == false,
        name .. " must exclude floating windows and modal dialogs")
    assert(rule.workspace == app.ws, name .. " must route to workspace " .. app.ws)
    assert(rule.float == nil and rule.size == nil and rule.move == nil,
        name .. " must not force floating or override geometry")
end

-- Spotify web-app window focuses workspace 8 (parity with the Brave Spotify window's behavior).
local focus_spotify = assert(rules["focus-firefox-taskbar-spotify"],
    "missing Spotify taskbar-tab focus rule: focus-firefox-taskbar-spotify")
assert(focus_spotify.match.class == anchored("firefox.webapp-c2ce0393-a858-42a0-82f6-779b2ac8fd8f"),
    "Spotify focus rule must match one exact anchored class")
assert(focus_spotify.workspace == "8", "Spotify taskbar tab must focus workspace 8")

-- Ordinary Firefox browser windows stay on search (ws3); previews starting with
-- "aerc Mail preview" are excluded from the class-only route via negative: title.
local browser = assert(rules["focus-browser"], "missing ordinary Firefox route")
assert(browser.match.class == "^(brave-browser|firefox)$", "ordinary Firefox route must cover Brave+Firefox")
assert(browser.match.title == "negative:^aerc Mail preview", "preview windows must be excluded from ws3 routing")
assert(browser.workspace == "3", "ordinary Firefox windows must keep routing to search")
assert(rules["glaze-app-firefox"] == nil, "plain firefox must not get a TSV route: previews share its class")

-- Brave regression guards (parallel phase keeps them; cutover swap happens later).
local brave_browser = assert(rules["glaze-app-brave-browser"], "missing ordinary Brave route")
assert(brave_browser.match.class == "^brave-browser$", "ordinary Brave route must stay exact")
assert(brave_browser.workspace == "3 silent", "ordinary Brave windows must keep routing to search")
local brave_discord = assert(rules["glaze-app-brave-discord.com__channels_@me-Default"],
    "missing Brave Discord route")
assert(brave_discord.workspace == "5 silent", "Brave Discord must keep routing to chat")
local brave_spotify = assert(rules["glaze-app-brave-open.spotify.com__-Default"],
    "missing Brave Spotify route")
assert(brave_spotify.workspace == "8 silent", "Brave Spotify must keep routing to others")

print("PASS: Firefox taskbar tabs route 6/5/8/8/8; Spotify focuses 8; ordinary Firefox stays 3; Brave guards unchanged")
