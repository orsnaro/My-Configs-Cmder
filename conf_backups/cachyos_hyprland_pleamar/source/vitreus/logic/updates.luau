-- The About page of the settings (System): the build this shell runs from, and how to update it. Vitreus is a git
-- checkout in its config folder, so its build is that commit plus pleamar's version. Checking is a `git fetch`,
-- updating is `git pull --ff-only` (it will not merge over changes of yours), and after it the shell is restarted
-- through its managed service (after the pull, `install.sh --refresh` sets up what the new version needs). ssh is told
-- not to ask for anything, so a fetch that needs a passphrase fails instead of hanging.
return function(key, with_dirs)
    local A = { busy = false, dir = nil, src = nil, shell_behind = 0, pl_behind = 0 }
    -- pleamar's source folders that matter to this shell: pleamar itself, and pleamar-wm when it is installed (a pleamar-alone install has no pleamar-wm, and nothing to tell about it). (The
    -- installer, `pleamar-update`, also keeps Marea's source, another shell: nothing of Vitreus's to be told about.)
    local SSH = "core.sshCommand=ssh -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=5 -o ServerAliveCountMax=3"

    local function busy(b, msg, patience)
        A.busy = b
        fact.about_busy = b
        if msg then text.about_msg = msg end
        -- A network command that hangs (a connection that stalls instead of failing, on a flaky network) must not leave the page
        -- busy for good, so after a while it lets go of it: the page is usable again, and a late answer only fills in its text.
        A.gen = (A.gen or 0) + 1
        if b then
            local mine = A.gen
            after(patience or 45000, function()
                if A.gen == mine and A.busy then
                    A.busy = false
                    fact.about_busy = false
                    text.about_msg = "That took too long and was given up on. Check the network and try again."
                end
            end)
        end
    end

    local function git(args, cb)
        local full = { "-C", A.dir, "-c", SSH }
        for _, a in ipairs(args) do full[#full + 1] = a end
        run("git", full, cb)
    end

    -- The same, in one of pleamar's source folders (the ones `pleamar-update` keeps).
    local function git_in(repo, args, cb)
        local full = { "-C", A.src .. "/" .. repo, "-c", SSH }
        for _, a in ipairs(args) do full[#full + 1] = a end
        run("git", full, cb)
    end

    -- Is version a ("0.3.11") newer than b ("0.3.9")? Numbers, part by part: as text, 0.3.9 would come out ahead.
    local function newer(a, b)
        local x, y = {}, {}
        for n in a:gmatch("%d+") do x[#x + 1] = tonumber(n) end
        for n in b:gmatch("%d+") do y[#y + 1] = tonumber(n) end
        for i = 1, math.max(#x, #y) do
            local p, q = x[i] or 0, y[i] or 0
            if p ~= q then return p > q end
        end
        return false
    end

    local function lines(out)
        local t = {}
        for l in (out or ""):gmatch("[^\n]+") do t[#t + 1] = l end
        return t
    end

    -- This shell's commit, its branch, whether there is anything of yours not committed, and pleamar's version.
    local function read_build()
        git({ "log", "-1", "--format=%h%n%cd%n%s", "--date=format:%b %d, %Y" }, function(out, code)
            local l = lines(out)
            if code ~= 0 or #l < 3 then
                text.about_commit = "not a git checkout"
                text.about_date = ""
                text.about_sub = ""
                return
            end
            text.about_date = l[2]
            text.about_sub = l[3]
            git({ "rev-parse", "--abbrev-ref", "HEAD" }, function(b)
                local branch = lines(b)[1] or ""
                git({ "status", "--porcelain", "--untracked-files=no" }, function(st)
                    local dirty = #lines(st) > 0
                    text.about_commit = l[1] .. (branch ~= "" and (" · " .. branch) or "") .. (dirty and " · local changes" or "")
                end)
            end)
        end)
        run("pleamar", { "--version" }, function(out)
            text.about_pl = lines(out)[1] or "unknown"
        end)
    end

    local function check(after)
        if A.busy then return end
        busy(true, "Checking…")
        git({ "fetch", "--quiet" }, function(_, code)
            if code ~= 0 then
                fact.about_behind = -1
                return busy(false, "Couldn't reach the remote. Is there a network, and an ssh key that needs no passphrase?")
            end
            git({ "rev-list", "--count", "HEAD..@{u}" }, function(behind, c1)
                git({ "rev-list", "--count", "@{u}..HEAD" }, function(ahead, c2)
                    local n = tonumber(lines(behind)[1] or "")
                    local m = tonumber(lines(ahead)[1] or "") or 0
                    if c1 ~= 0 or n == nil then
                        fact.about_behind = -1
                        return busy(false, "This branch doesn't follow a remote one, so there is nothing to check.")
                    end
                    A.shell_behind = n
                    local msg
                    if n == 0 then msg = nil
                    else msg = n == 1 and "1 shell update available." or (n .. " shell updates available.") end
                    -- Then pleamar itself: its source folders, fetched and counted the same way.
                    A.pl_behind = 0
                    local repos = { "pleamar" }
                    local pl_unreachable = false
                    local function repo(i)
                        local r = repos[i]
                        if not r then
                            -- The source folder being current says nothing about the program that runs: that one only changes when
                            -- `pleamar-update` builds it. So the version it reports is also compared with the one the source holds.
                            run("pleamar", { "--version" }, function(vout)
                                run("grep", { "-m1", "^version", A.src .. "/pleamar/Cargo.toml" }, function(gout)
                                    local have = (vout or ""):match("pleamar (%d[%d%.]*)")
                                    local src = (gout or ""):match('"(%d[%d%.]*)"')
                                    local unbuilt = have ~= nil and src ~= nil and newer(src, have)
                                    local waiting = A.pl_behind
                                    if unbuilt and waiting == 0 then waiting = 1 end
                                    fact.about_behind = A.shell_behind + waiting
                                    A.pl_behind = waiting
                                    local parts = {}
                                    if msg then parts[#parts + 1] = msg end
                                    if unbuilt then
                                        parts[#parts + 1] = "pleamar " .. src .. " is downloaded but not installed (you have " .. have .. ")."
                                    elseif waiting > 0 then
                                        parts[#parts + 1] = "pleamar has " .. waiting .. " update" .. (waiting == 1 and "" or "s") .. "."
                                    end
                                    if pl_unreachable then parts[#parts + 1] = "Couldn't reach pleamar's source to look for newer ones." end
                                    busy(false, #parts > 0 and table.concat(parts, " ") or "Up to date.")
                                    if after then after() end
                                end)
                            end)
                            return
                        end
                        git_in(r, { "fetch", "--quiet" }, function(_, fc)
                            if fc ~= 0 then
                                if r == "pleamar" then pl_unreachable = true end
                                return repo(i + 1)
                            end
                            git_in(r, { "rev-list", "--count", "HEAD..@{u}" }, function(o, rc)
                                local k = tonumber(lines(o)[1] or "")
                                if rc == 0 and k then A.pl_behind = A.pl_behind + k end
                                repo(i + 1)
                            end)
                        end)
                    end
                    run("which", { "pleamar-wm" }, function(_, c)
                        if c == 0 then repos[#repos + 1] = "pleamar-wm" end
                        repo(1)
                    end)
                end)
            end)
        end)
    end

    local function restart()
        text.about_msg = "Restarting…"
        fact.about_busy = true
        -- The service owns the process lifecycle (its ExecStart handles the keeper and the log); quitting and respawning
        -- a detached copy behind systemd's back left the unit pointing at a dead main PID.
        A.restart_gen = (A.restart_gen or 0) + 1
        local gen = A.restart_gen
        run("systemctl", { "--user", "--no-block", "restart", "pleamar.service" }, function(_, code)
            if code ~= 0 then
                A.restarting = false
                fact.about_restarting = false
                busy(false, "Couldn't restart the shell. Try `systemctl --user restart pleamar.service` in a terminal.")
            end
        end)
        -- `--no-block` answers as soon as the job is queued: if this process is not the one the unit owns (a manual run),
        -- it survives and the page would stay on "Restarting…" for ever. A successful restart kills this process first,
        -- so this only unlatches the case where nothing actually happened.
        after(20000, function()
            if gen ~= A.restart_gen or not A.restarting then return end
            A.restarting = false
            fact.about_restarting = false
            busy(false, "The restart did not replace the shell. Try `systemctl --user restart pleamar.service` in a terminal.")
        end)
    end

    on("about_check", function() check() end)
    -- Restart does not wait for a check or an update to finish (or to hang): it is the way out of one, and it only guards
    -- against being pressed twice.
    on("about_restart", function()
        if A.restarting then return end
        A.restarting = true
        fact.about_restarting = true
        restart()
    end)
    on("about_update", function()
        if A.busy or (fact.about_behind or 0) <= 0 then return end
        -- pleamar first, then Vitreus (`pleamar-update` pulls its source and builds it, which takes minutes): the newest
        -- Vitreus files may need the newest pleamar, so they are only pulled once it is in place, and the shell is
        -- only started again after both. If pleamar fails, Vitreus is left as it was.
        local update_shell
        local function pleamar_first()
            if A.pl_behind <= 0 then return update_shell() end
            busy(true, "Updating pleamar: building it, this takes a few minutes…", 1800000)
            -- Every build of pleamar-wm rewrites its Cargo.lock (it records pleamar's version, which upstream commits only now
            -- and then). `pleamar-update` takes a repo with changes as "yours" and does not pull it, so the same updates
            -- would be offered for ever. That file is a build artifact: put it back first.
            local function clean_lock(i)
                local r = ({ "pleamar", "pleamar-wm" })[i]
                if not r then
                    return run("pleamar-update", {}, function(_, code)
                        if code ~= 0 then
                            return busy(false, "Couldn't update pleamar. Try `pleamar-update` in a terminal to see why.")
                        end
                        A.pl_behind = 0
                        update_shell()
                    end)
                end
                git_in(r, { "checkout", "--", "Cargo.lock" }, function() clean_lock(i + 1) end)
            end
            clean_lock(1)
        end
        update_shell = function()
        busy(true, "Updating…")
        if A.shell_behind <= 0 then return restart() end
        -- Which monitors show the bar and the lock screen is kept in the `screens:` line of each scene (the Bar and Lock
        -- screen pages write it, and the choice itself is in bar.json / the lock screen's settings). A line changed that way
        -- is a change of the working tree, and git will not pull over a file it finds changed. So the stock lines are put
        -- back for the pull and the chosen ones written again after it, which is what install.sh does too.
        local BAR_FILE, LOCK_FILE = "/vitreus.plm", "/lockscreen/lockscreen.plm"
        local function screens_in(src, which)
            for line in (src or ""):gmatch("[^\n]+") do
                if which == "bar" then
                    if line:match("^    surface {") then return line:match("screens:%s*([^;]*);") end
                else
                    local v = line:match("^        screens:%s*(.-)%s*$")
                    if v then return v end
                end
            end
        end
        local function plausible(v) return type(v) == "string" and v ~= "" and v:match('^[%w%._%-", ]+$') ~= nil end
        local function write_screens(bar, lock, cb)
            local steps = {}
            if plausible(bar) then
                steps[#steps + 1] = { "-i", "-E", "/^    surface \\{/s/screens: [^;]*;/screens: " .. bar .. ";/", A.dir .. BAR_FILE }
            end
            if plausible(lock) then
                steps[#steps + 1] = { "-i", "-E", "/^        screens: /s/screens: .*/screens: " .. lock .. "/", A.dir .. LOCK_FILE }
            end
            local function nxt(i)
                if not steps[i] then return cb() end
                run("sed", steps[i], function() nxt(i + 1) end)
            end
            nxt(1)
        end
        local function read_file(rel, cb) run("grep", { "-s", "", A.dir .. rel }, function(out) cb(out or "") end) end
        read_file(BAR_FILE, function(bar_now)
            read_file(LOCK_FILE, function(lock_now)
                git({ "show", "HEAD:vitreus.plm" }, function(bar_head)
                    git({ "show", "HEAD:lockscreen/lockscreen.plm" }, function(lock_head)
                        local bar_mine, lock_mine = screens_in(bar_now, "bar"), screens_in(lock_now, "lock")
                        local bar_stock, lock_stock = screens_in(bar_head, "bar"), screens_in(lock_head, "lock")
                        local bar_changed = bar_mine ~= nil and bar_stock ~= nil and bar_mine ~= bar_stock
                        local lock_changed = lock_mine ~= nil and lock_stock ~= nil and lock_mine ~= lock_stock
                        write_screens(bar_changed and bar_stock or nil, lock_changed and lock_stock or nil, function()
                            -- Update means the folder becomes exactly what main is: whatever was changed or committed here is
                            -- overwritten, on purpose (only the screens choice is kept, put into the new files before they replace the old ones).
                            git({ "fetch", "--quiet" }, function(_, fcode)
                            -- The scene reloads itself the moment its file is saved, so the stock `screens:` line must never be on disk,
                            -- not even for the moment between the reset and writing the chosen one: the new files with the chosen lines are
                            -- made first (in .git) and moved over the reset ones in the same command.
                            local keep = [[
cd "$1" || exit 1
g=$(git rev-parse --git-dir) || exit 1
if [ -n "$2" ]; then git show @{u}:vitreus.plm | sed -E "/^    surface \{/s/screens: [^;]*;/screens: $2;/" > "$g/keep-bar" || exit 1; fi
if [ -n "$3" ]; then git show @{u}:lockscreen/lockscreen.plm | sed -E "/^        screens: /s/screens: .*/screens: $3/" > "$g/keep-lock" || exit 1; fi
git reset --hard --quiet @{u} || exit 1
[ -n "$2" ] && mv "$g/keep-bar" vitreus.plm
[ -n "$3" ] && mv "$g/keep-lock" lockscreen/lockscreen.plm
exit 0]]
                            run("setsid", { "-w", "sh", "-c", keep, "sh", A.dir, (bar_changed and plausible(bar_mine)) and bar_mine or "", (lock_changed and plausible(lock_mine)) and lock_mine or "" }, function(_, rcode)
                                local code = fcode ~= 0 and fcode or rcode
                                do
                                    if code ~= 0 then
                                        return busy(false, "Couldn't update: couldn't reach the remote. Check the network and try again.")
                                    end
                                    -- What this version needs besides the pull (new helpers, autostart lines, binds) is what install.sh
                                    -- does without questions or sudo (--refresh); it also says which packages are missing, and the shell
                                    -- tells you once it is back, since only you can install those.
                                    busy(true, "Updating…")
                                    run("setsid", { "-w", "sh", A.dir .. "/install.sh", "--refresh" }, function(out)
                                        local missing = (out or ""):match("vitreus%-missing:([^\n]*)")
                                        if missing and missing:match("^[%w%-%._+ ]+$") then
                                            local pk = missing:gsub("^%s+", "")
                                            run("setsid", { "-f", "sh", "-c", 'sleep 10; notify-send -a Vitreus "Vitreus updated" "Some features need packages: sudo pacman -S $1"', "sh", pk }, function() end)
                                        end
                                        restart()
                                    end)
                                end
                            end)
                            end)
                        end)
                    end)
                end)
            end)
        end)
        end
        pleamar_first()
    end)

    -- A quiet check in the background (a minute and a half after the shell starts, then every six hours): when the remote has commits this
    -- checkout does not, ONE critical notification says so and lists what is new (the commits' subjects, newest first). It is sent once
    -- for each new tip of the remote (kept in update-notified.json), so waiting does not repeat it. Nothing is said when the network is down.
    local function esc(t) return (t:gsub("&", "&amp;"):gsub("<", "&lt;"):gsub(">", "&gt;")) end
    local function announce()
        if A.busy or not A.dir then return end
        git({ "fetch", "--quiet" }, function(_, code)
            if code ~= 0 then return end
            git({ "rev-parse", "@{u}" }, function(head, c0)
                local tip = lines(head)[1]
                if c0 ~= 0 or not tip or not tip:match("^%x+$") then return end
                local ok, saved = pcall(sys.ask, "files.read", "update-notified.json", "json")
                if ok and type(saved) == "table" and saved.tip == tip then return end
                local function tell(subs)
                    if #subs == 0 then return end
                    local body, shown = {}, math.min(#subs, 6)
                    for i = 1, shown do body[i] = "• " .. esc(subs[i]) end
                    if #subs > shown then body[#body + 1] = "…and " .. (#subs - shown) .. " more" end
                    body[#body + 1] = ""
                    body[#body + 1] = "Update it in Settings › About."
                    pcall(sys.call, "files.write", "update-notified.json", { tip = tip })
                    run("notify-send", { "-u", "critical", "-a", "Vitreus", "Vitreus update available", table.concat(body, "\n") }, function() end)
                end
                git({ "log", "--no-merges", "--format=%s", "HEAD..@{u}" }, function(out, c1)
                    if c1 ~= 0 then return end
                    local subs = lines(out)
                    if #subs > 0 then return tell(subs) end
                    -- only merges: say what they say rather than nothing
                    git({ "log", "--format=%s", "HEAD..@{u}" }, function(out2, c2)
                        if c2 == 0 then tell(lines(out2)) end
                    end)
                end)
            end)
        end)
    end
    after(90000, announce)
    every(6 * 3600 * 1000, announce)

    with_dirs(function(d)
        A.dir = d.conf
        A.src = (d.data:gsub("/vitreus$", "/src"))
        read_build()
    end)
end
