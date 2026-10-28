-- Window input only; full/compact UTF-8 titles update without a rendering loop.
return function()
    local revision = tonumber(fact.bar_title_revision) or 0
    local last_title, last_class, last_id = nil, nil, nil

    local function restart()
        revision = revision + 1
        fact.bar_title_revision = revision
    end

    local function focus(id)
        if id ~= last_id then
            last_id = id
            restart()
        end
    end

    sys.watch("window", function(w)
        local title = ((w and w.title) or ""):gsub("%s+$", "")
        local length = utf8.len(title)
        if not length then title, length = "", 0 end
        local class = (w and w.class) or ""
        local id = last_id
        for _, window in ipairs((w and w.list) or {}) do
            if window.active then id = window.id; break end
        end
        text.bar_title_full = title
        local stop = length > 30 and utf8.offset(title, 31) or nil
        text.win_title30 = stop and title:sub(1, stop - 1) or title
        if title ~= last_title or class ~= last_class or id ~= last_id then
            last_title, last_class, last_id = title, class, id
            restart()
        end
    end)

    return { focus = focus }
end
