"""Whole-unit shifts that put a kit glyph where it belongs on the 24 grid (kit_shifts.json, written by kit_centre.py).

A glyph that sits a unit low, high or to one side looks like a mistake in a row of its neighbours: the box of the
drawing, not its mass, is what the eye reads against the edge of a button. The shifts are whole units, so a stroke
whose centre-line was on a whole coordinate stays on one and the glyph is as crisp at 24 px as it was.

A level series (wifi, battery ...) moves as one: every member gets the shift of the full drawing, so the levels keep
sharing one anchor. The mirrored `-rtl` copy is made from the shifted drawing, so it is shifted the other way.

    apply()      shift every glyph named in the table (once)
    restore()    put the drawings back as they were drawn (what kit_centre.py measures)
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import glyphkit as K

PATH = Path(__file__).with_name("kit_shifts.json")
ORIGINAL: dict = {}


def table() -> dict:
    return json.loads(PATH.read_text()) if PATH.exists() else {}


def moved(parts, dx: float, dy: float):
    return [replace(p, d=K.xf(p.d, dx=dx, dy=dy)) for p in parts]


def apply(extra: dict | None = None):
    """Shift the registered glyphs, and the entries of `extra` (a dict of id -> parts, such as tiles.EXTRA), in place."""
    for gid, (dx, dy) in table().items():
        if gid in K.GLYPHS:
            g = K.GLYPHS[gid]
            ORIGINAL.setdefault(gid, g.parts)
            g.parts = moved(ORIGINAL[gid], dx, dy)
        elif extra is not None and gid in extra:
            ORIGINAL.setdefault("extra:" + gid, extra[gid])
            extra[gid] = moved(ORIGINAL["extra:" + gid], dx, dy)


def restore(extra: dict | None = None):
    for gid, parts in ORIGINAL.items():
        if gid.startswith("extra:"):
            if extra is not None:
                extra[gid[6:]] = parts
        else:
            K.GLYPHS[gid].parts = parts
    ORIGINAL.clear()
