"""The Malva symbolic glyph kit: one SVG per glyph, drawn on a 24 x 24 grid, one colour (currentColor).

The whole set follows a few rules, and check_glyphs.py measures every one of them:
  * stroke 2, round caps and joins; a stroked shape is drawn on its centre-line, so a horizontal or vertical stroke
    whose centre-line is an integer covers whole pixels at 24 px (and at 48, 72, 96 ...)
  * ink inside 1 .. 23; every box corner is the Balance-dial superellipse (exponent from balance.rs), never a circular arc
  * three ways to paint a part: S stroke only, F solid fill, FS solid fill with the stroke on top. A part may be
    `dim` (opacity .35): the inactive bars of a level series
  * one drawing serves every size. Nothing here changes with the size it is shown at
  * no masks, no filters, no text, no <use>: a slash or a badge sits in a gap cut out of the strokes themselves
    (svgpath.cut), so the file recolours in any toolkit

A glyph is a list of Parts. A modifier (slash, badge, dim) takes a list of Parts and returns a new one, so
"wifi + slash" and "wifi + lock" come from the same wifi drawing and every variant keeps the base's proportions.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import svgpath as sp
from mi_geom import f
from ui_glyphs import R, C, L, D, P, Pc, RP, star, gear, rays          # the 24-grid path helpers of the first pack

GRID = 24
DIM = 0.35
SLASH = ((4.0, 4.0), (20.0, 20.0))           # the "off" stroke: top-left to bottom-right, as Material and SF Symbols draw it
GAP = 3.25                                    # centre-line distance kept clear of a slash or badge: a 1.25 unit gap between strokes


# ---------------------------------------------------------------- parts
@dataclass(frozen=True)
class Part:
    d: str
    kind: str = "S"              # S stroke | F fill | FS fill + stroke
    dim: bool = False
    eo: bool = False             # fill-rule evenodd (fills only)


def S(*ds, dim=False):
    return [Part("".join(ds), "S", dim)]


def F(*ds, dim=False, eo=False):
    return [Part("".join(ds), "F", dim, eo)]


def FS(*ds, dim=False):
    return [Part("".join(ds), "FS", dim)]


def dimmed(parts, on=True):
    return [replace(p, dim=on) for p in parts]


# ---------------------------------------------------------------- more path helpers
def arc(cx, cy, r, a0, a1):
    """Circular arc of radius r about (cx, cy) from angle a0 to a1 (degrees; 0 = right, 90 = down; a1 > a0 runs clockwise)."""
    t0, t1 = math.radians(a0), math.radians(a1)
    x0, y0 = cx + r * math.cos(t0), cy + r * math.sin(t0)
    x1, y1 = cx + r * math.cos(t1), cy + r * math.sin(t1)
    return (f"M{f(x0)} {f(y0)}A{f(r)} {f(r)} 0 {1 if abs(a1 - a0) > 180 else 0} {1 if a1 > a0 else 0} {f(x1)} {f(y1)}")


def disc(cx, cy, r):
    """A filled circle as a closed path (F parts)."""
    return C(cx, cy, r)


def rrect(x, y, w, h, r):
    return R(x, y, w, h, r)


def _circle_hit(c1, c2):
    """The upper of the two points where circle c1 meets circle c2; a circle is (cx, cy, r)."""
    (x1, y1, r1), (x2, y2, r2) = c1, c2
    d = math.hypot(x2 - x1, y2 - y1)
    a = (r1 * r1 - r2 * r2 + d * d) / (2 * d)
    h = math.sqrt(max(r1 * r1 - a * a, 0.0))
    mx, my = x1 + a * (x2 - x1) / d, y1 + a * (y2 - y1) / d
    ox, oy = -(y2 - y1) / d * h, (x2 - x1) / d * h
    p, q = (mx + ox, my + oy), (mx - ox, my - oy)
    return p if p[1] < q[1] else q


def cloud(cl, ct, cr):
    """A cloud: the union of three circles (left, top, right), each (cx, cy, r), cut off at the baseline of the left
    circle. The left and right circles must rest on the same baseline (cy + r). Arcs only, plus the baseline: the
    one straight stroke is horizontal, so it sits on a whole unit when the baseline does."""
    p1, p2 = _circle_hit(cl, ct), _circle_hit(ct, cr)
    yb = cl[1] + cl[2]
    assert abs(cr[1] + cr[2] - yb) < 1e-6, "left and right lobes must share a baseline"

    def ang(c, p):
        return math.degrees(math.atan2(p[1] - c[1], p[0] - c[0])) % 360

    def sweep(c, a0, a1, p):
        span = (a1 - a0) % 360
        return f"A{f(c[2])} {f(c[2])} 0 {1 if span > 180 else 0} 1 {f(p[0])} {f(p[1])}"
    return (f"M{f(cl[0])} {f(yb)}" + sweep(cl, 90, ang(cl, p1), p1) + sweep(ct, ang(ct, p1), ang(ct, p2), p2)
            + sweep(cr, ang(cr, p2), 90, (cr[0], yb)) + "Z")


def crescent(outer, inner):
    """A crescent: the part of circle `outer` that lies outside circle `inner`; circles are (cx, cy, r). A closed path
    made of two exact arcs, for a solid moon."""
    (ox, oy, R), (ix, iy, r) = outer, inner
    d = math.hypot(ix - ox, iy - oy)
    a = (R * R - r * r + d * d) / (2 * d)
    h = math.sqrt(max(R * R - a * a, 0.0))
    mx, my = ox + a * (ix - ox) / d, oy + a * (iy - oy) / d
    S0, E0 = (mx - (iy - oy) / d * h, my + (ix - ox) / d * h), (mx + (iy - oy) / d * h, my - (ix - ox) / d * h)
    phi = math.degrees(math.atan2(oy - iy, ox - ix)) % 360          # the thick side points away from the inner circle

    def through(c, p, q):
        ang = lambda pt: math.degrees(math.atan2(pt[1] - c[1], pt[0] - c[0])) % 360
        ap, aq = ang(p), ang(q)
        cw = (aq - ap) % 360
        if (phi - ap) % 360 <= cw:
            sweep, span = 1, cw
        else:
            sweep, span = 0, (ap - aq) % 360
        return f"A{f(c[2])} {f(c[2])} 0 {1 if span > 180 else 0} {sweep} {f(q[0])} {f(q[1])}"
    return f"M{f(S0[0])} {f(S0[1])}" + through(outer, S0, E0) + through(inner, E0, S0) + "Z"


# ---------------------------------------------------------------- transforms
def xf(d: str, s: float = 1.0, dx: float = 0.0, dy: float = 0.0, rot: float = 0.0, about=(12.0, 12.0)) -> str:
    """Scale by s, rotate by rot degrees about `about`, then shift by (dx, dy): a similarity, so arcs stay arcs."""
    a = math.radians(rot)
    ca, sa = math.cos(a) * s, math.sin(a) * s
    ox, oy = about
    # p' = about + R*s*(p - about) + (dx, dy)
    m = (ca, sa, -sa, ca, ox - ca * ox + sa * oy + dx, oy - sa * ox - ca * oy + dy)
    return sp.emit(sp.transform(sp.parse(d), m))


def head(x, y, dx, dy, size=4.0, spread=45.0):
    """An open arrow head: two strokes of length `size` back from the tip (x, y), `spread` degrees either side of the
    reverse of the direction (dx, dy)."""
    n = math.hypot(dx, dy)
    bx, by = -dx / n, -dy / n
    out = []
    for sgn in (1, -1):
        a = math.radians(spread * sgn)
        rx, ry = bx * math.cos(a) - by * math.sin(a), bx * math.sin(a) + by * math.cos(a)
        out.append((x + rx * size, y + ry * size))
    return P(out[0], (x, y), out[1])


def clip_half(points, x0, keep_left=True):
    """Sutherland-Hodgman clip of a polygon to the half plane x <= x0 (or x >= x0)."""
    inside = (lambda p: p[0] <= x0) if keep_left else (lambda p: p[0] >= x0)
    out = []
    n = len(points)
    for i in range(n):
        a, b = points[i], points[(i + 1) % n]
        ia, ib = inside(a), inside(b)
        if ia:
            out.append(a)
        if ia != ib:
            t = (x0 - a[0]) / (b[0] - a[0])
            out.append((x0, a[1] + (b[1] - a[1]) * t))
    return out


# ---------------------------------------------------------------- modifiers
def outline(*ds, tol=0.05):
    """The outline of one or more paths as a list of segments: a region that cut_parts can clear."""
    segs = []
    for d in ds:
        for closed, pts in sp.flatten(sp.parse(d), tol):
            segs += [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
            if closed and len(pts) > 2:
                segs.append((pts[-1], pts[0]))
    return segs


def _drop_short(subs, min_len):
    """Remove pieces whose stroke is shorter than min_len: a cut leaves crumbs next to a halo, and a crumb is noise."""
    return [s for s in subs if s.closed or sum(sp.seg_len(g) for g in s.segs) >= min_len]


def cut_parts(parts, region, gap=GAP, min_len=0.0):
    """Clear the strokes of every S part within `gap` of the region (a point, a segment or an outline)."""
    out = []
    for p in parts:
        if p.kind != "S":
            out.append(p)
            continue
        subs = _drop_short(sp.cut(sp.parse(p.d), region, gap), min_len)
        if subs:
            out.append(replace(p, d=sp.emit(subs)))
    return out


def slash(parts, line=SLASH, gap=GAP):
    """The off state: a diagonal stroke with a clear gap on both sides of it."""
    return cut_parts(parts, line, gap) + S(L(line[0][0], line[0][1], line[1][0], line[1][1]))


def with_badge(parts, badge, region, gap=GAP):
    """Base parts with a clean halo around `region`, and the badge parts drawn into it."""
    return cut_parts(parts, region, gap) + badge


# badges: small marks that sit in the bottom-right corner of a base drawing. Each returns (parts, region), the region
# being what the base has to keep clear of.
def bang(x=19.0, y0=13.0, y1=17.0, dot=20.5):
    return S(L(x, y0, x, y1), D(x, dot)), ((x, y0), (x, dot))


def lock_badge(cx=18.0, cy=17.0):
    """A padlock: solid body and a 2-wide shackle. 8 wide, 9 tall."""
    body = F(R(cx - 3.5, cy - 0.5, 7, 6, 1.2))
    shackle = S(f"M{f(cx - 2)} {f(cy - 0.5)}V{f(cy - 2.4)}a2 2 0 0 1 4 0V{f(cy - 0.5)}")
    return shackle + body, ((cx, cy - 1.5), (cx, cy + 2.5))


def tick_badge(cx=18.0, cy=17.0):
    return S(P((cx - 3, cy), (cx - 0.8, cy + 2.4), (cx + 3.4, cy - 2.6))), (cx, cy)


def dot_badge(cx=19.0, cy=5.0, r=3.0):
    return F(disc(cx, cy, r)), (cx, cy)


# ---------------------------------------------------------------- registry
@dataclass
class Gl:
    id: str                      # the icon-theme name, without "-symbolic"
    ctx: str                     # status | actions | devices | places | mimetypes | categories | emblems | ui | apps
    parts: list
    rtl: bool = False            # also ships a mirrored `-symbolic-rtl` copy
    tags: str = ""
    group: str = ""              # a level series: wifi, battery ... (check_glyphs: ink grows with the level)
    level: int = -1
    alias: tuple = ()            # other theme names this drawing is installed under


GLYPHS: dict[str, Gl] = {}


def add(id_, ctx, parts, **kw):
    assert id_ not in GLYPHS, f"duplicate glyph {id_}"
    GLYPHS[id_] = Gl(id_, ctx, list(parts), **kw)
    return GLYPHS[id_]


# ---------------------------------------------------------------- svg
HEAD = ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">')


def _path(kind, d, dim, eo):
    a = ""
    if kind == "F":
        a += ' fill="currentColor" stroke="none"'
    elif kind == "FS":
        a += ' fill="currentColor"'
    if eo:
        a += ' fill-rule="evenodd"'
    if dim:
        a += f' opacity="{f(DIM)}"'
    return f'<path{a} d="{d}"/>'


# The same drawing as filled shapes only: what the theme ships. GTK recolours a symbolic icon by forcing a fill onto
# every path, which fills a stroke drawing in; an outline of each stroke survives that (see svgstroke.py).
HEAD_FLAT = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="currentColor">'


def _flat(kind, d, dim, eo):
    import svgstroke
    op = f' opacity="{f(DIM)}"' if dim else ""
    if kind == "S":
        return f'<path{op} d="{svgstroke.outline_d(d)}"/>'
    if kind == "F":
        return f'<path{op}{" fill-rule=" + chr(34) + "evenodd" + chr(34) if eo else ""} d="{sp.emit_compact(sp.parse(d), 3)}"/>'
    inner = f'<path d="{sp.emit_compact(sp.parse(d), 3)}"/><path d="{svgstroke.outline_d(d)}"/>'        # fill + stroke
    return f"<g{op}>{inner}</g>" if dim else inner


def svg_of(parts, mirror: bool = False, flat: bool = False) -> str:
    """The SVG text of a list of parts. Neighbouring parts painted alike are merged into one <path>.
    flat=True draws every stroke as the filled outline of that stroke (no stroke attributes anywhere)."""
    runs = []
    for p in parts:
        d = p.d
        if mirror:
            d = sp.emit(sp.mirror_x(sp.parse(d)))
        if runs and runs[-1][0] == (p.kind, p.dim, p.eo):
            runs[-1][1].append(d)
        else:
            runs.append([(p.kind, p.dim, p.eo), [d]])
    if flat:
        return HEAD_FLAT + "".join(_flat(k, "".join(ds), dim, eo) for (k, dim, eo), ds in runs) + "</svg>"
    return HEAD + "".join(_path(k, "".join(ds), dim, eo) for (k, dim, eo), ds in runs) + "</svg>"


def svg(gl: Gl, rtl: bool = False, flat: bool = False) -> str:
    return svg_of(gl.parts, mirror=rtl, flat=flat)


def theme_name(gl: Gl, rtl: bool = False) -> str:
    return f"{gl.id}-symbolic{'-rtl' if rtl else ''}"
