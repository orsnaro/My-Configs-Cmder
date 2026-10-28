-- The desktop editor's logic: it does what the tiles say, by telling Vitreus (which knows how to start a desktop card that is not running) and the widgets' own scenes.
-- A tile is a position: 0 clock, 1 system monitor, 2 audio visualiser (the bottom edge rising into the music), 3 webcam, 4 a new sticky note.
-- (the calendar and the reminders, 4 and 5, are cards of desktopcards.plm: they are switched by its own facts, `cal_shown` and `rem_shown`)
local EVENTS = { "dclock_toggle", "dsys_toggle", "fw_toggle", "cam_toggle", false, false, "sticky_new" }
local CARD_FACT = { [4] = "cal_shown", [5] = "rem_shown" }
local SCENES = { "desktopclock", "desktopsysmon", "vitreus", "webcam" }
local SHOWN = { "shown", "shown", "fw_on", "shown" }      -- the fact that says whether each is on the desktop (the audio visualiser is Vitreus's own: the bottom edge)
-- The scenes whose cards can be dragged in place (`fact edit`): they show the cells they take while the editor is open.
local MOVABLE = { "desktopclock", "desktopsysmon", "desktopcards" }

local function refresh()
    for i, name in ipairs(SCENES) do
        run("pleamar", { "--say", name, "get " .. SHOWN[i] }, function(out, code)
            fact["on" .. (i - 1)] = code == 0 and (out or ""):match("true") ~= nil
        end)
    end
end

local CARDS_PLM = '$HOME/.config/pleamar/shells/vitreus/desktopcards/desktopcards.plm'
local function start_cards()
    run("sh", { "-c", 'PATH="$HOME/.local/bin:$PATH" vitreus-keep "' .. CARDS_PLM .. '" >/dev/null 2>&1 &' }, function() end)
end
local function refresh_cards()
    for tile, key in pairs(CARD_FACT) do
        run("pleamar", { "--say", "desktopcards", "get " .. key }, function(out, code)
            fact["on" .. tile] = code == 0 and (out or ""):match("true") ~= nil
        end)
    end
end
local function edit_widgets(on)
    for _, name in ipairs(MOVABLE) do
        run("pleamar", { "--say", name, "fact edit " .. tostring(on) }, function() end)
    end
end

-- It fires for what the scene sets (Done, Escape) and for what is said from outside (the menu, the key): the widgets are told either way.
on("fact:open", function(v)
    local opened = v and true or false
    edit_widgets(opened)
    if opened then refresh(); refresh_cards() end
end)

on("tile_do", function(i)
    local n = math.floor((tonumber(i) or 0) + 0.5)
    local key = CARD_FACT[n]
    if key then
        -- a card of the calendar / reminders scene: ask how it is, switch it (starting the scene first when it is not running)
        run("pleamar", { "--say", "desktopcards", "get " .. key }, function(out, code)
            if code ~= 0 then
                start_cards()
                after(3000, function()
                    run("pleamar", { "--say", "desktopcards", "fact " .. key .. " true", "fact edit true" }, function() end)
                    after(400, refresh_cards)
                end)
                return
            end
            local on = (out or ""):match("true") ~= nil
            run("pleamar", { "--say", "desktopcards", "fact " .. key .. " " .. (on and "false" or "true") }, function() end)
            after(300, refresh_cards)
        end)
        return
    end
    local ev = EVENTS[n + 1]
    if not ev then return end
    run("pleamar", { "--say", "vitreus", "emit " .. ev }, function() end)
    -- a card that was not running has to be started first: look again a moment later, and once more when it has settled
    after(450, refresh)
    after(1500, refresh)
end)

-- Whether Vitreus has its glass off (then the shelf is flat obsidian): asked of it when this starts, and again a few seconds in.
local function ask_obs()
    run("pleamar", { "--say", "vitreus", "get glass_obs" }, function(out, code)
        if code == 0 and out then fact.obs = out:match("true") ~= nil end
    end)
end
ask_obs()
after(4000, ask_obs)
-- Its colours come from Vitreus too (as facts, see `push_pal` in vitreus.luau).
run("pleamar", { "--say", "vitreus", "emit pal_push" }, function() end)
after(1500, function() run("pleamar", { "--say", "vitreus", "emit pal_push" }, function() end) end)
