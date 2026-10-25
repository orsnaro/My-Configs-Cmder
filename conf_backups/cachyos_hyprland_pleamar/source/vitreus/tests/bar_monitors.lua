-- Exercise the monitor controller with synthetic services/paths; no desktop commands run.
-- `opts` rehearses the initial screen: the surface actually running (`screens`), the monitor the
-- machine reports (`mons`) and the pending choice in bar.json (`pref`).
local function fixture(opts)
    opts = opts or {}
    local state = { events = {}, commands = {}, saved = {}, fact = {}, text = {}, sed_code = 0, restart_code = 0 }
    local mons = opts.mons or {
        { name = 'HDMI-A-2', x = 0, y = 0, transform = 0 },
        { name = 'DP-2', x = 1366, y = 0, transform = 0 },
        { name = 'DP-1', x = 3926, y = 0, transform = 0 },
    }
    local chosen = opts.pref or 'DP-2'
    local surface = opts.screens or 'screens: "DP-2";'
    local env = setmetatable({
        fact = state.fact,
        text = state.text,
        bar_fx = {},
        bar_mon = {},
        iris_fx = { apply_hypr = function() end },
        on = function(name, fn) state.events[name] = fn end,
        after = function() end,
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
assert(selected.saved['bar.json'].screens == 'HDMI-A-2', 'the selected monitor must be persisted')
assert(selected.commands[1].cmd == 'sed', 'rewrite the monitor selector before requesting restart')
assert(selected.commands[1].args[3]:find('HDMI-A-2', 1, true), 'the surface must target the selected monitor')
local restart = selected.commands[2]
assert(restart and restart.cmd == 'systemctl', 'monitor changes must restart through the owning service, not a self-quit helper')
assert(table.concat(restart.args, ' ') == '--user --no-block restart pleamar.service',
       'queue the managed service restart without blocking on the process being restarted')
assert(#selected.commands == 2, 'do not launch a competing keeper or unmanaged Pleamar process')

local unchanged = fixture()
unchanged.events.bar_pick_scr(1)
assert(#unchanged.commands == 0, 'choosing the existing monitor must not restart the bar')

local write_failed = fixture()
write_failed.sed_code = 1
write_failed.events.bar_pick_scr(0)
assert(#write_failed.commands == 1, 'a failed surface rewrite must not restart')
assert(write_failed.text.bar_msg == "Couldn't change where the bar shows.", 'surface rewrite failure must be visible')
write_failed.sed_code = 0
write_failed.events.bar_pick_scr(0)
assert(write_failed.commands[#write_failed.commands].cmd == 'systemctl', 'a failed rewrite must not leave the selector stuck busy')

local restart_failed = fixture()
restart_failed.restart_code = 1
restart_failed.events.bar_pick_scr(0)
assert(restart_failed.text.bar_msg == "Couldn't restart the bar service.", 'a failed restart request must be visible')
restart_failed.restart_code = 0
restart_failed.events.bar_pick_scr(0)
assert(#restart_failed.commands == 4, 'retrying the same monitor after a rejected restart must be possible')

-- The two published lite flags follow the surface actually running (`B.file`): the strip of the
-- monitor that shows the full bar closes, and All/fallback-All leaves no overlapping copies.
local dp2 = fixture()
assert(dp2.fact.bar_lite_dp1 == true and dp2.fact.bar_lite_hdmi == true,
       'DP-2 shows the full bar, so both side strips must stay open')

local dp1 = fixture({ screens = 'screens: "DP-1";', pref = 'DP-1' })
assert(dp1.fact.bar_lite_dp1 == false, 'the strip of the monitor running the full bar must close')
assert(dp1.fact.bar_lite_hdmi == true, 'the other side strip stays open when the bar is on DP-1')

local hdmi = fixture({ screens = 'screens: "HDMI-A-2";', pref = 'HDMI-A-2' })
assert(hdmi.fact.bar_lite_dp1 == true and hdmi.fact.bar_lite_hdmi == false,
       'HDMI-A-2 shows the full bar, so its own strip must close')

local all = fixture({ screens = 'screens: each max 4;', pref = 'all' })
assert(all.fact.bar_lite_dp1 == false and all.fact.bar_lite_hdmi == false,
       'All/fallback-All must leave no lite strip showing')

-- All monitors means every connected monitor, not two of three: the surface copy limit must
-- cover the full supported monitor count.
local all_choice = fixture({ pref = 'DP-2' })
all_choice.events.bar_pick_scr(-1)
local rewrite = all_choice.commands[1]
assert(rewrite and rewrite.cmd == 'sed', 'choosing All must rewrite the surface screens line')
assert(rewrite.args[3]:find('screens: each max 4;', 1, true),
       'All must create a bar copy for every monitor, not stop at two')
assert(not rewrite.args[3]:find('each max 2', 1, true),
       'the two-monitor cap is the defect that hid the third bar')

local gone = fixture({ screens = 'screens: "HDMI-A-2";', pref = 'HDMI-A-2',
                       mons = { { name = 'DP-2', x = 1366, y = 0, transform = 0 },
                                { name = 'DP-1', x = 3926, y = 0, transform = 0 } } })
assert(gone.fact.bar_lite_dp1 == false and gone.fact.bar_lite_hdmi == false,
       'an unplugged preferred monitor falls back to all, so no lite copy may show')

-- The facts describe the bar that is running, never a choice still waiting for its restart.
local pending = fixture({ screens = 'screens: "DP-2";', pref = 'DP-1' })
assert(pending.fact.bar_lite_dp1 == true and pending.fact.bar_lite_hdmi == true,
       'the flags must follow the running file, not the pending preference')

print('bar monitor service-restart and lite-flag contracts: PASS')
