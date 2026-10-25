"""Preview selections must export the same pixels, including non-16:9 edges.

Evaluate the scene's actual geometry using Pleamar's documented atlas fitting
rule, then execute Snap's real capture/export Lua against synthetic PNGs.
Only desktop-facing command boundaries are replaced; no screen is captured.
"""
from __future__ import annotations

import binascii
import os
import re
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENE = ROOT / "snap" / "snap.plm"
LOGIC = ROOT / "snap" / "snap.luau"
LUA_BIN = shutil.which("lua5.4") or shutil.which("lua")
MAGICK = shutil.which("magick")
TEMP_ROOT = "/tmp/opencode" if Path("/tmp/opencode").is_dir() else None
Rect = tuple[float, float, float, float]

LUA = r'''
local mode = arg[2]
local values = { phase = 0, shotw = 0, shoth = 0, typing = 0,
    scrw = 1440, vs = 1, vx = 0, vy = 0, sx = 0, sy = 0, sw = 1440, sh = 900 }
for i, name in ipairs({ "sx", "sy", "sw", "sh", "scrw", "vs", "vx", "vy" }) do
    if arg[i + 2] then values[name] = tonumber(arg[i + 2]) end
end
local order, handlers, commands = {}, {}, {}
fact = setmetatable({}, {
    __index = values,
    __newindex = function(_, key, value)
        values[key] = value
        order[#order + 1] = "fact." .. key
    end,
})
text = setmetatable({}, { __newindex = function(self, key, value)
    rawset(self, key, value)
    order[#order + 1] = "text." .. key
end })
model = {}
function on(name, callback) handlers[name] = callback end
function after() end
function run(command, args, callback)
    if command == "sh" and args[2]:find("SNAP_DIR", 1, true) then
        if mode == "script" then io.write(args[2]); return end
        callback(os.getenv("CAPTURE_RESULT") or "", 0)
    elseif command == "magick" then
        for _, value in ipairs(args) do commands[#commands + 1] = value end
    elseif command == "sh" then
        callback("", 0) -- palette lookup; never execute clipboard/save scripts
    elseif command == "notify-send" then
        callback("", 0)
    elseif command ~= "pleamar" then
        error("Unexpected external command: " .. command)
    end
end
dofile(arg[1])
if mode ~= "script" then
    print("SIZE\t" .. fact.shotw .. "\t" .. fact.shoth)
    print("PHASE\t" .. fact.phase)
    print("PATH\t" .. (text.shot_path or ""))
    print("ORDER\t" .. table.concat(order, ","))
    if mode == "export" and text.shot_path then handlers.do_copy() end
    for _, value in ipairs(commands) do print("ARG\t" .. value) end
end
'''


def choose(condition: bool, yes: float, no: float) -> float:
    return yes if condition else no


def evaluate(expression: str, scope: dict[str, float | bool]) -> float | bool:
    expression = re.sub(r"\bif\s*\(", "choose(", expression)
    return eval(expression, {"__builtins__": {}, "max": max, "min": min, "choose": choose}, scope)


def visible_preview(source: tuple[int, int], rect: Rect) -> Rect:
    """Evaluate production draw expressions, then the renderer's atlas fit."""
    scene = SCENE.read_text()
    component = re.search(r"component FrozenPicture\([^\n]+\) \{(.*?)\n    \}", scene, re.S)
    scope: dict[str, float | bool] = dict(zip(("x", "y", "w", "h"), rect))
    scope.update(shotw=source[0], shoth=source[1], W=rect[2], H=rect[3], phase=2, full=0)
    if component:
        body = component.group(1)
        for name, expression in re.findall(r"^\s*let (\w+) = ([^\n]+)", body, re.M):
            scope[name] = evaluate(expression.split("//")[0].strip(), scope)
    else:
        # Characterize the old region preview too, so RED reports the actual
        # 72px edge loss rather than failing just because a component is absent.
        body = scene
    for name, properties in re.findall(r"image (shotv?) \{([^}]+)\}", body):
        fields = dict(part.strip().split(":", 1) for part in properties.split(";") if ":" in part)
        if not evaluate(fields["show"].strip(), scope):
            continue
        x, y = (float(evaluate(item.strip(), scope)) for item in fields["at"].split(","))
        w, h = (float(evaluate(item.strip(), scope)) for item in fields["size"].split(","))
        cell = re.search(rf"image {name} = from shot_path, (\d+), (\d+)", scene)
        assert cell is not None
        cw, ch = (int(value) for value in cell.groups())
        scale = min(cw / source[0], ch / source[1])
        vw, vh = source[0] * scale * w / cw, source[1] * scale * h / ch
        return x + (w - vw) / 2, y + (h - vh) / 2, vw, vh
    raise AssertionError("No visible screenshot image")


