"""Measure every emblem and write the shift that centres it on its own origin (emblem_shifts.json).

The emblem is rendered alone, as the page template draws it (full and small cut), and its box and mass are measured on
the pixels (alpha above one half). The shift is optical.shift: the box on the origin, less a capped pull of the mass,
in the emblem's own units (the render is at scale 2.2 x the emblem's own size factor, so the cap of 1 % of the 1024
canvas is about 4 units).
Run after drawing or changing an emblem:   python3 tools/icons/centre_emblems.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import emblems as E
import emblemshift
import objfmt as F
import optical
from mi_render import Renderer

CANVAS, S, SCALE = 1024, 1024, 2.2


def _svg(els, small, s):
    o = F.Obj("emb", "emb", "files", lambda uid, sm: [F.emblem_part(els, uid, CANVAS / 2, CANVAS / 2, SCALE * s, "#000000",
                                                                  deboss=False, small=sm)], lambda: [])
    return F.object_svg(o, small=small)


def _shift(a, s):
    al = a[..., 3].astype(float)
    ys, xs = np.nonzero(al > 127)
    if not len(xs):
        raise ValueError("an emblem rendered empty")
    k = CANVAS / S
    bx, by = (xs.min() + xs.max() + 1) / 2 * k, (ys.min() + ys.max() + 1) / 2 * k
    mx = (al * np.arange(S)[None, :]).sum() / al.sum() * k + k / 2
    my = (al * np.arange(S)[:, None]).sum() / al.sum() * k + k / 2
    sc = SCALE * s
    return [round(optical.shift(bx - CANVAS / 2, mx - CANVAS / 2, CANVAS) / sc * 2) / 2,
            round(optical.shift(by - CANVAS / 2, my - CANVAS / 2, CANVAS) / sc * 2) / 2]


def plan(R):
    emblemshift.restore()
    jobs, seen = [], set()
    for name, e in E.EMBLEMS.items():
        if id(e) in seen:
            continue
        seen.add(id(e))
        jobs.append((name, "full", _svg(e.els, False, e.s), e.s))
        if e.small is not None:
            jobs.append((name, "small", _svg(e.small, True, e.s), e.s))
    arr = R.render([j[2] for j in jobs], S)
    table = {}
    for (name, cut, _svg_, s), a in zip(jobs, arr):
        table.setdefault(name, {})[cut] = _shift(a, s)
    return table


def main():
    with Renderer() as R:
        table = plan(R)
    emblemshift.PATH.write_text(json.dumps(dict(sorted(table.items())), indent=1, sort_keys=True) + "\n")
    worst = sorted(((max(abs(v[0]), abs(v[1])), n, c, v) for n, d in table.items() for c, v in d.items()), reverse=True)[:8]
    print(len(table), "emblems measured; largest shifts (own units):")
    for m, n, c, v in worst:
        print(f"  {n:14s} {c:5s} {v}")


if __name__ == "__main__":
    main()
