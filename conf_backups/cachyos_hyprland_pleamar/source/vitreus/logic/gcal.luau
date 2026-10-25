-- The read-only Google agenda that ~/.config/gcal/gcal-sync.py already writes.
-- The Pleamar calendar consumes cache.json; it never refreshes or writes it.
local M = {}

local function parts(date)
    if type(date) ~= "string" then return nil end
    local y, m, d = date:match("^(%d%d%d%d)%-(%d%d)%-(%d%d)")
    if not y then return nil end
    y, m, d = tonumber(y), tonumber(m), tonumber(d)
    if not y or m < 1 or m > 12 or d < 1 or d > 31 then return nil end
    return y, m, d
end

function M.date_of(stamp)
    if type(stamp) ~= "string" then return nil end
    local date = stamp:match("^(%d%d%d%d%-%d%d%-%d%d)")
    if not date then return nil end
    local y, m, d = parts(date)
    if not y then return nil end
    -- Reject impossible dates such as 2026-02-31: os.time normalises them.
    local t = os.time({ year = y, month = m, day = d, hour = 12 })
    local back = os.date("*t", t)
    if back.year ~= y or back.month ~= m or back.day ~= d then return nil end
    return date
end

local function next_day(date)
    local y, m, d = parts(date)
    if not y then return nil end
    local t = os.time({ year = y, month = m, day = d, hour = 12 })
    local n = os.date("*t", t + 86400)
    return string.format("%04d-%02d-%02d", n.year, n.month, n.day)
end

local function clock(stamp)
    local h, m = stamp:match("T(%d%d):(%d%d)")
    if not h then return "all day" end
    h = tonumber(h) % 12
    if h == 0 then h = 12 end
    local suffix = tonumber(stamp:match("T(%d%d):")) < 12 and "am" or "pm"
    return string.format("%d:%02d%s", h, tonumber(m), suffix)
end

local function valid(event)
    if type(event) ~= "table" then return nil end
    if event.status == "cancelled" then return nil end
    local start = M.date_of(event.start)
    if not start then return nil end
    local finish = M.date_of(event["end"])
    if not finish then return nil end
    local all_day = event.allDay == true
    if not all_day and finish < start then finish = start end
    local title = event.summary
    if type(title) ~= "string" or title == "" then title = "(no title)" end
    return {
        start = event.start,
        start_date = start,
        end_date = finish,
        all_day = all_day,
        title = title,
        time = all_day and "all day" or clock(event.start),
        done = false,
        src = "google",
    }
end

-- The Google rows for one day, in start-time order. They are read-only:
-- `done` stays false and the calendar never offers the check/delete zones.
function M.on_day(events, day)
    if type(events) ~= "table" or type(day) ~= "string" then return {} end
    local rows = {}
    for _, event in ipairs(events) do
        local row = valid(event)
        if row then
            local on = row.start_date == day
            if row.all_day then
                on = row.start_date <= day and day < row.end_date
            end
            if on then rows[#rows + 1] = row end
        end
    end
    table.sort(rows, function(a, b)
        if a.start_date ~= b.start_date then return a.start_date < b.start_date end
        if a.all_day ~= b.all_day then return a.all_day end
        if a.start ~= b.start then return a.start < b.start end
        return a.title < b.title
    end)
    return rows
end

-- A Google Task is due on a day, not at an hour: `due` is that date at midnight.
-- Completed and undated tasks have no day in the agenda and are left out, as a
-- Google calendar's task list leaves them out.
local function task_row(task)
    if type(task) ~= "table" then return nil end
    if task.status == "completed" then return nil end
    local due = M.date_of(task.due)
    if not due then return nil end
    local title = task.title
    if type(title) ~= "string" or title == "" then title = "(no title)" end
    return {
        start = task.due,
        start_date = due,
        all_day = true,
        title = title,
        time = "all day",
        done = false,
        src = "task",
    }
end

function M.tasks_on_day(tasks, day)
    if type(tasks) ~= "table" or type(day) ~= "string" then return {} end
    local rows = {}
    for _, task in ipairs(tasks) do
        local row = task_row(task)
        if row and row.start_date == day then rows[#rows + 1] = row end
    end
    table.sort(rows, function(a, b) return a.title < b.title end)
    return rows
end

function M.task_counts(tasks)
    if type(tasks) ~= "table" then return {} end
    local counts = {}
    for _, task in ipairs(tasks) do
        local row = task_row(task)
        if row then counts[row.start_date] = (counts[row.start_date] or 0) + 1 end
    end
    return counts
end

-- How many Google events fall on each day, for the calendar's month dots.
function M.counts(events)
    if type(events) ~= "table" then return {} end
    local counts = {}
    for _, event in ipairs(events) do
        local row = valid(event)
        if row then
            local day = row.start_date
            local last = row.all_day and row.end_date or next_day(row.start_date)
            local guard = 0
            while day and day < last and guard < 370 do
                counts[day] = (counts[day] or 0) + 1
                day = next_day(day)
                guard = guard + 1
            end
        end
    end
    return counts
end

return M