def preview_rectangles(scene: str) -> list[Rect]:
    component = re.search(r"component FrozenPicture\([^\n]+\) \{.*?\n    \}", scene, re.S)
    if component:
        scene = scene[:component.start()] + scene[component.end():]
    scope: dict[str, float | bool] = {"W": 1440, "H": 900, "vx": 132.8, "vy": 36, "vs": 734 / 900}
    return [tuple(float(evaluate(value.strip(), scope)) for value in args.split(","))
            for args in re.findall(r"FrozenPicture\(([^)]+)\)", scene)]


def png(width: int, height: int) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", binascii.crc32(kind + data))

    row = b"\x00" + b"\xff\x00\x00" + b"\x00\xff\x00" * (width - 2) + b"\x00\x00\xff"
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(row * height)) + chunk(b"IEND", b""))


class SnapGeometryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not LUA_BIN or not MAGICK:
            raise RuntimeError("Snap geometry tests require Lua and ImageMagick 7 (magick)")
        cls.capture_script = subprocess.run(
            [LUA_BIN, "-", str(LOGIC), "script"], input=LUA, capture_output=True,
            text=True, check=True, timeout=5,
        ).stdout

    def exercise(self, image: bytes, selection: tuple[float, ...] = (), *,
                 render: bool = False) -> dict[str, object]:
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as tmp:
            root = Path(tmp)
            tools = root / "bin"
            tools.mkdir()
            source = root / "fixture.png"
            source.write_bytes(image)
            grim = tools / "grim"
            grim.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$GRIM_ARGS"\n'
                            'for last do :; done\ncp "$FIXTURE" "$last"\n')
            grim.chmod(0o755)
            pleamar = tools / "pleamar"
            pleamar.write_text("#!/bin/sh\nexit 0\n")
            pleamar.chmod(0o755)
            env = os.environ | {
                "PATH": f"{tools}:{os.environ['PATH']}", "HOME": str(root),
                "SNAP_DIR": str(root / "capture"), "SNAP_OUTPUT": "DP-1",
                "SNAP_LOOK": "8", "SNAP_FULL": "0", "SNAP_WINDOWS": "0 0 100 100",
                "FIXTURE": str(source), "GRIM_ARGS": str(root / "grim-args"),
            }
            for name in ("SNAP_NO_CAPTURE", "SNAP_NOT_BEFORE", "HYPRLAND_INSTANCE_SIGNATURE"):
                env.pop(name, None)
            capture = subprocess.run(["sh", "-c", self.capture_script], env=env,
                                     capture_output=True, text=True, check=True, timeout=5)
            result = subprocess.run(
                [LUA_BIN, "-", str(LOGIC), "export", *(str(value) for value in selection)],
                input=LUA, env=env | {"CAPTURE_RESULT": capture.stdout},
                capture_output=True, text=True, check=True, timeout=5,
            )
            fields: dict[str, object] = {}
            args: list[str] = []
            for line in result.stdout.splitlines():
                key, value = line.split("\t", 1)
                if key == "ARG":
                    args.append(value)
                else:
                    fields[key] = value
            fields["args"] = args
            fields["grim"] = (root / "grim-args").read_text().splitlines()
            if render:
                subprocess.run([MAGICK, *args], check=True, capture_output=True, timeout=10)
                output = Path(args[-1])
                fields["output_size"] = struct.unpack(">II", output.read_bytes()[16:24])
                fields["edges"] = subprocess.run(
                    [MAGICK, str(output), "-format",
                     f"%[pixel:p{{0,0}}]|%[pixel:p{{{fields['output_size'][0] - 1},0}}]", "info:"],
                    capture_output=True, text=True, check=True, timeout=5,
                ).stdout
            return fields

    def test_preview_fills_the_same_rectangle_on_all_aspect_ratios(self) -> None:
        for source, rect in (
            ((1440, 900), (0, 0, 1440, 900)),
            ((1366, 768), (0, 0, 1366, 768)),
            ((2560, 1440), (0, 0, 2560, 1440)),
            ((1080, 1920), (0, 0, 1080, 1920)),
            ((1200, 1920), (0, 0, 1200, 1920)),
            ((2880, 1800), (0, 0, 1440, 900)),
            ((2160, 1350), (0, 0, 1440, 900)),
            ((1440, 900), (132.8, 36, 1174.4, 734)),
        ):
            with self.subTest(source=source, rect=rect):
                for actual, expected in zip(visible_preview(source, rect), rect):
                    self.assertAlmostEqual(actual, expected, places=7)

    def test_dp1_preview_selection_exports_both_original_edges(self) -> None:
        x, _, width, _ = visible_preview((1440, 900), (0, 0, 1440, 900))
        result = self.exercise(png(1440, 900), (x, 100, width, 201, 1440, 1, 0, 0), render=True)
        self.assertEqual(result["args"][2], "1440x201+0+100")
        self.assertEqual(result["output_size"], (1440, 201))
        self.assertEqual(result["edges"], "srgb(255,0,0)|srgb(0,0,255)")

    def test_capture_publishes_both_dimensions_before_the_picture(self) -> None:
        result = self.exercise(png(1440, 900))
        self.assertEqual(result["SIZE"], "1440\t900")
        order = result["ORDER"].split(",")
        self.assertLess(order.index("fact.shotw"), order.index("text.shot_path"))
        self.assertLess(order.index("fact.shoth"), order.index("text.shot_path"))
        self.assertEqual(result["grim"][:3], ["-c", "-l", "0"])
        self.assertTrue(result["args"][0].endswith("/capture/shot.png"))

    def test_incomplete_or_zero_dimensions_never_show_a_picture(self) -> None:
        for image in (png(1440, 900)[:20], b"", b"\x00" * 16 + struct.pack(">II", 0, 900)):
            with self.subTest(header=image[:24]):
                result = self.exercise(image)
                self.assertEqual(result["PATH"], "")
                self.assertEqual(result["PHASE"], "0")
                self.assertEqual(result["args"], [])

    def test_scaled_and_inset_exports_keep_original_pixel_coordinates(self) -> None:
        cases = (
            ((2880, 1800), (100, 50, 400, 200, 1440, 1, 0, 0), "800x400+200+100"),
            ((2160, 1350), (100, 50, 400, 200, 1440, 1, 0, 0), "600x300+150+75"),
            ((1440, 900), (132.8, 36, 1174.4, 734, 1440, 734 / 900, 132.8, 36), "1440x900+0+0"),
        )
        for source, selection, expected in cases:
            with self.subTest(source=source, selection=selection):
                self.assertEqual(self.exercise(png(*source), selection)["args"][2], expected)

    def test_all_preview_paths_share_the_corrected_geometry(self) -> None:
        scene = SCENE.read_text()
        component = re.search(r"component FrozenPicture\([^\n]+\) \{.*?\n    \}", scene, re.S)
        self.assertIsNotNone(component, "Region/full-screen/window previews need the same correction")
        outside = scene[:component.start()] + scene[component.end():]
        self.assertEqual(re.findall(r"image shotv? \{", outside), [])
        self.assertEqual(len(re.findall(r"FrozenPicture\(", outside)), 4)

    def test_each_preview_path_passes_its_actual_rectangle(self) -> None:
        expected: list[Rect] = [(0, 0, 1440, 900), (0, 0, 1440, 900),
                                (132.8, 36, 1174.4, 734), (0, 0, 1440, 900)]
        actual = preview_rectangles(SCENE.read_text())
        self.assertEqual(len(actual), len(expected))
        for rectangle, wanted in zip(actual, expected):
            for value, correct in zip(rectangle, wanted):
                self.assertAlmostEqual(value, correct, places=7)


if __name__ == "__main__":
    unittest.main()
