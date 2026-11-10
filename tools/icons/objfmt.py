"""The Malva object-icon format: folders, storage, people and files.

App icons (appfmt.py) are tiles: a glyph on a coloured squircle. Objects are not tiles. A folder, a drive, a person
and a page are drawn as themselves, on a 1024 canvas, in three materials taken from the brand kit:

  * orchid  = containers  (folders, bins):   the logo's orchid, lit from above
  * plum    = hardware    (drives, cards, people): the supplied tile gradient, #A24E8C to #4E1D42
  * lilac   = paper       (files, sheets, glyphs): the supplied glyph gradient, #FBF3FA to #DEC3E0
  * leaf    = the one accent per icon, the same green as the mark's centre

Rules that every object follows (all of them measured in check_objects.py, none by eye):
  * corners are the Balance-dial superellipse (exponent 4), built by `sqpoly`, never circular arcs
  * no SVG filters, no text, no clip tricks that a plain renderer drops: gradients, masks and clip paths only
  * each icon ships three drawings: full (>= 48 px), small (16 to 32 px: heavier, details dropped) and symbolic
    (one colour, currentColor)
  * an icon is a list of Parts (role + svg), so a check can render the back, the front or the emblem on its own
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable

import mi_geom as g
from mi_geom import f
from appfmt import E, P, Dm, Ac, At, K, circ, superellipse_path, LILAC_TOP, LILAC_BOT, LEAF_ON_TILE, LEAF_ON_LILAC, PLUM_LIGHT, PLUM_DARK

CANVAS = 1024
C0 = 512                     # canvas centre
SYM_FILL = 0.88              # a symbolic icon's longest side fills this share of its canvas (as for the app icons)

# ---------------------------------------------------------------- palette
# containers: the orchid of the logo (#C763B0 is OKLCH L .64 C .16 h 337); front panel lit from above
ORCHID_FRONT = ("#D06BBA", "#A64C93")
ORCHID_BACK = ("#9A4585", "#7C3369")
# hardware: the supplied tile gradient
PLUM_BODY = (PLUM_LIGHT, "#6F2B5F")
PLUM_DEEP = ("#7C3369", PLUM_DARK)
LILAC = (LILAC_TOP, LILAC_BOT)
LILAC_FOLD = "#CDAACF"            # the folded corner of a page
LEAF_SHEET = ("#B4CF98", "#8FB06D")   # the leaf accent as a sheet or lamp on orchid and plum
INK = "#3A1232"                   # engraved glyphs on orchid: 3.1:1 against the darkest face stop, 5:1 against the lightest
PAGE_EDGE = "#8C3274"             # the supplied mark's plum: outlines a lilac page so it reads on a light wallpaper
SHADE = "#2A0A24"


def ink_for_hue(h: float, L: float = 0.47, C: float = 0.125) -> str:
    """The colour a glyph is printed in on a lilac page: the app tile's hue, a step darker than the tile (>= 4.5:1
    against the page, measured in check_objects.py)."""
    return g.oklch_to_hex(L, C, h)


# ---------------------------------------------------------------- geometry
def sqpoly(pts, rs, n: float = g.N) -> str:
    """Closed polygon whose every corner is the Balance-dial superellipse (exponent n). rs[i] is the corner box of
    vertex i: the curve leaves each edge rs[i] from the vertex (0 = sharp). For a right angle this is exactly
    `mi_geom.rr`; for other angles the same curve is sheared onto the two edges. Convex and concave corners use
    the same curve: the fillet of an inside corner is the same arc as the rounding of an outside one."""
    a, b, m, _ = g.corner_fit(n)
    k = b / math.sqrt(2)
    s1 = [(0, 1), (0, 1 - a), (m - k, m + k), (m, m)]
    s2 = [(m, m), (m + k, m - k), (1 - a, 0), (1, 0)]
    N = len(pts)
    d, first = [], True
    for i, p in enumerate(pts):
        q0, q1 = pts[i - 1], pts[(i + 1) % N]
        u = (p[0] - q0[0], p[1] - q0[1]); lu = math.hypot(*u); u = (u[0] / lu, u[1] / lu)
        v = (q1[0] - p[0], q1[1] - p[1]); lv = math.hypot(*v); v = (v[0] / lv, v[1] / lv)
        r = rs[i]
        if r <= 0:
            d.append(("M" if first else "L") + f"{f(p[0])} {f(p[1])}")
        else:
            def Pt(X, Y, p=p, u=u, v=v, r=r):
                return (p[0] + r * (X * v[0] - Y * u[0]), p[1] + r * (X * v[1] - Y * u[1]))
            S = Pt(0, 1)
            d.append(("M" if first else "L") + f"{f(S[0])} {f(S[1])}")
            for seg in (s1, s2):
                d.append("C" + " ".join(f"{f(x)} {f(y)}" for x, y in (Pt(*q) for q in seg[1:])))
        first = False
    return "".join(d) + "Z"


def rect(x, y, w, h, r) -> str:
    return sqpoly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], [r] * 4)


def rect_c(cx, cy, w, h, r) -> str:
    return rect(cx - w / 2, cy - h / 2, w, h, r)


def rect_top(x, y, w, h, r_top, r_bot=0) -> str:
    """Rectangle with different top and bottom corner boxes."""
    return sqpoly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], [r_top, r_top, r_bot, r_bot])


# ---------------------------------------------------------------- svg pieces
def lgrad(uid: str, name: str, stops, x0=0.0, y0=0.0, x1=0.0, y1=CANVAS) -> str:
    """Linear gradient in canvas units. stops: (c0, c1) or [(offset, colour, opacity|None), ...]."""
    if isinstance(stops, tuple) and len(stops) == 2 and isinstance(stops[0], str):
        stops = [(0, stops[0], None), (1, stops[1], None)]
    s = "".join(f'<stop offset="{f(o)}" stop-color="{c}"' + (f' stop-opacity="{f(op)}"' if op is not None else "") + "/>"
                for o, c, op in stops)
    return (f'<linearGradient id="{uid}-{name}" gradientUnits="userSpaceOnUse" x1="{f(x0)}" y1="{f(y0)}" '
            f'x2="{f(x1)}" y2="{f(y1)}">{s}</linearGradient>')


def path(d: str, fill: str, op: float = 1.0, tf: str = "", extra: str = "") -> str:
    t = f' transform="{tf}"' if tf else ""
    o = f' opacity="{f(op)}"' if op != 1.0 else ""
    return f'<path d="{d}" fill="{fill}"{o}{t}{extra}/>'


def stroke_path(d: str, col: str, w: float, op: float = 1.0, cap: str = "round") -> str:
    o = f' opacity="{f(op)}"' if op != 1.0 else ""
    return f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{f(w)}" stroke-linecap="{cap}" stroke-linejoin="round"{o}/>'


@dataclass
class Part:
    role: str                 # back | sheet | front | rim | emblem | detail | body | lid | disc | page | ...
    body: str
    defs: str = ""


# ---------------------------------------------------------------- element groups (emblems, symbolic cuts)
def _elem(e: E, fill: str) -> str:
    tf = f' transform="{e.tf}"' if e.tf else ""
    if e.stroke:
        return (f'<path d="{e.d}" fill="none" stroke="{fill}" stroke-width="{f(e.stroke)}" stroke-linecap="round" '
                f'stroke-linejoin="round"{tf}/>')
    if e.rnd:
        return f'<path d="{e.d}" fill="{fill}" stroke="{fill}" stroke-width="{f(e.rnd)}" stroke-linejoin="round"{tf}/>'
    return f'<path d="{e.d}" fill="{fill}"{tf}/>'


def group(els, uid: str, region=(-130, -130, 260, 260), small: bool = False) -> tuple[str, str]:
    """(defs, body) for an element list in currentColor. Same tone model as appfmt.glyph_group: p = solid,
    d = dim, k = cut (punches holes in everything drawn before it in the run), a/t = accent. `region` is the
    mask's user-space box, which has to cover the geometry. small drops detail elements."""
    if small:
        els = [e for e in els if not e.detail]
    defs, out, cur, nmask = [], [], [], 0

    def flush():
        if cur:
            out.append("".join(cur)); cur.clear()
    i = 0
    while i < len(els):
        e = els[i]
        if e.tone == "k":
            j = i
            while j < len(els) and els[j].tone == "k":
                j += 1
            nmask += 1
            cm = "".join(_elem(c, "#000") for c in els[i:j])
            x, y, w, h = region
            defs.append(f'<mask id="{uid}-m{nmask}" maskUnits="userSpaceOnUse" x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}">'
                        f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" fill="#fff"/>{cm}</mask>')
            out.append(f'<g mask="url(#{uid}-m{nmask})">{"".join(cur)}</g>'); cur.clear()
            i = j
            continue
        if e.tone == "d":
            cur.append(f'<g opacity="{f(e.op or 0.55)}">{_elem(e, "currentColor")}</g>')
        elif e.tone == "p":
            cur.append(_elem(e, "currentColor"))
        else:      # a / t: accents are drawn flat in one colour at the symbolic opacity
            flush()
            out.append(f'<g opacity=".85">{_elem(e, "currentColor")}</g>')
        i += 1
    flush()
    return "".join(defs), "".join(out)


def emblem_part(els, uid: str, cx: float, cy: float, s: float, ink: str, deboss: bool = True, small: bool = False,
                hi: str = "#FFFFFF", role: str = "emblem") -> Part:
    """An engraved glyph: `els` are drawn in a +-100 box, scaled by s and centred on (cx, cy). The highlight copy
    below it is what makes it look cut into the surface; it is dropped in the small cut (it would be under a pixel)."""
    d1, b1 = group(els, uid + "-e", small=small)
    body = f'<g transform="translate({f(cx)} {f(cy)}) scale({f(s)})" color="{ink}" opacity=".92">{b1}</g>'
    defs = d1
    if deboss and not small:
        d2, b2 = group(els, uid + "-h", small=small)
        body = f'<g transform="translate({f(cx)} {f(cy + 3.6)}) scale({f(s)})" color="{hi}" opacity=".42">{b2}</g>' + body
        defs += d2
    return Part(role, body, defs)


# ---------------------------------------------------------------- objects
@dataclass
class Obj:
    id: str
    name: str
    group: str                                     # folders | storage | people | files
    build: Callable[[str, bool], list]             # (uid, small) -> [Part]
    sym: Callable[[], list]                        # -> [E] in canvas units (symbolic cut)
    xdg: str = ""                                  # the name an icon theme installs it under: one that Adwaita or Humanity
                                                   # ships. Empty when there is no standard name. Unique across the set.
    kind: str = ""                                 # template: folder | page | drive | person | card | ...
    emblem: str = ""
    meta: dict = field(default_factory=dict)
    shift: tuple = (0.0, 0.0)                      # optical centring, canvas units (object_shifts.json, from centre_objects.py)

    def parts(self, small: bool = False):
        return self.build(self.id, small)


def object_svg(o: Obj, small: bool = False, only=None, skip=None, name: str | None = None) -> str:
    allp = o.parts(small)
    parts = allp
    if only is not None:
        parts = [p for p in parts if p.role in only]
    if skip is not None:
        parts = [p for p in parts if p.role not in skip]
    defs = "".join(p.defs for p in allp)           # every definition stays, so a filtered render never loses a gradient
    body = "".join(p.body for p in parts)
    if o.shift != (0.0, 0.0):
        body = f'<g transform="translate({f(o.shift[0])} {f(o.shift[1])})">{body}</g>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CANVAS} {CANVAS}" role="img" '
            f'aria-label="{name or "Malva " + o.name}"><defs>{defs}</defs>{body}</svg>')


