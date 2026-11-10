"""The 16 Malva system app icons. Drawing rules (see docs/ICON_DESIGN.md):
  * local box +-100 units, 100 units = the supplied flower's unit; keyline: circle 190, square 160,
    landscape 180x136, portrait 130x170
  * lilac glyph, details cut out as lines (the supplied "veins"), at most one leaf accent
  * every glyph carries one rounded notch or leaf centre as a quiet echo of the mark
Tile hues are spaced around the wheel; three neutrals (Terminal, Camera, Settings)."""
from __future__ import annotations

import math

from appfmt import (E, Glyph, Tile, P, Dm, Ac, At, K, circ, line, poly, rr, PETAL, superellipse_path, TILE_N)


def ell(cx, cy, rx, ry):
    return (f"M{cx - rx:g} {cy:g}a{rx:g} {ry:g} 0 1 0 {2 * rx:g} 0a{rx:g} {ry:g} 0 1 0 {-2 * rx:g} 0Z")


def arc_with_head(r, a0, a1, head=30, half=26, sw=16):
    """Stroked circular arc (degrees, clockwise on screen) plus a triangular head at its end."""
    p = lambda a: (r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))
    (x0, y0), (x1, y1) = p(a0), p(a1)
    big = 1 if (a1 - a0) % 360 > 180 else 0
    arc = f"M{x0:.2f} {y0:.2f}A{r:g} {r:g} 0 {big} 1 {x1:.2f} {y1:.2f}"
    ta = math.radians(a1)
    tx, ty = -math.sin(ta), math.cos(ta)           # clockwise tangent
    nx, ny = math.cos(ta), math.sin(ta)            # radial
    tip = (x1 + tx * head, y1 + ty * head)
    b1 = (x1 + nx * half, y1 + ny * half)
    b2 = (x1 - nx * half, y1 - ny * half)
    return P(arc, stroke=sw), P(poly(tip, b1, b2) if False else poly(tip, b1, b2), rnd=6)


def _poly(*pts):
    return poly(*pts)


GLYPHS: dict[str, Glyph] = {}
NAMES: dict[str, str] = {}


def add(id_, name, tile, els, scale=1.15):
    GLYPHS[id_] = Glyph(tile, els, name, scale)
    NAMES[id_] = name


# ---- Malva (About / Welcome): the supplied icon, rebuilt in this pipeline so it stays in format
_pet = lambda k: f"rotate({72 * k}) translate(0 -24) scale(.86)"
add("malva", "Malva", None,
    [P(PETAL, tf=_pet(k)) for k in range(5)]
    + [K("M-7.5 -14L-16.5 -60M0 -14V-62M7.5 -14L16.5 -60", stroke=5, tf=_pet(k), detail=True) for k in range(5)]
    + [At(circ(0, 0, 16))], scale=1.0)

# ---- Files: a folder holding a leaf-green sheet
add("files", "Files", Tile(h=128), [
    Dm(rr(-84, -72, 78, 46, 14)),
    Dm(rr(-84, -58, 168, 126, 18)),
    Ac(rr(-58, -46, 116, 74, 10)),
    P(rr(-84, -22, 168, 94, 18)),
    K(line(-50, 14, 10, 14), stroke=7, detail=True),
])

# ---- Terminal: a window, a chevron prompt and an underscore cursor, cut out of the window
add("terminal", "Terminal", Tile(h=330, c=0.035, l=0.31, ld=0.14, cd=0.03), [
    P(rr(-86, -66, 172, 132, 24)),
    K(circ(-62, -43, 6), detail=True), K(circ(-46, -43, 6), detail=True), K(circ(-30, -43, 6), detail=True),
    K("M-52 -12L-18 12L-52 36", stroke=14),
    K(line(4, 36, 46, 36), stroke=14),
])

# ---- Text Editor: a page of text with a pencil writing across its corner
_pen = "translate(24 28) rotate(45)"
add("text-editor", "Text Editor", Tile(h=184), [
    P(rr(-76, -80, 124, 152, 18)),
    K(line(-50, -44, 20, -44), stroke=10, detail=True),
    K(line(-50, -18, 20, -18), stroke=10, detail=True),
    K(line(-50, 8, -8, 8), stroke=10),
    K(rr(-11, -60, 22, 70, 6), rnd=26, tf=_pen), K(poly((-11, 10), (11, 10), (0, 40)), rnd=26, tf=_pen),
    P(rr(-11, -60, 22, 70, 6), tf=_pen),
    Ac(poly((-9, 12), (9, 12), (0, 36)), rnd=6, tf=_pen),
    K(line(-11, -44, 11, -44), stroke=5, tf=_pen, detail=True),
], scale=1.06)

