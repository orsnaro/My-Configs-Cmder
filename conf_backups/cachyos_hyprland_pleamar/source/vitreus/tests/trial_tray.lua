-- Exercise the actual tray adapter; no D-Bus calls or desktop writes are made.
local events, calls, watchers, panels = {}, {}, {}, {}
fact, text, model = {}, {}, {}
on = function(name, fn) events[name] = fn end
run = function(_, _, callback) callback('', 1) end -- No live D-Bus calls in this styling test.
sys = {
    watch = function(name, fn) watchers[name] = fn end,
    ask = function(name)
        if name == 'files.read' then return {} end
        if name == 'tray.menu' then return {{ label = '_Open', id = 42 }} end
    end,
    call = function(...) calls[#calls + 1] = {...} end,
}
dofile('logic/tray.luau')(function(panel) panels[#panels + 1] = panel end)
watchers.tray({
    {id = 'proton.vpn.app.gtk', key = 'vpn-bus', icon = 'vpn-art', menu = true},
    {id = 'unknown', key = 'other-bus', icon = 'other-art'},
    {id = 'nm-applet', key = 'network-bus', icon = 'network-art'},
    {id = 'blueman', key = 'bluetooth-bus', icon = 'bluetooth-art', menu = true},
})
assert(#model.bartrays == 4, 'styling must not add, remove or duplicate tray apps')
for i, wanted in ipairs({'bluetooth', 'lan', 'shield_lock', ''}) do
    assert(model.bartrays[i].symbol == wanted, 'incorrect preview symbol at sorted row ' .. i)
    assert(model.bartrays[i].symbol_on == (wanted ~= ''), 'renderer needs a boolean, not a text comparison')
end
assert(model.bartrays[4].icon == 'other-art', 'unknown apps must retain native artwork')
assert(model.trays[1].icon == 'bluetooth-art', 'full tray menu keeps native app artwork')
events.bar_tray_click(0)
assert(calls[#calls][1] == 'tray.activate' and calls[#calls][2] == 'bluetooth-bus', 'Bluetooth left click must still activate Blueman')
events.bar_tray_menu(0)
assert(text.tm_iconurl == 'bluetooth-art' and panels[#panels] == 'tray', 'right click must open original app menu')
events.tray_menu_pick(0)
assert(calls[#calls][1] == 'tray.menu_click' and calls[#calls][2] == 'bluetooth-bus' and calls[#calls][3] == 42, 'menu items must keep original D-Bus identity')
events.tray_pin(2)
events.tray_mode()
assert(#model.bartrays == 1 and model.bartrays[1].symbol == 'shield_lock', 'pinned-only mode preserves symbol and app mapping')
events.bar_tray_click(0)
assert(calls[#calls][2] == 'vpn-bus', 'filtering must not misroute icon clicks')
events.tray_mode()
watchers.tray({{id = '', key = 'menu-only', icon = 'menu-art', menu = true}})
assert(model.bartrays[1].symbol == '' and model.bartrays[1].icon == 'menu-art', 'menu-only app keeps fallback artwork')
events.bar_tray_click(0)
assert(panels[#panels] == 'tray', 'menu-only apps must still open their menus')
print('trial tray styling and action contracts: PASS')
