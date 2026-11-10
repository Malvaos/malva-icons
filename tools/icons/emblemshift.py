"""Put every emblem on the middle of its own box (emblem_shifts.json, written by centre_emblems.py).

An emblem is drawn in a +-100 box, but the drawings are not all centred on the origin: a presentation board with its
stand reaches 74 down and 60 up, a zip 110 down and 74 up. Placed by their origins, one file type's symbol sat 3 % of
the icon lower than its neighbour's, which reads as a mistake in a row of file icons. So each emblem is moved, in its
own units, by the one centring rule of optical.py (its box on the origin, less a small capped pull of its mass), and
every host (folder, page, drive, symbolic cut) places the origin on the middle of its surface. Nothing places an emblem
by a hand-tuned offset any more: dx and dy are kept at zero.

    apply(EMBLEMS)     move every emblem named in the table (once)
    restore()          put the drawings back as they were drawn (what centre_emblems.py measures)
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

PATH = Path(__file__).with_name("emblem_shifts.json")
ORIGINAL: dict = {}


def table() -> dict:
    return json.loads(PATH.read_text()) if PATH.exists() else {}


def moved(els, dx: float, dy: float):
    tf = f"translate({dx:g} {dy:g})"
    return [replace(e, tf=(tf + " " + e.tf).strip()) for e in els]


def apply(emblems: dict):
    t = table()
    seen = set()
    for name, e in emblems.items():
        if id(e) in seen:
            continue
        seen.add(id(e))
        if e.dx or e.dy:
            raise ValueError(f"emblem {name}: dx/dy are set; emblems are centred by emblem_shifts.json, not by hand")
        row = t.get(name)
        if not row:
            continue
        ORIGINAL.setdefault(id(e), (e, e.els, e.small))
        e.els = moved(e.els, *row["full"])
        if e.small is not None and "small" in row:
            e.small = moved(e.small, *row["small"])


def restore():
    for e, els, small in ORIGINAL.values():
        e.els, e.small = els, small
    ORIGINAL.clear()
