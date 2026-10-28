-- Drive the production window-title controller at its service boundary.
local watch
fact, text = { bar_title_revision = 0 }, {}
sys = { watch = function(name, callback)
    assert(name == "window")
    watch = callback
end }
local controller = dofile("logic/bar_title.luau")()
assert(watch, "title input must follow the native window service")
local title = string.rep("مرحبا 🌟 ", 8) .. "full title ending"
watch({ title = title .. "  ", class = "editor", monitor = "DP-2" })
assert(text.bar_title_full == title, "the complete UTF-8 title must reach the scene")
assert(utf8.len(text.win_title30) == 30, "compact and vertical title stays UTF-8 safe")
local revision = fact.bar_title_revision
assert(revision > 0, "a new title must invalidate its previous tooltip")
watch({ title = title, class = "editor", monitor = "DP-2", fullscreen = true })
assert(fact.bar_title_revision == revision, "fullscreen-only changes must not restart")
controller.focus("123abc")
revision = fact.bar_title_revision
controller.focus("123abc")
assert(fact.bar_title_revision == revision, "duplicate focus events must not restart")
controller.focus("456def")
assert(fact.bar_title_revision == revision + 1, "equal-title windows restart by address")
watch({ title = "Short", class = "editor" })
assert(text.bar_title_full == "Short" and text.win_title30 == "Short")
watch(nil)
assert(text.bar_title_full == "" and text.win_title30 == "", "no focus clears the title")
watch({ title = "bad\255", class = "editor" })
assert(text.bar_title_full == "", "invalid UTF-8 must not reach the renderer")
watch({ title = title, class = "editor", list = { { id = "a", active = true } } })
revision = fact.bar_title_revision
watch({ title = title, class = "editor", list = { { id = "b", active = true } } })
assert(fact.bar_title_revision == revision + 1, "foreign-toplevel focus identity also restarts")
revision = fact.bar_title_revision
dofile("logic/bar_title.luau")()
watch({ title = title, class = "editor" })
assert(fact.bar_title_revision > revision, "logic reload must not reuse a previous revision")
-- The main logic also uses its existing UTF-8 cutter for launcher response previews.
local source_file = assert(io.open("vitreus.luau"))
local source = source_file:read("*a")
source_file:close()
local helper = source:match("(cut_utf8 = function%(s, limit%).-\nend)")
assert(helper, "launcher response previews must keep their shared UTF-8 cutter")
local cut = assert(load(helper .. "\nreturn cut_utf8", "launcher cutter", "t", { utf8 = utf8 }))()
assert(cut("Short", 600) == "Short")
assert(utf8.len(cut(string.rep("مرحبا 🌟 ", 100), 600)) == 600)
print("PASS: full Unicode title, compact fallback, focus identity and irrelevant updates")