# ---- Documents (PDF viewer): an open book with a bookmark whose end carries the notch
add("document-viewer", "Documents", Tile(h=240), [
    P("M-84 -46Q-44 -58 -6 -38V56Q-44 36 -84 48Z", rnd=10),
    P("M84 -46Q44 -58 6 -38V56Q44 36 84 48Z", rnd=10),
    K(line(-66, -20, -24, -12), stroke=8, detail=True), K(line(-66, 0, -24, 8), stroke=8, detail=True),
    K(line(-66, 20, -42, 24), stroke=8, detail=True),
    K(line(24, -12, 66, -20), stroke=8, detail=True), K(line(24, 8, 66, 0), stroke=8, detail=True),
    Ac("M36 -56V4L48 -8L60 4V-56Z"),
])

# ---- Image Viewer: a frame whose window holds mountains and a leaf-green sun
add("image-viewer", "Image Viewer", Tile(h=64), [
    P(rr(-88, -64, 176, 128, 22)),
    K(rr(-70, -46, 140, 92, 10)),
    P(_poly((-64, 40), (-24, -6), (14, 40)), rnd=8),
    Dm(_poly((-2, 40), (34, 0), (64, 40)), rnd=8),
    At(circ(40, -22, 13)),
])

# ---- Photos: two prints, the front one with a window onto hills and a sun
add("photos", "Photos", Tile(h=8), [
    Dm(rr(-50, -66, 112, 132, 14), tf="rotate(13)"),
    P(rr(-62, -58, 124, 128, 14), tf="rotate(-7)"),
    K(rr(-46, -42, 92, 84, 8), tf="rotate(-7)"),
    P("M-46 42C-30 4 -6 4 8 24C22 8 36 10 46 20V42Z", tf="rotate(-7)"),
    At(circ(22, -16, 11), tf="rotate(-7)"),
])

# ---- Camera: body with a viewfinder bump, a lens whose centre is the leaf disc of the mark
add("camera", "Camera", Tile(h=52, c=0.06, l=0.42, ld=0.22, cd=0.05), [
    P(rr(-88, -44, 176, 116, 26)),
    P(rr(-34, -68, 68, 38, 12)),
    K(circ(0, 14, 42)), K(circ(62, -20, 6), detail=True),
    P(circ(0, 14, 29)),
    K(circ(0, 14, 15)),
    At(circ(0, 14, 10)),
])

# ---- Music: a beamed pair of notes, built from one rule set so every junction is clean.
#   * heads: two identical ellipses tilted -22 degrees (engraving angle); their centres define the phrase line
#   * beam: parallel to that line, so the two heads and the beam form one parallelogram
#   * stems: flush with each head's right-most tangent (no step on that side), ending INSIDE the head
#   * every concave junction is filleted (beam/stem r4, stem/head r4); every convex beam corner has the same
#     TRUE radius r7 (the slanted beam makes the two ends different angles, so the cut length is corrected)
#   * second beam in leaf green = a sixteenth-note beam (decorative accent, dropped in the small cut)
#   * the small cut (<= 32 px) is a separate drawing: heavier stems, beam and heads, no accent
def rpoly(pts, rs, k=0.62):
    """Closed polygon with a rounded corner at every vertex: rs[i] is that vertex's TRUE corner radius
    (0 = sharp). The tangent length is R*tan(turn/2), so unequal angles still give equal radii."""
    n = len(pts)
    segs = []
    for i, p in enumerate(pts):
        r = rs[i]
        if r <= 0:
            segs.append((p, p, p)); continue
        q0, q1 = pts[i - 1], pts[(i + 1) % n]
        u = (p[0] - q0[0], p[1] - q0[1]); lu = math.hypot(*u); u = (u[0] / lu, u[1] / lu)
        v = (q1[0] - p[0], q1[1] - p[1]); lv = math.hypot(*v); v = (v[0] / lv, v[1] / lv)
        turn = math.acos(max(-1.0, min(1.0, u[0] * v[0] + u[1] * v[1])))
        t = min(r * math.tan(turn / 2), lu / 2, lv / 2)
        segs.append(((p[0] - u[0] * t, p[1] - u[1] * t), p, (p[0] + v[0] * t, p[1] + v[1] * t)))
    d = f"M{segs[0][2][0]:.2f} {segs[0][2][1]:.2f}"
    for i in range(1, n + 1):
        A_, P_, B_ = segs[i % n]
        if A_ == P_ == B_:
            d += f"L{P_[0]:.2f} {P_[1]:.2f}"
            continue
        c1 = (A_[0] + (P_[0] - A_[0]) * k, A_[1] + (P_[1] - A_[1]) * k)
        c2 = (B_[0] + (P_[0] - B_[0]) * k, B_[1] + (P_[1] - B_[1]) * k)
        d += f"L{A_[0]:.2f} {A_[1]:.2f}C{c1[0]:.2f} {c1[1]:.2f} {c2[0]:.2f} {c2[1]:.2f} {B_[0]:.2f} {B_[1]:.2f}"
    return d + "Z"


