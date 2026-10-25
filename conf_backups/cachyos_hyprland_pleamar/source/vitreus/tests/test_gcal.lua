-- The Google agenda is the read-only cache written by ~/.config/gcal/gcal-sync.py.
-- These are the pure date/time rules the Pleamar calendar uses.
local gcal = dofile('logic/gcal.luau')

assert(gcal, 'the Google agenda helper must return its API')
assert(gcal.date_of('2026-10-23T14:00:00+03:00') == '2026-10-23',
       'a timed event belongs to its local calendar date')
assert(gcal.date_of('2026-10-24') == '2026-10-24', 'an all-day date is already a date')
assert(gcal.date_of('not a date') == nil, 'malformed dates are ignored')

local events = {
    { summary = 'Ischool shift', start = '2026-10-23T14:00:00+03:00',
      ['end'] = '2026-10-23T15:00:00+03:00', allDay = false },
    { summary = 'Conference', start = '2026-10-24', ['end'] = '2026-10-26', allDay = true },
    { summary = 'Bad entry', start = '2026-10-23T14:00:00+03:00' },
}

local fri = gcal.on_day(events, '2026-10-23')
assert(#fri == 1, 'only the valid timed event is on Friday')
assert(fri[1].title == 'Ischool shift' and fri[1].time == '2:00pm',
       'the Google row keeps its title and 12-hour time')
assert(fri[1].src == 'google' and fri[1].done == false,
       'Google rows are read-only and marked as Google')

assert(#gcal.on_day(events, '2026-10-24') == 1, 'an all-day event starts on its start date')
assert(#gcal.on_day(events, '2026-10-25') == 1, 'an all-day event covers the days before its exclusive end')
assert(#gcal.on_day(events, '2026-10-26') == 0, 'the all-day end date is exclusive')

local counts = gcal.counts(events)
assert(counts['2026-10-23'] == 1 and counts['2026-10-24'] == 1 and counts['2026-10-25'] == 1,
       'the month dots count each Google day')
assert(counts['2026-10-26'] == nil, 'the exclusive end day gets no dot')

-- Google Tasks: the open ones land on the date part of their due stamp, beside the events.
assert(gcal.tasks_on_day, 'the helper must place tasks on their due day')
assert(gcal.task_counts, 'the helper must count tasks for the month dots')

local tasks = {
    { title = 'Rosemary oil', due = '2026-10-23T00:00:00.000Z', status = 'needsAction' },
    { title = 'Charge the router', due = '2026-10-23T00:00:00.000Z', status = 'completed' },
    { title = 'No date yet', status = 'needsAction' },
    { title = 'Impossible', due = '2026-02-31T00:00:00.000Z', status = 'needsAction' },
}

local friday = gcal.tasks_on_day(tasks, '2026-10-23')
assert(#friday == 1, 'only open tasks with a real due date land on the day')
assert(friday[1].title == 'Rosemary oil' and friday[1].time == 'all day',
       'a task is a whole-day row')
assert(friday[1].src == 'task' and friday[1].done == false,
       'a task is read-only and not done')

assert(#gcal.tasks_on_day(tasks, '2026-10-22') == 0,
       'a task does not spill onto the days around it')

local task_counts = gcal.task_counts(tasks)
assert(task_counts['2026-10-23'] == 1, 'the month dots count the task once')
assert(task_counts['2026-02-31'] == nil, 'an impossible due date gets no dot')

print('gcal tests passed')
