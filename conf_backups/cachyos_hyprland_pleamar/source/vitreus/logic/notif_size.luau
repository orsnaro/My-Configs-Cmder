-- How big a notification is (Settings > Notifications, "Size", beside the test button): the drawer and what it holds are drawn at
-- `nt_size` of their size (vitreus.plm, `nk`). Kept in notif-size.json, in Vitreus's data folder, and put back when it starts.
-- The chips send 0, 1 or 2; the fact can be set from outside too (`pleamar --say vitreus "fact nt_size 0.8"`) and is kept.
return function()
    local SIZES = { [0] = 0.7, [1] = 0.85, [2] = 1 }
    local size = 1
    local function norm(v) return math.floor(math.max(0.5, math.min(1, tonumber(v) or 1)) * 100 + 0.5) / 100 end

    local ok, saved = pcall(sys.ask, "files.read", "notif-size.json", "json")
    if ok and type(saved) == "table" and type(saved.size) == "number" then size = norm(saved.size) end
    fact.nt_size = size
    local function save() pcall(sys.call, "files.write", "notif-size.json", { size = size }) end

    on("nt_size_set", function(i)
        local v = SIZES[math.floor((tonumber(i) or 2) + 0.5)]
        if not v then return end
        size = v
        fact.nt_size = size
        save()
    end)
    on("fact:nt_size", function(v)
        local n = norm(v)
        if n ~= size then size = n; save() end
    end)
end
