#!/usr/bin/env python3
"""Writes desktopcava.plm from head.plm.txt (the scene up to its drawing) and the bars below.

A `body` takes only literal shapes (no `repeat`), so the bars of every style are unrolled here.
Run `python3 gen.py` after changing this or the head, then `pleamar --check desktopcava.plm`."""
import os

here = os.path.dirname(os.path.abspath(__file__))

OPEN = """    let slot = len / 48
    let bw = max(2, slot * 0.62)
    let ps = len / 96
    let rr = thk * 0.3
    let rw = max(2, rr * 0.13)
    let gl = if(cm == 0 and ob < 0.5, 1, 0)
    //  A shape inside a body ignores `show`, so what is not in the style in use is put out of the screen (as the clock's digits are).
    let o0 = if(sty == 0, 0, 30000)
    let o1 = if(sty == 1, 0, 30000)
    let o2 = if(sty == 2, 0, 30000)
    let o3 = if(sty == 3, 0, 30000)
    let o4 = if(sty == 4, 0, 30000)
    let o5 = if(sty == 5, 0, 30000)

    //  One body for every look: with the glass on it is the shell's glass (as the system monitor's, flat obsidian when Vitreus has its glass off), otherwise a plain
    //  fill in the accent, the light or the warm colour. The shapes are channels of it, drawn in the frame above as if it sat at the bottom of the screen; the
    //  group turns the frame to its edge. (Written by gen.py: a body takes no `repeat`.)
    group {
        pivot: cx, cy
        rotate: ang * 1deg
        show: vis > 0.01
        body {
            color: if(cm == 0, mix(tint, mix(mix(tint, #000000, 0.7), ink, 0.3), ob * (1 - pl)), if(cm == 1, mint, if(cm == 2, ink, alert)))
            glass: gl
            lens: false
            rim: 70% * gl
            shine: 0, 0
            border: (2 + 1.2 * uk) * pl, deep
            shadow: 4 * pl, 6 - pl, 18 * (1 - pl), 30% + 15% * ob * (1 - gl) + 40% * pl, mix(mix(#000000, deep, pl), #ff6ec7, 0.75 * uk)
            opacity: vis * if(cm == 0 or pl > 0.5, 100%, 85%)
"""


def shapes():
    o = []
    for i in range(48):
        v = f"clamp(bars.{i}.v, 0, 1)"
        x = f"x0 + {i + 0.5} * slot"
        o.append(f"            box {{ at: {x} + o0, y0 - max(bw, {v} * thk) / 2; size: bw, max(bw, {v} * thk); corner: bw / 2 }}")
        o.append(f"            box {{ at: {x} + o1, cy; size: bw, max(bw, {v} * thk); corner: bw / 2 }}")
    for i in range(24):      # dots: 24 columns of eight, each swelling as the bar reaches it
        v = f"clamp(bars.{2 * i}.v, 0, 1)"
        x = f"x0 + {2 * i + 1} * slot"
        for k in range(8):
            lit = f"clamp({v} * 8.4 - {k}, 0, 1)"
            o.append(f"            ellipse {{ at: {x} + o4, y0 - {k + 0.5} * thk / 8; radius: max(1.5, min(bw * 1.6, thk / 8 * 0.8) / 2) * (0.2 + 0.8 * {lit}) }}")
    for i in range(24):      # radial: a ring of bars, the same on both sides
        v = f"clamp(bars.{i}.v, 0, 1)"
        h = f"max(2, {v} * thk * 0.4)"
        a = i * 7.5 + 3.75
        o.append(f"            box {{ at: cx + sin({a}) * (rr + {h} / 2) + o5, cy - cos({a}) * (rr + {h} / 2); size: rw, {h}; corner: rw / 2; rotate: {a} * 1deg }}")
        o.append(f"            box {{ at: cx - sin({a}) * (rr + {h} / 2) + o5, cy - cos({a}) * (rr + {h} / 2); size: rw, {h}; corner: rw / 2; rotate: {-a} * 1deg }}")
    for j in range(96):      # wave (a filled hill of columns) and line (a chain of dots along its top)
        v = f"clamp(pts.{j}.v, 0, 1)"
        x = f"x0 + {j + 0.5} * ps"
        o.append(f"            box {{ at: {x} + o2, y0 - max(2, {v} * thk) / 2; size: ps + 0.8, max(2, {v} * thk); corner: ps / 2 }}")
        o.append(f"            ellipse {{ at: {x} + o3, y0 - max(2, {v} * thk); radius: max(2, ps * 0.45) }}")
    return "\n".join(o)


head = open(os.path.join(here, "head.plm.txt")).read()
open(os.path.join(here, "desktopcava.plm"), "w").write(head + OPEN + shapes() + "\n        }\n    }\n}\n")