MUSIC = dict(tilt=-22.0, rx=27.0, ry=20.0, h1=(-38.0, 50.0), h2=(42.0, 34.0), stem_w=14.0, beam_t=24.0,
             beam_top_left=-52.0, gap=10.0, leaf_t=13.0, fillet=4.0, r_outer=7.0, r_beam_inner=4.0)
# the <= 32 px cut: same construction, heavier parts, no accent beam
MUSIC_SMALL = {**MUSIC, "rx": 29.0, "ry": 22.0, "stem_w": 19.0, "beam_t": 30.0, "beam_top_left": -54.0,
               "h1": (-38.0, 50.0), "h2": (42.0, 34.0), "fillet": 5.0, "r_outer": 8.0, "r_beam_inner": 5.0}   # same heads as the full cut: the two cuts share one centre


def _head_pt(M, h, t):
    th = math.radians(M["tilt"])
    return (h[0] + M["rx"] * math.cos(t) * math.cos(th) - M["ry"] * math.sin(t) * math.sin(th),
            h[1] + M["rx"] * math.cos(t) * math.sin(th) + M["ry"] * math.sin(t) * math.cos(th))


def head_tangent(M=MUSIC):
    """Right-most point of a head, relative to its centre: the stem's right edge sits exactly on this tangent,
    so stem and head meet with no step."""
    th = math.radians(M["tilt"])
    t = math.atan2(-M["ry"] * math.sin(th), M["rx"] * math.cos(th))      # parameter of the max-x point
    x, y = _head_pt(M, (0.0, 0.0), t)
    return x, y


def stem_head_fillet(M, h):
    """Filler shape that rounds the concave corner where a stem's left edge meets the top of its head:
    a circle of radius M['fillet'] tangent to the stem edge and to the head ellipse."""
    rf = M["fillet"]
    if rf <= 0:
        return None
    xr, _ = head_tangent(M)
    xl = h[0] + xr - M["stem_w"]
    ts = [2 * math.pi * k / 4000 for k in range(4000)]
    bd = [_head_pt(M, h, t) for t in ts]
    # Q: the upper-boundary point whose x is the stem's left edge
    Q = min((p for p in bd if abs(p[0] - xl) < 0.05 and p[1] < h[1]), key=lambda p: p[1])
    near = lambda c: min(bd, key=lambda p: (p[0] - c[0]) ** 2 + (p[1] - c[1]) ** 2)
    dist = lambda c: math.hypot(*(a - b for a, b in zip(near(c), c)))
    lo, hi = Q[1] - 4 * rf, Q[1]                 # centre height: far above (distance > rf) .. at Q (< rf)
    for _ in range(40):
        mid = (lo + hi) / 2
        if dist((xl - rf, mid)) > rf:
            lo = mid
        else:
            hi = mid
    c = (xl - rf, (lo + hi) / 2)
    T2 = near(c)
    T1 = (xl, c[1])
    # the filler runs on into the stem and the head, so no edge of it lies on the silhouette except the arc
    # (shapes that merely touch show an anti-aliasing seam)
    xin = xl + 0.6 * M["stem_w"]
    return (f"M{T1[0]:.2f} {T1[1]:.2f}A{rf:g} {rf:g} 0 0 1 {T2[0]:.2f} {T2[1]:.2f}"
            f"L{xin:.2f} {T2[1] + 0.3 * M['stem_w']:.2f}L{xin:.2f} {T1[1]:.2f}Z")


