-- Exercise the actual controller across the external-command boundary.
local events, timers, calls, writes, periodic, watchers = {}, {}, {}, {}, {}, {}
local scene_file = assert(io.open('vitreus.plm'))
local scene = scene_file:read('*a')
scene_file:close()
local allowed = assert(scene:match('run:%s*(.-)%s*}'))
local function permitted(cmd)
    assert(allowed:find('"' .. cmd .. '"', 1, true), 'command lacks scene permission: ' .. cmd)
end
fact, text, model = {}, {}, {}
json = { decode = function(line)
    if line == 'bad' then error('invalid JSON') end
    local data = { cpu = 'CPU 25%', ram = 'MEM 4.0 GiB', gpu = 'GPU 42%',
             vram = 'VMEM 2.0 GiB', weather = '22°C', pomo = 'Pomo idle',
             weather_icon = 'clear_night', updates = '2', keyboard = 'US' }
    if line == 'no_icon' then data.weather_icon = nil end
    return data
end }
on = function(name, fn) events[name] = fn end
after = function(ms, fn) timers[#timers + 1] = { ms, fn } end
every = function(ms, fn) periodic[ms] = fn end
log = function() end
run = function(cmd, args, fn)
    permitted(cmd)
    calls[#calls + 1] = { cmd, args }
    if cmd == 'pgrep' then fn('', 1) else fn('', 0) end
end
spawn = function(cmd, args, line, exited)
    permitted(cmd)
    writes.line, writes.exited = line, exited
    return 1
end
sys = { call = function(...) calls[#calls + 1] = { ... } end,
        watch = function(name, fn) watchers[name] = fn end }
exec_on_desktop = function(cmd) calls[#calls + 1] = { 'desktop', cmd } end
assert(io.open('logic/trial_status.luau'), 'trial controller is not implemented')
dofile('logic/trial_status.luau')()
--  The switcher publishes its pinned empty rows before the first service update.
local initial_ids, initial_dense = {}, true
for i, r in ipairs(model.trial_workspaces or {}) do
    initial_ids[i] = r.id
    if r.slot ~= i - 1 then initial_dense = false end
end
assert(table.concat(initial_ids, ',') == '1,2,3,4,5,6,7,8,9',
       'initial rows must show every workspace through nine')
assert(initial_dense, 'initial slots must be zero-based and dense')
assert(model.trial_workspaces[1].occupied == false and model.trial_workspaces[1].icon == 'crop_square',
       'empty rows show the empty-workspace square')

writes.line('ok')
assert(text.trial_cpu == 'CPU 25%', 'helper values must reach the bar')
assert(text.trial_vram == 'VMEM 2.0 GiB', 'VMEM must keep its used-only units')
assert(text.trial_weather_icon == 'clear_night', 'weather symbol must reach the scene')
writes.line('no_icon')
assert(text.trial_weather_icon == 'cloud_off', 'missing symbol must not retain old weather')
assert(watchers.clock, 'compact date must follow the existing native clock service')
watchers.clock({day = 19, month = 10})
assert(text.trial_date_dm == '19 OCT', 'preview date is day before abbreviated month')
assert(periodic[10000], 'a stalled helper needs a freshness watchdog')
periodic[10000]()
periodic[10000]()
assert(text.trial_gpu == 'GPU —', 'a stalled helper must not leave frozen telemetry')
assert(text.trial_weather_icon == 'cloud_off', 'stalled helper must reset the weather symbol')
writes.line('bad')
assert(text.trial_cpu == 'CPU —', 'malformed input must invalidate old readings')
writes.line('ok')
writes.exited()
assert(text.trial_vram == 'VMEM —', 'helper exit must invalidate old readings')
assert(#timers > 0, 'helper must restart after exit')
events.trial_pomo_start()
assert(calls[#calls][1] == 'desktop' and calls[#calls][2] == 'pomo', 'user pomo must outlive the trial cgroup')
events.trial_updates_open()
assert(calls[#calls][1] == 'desktop' and calls[#calls][2]:find('arch-update', 1, true), 'interactive updater must outlive trial and use normal desktop environment')
events.trial_keyboard_switch()
assert(calls[#calls][1] == 'hypr-switch-xkblayout', 'keyboard click must use existing script')
assert(events.trial_power_open, 'power shortcut needs a deferred subview handler')
assert(events.trial_alerts_open, 'notification shortcut needs a deferred subview handler')
fact.panel = 'controls'
events.trial_power_open()
assert(timers[#timers][1] == 30, 'wait for native panel-change reset before choosing subview')
timers[#timers][2]()
assert(fact.panel_sub == 'powview', 'power shortcut must reach the session actions')
events.trial_alerts_open()
timers[#timers][2]()
assert(fact.panel_sub == 'notifview', 'alerts shortcut must reach notification history')
events.trial_power_open()
fact.panel, fact.panel_sub = 'none', 'none'
timers[#timers][2]()
assert(fact.panel_sub == 'none', 'late shortcut callback must not revive dismissed UI')
--  The workspace app glyphs: the compositor's window events are debounced into one `hyprctl clients`
--  read, mapped through the glyph table onto the bar's text props.
local fixture = { text = table.concat({
    'Window 55824c000000 -> Quake:', '\tworkspace: -98 (special:quake)', '\tclass: quake-kitty',
    '\tfocusHistoryID: 5', '\tmapped: 1',
    'Window 55824c000001 -> Obsidian:', '\tworkspace: 4 (4)', '\tclass: md.obsidian.Obsidian',
    '\tfocusHistoryID: 4', '\tmapped: 1',
    'Window 55824c000002 -> Brave:', '\tworkspace: 3 (3)', '\tclass: brave-browser',
    '\tfocusHistoryID: 0', '\tmapped: 1',
    'Window 55824c000003 -> kitty:', '\tworkspace: 3 (3)', '\tclass: kitty',
    '\tfocusHistoryID: 1', '\tmapped: 1',
    'Window 55824c000004 -> Some Tool:', '\tworkspace: 5 (5)', '\tclass: some-tool',
    '\tfocusHistoryID: 2', '\tmapped: 1',
    'Window 55824c000005 -> Hidden:', '\tworkspace: 6 (6)', '\tclass: brave-browser',
    '\tfocusHistoryID: 1', '\tmapped: 0',
    'Window 55824c000006 -> Seven:', '\tworkspace: 7 (7)', '\tclass: md.obsidian.Obsidian',
    '\tfocusHistoryID: 0', '\tmapped: 1',
}, '\n') }
local clients_reads = 0
run = function(cmd, args, fn)
    permitted(cmd)
    if cmd == 'hyprctl' and args and args[1] == 'clients' then
        clients_reads = clients_reads + 1
        fn(fixture.text, 0)
        return
    end
    if cmd == 'printenv' then
        if args and args[1] == 'HYPRLAND_INSTANCE_SIGNATURE' then fn('testsig\n', 0)
        else fn('/run/user/1000\n', 0) end
        return
    end
    fn('', 0)
end
local spawned
spawn = function(cmd, args, line, exited)
    permitted(cmd)
    spawned = { cmd = cmd, args = args }
    writes.line, writes.exited = line, exited
    return 1
end
local arm
for _, t in ipairs(timers) do
    if t[1] == 1500 then arm = t[2] end
end
assert(arm, 'the compositor event socket must be armed after load')
arm()
assert(spawned and spawned.cmd == 'socat', 'arming must read the compositor socket')
assert(spawned.args[2]:find('/hypr/testsig/.socket2.sock', 1, true),
       'the reader must connect .socket2.sock under the instance runtime dir')
writes.line('openwindow>>55824c000003,3,kitty,Brave')
assert(timers[#timers][1] == 400, 'window events must debounce into one refresh')
timers[#timers][2]()
assert(clients_reads == 1, 'the debounce must read the compositor once')
assert(text.ws_app3 == 'language', 'the most recent window on a workspace must win (brave over kitty)')
assert(text.ws_app4 == 'edit_note', 'the glyph table must map the Obsidian class')
assert(text.ws_app5 == 'apps', 'an unmapped app falls back to the generic app glyph')
assert(text.ws_app6 == '', 'a hidden window must not name its workspace')
assert(text.ws_app7 == 'edit_note', 'workspaces past the five keep their glyph for the chip')
assert(text.ws_app1 == '' and text.ws_app2 == '', 'empty workspaces carry no glyph')
--  An event that does not move a window (a workspace switch on its own) must not read the compositor.
local quiet = #timers
writes.line('workspace>>7')
assert(#timers == quiet, 'unrelated compositor events must not refresh the glyphs')
--  A burst of events collapses into one read: only the newest debounce survives.
writes.line('activewindow>>55824c000002,Brave')
writes.line('closewindow>>55824c000003')
local superseded, latest = timers[#timers - 1], timers[#timers]
superseded[2]()
assert(clients_reads == 1, 'a superseded debounce must not read the compositor')
latest[2]()
assert(clients_reads == 2, 'the surviving debounce must read the compositor')
--  The workspaces service is the backstop, and workspaces left empty must clear their glyph.
fixture.text = 'Window 55824c000007 -> kitty:\n\tworkspace: 8 (8)\n\tclass: kitty\n\tfocusHistoryID: 0\n\tmapped: 1'
assert(watchers.workspaces, 'a workspace change must refresh the glyphs too')
watchers.workspaces({})
timers[#timers][2]()
assert(text.ws_app8 == 'terminal', 'the workspaces backstop must refresh the glyphs')
assert(text.ws_app3 == '', 'a workspace with no windows left must clear its glyph')
--  A dropped socket is picked up again.
local first_reader = spawned
writes.exited()
assert(timers[#timers][1] == 3000, 'a dropped socket must try the reader again')
timers[#timers][2]()
assert(spawned ~= first_reader and spawned.cmd == 'socat', 'the re-armed reader must connect again')
--  The live switcher: one row per visible workspace, driven by the workspaces service and the glyph cache.
local function ws_ids()
    local ids = {}
    for i, r in ipairs(model.trial_workspaces) do ids[i] = r.id end
    return table.concat(ids, ',')
end
local function ws_row(id)
    for _, r in ipairs(model.trial_workspaces) do if r.id == id then return r end end
end
local function ws_dense()
    for i, r in ipairs(model.trial_workspaces) do if r.slot ~= i - 1 then return false end end
    return true
end
local function ws_ascending()
    local prev = 0
    for _, r in ipairs(model.trial_workspaces) do
        if r.id <= prev then return false end
        prev = r.id
    end
    return true
end
local function ws_count() return #model.trial_workspaces end
--  Every workspace is present. 1-7 are primary and keep their faded marks; 8-9 are secondary.
watchers.workspaces({ active = 1, list = {} })
assert(ws_ids() == '1,2,3,4,5,6,7,8,9', 'all workspaces must show through nine')
assert(ws_dense(), 'workspace slots must be zero-based and dense')
for id = 1, 7 do
    assert(ws_row(id) and ws_row(id).occupied == false,
           'empty primary workspace must stay in the row: ' .. id)
end
for id = 8, 9 do
    assert(ws_row(id) and ws_row(id).occupied == false,
           'empty secondary workspace must stay in the row: ' .. id)
end
--  The active workspace shows even while empty.
watchers.workspaces({ active = 7, list = {} })
assert(ws_row(7) and ws_row(7).occupied == false,
       'the empty but active primary workspace must show, unoccupied')
--  An occupied primary workspace stays in its slot, marked occupied.
watchers.workspaces({ active = 1, list = { { id = 2, windows = 3 } } })
assert(ws_row(2) and ws_row(2).occupied == true,
       'an occupied primary workspace must show as occupied')
assert(ws_ids() == '1,2,3,4,5,6,7,8,9', 'occupied 2 must keep every workspace')
--  A higher-numbered workspace extends the range (bounded by the model's row capacity, not the id).
watchers.workspaces({ active = 12, list = { { id = 12, windows = 2 } } })
assert(ws_row(12) and ws_row(12).occupied == true,
       'a twelfth workspace must extend the range')
assert(ws_ids() == '1,2,3,4,5,6,7,8,9,10,11,12', 'the range must climb to the highest existing workspace')
assert(ws_dense(), 'extended rows must stay densely slotted')
--  A higher active workspace is included even when the service omits its empty list entry.
watchers.workspaces({ active = 12, list = {} })
assert(ws_row(12) and ws_row(12).occupied == false,
       'an active workspace the list omits must still show')
--  Special and negative workspace ids are ignored entirely.
watchers.workspaces({ active = 1, list = { { id = -98, windows = 4 }, { id = -1, windows = 1 } } })
assert(ws_ids() == '1,2,3,4,5,6,7,8,9', 'special and negative ids must not appear or extend the range')
--  Secondary workspaces stay in the model when occupied, and when empty and active.
watchers.workspaces({ active = 1, list = { { id = 7, windows = 2 } } })
assert(ws_row(7) and ws_row(7).occupied == true, 'occupied 7 must show')
watchers.workspaces({ active = 1, list = { { id = 9, windows = 1 } } })
assert(ws_row(9) and ws_row(9).occupied == true, 'occupied 9 must show')
watchers.workspaces({ active = 2, list = {} })
assert(ws_row(2) and ws_row(2).occupied == false, 'the empty active 2 must show')
watchers.workspaces({ active = 9, list = {} })
assert(ws_row(9) and ws_row(9).occupied == false,
       'the empty active 9 must show')
assert(ws_ids() == '1,2,3,4,5,6,7,8,9', 'active 9 must keep every workspace')
--  The event payload is read, never written: the controller keeps its own state.
local payload = { active = 2, list = { { id = 2, windows = 1 } } }
watchers.workspaces(payload)
assert(payload.active == 2 and payload.list[1].id == 2 and payload.list[1].windows == 1,
       'the incoming payload must be left untouched')
local bare = {}
watchers.workspaces(bare)
assert(bare.list == nil and bare.active == nil, 'no key may be added to the incoming payload')
--  Row capacity bounds rows, not ids: the first 64 fill the model, and a higher active workspace takes the last slot.
watchers.workspaces({ active = 1, list = { { id = 64, windows = 1 } } })
assert(ws_row(64) and ws_row(64).occupied == true, 'workspace 64 must appear normally')
assert(ws_count() == 64 and ws_dense() and ws_ascending(), 'the 64-workspace list must stay dense and ascending')
assert(model.trial_workspaces[#model.trial_workspaces].id == 64, '64 must be the last visible id')
watchers.workspaces({ active = 1, list = { { id = 65, windows = 1 } } })
assert(ws_row(65) == nil, 'workspace 65 outside the active slot must not push the first 64 out')
assert(ws_count() == 64 and ws_dense() and ws_ascending(), 'the capped list must stay dense and ascending')
assert(model.trial_workspaces[#model.trial_workspaces].id == 64, '64 stays the last retained id')
watchers.workspaces({ active = 65, list = { { id = 65, windows = 1 } } })
assert(ws_row(65) and ws_row(65).occupied == true, 'active workspace 65 must take the final slot')
assert(ws_count() == 64 and ws_dense() and ws_ascending(), 'the active fallback must stay dense and ascending')
assert(model.trial_workspaces[#model.trial_workspaces].id == 65, '65 must be the last visible id when active')
--  A huge active id past the retained rows takes the final slot, keeping the fallback dense and ascending.
watchers.workspaces({ active = 200, list = {} })
assert(ws_row(200) and ws_row(200).occupied == false, 'active 200 omitted by the list must still show')
assert(ws_count() == 64, 'the capacity fallback keeps exactly the row capacity')
assert(ws_dense() and ws_ascending(), 'the retained-plus-active fallback must stay dense and ascending')
assert(model.trial_workspaces[#model.trial_workspaces].id == 200, 'active 200 must take the final slot')
watchers.workspaces({ active = 200, list = { { id = 200, windows = 1 } } })
assert(ws_row(200) and ws_row(200).occupied == true, 'listed active 200 must show as occupied')
assert(ws_count() == 64 and ws_dense() and ws_ascending(), 'listed active 200 must keep rows dense and ascending')
assert(model.trial_workspaces[#model.trial_workspaces].id == 200, 'listed active 200 must take the final slot')
--  Glyphs ride on the rows and clear when a workspace empties.
fixture.text = 'Window 1 -> Brave:\n\tworkspace: 3 (3)\n\tclass: brave-browser\n\tfocusHistoryID: 0\n\tmapped: 1'
watchers.workspaces({ active = 3, list = { { id = 3, windows = 1 } } })
timers[#timers][2]()
assert(ws_row(3).icon == 'language', 'a mapped window must put its glyph on the row')
assert(ws_row(3).occupied == true, 'the row must follow the service occupancy')
assert(text.ws_app3 == 'language', 'the legacy text prop must stay in step with the row')
fixture.text = 'Window 2 -> kitty:\n\tworkspace: 8 (8)\n\tclass: kitty\n\tfocusHistoryID: 0\n\tmapped: 1'
watchers.workspaces({ active = 3, list = {} })
timers[#timers][2]()
assert(ws_row(3).icon == 'crop_square', 'a workspace with no windows left must clear to the empty square in the model')
--  Glyphs past the tenth still land on their rows.
fixture.text = 'Window 3 -> Brave:\n\tworkspace: 12 (12)\n\tclass: brave-browser\n\tfocusHistoryID: 0\n\tmapped: 1'
watchers.workspaces({ active = 12, list = { { id = 12, windows = 1 } } })
timers[#timers][2]()
assert(ws_row(12) and ws_row(12).icon == 'language', 'glyphs must not stop at the tenth workspace')
--  A browser-embedded Discord is a real app class: the webapp's workspace shows the forum glyph.
fixture.text = 'Window 4 -> Discord:\n\tworkspace: 5 (5)\n\tclass: brave-discord.com__channels_@me-Default\n\tfocusHistoryID: 0\n\tmapped: 1'
watchers.workspaces({ active = 5, list = { { id = 5, windows = 1 } } })
timers[#timers][2]()
assert(ws_row(5) and ws_row(5).icon == 'forum', 'the Discord webapp class must map to the forum glyph')
assert(text.ws_app5 == 'forum', 'the Discord webapp must reach the legacy text prop too')
--  A mapped but unknown app is still an app: legacy and model both fall back to the generic glyph.
fixture.text = 'Window 9 -> Some Tool:\n\tworkspace: 5 (5)\n\tclass: some-tool\n\tfocusHistoryID: 0\n\tmapped: 1'
watchers.workspaces({ active = 5, list = { { id = 5, windows = 1 } } })
timers[#timers][2]()
assert(text.ws_app5 == 'apps', 'an unmapped app must reach the legacy prop as the generic glyph')
assert(ws_row(5) and ws_row(5).icon == 'apps', 'an unmapped app must carry the generic glyph on its row')
--  Repeated app icons are intentional: two Brave workspaces both name their browser.
fixture.text = 'Window 5 -> Brave:\n\tworkspace: 3 (3)\n\tclass: brave-browser\n\tfocusHistoryID: 0\n\tmapped: 1'
    .. '\nWindow 6 -> Brave:\n\tworkspace: 4 (4)\n\tclass: brave-browser\n\tfocusHistoryID: 0\n\tmapped: 1'
watchers.workspaces({ active = 3, list = { { id = 3, windows = 1 }, { id = 4, windows = 1 } } })
timers[#timers][2]()
assert(ws_row(3).icon == 'language' and ws_row(4).icon == 'language',
       'two workspaces running the same app must each carry its glyph')
--  An occupied workspace whose app the clients read has not named yet shows the generic app glyph.
fixture.text = ''
watchers.workspaces({ active = 1, list = { { id = 6, windows = 1 } } })
assert(ws_row(6) and ws_row(6).occupied == true and ws_row(6).icon == 'apps',
       'an occupied workspace with no known app must show the generic glyph before the refresh')
--  Unrelated and lookalike domains are not the Discord webapp: they fall back to the generic glyph.
fixture.text = 'Window 7 -> Copy:\n\tworkspace: 6 (6)\n\tclass: brave-discord.com.evil__x\n\tfocusHistoryID: 0\n\tmapped: 1'
watchers.workspaces({ active = 1, list = { { id = 6, windows = 1 } } })
timers[#timers][2]()
assert(ws_row(6) and ws_row(6).icon == 'apps', 'a lookalike domain must not be mistaken for the Discord webapp')
fixture.text = 'Window 8 -> Other:\n\tworkspace: 6 (6)\n\tclass: xxbrave-discord.com__y\n\tfocusHistoryID: 0\n\tmapped: 1'
watchers.workspaces({ active = 1, list = { { id = 6, windows = 1 } } })
timers[#timers][2]()
assert(ws_row(6) and ws_row(6).icon == 'apps', 'an unrelated class embedding the name must not match the webapp')
--  Focus follows the mouse: a window taking the focus closes an open drawer, but the launcher stays.
fact.panel = 'settings'
writes.line('activewindow>>55824c000003,kitty,Some window')
assert(fact.panel == 'none', 'a focus move must close the open drawer')
--  The launcher ignores the same window-focus event, even after the opening grace.
fact.panel = 'launch'
events.panel_opened()
local grace = timers[#timers]
assert(grace[1] == 400, 'opening a drawer must arm a short grace period')
writes.line('activewindow>>55824c000003,kitty,Some window')
assert(fact.panel == 'launch', 'a window focus change must not close the launcher')
grace[2]()
writes.line('activewindow>>55824c000003,kitty,Some window')
assert(fact.panel == 'launch', 'the launcher stays open until a click-away or an explicit close')
--  Monitor changes arrive even when no application window gains focus (e.g. an empty output).
--  Exercise the real socket reader: no activewindow event is supplied here.
for _, line in ipairs({ 'focusedmon>>DP-1,1', 'focusedmonv2>>HDMI-A-2,3' }) do
    fact.panel = 'settings'
    writes.line(line)
    assert(fact.panel == 'none', 'changing monitor must release the drawer without a window focus event: ' .. line)
    fact.panel = 'launch'
    events.panel_opened()
    local monitor_grace = timers[#timers]
    writes.line(line)
    assert(fact.panel == 'launch', 'monitor focus must not dismiss the launcher: ' .. line)
    monitor_grace[2]()
    writes.line(line)
    assert(fact.panel == 'launch', 'monitor focus after the grace must keep the launcher open: ' .. line)
end
--  The focus watcher still closes the side dropdowns while the launcher stays open.
fact.panel = 'launch'
fact.lite_vol_dp1, fact.lite_vol_hdmi = true, true
writes.line('activewindow>>55824c000003,kitty,Some window')
assert(fact.panel == 'launch', 'focus must not dismiss the launcher')
assert(fact.lite_vol_dp1 == false and fact.lite_vol_hdmi == false,
       'focus must still close the side dropdowns under the launcher')
fact.panel = 'none'
fact.lite_vol_dp1, fact.lite_vol_hdmi = false, false
--  These standalone overlays also request the keyboard while panel itself is none.
for _, overlay in ipairs({ 'wp_picker_open', 'ov_open', 'dash_open' }) do
    for _, line in ipairs({ 'focusedmon>>DP-1,1', 'focusedmonv2>>HDMI-A-2,3' }) do
        fact.panel = 'none'
        fact.wp_picker_open, fact.ov_open, fact.dash_open = false, false, false
        fact[overlay] = true
        fact.pk_open, fact.desk_open = true, true
        writes.line('activewindow>>55824c000003,kitty,Some window')
        assert(fact[overlay], 'ordinary window focus must preserve existing standalone overlay behavior: ' .. overlay)
        writes.line(line)
        assert(not fact[overlay], 'changing monitor must release the standalone overlay: ' .. overlay)
        assert(fact.panel == 'none' and not fact.wp_picker_open and not fact.ov_open and not fact.dash_open,
               'monitor dismissal must leave no click-away overlay active')
        assert(fact.pk_open and fact.desk_open, 'monitor dismissal must not change auth or desk state')
    end
end
--  The side strips' volume dropdowns close like the drawer: a window focus or a monitor change.
fact.panel = 'none'
fact.lite_vol_dp1, fact.lite_vol_hdmi = false, false
--  Their own opening click gets the same grace as a drawer's.
events['fact:lite_vol_dp1'](true)
fact.lite_vol_dp1 = true
local side_grace = timers[#timers]
assert(side_grace[1] == 400, 'opening a side dropdown must arm a short grace period')
writes.line('activewindow>>55824c000003,kitty,Some window')
assert(fact.lite_vol_dp1 == true,
       'a side dropdown must not be dismissed by the focus change of its own opening click')
side_grace[2]()
writes.line('activewindow>>55824c000003,kitty,Some window')
assert(fact.lite_vol_dp1 == false, 'once the grace has passed, a focus move closes the side dropdown')
fact.lite_vol_dp1, fact.lite_vol_hdmi = true, true
writes.line('focusedmon>>DP-1,1')
assert(fact.lite_vol_dp1 == false and fact.lite_vol_hdmi == false,
       'changing monitor must close both side dropdowns')
print('trial controller contracts: PASS')
