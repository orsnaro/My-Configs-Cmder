-- The bar's position (Settings > Bar): along the top (the default, the Island), or a strip on any of the four edges with a frame round
-- the rest of the screen. The surface's anchor follows `bar_anchor`, so it moves without being recreated. The panels hang from the top edge
-- in the first, their edge by the strip in the others; `lp_w` is how wide the one last opened is, so that they line up. Kept in bar-position.json
-- (`pos`: "top", "left", "right", "ftop" or "fbottom"; an older file only has `left`).
return function()
    -- pos: "top" is the Island; "left", "right", "ftop" and "fbottom" are the strip on that edge with a frame round the rest.
    local POS = { [0] = "top", "left", "right", "ftop", "fbottom" }
    local EDGE = { top = { "top", false }, left = { "left", true }, right = { "right", true }, ftop = { "top", true }, fbottom = { "bottom", true } }
    local pos = "top"
    local function show()
        local e = EDGE[pos] or EDGE.top
        fact.bar_anchor = e[1]
        fact.bar_frame = e[2]
        bar_fx.left = e[2]
        bar_fx.edge = e[1]
        -- the desktop scenes keep their widgets' grid out of the bar's room (`room_*`): told again whenever the bar moves. (A fact the logic sets itself
        -- does not fire `on("fact:bar_anchor")`, so it has to be said from here.)
        if iris_fx and iris_fx.push_room then iris_fx.push_room() end
    end
    local ok, saved = pcall(sys.ask, "files.read", "bar-position.json", "json")
    if ok and type(saved) == "table" then
        if type(saved.pos) == "string" and EDGE[saved.pos] then pos = saved.pos
        elseif saved.left == true then pos = "left" end
    end
    show()
    -- What the gaps round the windows were, to give back up on the top: read once, before anything of ours changes them. If the
    -- active edge already has the frame's wide gap, it is the file we wrote on a previous run, not the original; use the usual 16 then.
    run("hyprctl", { "getoption", "general:gaps_out", "-j" }, function(out, code)
        local g = { 16, 16, 16, 16 }
        if code == 0 and out then
            local css = out:match('"css":%s*"([^"]*)"')
            local n = {}
            for v in (css or ""):gmatch("%d+") do n[#n + 1] = tonumber(v) end
            if #n == 4 then
                local edge = ({ top = 1, right = 2, bottom = 3, left = 4 })[bar_fx.edge] or 1
                local frame = EDGE[pos] and EDGE[pos][2]
                local ours = frame and n[edge] and n[edge] >= 60
                if not ours then g = n end
            end
        end
        bar_fx.orig = g
        iris_fx.apply_hypr()
    end)
    on("bar_pick_pos", function(i)
        pos = POS[math.floor(i + 0.5)] or "top"
        pcall(sys.call, "files.write", "bar-position.json", { pos = pos, left = pos == "left" })
        show()
        iris_fx.apply_hypr()
    end)
end