def music_parts(M=MUSIC):
    (x1, y1), (x2, y2) = M["h1"], M["h2"]
    slope = (y2 - y1) / (x2 - x1)
    xr, yt = head_tangent(M)
    sl, sr = xr - M["stem_w"], xr
    s1l, s1r = x1 + sl, x1 + sr
    s2l, s2r = x2 + sl, x2 + sr
    foot = yt + M.get("foot_extra", 0.2)             # stems stop here: inside the head, on its tangent line
    bslope = slope + M.get("beam_dslope", 0.0)       # 0 = the beam runs parallel to the line through the heads
    top = lambda x: M["beam_top_left"] + bslope * (x - s1l)
    t = M["beam_t"]
    pts = [(s1l, top(s1l)), (s2r, top(s2r)), (s2r, y2 + foot), (s2l, y2 + foot), (s2l, top(s2l) + t),
           (s1r, top(s1r) + t), (s1r, y1 + foot), (s1l, y1 + foot)]
    ro, ri = M["r_outer"], M["r_beam_inner"]
    body = P(rpoly(pts, [ro, ro, 0, 0, ri, ri, 0, 0]))
    heads = [P(ell(h[0], h[1], M["rx"], M["ry"]), tf=f"rotate({M['tilt']:g} {h[0]:g} {h[1]:g})") for h in (M["h1"], M["h2"])]
    fillets = [P(d) for d in (stem_head_fillet(M, h) for h in (M["h1"], M["h2"])) if d]
    g0, lt = M["gap"], M["leaf_t"]
    a0, a1 = top(s1r) + t + g0, top(s2l) + t + g0
    leaf = At(rpoly([(s1r - .5, a0), (s2l + .5, a1), (s2l + .5, a1 + lt), (s1r - .5, a0 + lt)], [3.0] * 4), detail=True)
    return heads, fillets, body, leaf, slope


def _music_els(M=MUSIC, leaf=True):
    heads, fillets, body, lf, _ = music_parts(M)
    return heads + fillets + [body] + ([lf] if leaf else [])


add("music", "Music", Tile(h=36), _music_els(), scale=1.3)
GLYPHS["music"].small_els = _music_els(MUSIC_SMALL, leaf=False)

# ---- Video: a clapperboard (slanted stick) with a rounded play knock-out and a leaf progress bar
_stick = "rotate(-9 -76 -26)"
add("video", "Video", Tile(h=312), [
    P(rr(-76, -14, 152, 92, 16)),
    P(rr(-76, -52, 152, 30, 9), tf=_stick),
    K(_poly((-44, -54), (-30, -54), (-48, -20), (-62, -20)), tf=_stick),
    K(_poly((-8, -54), (6, -54), (-12, -20), (-26, -20)), tf=_stick),
    K(_poly((28, -54), (42, -54), (24, -20), (10, -20)), tf=_stick),
    K(_poly((-14, 4), (30, 28), (-14, 52)), rnd=12),
    K(line(-56, 66, 56, 66), stroke=7, detail=True),
    At(line(-56, 66, -6, 66), stroke=7, detail=True),
], scale=1.1)

# ---- Screenshots: viewfinder corners, a crosshair and a leaf dot
add("screenshot", "Screenshots", Tile(h=290), [
    P("M-76 -28L-76 -76L-28 -76", stroke=22), P("M28 -76L76 -76L76 -28", stroke=22),
    P("M76 28L76 76L28 76", stroke=22), P("M-28 76L-76 76L-76 28", stroke=22),
    P("M0 -28V28M-28 0H28", stroke=12),
    At(circ(0, 0, 11)),
])

# ---- Settings: three sliders; the middle knob carries the leaf centre
_rows = [(-50, -34), (0, 30), (50, -8)]
add("settings", "Settings", Tile(h=250, c=0.045, l=0.54, ld=0.30, cd=0.04),
    [Dm(line(-80, y, 80, y), stroke=16) for y, _ in _rows]
    + [P(line(-80, y, x, y), stroke=16) for y, x in _rows]
    + [P(circ(x, y, 24)) for y, x in _rows]
    + [K(circ(x, y, 9)) for y, x in _rows]
    + [At(circ(30, 0, 9))])

