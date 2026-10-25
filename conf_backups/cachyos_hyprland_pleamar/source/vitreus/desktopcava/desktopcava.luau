-- The desktop audio visualiser's logic. It runs cava while the visualiser is shown, turns each of its lines into the bars the scene draws (48, and 96 smoothed
-- between them for the wave and the line), and keeps the settings, which Settings > Widgets and the desktop's menu change from outside
-- (`pleamar --say desktopcava "fact sty 2"`).
--
-- `desktopcava.json`, in this scene's own folder (~/.local/share/pleamar/desktopcava): what is missing from it is the default below, and a
-- file that is not there is written so that there is one to edit. It is read when the scene starts.
--   shown   whether the visualiser is on the desktop
--   style   0 bars, 1 mirror, 2 wave, 3 line, 4 dots, 5 radial
--   place   0 bottom, 1 top, 2 left, 3 right, 4 middle
--   size    0 small, 1 medium, 2 large
--   look    0 the shell's glass, 1 accent, 2 light, 3 warm
--   monitor "all" (every monitor draws it), or the name of the one monitor that does (its connector name); one that is not plugged in shows as "all"
local cfg = { shown = false, style = 0, place = 0, size = 1, look = 0, monitor = "all" }
local function clampi(v, lo, hi) return math.max(lo, math.min(hi, math.floor(v + 0.5))) end
do
    local ok, saved = pcall(sys.ask, "files.read", "desktopcava.json", "json")
    if ok and type(saved) == "table" then
        for k, v in pairs(cfg) do
            if type(saved[k]) == type(v) then cfg[k] = saved[k] end
        end
        cfg.style = clampi(cfg.style, 0, 5)
        cfg.place = clampi(cfg.place, 0, 4)
        cfg.size = clampi(cfg.size, 0, 2)
        cfg.look = clampi(cfg.look, 0, 3)
    elseif ok and saved == nil then
        pcall(sys.call, "files.write", "desktopcava.json", cfg)
    end
end
local function save() pcall(sys.call, "files.write", "desktopcava.json", cfg) end

fact.sty = cfg.style
fact.pos = cfg.place
fact.siz = cfg.size
fact.cm = cfg.look
fact.shown = cfg.shown
text.mon_pick = cfg.monitor

-- cava wants its config as a file, in this scene's own data folder (the sandbox has no `os.getenv`, so the folder is asked of the system once).
local CONF = table.concat({
    "[general]", "bars = 48", "framerate = 30",
    "[input]", "method = pipewire",
    "[output]", "method = raw", "raw_target = /dev/stdout", "data_format = ascii",
    "ascii_max_range = 1000", "bar_delimiter = 59", "frame_delimiter = 10",
}, "\n") .. "\n"
pcall(sys.call, "files.write", "cava.conf", CONF)
local conf = nil

