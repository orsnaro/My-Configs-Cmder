-- Exercise the actual runtime startup script at the compositor API boundary.
local hooks, timers, commands, rules = {}, {}, {}, {}
local mail = { address = "0xaaa", class = "aerc-mail", workspace = { id = 6 }, floating = false }
local options = {
    ["general.layout"] = "dwindle",
    ["dwindle.use_active_for_splits"] = true,
    ["dwindle.permanent_direction_override"] = false,
}
hl = {
    get_config = function(key) return options[key] end,
    get_window = function(selector)
        assert(selector == "address:0xaaa")
        return mail
    end,
    window_rule = function(spec)
        assert(spec.name == "glaze-mail-preview-startup")
        assert(spec.workspace == "6" and spec.float == false)
        local rule = { spec = spec, enabled = true }
        function rule:set_enabled(value) self.enabled = value end
        rules[#rules + 1] = rule
        return rule
    end,
    on = function(event, callback)
        local sub = { callback = callback, removed = false }
        function sub:remove() self.removed = true end
        hooks[event] = sub
        return sub
    end,
    timer = function(callback, opts)
        assert(opts.type == "oneshot" and opts.timeout == 10000)
        local timer = { callback = callback, enabled = true }
        function timer:set_enabled(value) self.enabled = value end
        timers[#timers + 1] = timer
        return timer
    end,
    dsp = {
        focus = function(spec) assert(spec.window == mail); return "focus-mail" end,
        layout = function(action)
            assert(action == "preselect r" or action == "preselect none", "Post-open movement forbidden")
            return action
        end,
    },
    dispatch = function(action) commands[#commands + 1] = action end,
}

local register = assert(load(arg[1]))
register()
local early, opened = hooks["window.open_early"], hooks["window.open"]
assert(early and opened)
local invocation = string.rep("3", 32)
local identifier = string.rep("7", 32)
local prefix = "brave-__run_user_1000_glaze-mail-preview_" .. invocation .. "_"
local preview = { address = "0xbbb", class = prefix .. identifier .. "_blocked.html-Default" }
for _, class in ipairs({ "brave-browser", "brave-open.spotify.com__-Default",
                         "brave-__other_" .. identifier .. "_blocked.html-Default",
                         prefix .. "short_images.html-Default",
                         prefix .. identifier .. "_raw.html-Default",
                         prefix:gsub(invocation, string.rep("4", 32)) .. identifier .. "_images.html-Default" }) do
    early.callback({ address = "0xccc", class = class, title = "aerc Mail preview " .. identifier })
end
assert(#commands == 0, "Unrelated window consumed a split")
early.callback(preview)
assert(#commands == 2 and commands[1] == "focus-mail" and commands[2] == "preselect r")
opened.callback({ address = "0xccc", class = "brave-browser" })
assert(#commands == 2, "Unrelated open reset a split")
opened.callback(preview)
assert(#commands == 3 and commands[3] == "preselect none")

mail.workspace.id = 3
early.callback(preview)
assert(#commands == 3, "Stale mail workspace used")
mail.workspace.id = 6
mail.floating = true
early.callback(preview)
assert(#commands == 3, "Floating mail changed")
mail.floating = false

register()
assert(early.removed and opened.removed and not rules[1].enabled and not timers[1].enabled)
timers[2].callback()
assert(hooks["window.open_early"].removed and hooks["window.open"].removed and not rules[2].enabled)
print("startup scope, before-layout split, no movement, replacement and timeout verified")