# ---- Software (app store): a bag holding a 2x2 grid of apps, one of them leaf-green
add("app-store", "Software", Tile(h=156), [
    P("M-28 -30V-46A28 28 0 0 1 28 -46V-30", stroke=14),
    P(rr(-66, -36, 132, 118, 24)),
    K(rr(-34, -8, 30, 30, 8)), K(rr(4, -8, 30, 30, 8)), K(rr(-34, 30, 30, 30, 8)), K(rr(4, 30, 30, 30, 8)),
    At(rr(4, -8, 30, 30, 8)),
])

# ---- Updates: two arrows chasing round a leaf arrow
_a1, _h1 = arc_with_head(62, 200, 338)
_a2, _h2 = arc_with_head(62, 20, 158)
add("updater", "Updates", Tile(h=212), [
    _a1, _h1, _a2, _h2,
    At("M0 -24V14", stroke=14), At("M-18 -2L0 18L18 -2", stroke=14),
])

# ---- Passwords (keyring): a key; the hole in its bow is the leaf disc
_rot = "rotate(45)"
add("passwords", "Passwords", Tile(h=94, c=0.11), [
    P(circ(-50, 0, 46), tf=_rot),
    P(rr(-14, -15, 116, 30, 12), tf=_rot),
    P(rr(50, 8, 20, 36, 6), tf=_rot), P(rr(78, 8, 20, 26, 6), tf=_rot),
    K(circ(-50, 0, 17), tf=_rot),
    At(circ(-50, 0, 10), tf=_rot),
])

# ---- Launcher (app grid): a 3x3 block of app tiles; the centre tile is the leaf disc of the mark.
#   * every cell is a miniature of the icon tile itself: the same superellipse (exponent TILE_N), so the glyph
#     and the tile that holds it share one shape. A grid of tiles is what a launcher shows
#   * the block fills the square keyline (160 units): 3 cells + 2 gaps, all cells the same size
#   * the leaf disc is inscribed in the centre cell (diameter = cell, plus a small optical overshoot because a
#     circle looks smaller than a square of the same width). It is the brand's leaf accent, as in Camera, Settings
#     and Passwords; the icon reads without it
#   * the <= 32 px cut is a separate drawing: bigger cells and a heavier gap (c 48, gap 17: the gap is exactly 1 px at
#     16 px). The pair was chosen by sweeping c and gap over the hinted blur at 16/22/24/32/48 px (see LAUNCHER_ICON.md)
LAUNCHER = dict(n=3, c=45.0, gap=12.5, disc=1.04)
LAUNCHER_SMALL = {**LAUNCHER, "c": 48.0, "gap": 17.0}


def launcher_geom(L):
    """Cells as (row, col, x, y) in local units (top-left corner), and the block size T."""
    n, c, gp = L["n"], L["c"], L["gap"]
    T = n * c + (n - 1) * gp
    return [(r, q, -T / 2 + q * (c + gp), -T / 2 + r * (c + gp)) for r in range(n) for q in range(n)], T


def launcher_els(L=None):
    L = {**LAUNCHER, **(L or {})}
    n, c = L["n"], L["c"]
    mid = (n - 1) // 2
    cells, _ = launcher_geom(L)
    d = "".join(superellipse_path(x + c / 2, y + c / 2, c / 2, c / 2, TILE_N, m=L.get("m", 4))
                for r, q, x, y in cells if not (r == mid and q == mid))      # the centre cell is the leaf disc
    return [P(d), At(circ(0, 0, c / 2 * L["disc"]))]


add("launcher", "Launcher", Tile(h=266, l=0.52, ld=0.30), launcher_els(), scale=1.15)
GLYPHS["launcher"].small_els = launcher_els(LAUNCHER_SMALL)

ORDER = ["malva", "files", "terminal", "text-editor", "document-viewer", "image-viewer", "photos",
         "camera", "music", "video", "screenshot", "settings", "app-store", "updater", "passwords", "launcher"]
assert set(ORDER) == set(GLYPHS)


# optical centring offsets measured from the rendered pixels (tools/icons/centre.py)
import json as _json
from pathlib import Path as _P
_sh = _P(__file__).with_name("glyph_shifts.json")
if _sh.exists():
    for _k, _v in _json.loads(_sh.read_text()).items():
        GLYPHS[_k].shift = tuple(_v)
