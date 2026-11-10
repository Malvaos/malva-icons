"""Find the kit glyphs that sit visibly off the centre of the 24 grid and write the whole-unit shift that fixes each
(kit_shifts.json). Run after drawing or changing a glyph:   python3 tools/icons/kit_centre.py

A glyph is judged the way check_glyphs.py judges it (a render at 96 px; box = pixels above half the glyph's own ink
opacity), by the best of three centres: its box, its mass (a play triangle is centred by mass) and their mean (an
arrow over a sun: one high, the other low). It needs a shift when all three are more than 0.75 unit from the middle.
The shift is the whole-unit move (up to one unit either side of the box offset, per axis) that leaves the glyph best
centred by that measure.
A level series moves as one, by the shift of its full drawing.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import glyphs_all                                        # noqa: F401  registers every glyph
import glyphkit as K
import kitshift
import check_glyphs as C
from mi_render import Renderer

LIMIT = 0.75                      # units: C.T["centre_max"]
GRID_MID = 12.0


def offsets(g, a):
    b = C.box_of(g, a)
    if b is None:
        return None
    x0, y0, x1, y1 = b
    mx, my = C.mass_centre(a)
    return ((x0 + x1) / 2 - GRID_MID, (y0 + y1) / 2 - GRID_MID), (mx - GRID_MID, my - GRID_MID)


def best(box, mass):
    mean = ((box[0] + mass[0]) / 2, (box[1] + mass[1]) / 2)
    return min(math.hypot(*box), math.hypot(*mean))


def candidates(v: float):
    """Whole-unit shifts worth trying on one axis: none, or either whole unit next to the box offset."""
    return sorted({0.0, float(-math.floor(v)), float(-math.ceil(v))} if abs(v) >= LIMIT else {0.0}, key=abs)


def measure(R, gls):
    arrs = R.render([K.svg(g) for g in gls], 96)
    return {g.id: a[..., 3].astype(float) / 255 for g, a in zip(gls, arrs)}


def plan(R=None):
    kitshift.restore()
    gls = list(K.GLYPHS.values())
    own = R is None
    if own:
        R = Renderer().__enter__()
    try:
        alpha = measure(R, gls)
    finally:
        if own:
            R.__exit__(None, None, None)
    groups = {}
    for g in gls:
        if g.group:
            groups.setdefault(g.group, []).append(g)
    full = {n: max(ms, key=lambda g: alpha[g.id].sum()) for n, ms in groups.items()}
    members = {g.id for n, ms in groups.items() for g in ms if g.id != full[n].id}
    table, report = {}, []
    for g in gls:
        if g.id in members or "anchored" in g.tags.split():
            continue
        o = offsets(g, alpha[g.id])
        if o is None:
            continue
        box, mass = o
        before = best(box, mass)
        if before <= LIMIT:
            continue
        scored = [(best((box[0] + sx, box[1] + sy), (mass[0] + sx, mass[1] + sy)), abs(sx) + abs(sy), (sx, sy))
                  for sx in candidates(box[0]) for sy in candidates(box[1])]
        after, _, s = min(scored)
        if s == (0.0, 0.0) or after > before - 0.2:
            continue
        table[g.id] = list(s)
        report.append((g.id, before, after, s))
        if g.group:
            for m in groups[g.group]:
                table[m.id] = list(s)
    return table, report


def main():
    table, report = plan()
    kitshift.PATH.write_text(json.dumps(dict(sorted(table.items())), indent=1) + "\n")
    for gid, before, after, s in sorted(report, key=lambda r: -r[1]):
        print(f"{gid:40s} off {before:4.2f} -> {after:4.2f}   shift {s[0]:+.0f} {s[1]:+.0f}")
    print(len(table), "glyphs shifted;", len(report), "off-centre drawings found")


if __name__ == "__main__":
    main()
