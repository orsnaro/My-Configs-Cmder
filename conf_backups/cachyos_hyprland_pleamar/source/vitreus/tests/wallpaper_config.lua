-- Execute the real wallpaper loader with synthetic command/filesystem boundaries.
-- Run from the scene directory; arg[1] is the staged/live runtime-data directory.
local data = assert(arg[1], 'runtime-data directory required')
local function read(path)
    local file = io.open(path)
    if not file then return nil end
    local value = file:read('*a'); file:close(); return value
end
local source = assert(read('vitreus.luau'))
local first = assert(source:find('local WP_PER_PAGE =', 1, true))
local last = assert(source:find('-- ── glass ─', first, true))
local directory_json = read(data .. '/wallpaper-dir.json') or ''
local wallpaper_json = assert(read(data .. '/wallpaper.json'))
local directory = directory_json:match('"dir"%s*:%s*"([^"]+)"')
local saved = {
    ['wallpaper-dir.json'] = directory and { dir = directory } or nil,
    ['wallpaper.json'] = { slideshow = wallpaper_json:match('"slideshow"%s*:%s*true') ~= nil, minutes = 5 },
}
local tick, emitted, commands, model = nil, {}, {}, {}
local now = 1000
local env = setmetatable({
    fact = {}, text = {}, model = model,
    os = { time = function() return now end },
    on = function(name, fn) emitted[name] = fn end,
    after = function() end,
    every = function(_, fn) tick = fn end,
    with_dirs = function(fn) fn({home='/fixture',cache='/fixture/cache'}) end,
    wpv = { exts = {}, is = function() return false end,
        src = function(path, fn) fn(path) end, settle = function() end },
    sys = {
        watch = function(_, fn) fn({day=1,hour=1,minute=0,second=0}) end,
        ask = function(_, name) return saved[name] end,
        call = function(_, name, value) saved[name] = value end,
    },
    run = function(command, args, fn)
        commands[#commands+1] = {command=command,args=args}
        if command == 'xdg-user-dir' then fn('/fixture/Pictures',0)
        elseif command == 'ls' then
            if args[2] == '/home/narol/.config/ml4w/wallpapers' then
                fn('one.jpg\ntwo.PNG\nnot-an-image.txt\n',0)
            else fn('',2) end
        elseif fn then fn('',0) end
    end,
}, {__index=_G})
local code = source:sub(first,last-1) .. '\nreturn {directory=wp_dir,count=#wp_files,slideshow=wp_show}\n'
local result = assert(load(code,'@production-wallpaper-loader','t',env))()
assert(result.directory == '/home/narol/.config/ml4w/wallpapers', 'picker must use the existing collection, not missing Pictures/Wallpapers')
assert(result.count == 2 and #model.wps == 2, 'supported collection images must populate gallery rows')
assert(result.slideshow == false, 'manual mode must not activate the saved slideshow')
now = now + 301
assert(tick)()
for _, command in ipairs(commands) do
    assert(not (command.command == 'awww' and command.args[1] == 'img'), 'loading/manual timer must never select a wallpaper')
end
print('wallpaper collection loader and manual-mode contracts: PASS')