local function smooth(b)
    -- twice as many points, a Catmull-Rom curve between the bars, so that the wave and the line read as one smooth shape
    local function at(i) return b[math.max(1, math.min(#b, i))] end
    local out = {}
    for i = 1, #b do
        local p0, p1, p2, p3 = at(i - 1), at(i), at(i + 1), at(i + 2)
        out[#out + 1] = { v = p1 }
        local t = 0.5
        local v = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t)
        out[#out + 1] = { v = math.max(0, math.min(1, v)) }
    end
    return out
end

local quiet = 0
local function on_line(line)
    local b = {}
    for v in string.gmatch(line, "(%d+);") do b[#b + 1] = math.min(1, tonumber(v) / 1000) end
    if #b < 48 then return end
    local top = 0
    for i = 1, 48 do top = math.max(top, b[i]) end
    -- live from the first sound; quiet after two seconds of nothing (the scene fades it out, and then costs nothing)
    if top > 0.03 then
        quiet = 0
        if not fact.live then fact.live = true end
    else
        quiet = quiet + 1
        if quiet > 60 and fact.live then fact.live = false end
    end
    if quiet > 90 then return end
    local rows = {}
    for i = 1, 48 do rows[i] = { v = b[i] } end
    model.bars = rows
    model.pts = smooth(b)
end

-- For finding faults: made-up bars (a wave that travels), without any sound.
local demo_t = 0
every(33, function()
    if not (fact.demo and fact.shown) then return end
    demo_t = demo_t + 0.033
    local b = {}
    for i = 1, 48 do
        local x = i / 48
        b[i] = math.max(0, math.min(1, 0.5 + 0.35 * math.sin(demo_t * 2.4 + x * 9) * math.cos(demo_t * 0.7 + x * 3) + 0.2 * math.sin(demo_t * 5 - x * 20)) * (1 - 0.5 * x))
    end
    fact.live = true
    local rows = {}
    for i = 1, 48 do rows[i] = { v = b[i] } end
    model.bars = rows
    model.pts = smooth(b)
end)

local proc = nil
local function refresh()
    if fact.shown and conf and not proc then
        local mine
        mine = spawn("cava", { "-p", conf }, function(line) if proc == mine then on_line(line) end end,
            function() if proc == mine then proc = nil end end)
        proc = mine
    elseif not fact.shown and proc then
        -- asked to stop, not killed: pleamar only collects a process that leaves by itself
        kill(proc, "term")
        proc = nil
        quiet = 0
        fact.live = false
    end
end

local function conf_ready(base)
    base = (base or ""):gsub("%s+$", "")
    if base == "" then return false end
    conf = base .. "/pleamar/desktopcava/cava.conf"
    refresh()
    return true
end
run("printenv", { "XDG_DATA_HOME" }, function(out, code)
    if code == 0 and conf_ready(out) then return end
    run("printenv", { "HOME" }, function(home)
        conf_ready((home or ""):gsub("%s+$", "") .. "/.local/share")
    end)
end)

-- Where the monitors lie, in the order of the scene's copies (`screen.index`), which is not the order `hyprctl monitors` lists them in: the copies' sizes
-- are read from `pleamar --say desktopcava describe` and matched to hyprctl's monitors by size. Each copy lays the visualiser out against its own
-- monitor's size (a tall monitor is not a wide one turned), and only the copy of the chosen monitor draws it (all of them for "all").
local names = {}
local function pick_monitor()
    local mine = nil
    for k = 1, 4 do if names[k] and names[k] == cfg.monitor then mine = k - 1 end end
    fact.mon = mine or 0
    fact.allm = cfg.monitor == "all" or cfg.monitor == "" or mine == nil
end
local function refresh_monitors()
    run("hyprctl", { "monitors", "-j" }, function(out, code)
        if code ~= 0 or not out then return end
        local ok, list = pcall(json.decode, out)
        if not ok or type(list) ~= "table" then
            -- pleamar-wm's `hyprctl monitors` is text ("Monitor <name> (ID 1):", "2560x1440@164.83 at 1440x730", "scale: 1.00"), its sizes already turned by the rotation.
            ok, list = true, {}
            for name, id, body in (out .. "\n\n"):gmatch("Monitor (%S+) %(ID (%d+)%):\n(.-)\n\n") do
                local w, h = body:match("(%d+)x(%d+)@")
                if w then list[#list + 1] = { id = tonumber(id), name = name, width = tonumber(w), height = tonumber(h), scale = tonumber(body:match("scale:%s*([%d.]+)")) or 1, transform = 0 } end
            end
        end
        if not ok or type(list) ~= "table" or #list == 0 then return end
        table.sort(list, function(a, b) return (a.id or 0) < (b.id or 0) end)
        local mons = {}
        for i, d in ipairs(list) do
            if i > 4 then break end
            local sc = tonumber(d.scale) or 1
            local w, h = (tonumber(d.width) or 0) / sc, (tonumber(d.height) or 0) / sc
            if (tonumber(d.transform) or 0) % 2 == 1 then w, h = h, w end
            mons[i] = { name = d.name, w = math.floor(w + 0.5), h = math.floor(h + 0.5) }
        end
        run("pleamar", { "--say", "desktopcava", "describe" }, function(desc, code2)
            local order = {}
            if code2 == 0 and desc then
                -- each line says which copy it is (`screen N`, the copy's `screen.index`): the copies are not always in the same order from one start to the next
                local used = {}
                for n, w, h in desc:gmatch("%(screen (%d+)%) [^\n]-panel (%d+)\xC3\x97(%d+)") do
                    n, w, h = tonumber(n), tonumber(w), tonumber(h)
                    for i, m in ipairs(mons) do
                        if not used[i] and m.w == w and m.h == h and n < 4 and not order[n + 1] then used[i] = true; order[n + 1] = m; break end
                    end
                end
                for k = 1, #mons do if not order[k] then order = {}; break end end
            end
            if #order ~= #mons then order = mons end   -- (what describe says does not fit: hyprctl's own order)
            names = {}
            for k = 1, 4 do
                local d = order[k]
                fact["m" .. (k - 1) .. "w"] = d and d.w or 0
                fact["m" .. (k - 1) .. "h"] = d and d.h or 0
                names[k] = d and d.name or nil
            end
            pick_monitor()
        end)
    end)
end
refresh_monitors()
every(5000, refresh_monitors)

-- What Settings and the menu tell it (it does not fire for what is set from here).
on("fact:shown", function(v) cfg.shown = v and true or false; save(); refresh() end)
on("fact:sty", function(v) if type(v) == "number" then cfg.style = clampi(v, 0, 5); save() end end)
on("fact:pos", function(v) if type(v) == "number" then cfg.place = clampi(v, 0, 4); save() end end)
on("fact:siz", function(v) if type(v) == "number" then cfg.size = clampi(v, 0, 2); save() end end)
on("fact:cm", function(v) if type(v) == "number" then cfg.look = clampi(v, 0, 3); save() end end)
on("text:mon_pick", function(t) if type(t) == "string" and t ~= "" then cfg.monitor = t; save(); pick_monitor() end end)

-- Whether Vitreus has its glass off (then this is flat obsidian): asked of it when this starts (it says so itself when it changes), and again a few
-- seconds in, for when Vitreus starts after this does.
local function ask_obs()
    run("pleamar", { "--say", "vitreus", "get glass_obs" }, function(out, code)
        if code == 0 and out then fact.obs = out:match("true") ~= nil end
    end)
end
ask_obs()
after(4000, ask_obs)
-- And which theme it has (0 Glass, 1 Retro, 2 UwU): Retro and UwU draw the bars as plastic. Vitreus tells it when the theme changes.
local function ask_look()
    run("pleamar", { "--say", "vitreus", "get cas" }, function(cas, code)
        if code ~= 0 or not cas then return end
        run("pleamar", { "--say", "vitreus", "get uwu" }, function(uwu, code2)
            if code2 ~= 0 or not uwu then return end
            fact.look = cas:match("true") and 1 or (uwu:match("true") and 2 or 0)
        end)
    end)
end
ask_look()
after(4000, ask_look)