def symbolic_svg(o: Obj, vb: tuple | None = None, name: str | None = None) -> str:
    """One-colour cut. vb = (x, y, side): the square canvas that fits the ink (fit_viewbox)."""
    d, b = group(o.sym(), o.id + "-s", region=(-64, -64, CANVAS + 128, CANVAS + 128))
    x, y, s = vb or (0.0, 0.0, float(CANVAS))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{f(x)} {f(y)} {f(s)} {f(s)}" role="img" '
            f'aria-label="{name or "Malva " + o.name}" fill="currentColor"><defs>{d}</defs>{b}</svg>')


def fit_viewbox(R, o: Obj) -> tuple:
    """Square canvas around the symbolic ink, centred by the rule of optical.py: its centre is the middle of the ink's
    bounding box, moved a fifth of the way towards the centre of mass (at most 1 % of the canvas), so a bottom-heavy
    folder sits a hair high and everything else sits on the middle. The farthest ink edge from that centre reaches
    SYM_FILL of the half-canvas, so nothing is clipped and every icon fills the same share of its canvas."""
    import numpy as np
    import optical
    al = R.render([symbolic_svg(o)], 512)[0][..., 3].astype(float)
    ys, xs = np.nonzero(al > 20)
    k = CANVAS / 512
    x0, x1, y0, y1 = xs.min() * k, (xs.max() + 1) * k, ys.min() * k, (ys.max() + 1) * k
    cx_m = (al * np.arange(512)[None, :]).sum() / al.sum() * k + k / 2
    cy_m = (al * np.arange(512)[:, None]).sum() / al.sum() * k + k / 2
    side0 = max(x1 - x0, y1 - y0) / SYM_FILL                           # the canvas the pull is measured against
    cx = (x0 + x1) / 2 + optical.pull((x0 + x1) / 2, cx_m, side0)       # the canvas centre: the box centre, moved towards the mass
    cy = (y0 + y1) / 2 + optical.pull((y0 + y1) / 2, cy_m, side0)
    half = max(abs(x0 - cx), abs(x1 - cx), abs(y0 - cy), abs(y1 - cy))
    side = round(2 * half / SYM_FILL, 1)
    return (round(cx - side / 2, 1), round(cy - side / 2, 1), side)
