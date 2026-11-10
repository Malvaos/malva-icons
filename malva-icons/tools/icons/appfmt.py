"""The Malva app-icon format, taken from the supplied assets/brand/logo/malva-app-icon.svg:

  * 1024 canvas, full-bleed superellipse tile with exponent 5 (measured on the supplied clip path)
  * diagonal tile gradient (top-left light, bottom-right dark) + soft radial highlight at (.3, .18)
  * glyph in lilac (#FBF3FA -> #DEC3E0), details cut out of it as thin lines (the "veins"),
    one leaf-green accent, a soft shadow under the glyph
Glyphs are drawn in a local box of +-100 units; 100 units = 272.727 px, the supplied flower's unit.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import mi_geom as g
from mi_geom import f, rr as _rr

TILE_N = 5.0
SYMBOLIC_VB = 118          # default symbolic canvas half-size in local units (build_apps fits it per glyph)
SYMBOLIC_FILL = 0.88       # a symbolic glyph's longest half-extent fills this share of its canvas
SMALL_BOOST = 1.2          # optical size: the <=32 px cut draws the glyph this much larger
UNIT = 272.727 / 100          # px per local unit
LILAC_TOP, LILAC_BOT = "#FBF3FA", "#DEC3E0"
LEAF_ON_TILE = "#9DBB7E"      # the supplied icon's centre-disc colour
LEAF_ON_LILAC = "#4F7A2F"     # darker leaf for accents that sit on the lilac glyph
PLUM_LIGHT, PLUM_DARK = "#A24E8C", "#4E1D42"   # the supplied tile gradient
SHADOW = "#2A0A24"


def superellipse_path(cx: float, cy: float, a: float, b: float, n: float, m: int = 4) -> str:
    """Full superellipse |x/a|^n + |y/b|^n = 1 as 4*m cubic Beziers. Points are taken at equal polar
    angles with analytic tangents (Hermite), so the error is far below a pixel at 1024."""
    def pt(th):
        c, s_ = math.cos(th), math.sin(th)
        r = (abs(c) ** n + abs(s_) ** n) ** (-1 / n)
        # dr/dth for r = (|c|^n + |s|^n)^(-1/n)
        dc = -s_ * n * abs(c) ** (n - 1) * math.copysign(1, c)
        ds = c * n * abs(s_) ** (n - 1) * math.copysign(1, s_)
        dr = -(1 / n) * (abs(c) ** n + abs(s_) ** n) ** (-1 / n - 1) * (dc + ds)
        x, y = r * c, r * s_
        dx, dy = dr * c - r * s_, dr * s_ + r * c
        return (cx + a * x, cy + b * y), (a * dx, b * dy)
    steps = 4 * m
    d = []
    for i in range(steps):
        t0, t1 = 2 * math.pi * i / steps, 2 * math.pi * (i + 1) / steps
        (p0, v0), (p1, v1) = pt(t0), pt(t1)
        k = (t1 - t0) / 3
        c1 = (p0[0] + v0[0] * k, p0[1] + v0[1] * k)
        c2 = (p1[0] - v1[0] * k, p1[1] - v1[1] * k)
        if i == 0:
            d.append(f"M{f(p0[0])} {f(p0[1])}")
        d.append(f"C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(p1[0])} {f(p1[1])}")
    return "".join(d) + "Z"


def tile_path() -> str:
    return superellipse_path(512, 512, 512, 512, TILE_N, m=4)


# ------------------------------------------------------------------ tile colour
def _mix_oklab(h1: str, h2: str, t: float) -> str:
    import numpy as np
    a = g.oklab_from_lin(g.srgb_to_lin(np.array(g.hex_to_rgb(h1)) / 255))
    b = g.oklab_from_lin(g.srgb_to_lin(np.array(g.hex_to_rgb(h2)) / 255))
    m = [x * (1 - t) + y * t for x, y in zip(a, b)]
    lin = g.lin_from_oklab(*m)
    return g.rgb_to_hex(g.lin_to_srgb(np.clip(lin, 0, 1)) * 255)


@dataclass(frozen=True)
class Tile:
    h: float                 # OKLCH hue
    c: float = 0.125         # light-stop chroma
    l: float = 0.55          # light-stop lightness
    ld: float = 0.31         # dark-stop lightness
    cd: float = 0.095        # dark-stop chroma
    shadow_mix: float = 0.28  # how far the dark stop leans toward brand plum-dark (shared shadow tone)

    def stops(self):
        light = g.oklch_to_hex(self.l, self.c, self.h)
        dark = g.oklch_to_hex(self.ld, self.cd, self.h)
        return light, _mix_oklab(dark, PLUM_DARK, self.shadow_mix)


BRAND_TILE_STOPS = (PLUM_LIGHT, PLUM_DARK)


# ------------------------------------------------------------------ glyph elements
@dataclass
class E:
    d: str                   # path data (local units) ...
    tone: str                # p primary | d dim | a accent on lilac | t accent on tile | k cut
    stroke: float = 0.0      # >0: draw as a round-capped stroke of this width instead of a fill
    tf: str = ""             # optional transform
    detail: bool = False     # dropped in the small (<=32 px) cut
    rnd: float = 0.0         # >0: also stroke the fill with this width (round joins) to soften corners
    op: float = 0.0          # tone d only: opacity of the dim layer (0 = the default .55)


def P(d, **k): return E(d, "p", **k)
def Dm(d, **k): return E(d, "d", **k)
def Ac(d, **k): return E(d, "a", **k)
def At(d, **k): return E(d, "t", **k)
def K(d, **k): return E(d, "k", **k)


def circ(cx, cy, r):
    return f"M{f(cx - r)} {f(cy)}a{f(r)} {f(r)} 0 1 0 {f(2 * r)} 0a{f(r)} {f(r)} 0 1 0 {f(-2 * r)} 0Z"


def line(x1, y1, x2, y2):
    return f"M{f(x1)} {f(y1)}L{f(x2)} {f(y2)}"


def poly(*pts):
    return "M" + "L".join(f"{f(x)} {f(y)}" for x, y in pts) + "Z"


def rr(x, y, w, h, r):
    return _rr(x, y, w, h, r)          # exponent from the Balance dial


# the supplied mark's petal (unit petal x100): base at origin, tip up, signature notch at the tip
PETAL = ("M0 0C-20 -10 -50 -30 -50 -62C-50 -86 -43 -100 -26 -100C-11.7 -100 -3 -80 0 -70"
         "C3 -80 11.7 -100 26 -100C43 -100 50 -86 50 -62C50 -30 20 -10 0 0Z")


def petal(cx, cy, h, rot=0):
    """A petal of height h (units) with its base at (cx, cy), rotated rot degrees about the base."""
    s = h / 100
    r = f" rotate({f(rot)})" if rot else ""
    return PETAL, f"translate({f(cx)} {f(cy)}){r} scale({f(s)})"


@dataclass
class Glyph:
    tile: Tile | None            # None = brand plum (the supplied icon)
    els: list
    label: str = ""
    scale: float = 1.15          # glyph scale; the supplied flower itself is 1.0
    shift: tuple = (0.0, 0.0)    # optical-centring offset in local units (from glyph_shifts.json)
    small_els: list | None = None  # optional separate drawing for the <= 32 px cut (heavier parts)


# ------------------------------------------------------------------ rendering
def _elem(e: E, fill: str, stroke_col: str | None = None) -> str:
    tf = f' transform="{e.tf}"' if e.tf else ""
    if e.stroke:
        return (f'<path d="{e.d}" fill="none" stroke="{stroke_col or fill}" stroke-width="{f(e.stroke)}" '
                f'stroke-linecap="round" stroke-linejoin="round"{tf}/>')
    if e.rnd:
        return (f'<path d="{e.d}" fill="{fill}" stroke="{stroke_col or fill}" stroke-width="{f(e.rnd)}" '
                f'stroke-linejoin="round"{tf}/>')
    return f'<path d="{e.d}" fill="{fill}"{tf}/>'


def glyph_group(els, uid: str, mode: str, lilac_stops=(LILAC_TOP, LILAC_BOT), leaf_tile=LEAF_ON_TILE,
                leaf_lilac=LEAF_ON_LILAC) -> tuple[str, str]:
    """Returns (defs, body) for the glyph in local units. mode: full | small | mono.
    Elements are drawn in list order. A run of cuts (tone k) punches holes in every lilac element
    drawn before it; elements after the run are not affected. Tone t (leaf accent on the tile)
    is drawn unmasked, in order."""
    if mode in ("small", "symbolic"):
        els = [e for e in els if not e.detail]      # the glanceable cut: details are dropped
    mono = mode in ("mono", "symbolic")
    lilac = "currentColor" if mono else f"url(#{uid}-lg)"
    defs = []
    if not mono:
        defs.append(f'<linearGradient id="{uid}-lg" gradientUnits="userSpaceOnUse" x1="0" y1="-110" x2="0" y2="110">'
                    f'<stop offset="0" stop-color="{lilac_stops[0]}"/><stop offset="1" stop-color="{lilac_stops[1]}"/></linearGradient>')
    out, cur, nmask = [], [], 0

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
            cm = "".join(_elem(c, "#000", "#000") for c in els[i:j])
            defs.append(f'<mask id="{uid}-m{nmask}" maskUnits="userSpaceOnUse" x="-120" y="-120" width="240" height="240">'
                        f'<rect x="-120" y="-120" width="240" height="240" fill="#fff"/>{cm}</mask>')
            out.append(f'<g mask="url(#{uid}-m{nmask})">{"".join(cur)}</g>'); cur.clear()
            i = j
            continue
        if e.tone == "d":
            cur.append(f'<g opacity="{f(e.op or 0.55)}">{_elem(e, lilac)}</g>')
        elif e.tone == "p":
            cur.append(_elem(e, lilac))
        elif e.tone == "a":
            col = "currentColor" if mono else leaf_lilac
            cur.append(_elem(e, col) if not mono else f'<g opacity=".85">{_elem(e, col)}</g>')
        elif e.tone == "t":
            flush()
            col = "currentColor" if mono else leaf_tile
            out.append(_elem(e, col) if not mono else f'<g opacity=".85">{_elem(e, col)}</g>')
        i += 1
    flush()
    return "".join(defs), "".join(out)


def app_icon_svg(gl: Glyph, uid: str, name: str, mode: str = "full", brand_stops=None, shadow: bool = True,
                 tile: bool = True, tones: str | None = None, lilac_stops=(LILAC_TOP, LILAC_BOT),
                 leaf_tile=LEAF_ON_TILE, leaf_lilac=LEAF_ON_LILAC, hl: float = 0.22, shadow_col=SHADOW, sym_vb: float | tuple | None = None, hint: tuple | None = None) -> str:
    """mode: full (the app-icon format), small (<=32 px: no details, no shadow), mono (glyph only,
    currentColor, no tile). hint = (size_px, dx_px, dy_px, k): pixel-snapping nudge of the glyph (not the tile)
    for a PNG of that size: shifted by dx, dy pixels and scaled by k."""
    base = gl.small_els if (mode in ("small", "symbolic") and gl.small_els is not None) else gl.els
    els = base if tones is None else [e for e in base if e.tone in tones or e.tone == "k"]
    gdefs, gbody = glyph_group(els, uid, mode, lilac_stops, leaf_tile, leaf_lilac)
    if mode in ("mono", "symbolic"):
        if mode != "symbolic":
            vb, sx, sy = 110, 0.0, 0.0
        elif isinstance(sym_vb, tuple):                      # (half-size, shift x, shift y): the cut centred on its own ink (build_apps.symbolic_vb)
            vb, sx, sy = sym_vb
        else:
            vb, (sx, sy) = (sym_vb or SYMBOLIC_VB), gl.shift
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-vb} {-vb} {2 * vb} {2 * vb}" role="img" '
                f'aria-label="{name}" fill="currentColor"><defs>{gdefs}</defs>'
                f'<g transform="translate({f(sx)} {f(sy)})">{gbody}</g></svg>')
    light, dark = brand_stops or gl.tile.stops()
    defs = (f'<linearGradient id="{uid}-bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{light}"/>'
            f'<stop offset="1" stop-color="{dark}"/></linearGradient>'
            f'<radialGradient id="{uid}-hl" cx=".3" cy=".18" r=".7"><stop offset="0" stop-color="#fff" stop-opacity="{f(hl)}"/>'
            f'<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>')
    shadow = ""
    if mode == "full" and shadow:
        defs += (f'<filter id="{uid}-sh" x="-20%" y="-20%" width="140%" height="150%">'
                 f'<feDropShadow dy="12" stdDeviation="14" flood-color="{shadow_col}" flood-opacity=".32"/></filter>')
        shadow = f' filter="url(#{uid}-sh)"'
    t = tile_path()
    hx = hy = 0.0
    hk = 1.0
    if hint is not None:
        size_px, dx_px, dy_px, hk = hint
        hx, hy = dx_px * 1024.0 / size_px, dy_px * 1024.0 / size_px
    tile_svg = (f'<path d="{t}" fill="url(#{uid}-bg)"/><path d="{t}" fill="url(#{uid}-hl)"/>') if tile else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" role="img" aria-label="{name}">'
            f'<defs>{defs}{gdefs}</defs>{tile_svg}'
            f'<g{shadow}><g transform="translate({f(512 + hx)} {f(512 + hy)}) scale({UNIT * gl.scale * (SMALL_BOOST if mode == "small" else 1.0) * hk:.5f}) translate({f(gl.shift[0])} {f(gl.shift[1])})">{gbody}</g></g></svg>')
