-- The wallpaper hook: an add-on with `[wallpaper] frames = true` in its addon.toml is asked for the picture awww shows whenever Vitreus sets a
-- wallpaper (a pick, Random, the slideshow, the picker; not a card's quick try). It answers with a picture it made (a frame, an effect) or the
-- one it was given. While it works the old wallpaper stays; after 30 s with neither an answer nor `wph_busy`, or with the add-on gone, the
-- plain one is shown. `wph.rec` (vitreus.luau) keeps the picture it made and the wallpaper it came from: Iris and the page read the wallpaper.
--   shell -> add-on:  text wph_path, text wph_src, emit wph_frame <n>;  text wph_cur (on change, and every 10 s)
--   add-on -> shell:  text wph_out + emit wph_done <n>;  emit wph_busy <n>;  emit wph_again
return function(wp_apply, wp_cur)
    local WAIT = 30
    local n = 0
    local waiting = nil                        -- the request out: { id, path, src, show, skip, at }
    local function say(sock, cmds)
        local args = { "--say", sock }
        for _, c in ipairs(cmds) do args[#args + 1] = c end
        run("pleamar", args, function() end)
    end
    local function id_of(v) return math.floor((tonumber(v) or -1) + 0.5) end
    local function finish(w, pic)
        if waiting ~= w then return end
        waiting = nil
        wph.busy = false
        w.show(pic)
    end

    wph.frame = function(path, src, show, skip)
        local sock = addon_framer and addon_framer()
        if not sock then show(src) return end
        local real = wph.src_of(path)          -- a picture an add-on made: ask about its wallpaper (a frame is never framed again)
        if real and not wpv.is(real) then path, src = real, real end
        n = n + 1
        local w = { id = n, path = path, src = src, show = show, skip = skip, at = os.time() }
        local old = waiting
        waiting = w                            -- an older one still out is dropped: its answer no longer matches
        wph.busy = true
        if old and old.skip then old.skip() end
        say(sock, { "text wph_path " .. path, "text wph_src " .. src, "emit wph_frame " .. w.id })
    end

    on("wph_done", function(id)
        local w = waiting
        if not w or id_of(id) ~= w.id then return end
        local out = text.wph_out or ""
        if out == "" then finish(w, w.src) return end
        run("test", { "-s", out }, function(_, code)
            if code ~= 0 then finish(w, w.src) return end
            if waiting == w and out ~= w.src then
                -- (a local, written from: a handler reads the global table `wph.rec` as it was when this module loaded, so reading it back here would give the old record)
                local rec = { out = out, src = w.path }
                wph.rec = rec
                pcall(sys.call, "files.write", "wallpaper-frame.json", rec)
            end
            finish(w, out)
        end)
    end)
    on("wph_busy", function(id)
        local w = waiting
        if w and id_of(id) == w.id then w.at = os.time() end
    end)
    on("wph_again", function()
        local cur = wp_cur()
        if cur then wp_apply(cur) end
    end)

    local last_cur, last_sock, last_at = nil, nil, 0
    every(1000, function()
        local sock = addon_framer and addon_framer()
        local w = waiting
        if w and (not sock or os.time() - w.at > WAIT) then finish(w, w.src) end
        local cur = wp_cur()
        if sock and cur and (cur ~= last_cur or sock ~= last_sock or os.time() - last_at >= 10) then
            last_cur, last_sock, last_at = cur, sock, os.time()
            say(sock, { "text wph_cur " .. cur })
        end
    end)
end
