local passed, events = {}, {}
run = function(cmd, args, done) passed[#passed + 1] = {cmd, args}; if done then done('ok', 0) end end
on = function(event, fn) events[event] = fn end
log = function() end
assert(io.open('logic/trial_policy.luau'), 'trial policy is not implemented')
local policy = dofile('logic/trial_policy.luau')()
for _, request in ipairs({
    {'hyprctl', {'eval', 'hl.config({general={gaps_out=0}})'}},
    {'hyprctl', {'hyprsunset', 'identity'}},
    {'hyprctl', {'reload'}},
    {'pkill', {'-x', 'hypridle'}},
    {'pkill', {'-x', 'mpvpaper'}},
    {'systemctl', {'--user', 'stop', 'hypridle.service'}},
    {'awww', {'img', '/some/wallpaper'}},
    {'setsid', {'sh', '-c', 'vitreus-keep /some/scene.plm'}},
}) do
    local rejected = false
    run(request[1], request[2], function(_, code) rejected = code ~= 0 end)
    assert(rejected, 'protected desktop command must be rejected: ' .. request[1])
end
assert(#passed == 0, 'protected commands reached the real command API')
run('hyprctl', {'monitors', '-j'}, function() end)
run('hyprctl', {'dispatch', 'hl.dsp.workspace(2)'}, function() end)
run('pomo', {}, function() end)
assert(#passed == 3, 'read-only queries and user bar actions must remain available')
on('wp_next', function() error('must not register') end)
on('caf_toggle', function() error('must not register') end)
on('disp_apply', function() error('must not register') end)
on('trial_pomo_start', function() end)
assert(not events.wp_next and not events.caf_toggle and not events.disp_apply)
assert(events.trial_pomo_start, 'bar action registration was blocked')
assert(policy.desktop('vitreus-keep ~/.config/pleamar/shells/vitreus/webcam/webcam.plm') == nil)
assert(policy.desktop('pleamar --say lockscreen "fact locked true"') == '$HOME/.config/pleamar/shells/vitreus/bin/vitreus-lock')
assert(policy.desktop('kitty') == 'kitty')
print('trial desktop policy contracts: PASS')
