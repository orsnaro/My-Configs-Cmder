-- Real Widgets handlers/controller; only external IPC, process startup and time are simulated.
local function fixture(opts)
    opts = opts or {}
    local s = { now = 0, timers = {}, events = {}, launches = 0, writes = {}, remote = {},
        fact = { ck_on = false, sy_on = false, ck_ok = false, sy_ok = false,
            ck_lay = 0, ck_px = 220, ck_wt = 1, ck_cl = 1, ck_12h = true, sy_cl = 1,
            gl_sel = 0, ghw = 1, ghz = 1, ghc = 0, gmw = 1, gmz = 1, gmc = 0,
            gsw = 1, gsz = 1, gsc = 0, gl_w = 2, gl_z = 2, gl_c = 0, ck_mon = 0, sy_mon = 0 },
        text = { ck_status = '', sy_status = '' }, delay = opts.delay or 0, fail = false }
    local function scene(available)
        return { available = available, shown = false, lay = 0, px = 220, wti = 1, cli = 1,
            where = 'center', h12 = true, mon_name = 'DP-2', gpack = '1,1,0;1,1,0;1,1,0;',
            ghw = 1, ghz = 1, ghc = 0, gmw = 1, gmz = 1, gmc = 0, gsw = 1, gsz = 1, gsc = 0 }
    end
    if opts.running then
        s.remote.desktopclock = scene(0)
        s.remote.desktopsysmon = scene(0)
    end
    local function ready(name)
        local r = s.remote[name]
        return r and r.available <= s.now and r
    end
    local function reply(name, command)
        local r = ready(name)
        if not r then return '', 1 end
        local key = command:match('^get (.+)$')
        if key == 'gpack' then
            local parts = {}
            for _, part in ipairs({ 'h', 'm', 's' }) do
                parts[#parts + 1] = r['g' .. part .. 'w'] .. ',' .. r['g' .. part .. 'z'] .. ',' .. r['g' .. part .. 'c'] .. ';'
            end
            return table.concat(parts), 0
        end
        if key then return tostring(r[key]), 0 end
        if s.fail then return '? delivery rejected', 0 end
        local field, value = command:match('^fact (%S+) (.+)$')
        if not field then field, value = command:match('^text (%S+) (.+)$') end
        assert(field, command)
        if value == 'true' then value = true elseif value == 'false' then value = false else value = tonumber(value) or value end
        if field == 'greset' then
            for _, part in ipairs({ 'h', 'm', 's' }) do r['g' .. part .. 'w'], r['g' .. part .. 'z'], r['g' .. part .. 'c'] = 1, 1, 0 end
        else r[field] = value end
        s.writes[#s.writes + 1] = { scene = name, command = command }
        return '', 0
    end
    local function after(ms, fn) s.timers[#s.timers + 1] = { at = s.now + ms, fn = fn } end
    local env = setmetatable({
        fact = s.fact, text = s.text, log = function() end,
        on = function(name, fn) s.events[name] = fn end,
        after = after, every = function(_, fn) s.periodic = fn end,
        json = { decode = function() return { { id = 0, name = 'DP-2' }, { id = 1, name = 'DP-1' } } end },
        run = function(command, args, done)
            if command == 'hyprctl' then return done('monitors', 0) end
            assert(command == 'pleamar', command)
            local function complete()
                local out, code = '', 0
                for i = 3, #args do
                    out, code = reply(args[2], args[i])
                    if code ~= 0 or out:match('^%?') then break end
                end
                done(out, code)
            end
            if s.delay > 0 then after(s.delay, complete) else complete() end
        end,
        say_many = function(name, commands, done)
            local answers = {}
            for _, command in ipairs(commands) do
                local out, code = reply(name, command)
                if code ~= 0 then return done(nil) end
                answers[#answers + 1] = out
            end
            local function complete() done(answers) end
            if s.read_delay then after(s.read_delay, complete) else complete() end
        end,
        exec_on_desktop = function(command)
            local name = command:match('/(desktopclock)/') or command:match('/(desktopsysmon)/')
            assert(name, command)
            s.launches = s.launches + 1
            if not opts.launch_fail then s.remote[name] = scene(s.now + (opts.start_delay or 0)) end
        end,
    }, { __index = _G })
    env.require = function(path) return assert(loadfile(path .. '.luau', 't', env))() end
    assert(loadfile('logic/clock.luau', 't', env))()()
    function s.advance(ms)
        local until_at = s.now + ms
        local steps = 0
        while true do
            table.sort(s.timers, function(a, b) return a.at < b.at end)
            if not s.timers[1] or s.timers[1].at > until_at then break end
            local timer = table.remove(s.timers, 1)
            s.now = timer.at
            timer.fn()
            steps = steps + 1
            assert(steps < 5000, 'unbounded polling')
        end
        s.now = until_at
    end
    return s
end

local cases = {}
function cases.cold_clock_applies_on_after_saved_off()
    local s = fixture({ start_delay = 400 })
    s.events.ck_toggle(); s.advance(1000)
    assert(s.remote.desktopclock.shown == true, 'first On must survive the restored saved Off')
    assert(s.fact.ck_on == true and s.fact.ck_ok == true)
end
function cases.slow_monitor_waits_for_readiness()
    local s = fixture({ start_delay = 4000 })
    s.events.sy_toggle(); s.advance(5000)
    assert(s.remote.desktopsysmon.shown == true, 'startup slower than 2500ms must still receive On')
    assert(s.launches == 1 and s.fact.sy_on == true)
end
function cases.failed_start_reports_error_without_false_on()
    local s = fixture({ launch_fail = true })
    s.events.ck_toggle(); s.advance(12000)
    assert(s.fact.ck_on == false and s.fact.ck_ok == false)
    assert(s.text.ck_status:lower():find('start'), 'startup failure must be visible')
    assert(s.fact.ck_notice == true, 'failure subtitle must be shown')
    assert(s.launches == 1)
end
function cases.pending_off_can_be_reversed_while_currently_on()
    local s = fixture({ running = true, delay = 100 })
    s.fact.ck_on, s.remote.desktopclock.shown = true, true
    s.events.ck_toggle(); s.events.ck_toggle(); s.advance(500)
    assert(s.fact.ck_on == true and s.remote.desktopclock.shown == true, 'pending false is a real intent, not an absent value')
end
function cases.rapid_on_off_keeps_last_intent()
    local s = fixture({ start_delay = 1000 })
    s.events.ck_toggle(); s.events.ck_toggle(); s.advance(2000)
    assert(s.remote.desktopclock.shown == false and s.fact.ck_on == false)
    assert(s.launches == 1)
end
function cases.pending_style_is_delivered_after_startup()
    local s = fixture({ start_delay = 1000 })
    s.events.ck_toggle(); s.events.ck_lay_set(1); s.events.ck_lay_set(2)
    assert(s.fact.ck_lay == 0, 'unconfirmed preview must not claim the setting was saved')
    s.advance(2000)
    assert(s.remote.desktopclock.lay == 2 and s.fact.ck_lay == 2)
    assert(s.launches == 1)
end
function cases.absent_widget_rejects_style_without_preview_or_launch()
    local s = fixture()
    s.events.ck_lay_set(2); s.advance(100)
    assert(s.fact.ck_lay == 0 and s.launches == 0)
    assert(s.text.ck_status ~= '', 'a rejected change needs a visible explanation')
end
function cases.successful_setting_waits_for_acknowledgement()
    local s = fixture({ running = true, delay = 100 })
    s.events.ck_size_set(2)
    assert(s.fact.ck_px == 220, 'do not update before delivery completes')
    s.advance(200)
    assert(s.fact.ck_px == 280 and s.remote.desktopclock.px == 280)
end
function cases.protocol_failure_does_not_confirm_preview()
    local s = fixture({ running = true })
    s.fail = true; s.events.sy_cl_set(2); s.advance(100)
    assert(s.fact.sy_cl == 1 and s.remote.desktopsysmon.cli == 1)
    assert(s.text.sy_status ~= '', 'a protocol error with exit status 0 is still a failure')
end
function cases.glyph_changes_wait_for_confirmation()
    local s = fixture({ running = true, delay = 100 })
    s.events.gl_w_set(4)
    assert(s.fact.ghw == 1)
    s.advance(200)
    assert(s.fact.ghw == 1.5 and s.remote.desktopclock.ghw == 1.5)
end
function cases.reset_failure_preserves_the_confirmed_glyph()
    local s = fixture({ running = true })
    s.events.gl_w_set(4)
    s.fail = true; s.events.gl_reset()
    assert(s.fact.ghw == 1.5, 'failed reset must not overwrite the confirmed glyph')
end
function cases.monitor_selection_waits_for_confirmation()
    local s = fixture({ running = true, delay = 100 })
    s.events.ck_mon_set(2)
    assert(s.fact.ck_mon == 0)
    s.advance(200)
    assert(s.fact.ck_mon == 2 and s.remote.desktopclock.mon_name == 'DP-1')
end
function cases.stale_page_refresh_cannot_override_newer_intent()
    local s = fixture({ running = true })
    s.read_delay = 500
    s.events['fact:set_page']('pg_clock')
    s.read_delay = nil
    s.events.ck_toggle()
    s.advance(600)
    assert(s.fact.ck_on == true and s.remote.desktopclock.shown == true, 'old Off snapshot must not revert acknowledged On')
end
function cases.repeated_on_intent_does_not_launch_another_keeper()
    local s = fixture({ start_delay = 1000 })
    s.events.ck_toggle(); s.events.ck_toggle(); s.events.ck_toggle(); s.advance(2000)
    assert(s.launches == 1 and s.remote.desktopclock.shown == true)
end
function cases.latest_change_keeps_order_across_reset()
    local s = fixture({ start_delay = 1000 })
    s.events.ck_toggle(); s.events.gl_w_set(4); s.events.gl_reset_all(); s.events.gl_w_set(3)
    s.advance(2000)
    assert(s.remote.desktopclock.ghw == 1.25, 'latest style change must follow the queued reset')
end

local names = {}
for name in pairs(cases) do names[#names + 1] = name end
table.sort(names)
local failures = 0
for _, name in ipairs(names) do
    local ok, err = pcall(cases[name])
    print((ok and 'PASS ' or 'FAIL ') .. name .. (ok and '' or ': ' .. tostring(err)))
    if not ok then failures = failures + 1 end
end
assert(failures == 0, tostring(failures) .. ' Widgets behavioral failures')
print('Widgets behavior: ' .. #names .. ' passed')
