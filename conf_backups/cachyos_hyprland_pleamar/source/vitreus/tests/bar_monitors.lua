-- Exercise the monitor controller with synthetic services/paths; no desktop commands run.
-- v0.2.0 uses per-monitor copies: selection changes live; only a copy-capacity migration restarts.
local function fixture(opts)
    opts = opts or {}
    local state = { events = {}, commands = {}, saved = {}, fact = {}, text = {}, sed_code = 0, restart_code = 0 }
    local mons = opts.mons or {
        { name = 'HDMI-A-2', x = 0, y = 0, transform = 0 },
        { name = 'DP-2', x = 1366, y = 0, transform = 0 },
        { name = 'DP-1', x = 3926, y = 0, transform = 0 },
    }
    local chosen = opts.pref or 'DP-2'
    local surface = opts.screens or 'screens: each max 3;'
    for i, mon in ipairs(mons) do state.text['screen.' .. (i - 1) .. '.name'] = mon.name end
    local env = setmetatable({
        fact = state.fact,
        text = state.text,
        bar_fx = {},
        bar_mon = {},
        iris_fx = { apply_hypr = function() end },
        on = function(name, fn) state.events[name] = fn end,
        after = function(ms, fn) if ms == 8000 then state.wake = fn end end,
        every = function() end,
        json = { decode = function() return mons end },
        hypr_monitors = function(_, fn) fn('fixture monitors', 0) end,
        sys = {
            ask = function(_, name) assert(name == 'bar.json'); return { screens = chosen } end,
            call = function(_, name, value) state.saved[name] = value end,
        },
        run = function(cmd, args, fn)
            state.commands[#state.commands + 1] = { cmd = cmd, args = args }
            if cmd == 'grep' then fn(surface, 0)
            elseif cmd == 'sed' then fn('', state.sed_code)
            elseif cmd == 'systemctl' then fn('', state.restart_code)
            elseif fn then fn('', 0) end
        end,
    }, { __index = _G })
    local controller = assert(loadfile('logic/bar_monitors.luau', 't', env))()
    controller(function(fn) fn({ conf = '/fixture/conf', data = '/fixture/data' }) end)
    state.commands = {}
    return state
end

local selected = fixture()
selected.events.bar_pick_scr(0)
local saved = selected.saved['bar.json'].screens
assert(#saved == 2 and saved[1] == 'DP-2' and saved[2] == 'HDMI-A-2', 'persist the native multi-selection')
assert(#selected.commands == 0, 'changing per-monitor selection must not restart the whole shell')
assert(selected.fact.bar_lite_hdmi == false and selected.fact.bar_lite_dp1 == true,
       'only the side monitor without a full bar keeps its lite strip')
selected.events.bar_pick_scr(1)
saved = selected.saved['bar.json'].screens
assert(#saved == 1 and saved[1] == 'HDMI-A-2', 'a selected monitor can be removed from the set')
selected.events.bar_pick_scr(0)
assert(#selected.saved['bar.json'].screens == 1, 'the last selected monitor must not be removed')
assert(selected.text.bar_msg == 'The bar needs a monitor.', 'explain why the last bar cannot be hidden')

local migration = fixture({ screens = 'screens: "DP-2";' })
migration.wake()
assert(migration.commands[1].cmd == 'sed', 'migrate the old named surface before requesting restart')
assert(migration.commands[1].args[3]:find('each max 3', 1, true), 'allocate all three connected copies')
local restart = migration.commands[2]
assert(restart and restart.cmd == 'systemctl', 'capacity migration must use the existing service owner')
assert(table.concat(restart.args, ' ') == '--user --no-block restart pleamar.service')
assert(#migration.commands == 2, 'never launch a competing keeper or unmanaged shell')

local write_failed = fixture({ screens = 'screens: "DP-2";' })
write_failed.sed_code = 1
write_failed.wake()
assert(#write_failed.commands == 1, 'a failed surface rewrite must not restart')
assert(write_failed.text.bar_msg == "Couldn't change where the bar shows.", 'surface rewrite failure must be visible')
write_failed.sed_code = 0
write_failed.wake()
assert(write_failed.commands[#write_failed.commands].cmd == 'systemctl', 'a failed rewrite must not leave the selector stuck busy')

local restart_failed = fixture({ screens = 'screens: "DP-2";' })
restart_failed.restart_code = 1
restart_failed.wake()
assert(restart_failed.text.bar_msg == "Couldn't restart the bar service.", 'a failed restart request must be visible')
restart_failed.restart_code = 0
restart_failed.wake()
assert(#restart_failed.commands == 4, 'retrying a rejected capacity migration must be possible')

-- The lite flags follow the active per-monitor selection; All/fallback-All closes both strips.
local dp2 = fixture()
assert(dp2.fact.bar_lite_dp1 == true and dp2.fact.bar_lite_hdmi == true,
       'DP-2 shows the full bar, so both side strips must stay open')

local dp1 = fixture({ pref = 'DP-1' })
assert(dp1.fact.bar_lite_dp1 == false, 'the strip of the monitor running the full bar must close')
assert(dp1.fact.bar_lite_hdmi == true, 'the other side strip stays open when the bar is on DP-1')

local hdmi = fixture({ pref = 'HDMI-A-2' })
assert(hdmi.fact.bar_lite_dp1 == true and hdmi.fact.bar_lite_hdmi == false,
       'HDMI-A-2 shows the full bar, so its own strip must close')

local all = fixture({ screens = 'screens: each max 4;', pref = 'all' })
assert(all.fact.bar_lite_dp1 == false and all.fact.bar_lite_hdmi == false,
       'All/fallback-All must leave no lite strip showing')

local four = fixture({ mons = {
    { name = 'HDMI-A-2', x = 0 }, { name = 'DP-2', x = 1000 },
    { name = 'DP-1', x = 2000 }, { name = 'DP-3', x = 3000 },
} })
four.wake()
assert(four.commands[1].args[3]:find('each max 4', 1, true), 'hot-plug growth must cover all four supported monitors')
assert(four.commands[2].cmd == 'systemctl', 'growth uses the same service owner')

local gone = fixture({ pref = 'HDMI-A-2',
                       mons = { { name = 'DP-2', x = 1366, y = 0, transform = 0 },
                                { name = 'DP-1', x = 3926, y = 0, transform = 0 } } })
assert(gone.fact.bar_lite_dp1 == false and gone.fact.bar_lite_hdmi == false,
       'an unplugged preferred monitor falls back to all, so no lite copy may show')

print('bar monitor live-selection, managed-migration and lite-flag contracts: PASS')
