"""Optical centring of the object icons, measured on rendered pixels.
Each icon is moved so its bounding box sits on the middle of the canvas, less a small capped pull of its mass (the one
rule of optical.py, shared with the app glyphs and the tiles), in whole canvas units, when that shift is 6 units or more.
Icons that are two states of one thing (the bin empty and full) move together, by the mean of their shifts, so the part
that does not change (the can) stays where it is when the state does.
Run: python3 tools/icons/centre_objects.py   (writes object_shifts.json)"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import objects as O
import optical
from objfmt import object_svg, CANVAS
from mi_render import Renderer

S = 512


def measure(R, ids):
    objs = [O.OBJECTS[i] for i in ids]
    for o in objs:
        o.shift = (0.0, 0.0)
    arr = R.render([object_svg(o) for o in objs], S)
    out = {}
    k = CANVAS / S
    for i, a in zip(ids, arr):
        al = a[..., 3].astype(float)
        ys, xs = np.nonzero(al > 127)
        bx, by = (xs.min() + xs.max() + 1) / 2 * k, (ys.min() + ys.max() + 1) / 2 * k
        mx = (al * np.arange(S)[None, :]).sum() / al.sum() * k + k / 2
        my = (al * np.arange(S)[:, None]).sum() / al.sum() * k + k / 2
        out[i] = (optical.shift(bx - CANVAS / 2, mx - CANVAS / 2, CANVAS), optical.shift(by - CANVAS / 2, my - CANVAS / 2, CANVAS))
    return out


PAIRS = (("trash-empty", "trash-full"),)          # states of one object: they share one shift


def main():
    with Renderer() as R:
        m = measure(R, O.ORDER)
    for pair in PAIRS:
        if all(p in m for p in pair):
            mean = tuple(sum(m[p][k] for p in pair) / len(pair) for k in (0, 1))
            for p in pair:
                m[p] = mean
    shifts = {}
    for i, (sx, sy) in m.items():
        sx = round(sx) if abs(sx) >= 6 else 0
        sy = round(sy) if abs(sy) >= 6 else 0
        if sx or sy:
            shifts[i] = [float(sx), float(sy)]
    (Path(__file__).with_name("object_shifts.json")).write_text(json.dumps(shifts, indent=1, sort_keys=True) + "\n")
    print(len(shifts), "of", len(m), "icons shifted:", {k: v for k, v in list(shifts.items())[:6]}, "...")


if __name__ == "__main__":
    main()
