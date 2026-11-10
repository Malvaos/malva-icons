"""Measured checks for the object icons (folders, storage, people, files). Everything here reads pixels rendered by
Chromium or parses the SVG; nothing is judged by eye. Every check has a negative test: a deliberately broken icon
that the check has to reject, so a check that cannot fail does not count.

Run: python3 tools/icons/check_objects.py [--report PATH] [--no-negative]

How the numbers were chosen. Each threshold sits between what the finished set measures and what the matching
defect measures (both are printed in the report), never at the edge of the set. Where the app icons set a
standard (wallpaper edge, WCAG 1.4.11 contrast) the object icons are held to it.
"""
from __future__ import annotations

import math
import re
import sys
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from dataclasses import replace
from itertools import combinations
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
try:
    from skimage.morphology import convex_hull_image
except ImportError:
    from scipy.spatial import ConvexHull
    from PIL import ImageDraw as _ImageDraw

    def convex_hull_image(mask: np.ndarray) -> np.ndarray:
        ys, xs = np.nonzero(mask)
        if len(xs) < 3:
            return np.asarray(mask, dtype=bool)
        pts = np.column_stack((xs, ys))
        hull = ConvexHull(pts)
        poly = [tuple(map(int, pts[idx])) for idx in hull.vertices]
        img = Image.new("L", (mask.shape[1], mask.shape[0]), 0)
        _ImageDraw.Draw(img).polygon(poly, outline=1, fill=1)
        return np.asarray(img, dtype=bool) | np.asarray(mask, dtype=bool)


sys.path.insert(0, str(Path(__file__).parent))
import mi_geom as g
import objects as O
from objfmt import Obj, Part, object_svg, symbolic_svg, fit_viewbox, CANVAS
from mi_render import Renderer

ROOT = Path(__file__).resolve().parents[2]
S = 256                                   # analysis size for the full-colour pixel checks
FORBIDDEN = {"text", "image", "script", "style", "foreignObject", "use", "a", "filter"}

# --------------------------------------------------------------------------------------------- thresholds
T = dict(
    reach_max=0.90,            # set measures 0.71..0.88 of the half canvas; a 1.15x icon measures 0.99
    longest_min=0.60,          # set: >= 0.63 (USB stick); an icon at half size measures 0.41
    centre_box_max=0.0125,     # the box of the drawing on the middle of the canvas: optical.py leaves at most 1 % (a small pull towards the
                               # mass), pixels and whole-unit shifts the rest. The set measures <= 1.0 % (the bin pair: see pair_box_max);
                               # a 40-unit slip is 3.9 %
    pair_box_max=0.030,        # the two states of one object (bin empty / full) share one shift, so that the can stays put when the
                               # papers appear: each state's box is then off by half the difference (2.3 % and 1.6 %); their mean must still be centred
    centre_mass_max=0.050,     # centre of mass: only a guard against a lopsided drawing (the cloud is the lowest, 4.1 %); a slip of 80 units is 7.8 %
    small_reach_max=0.92, small_box_max=0.0125, small_mass_max=0.050,
    emb_med_min=3.0,           # WCAG 1.4.11: 3:1 for a graphical object. Median over the emblem's pixels
    emb_p10_min=2.5,           # and the 10th percentile, so a half-lit corner of the glyph cannot hide behind the median
    sep_min=1.6,               # median edge contrast against both wallpapers (the app tiles measure 1.3..1.7 on dusk)
    ink32_min=120, ink16_min=40, emb32_min=20, emb16_min=5,
    heavier_min=1.04,          # the small cut carries more emblem ink than the full cut at 16 px (a copy of the full cut measures 1.00; the lightest real one 1.08)
    emb_dy_small_max=0.020,    # the small cut's thicker outline moves a page's centre of mass a little and the mass pull adds up to 1 %: the set measures <= 1.22 %
    state_move_max=0.004,      # the common part of two states (the can of the bin) may not move between them: 2 px at 512; the set measures 0
    emb_dx_max=0.012, emb_dy_max=0.0125, emb_margin_min=0.030,   # the emblem's box on the middle of its surface, a page's on its centre of mass (emblem_shifts.json): the set measures <= 0.8 % both ways; a slip of 60 units is 5.9 %
    small_margin_min={'page': 0.050, 'cloud': 0.050, 'folder': 0.030, 'drive:internal': 0.030},
    corner_tol=0.08,          # measured depth / expected depth of a Balance-dial corner (a circular arc is 1.84)
    iou_template_min=0.995, weight_template_tol=0.04, weight_lo=0.30, weight_hi=2.0,
    circle_iou_min=0.985,
    sym_fill=(0.84, 0.92), sym_box_max=0.015, sym_mass_max=0.060, sym_ink16_min=40, sym_sil_iou_min=0.85,   # the set: box <= 1.1 %, mass <= 5.2 % (user-admin: the badge)
    pair_shape_iou=0.55, pair_de=10.0, pair_de_cvd=4.5, pair_frac_min=0.02,   # dE00 10 in normal vision, 4.5 in each colour-blind simulation (see AVATAR_TILE)
    hue_brand=18.0, hue_leaf=10.0, hue_decl=30.0, chroma_min=0.03,
)
BRAND_H, LEAF_H = 338.0, 132.0
VISIONS = ("normal", "protan", "deutan", "tritan")


# --------------------------------------------------------------------------------------------- result plumbing
def num(name, v, lo=None, hi=None, fmt=".3f", label=None):
    """A numeric check: (label, ok, text, value, (lo, hi)). The label carries the threshold."""
    ok = (lo is None or v >= lo) and (hi is None or v <= hi)
    lab = label or name + "(" + ("" if lo is None else f">={lo:{fmt}}") + ("" if hi is None else f"<={hi:{fmt}}") + ")"
    return (lab, bool(ok), f"{v:{fmt}}", float(v), (lo, hi))


def flag(name, ok, text=""):
    return (name, bool(ok), text, None, (None, None))


class Agg:
    """Collects per-icon results and prints one line per check: the worst value in the set, or the icons that failed."""

    def __init__(self):
        self.rows: dict[str, list] = {}

    def add(self, icon, results):
        for r in results:
            self.rows.setdefault(r[0], []).append((icon,) + tuple(r[1:]))

    def lines(self, scope="icons"):
        out, failed = [], 0
        for name, rs in self.rows.items():
            bad = [r for r in rs if not r[1]]
            vals = [(r[3], r[0]) for r in rs if r[3] is not None]
            lo, hi = rs[0][4]
            if bad:
                failed += 1
                info = f"{len(bad)} of {len(rs)} failed: " + "; ".join(f"{r[0]} {r[2]}" for r in bad[:8]) + (" ..." if len(bad) > 8 else "")
            elif vals:
                if lo is not None and hi is not None:
                    a, b = min(vals), max(vals)
                    info = f"{len(rs)} icons, range {a[0]:.3f} ({a[1]}) .. {b[0]:.3f} ({b[1]})"
                elif lo is not None:
                    a = min(vals)
                    info = f"{len(rs)} icons, lowest {a[0]:.3f} ({a[1]})"
                else:
                    b = max(vals)
                    info = f"{len(rs)} icons, highest {b[0]:.3f} ({b[1]})"
            else:
                info = f"{len(rs)} icons ok"
            out.append((f"{'FAIL' if bad else 'PASS'}  {scope:<8} {name}  {info}", not bad))
        return out, failed


# --------------------------------------------------------------------------------------------- small helpers
def lumY(rgb):
    l = g.srgb_to_lin(np.asarray(rgb, float) / 255.0)
    return 0.2126 * l[..., 0] + 0.7152 * l[..., 1] + 0.0722 * l[..., 2]


def contrast_px(a, b):
    ya, yb = lumY(a), lumY(b)
    return (np.maximum(ya, yb) + 0.05) / (np.minimum(ya, yb) + 0.05)


from centre_objects import PAIRS as STATE_PAIRS                  # noqa: E402  (bin empty / full: two states of one object)
STATE_PAIR_MEMBERS = {i for p in STATE_PAIRS for i in p}


def has_role(o, role):
    return any(p.role == role for p in o.parts(False))


def _extents(al, size=S):
    m = al > 127
    ys, xs = np.nonzero(m)
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
    half = size / 2
    w = al.astype(float)
    ar = np.arange(size) + 0.5
    mx, my = (w.sum(0) * ar).sum() / w.sum(), (w.sum(1) * ar).sum() / w.sum()
    bx, by = (x0 + x1) / 2, (y0 + y1) / 2
    return dict(reach=max(abs(x0 - half), abs(x1 - half), abs(y0 - half), abs(y1 - half)) / half,
                longest=max(x1 - x0, y1 - y0) / size, bbox=(x0, y0, x1, y1), cx=mx, cy=my,
                mass=max(abs(mx - half), abs(my - half)) / size,
                box=max(abs(bx - half), abs(by - half)) / size)


# --------------------------------------------------------------------------------------------- the icons' roles
CORNER = {      # template -> (role whose outline is measured, declared corner box in canvas units)
    "folder": ("front", 64), "drive:internal": ("body", 76), "drive:external": ("body", 76), "page": ("page", 56),
    "card": ("body", 44),
}
HOST = {        # template -> (role of the surface the emblem sits on, how it must be centred)
    "folder": (("front",), "both"), "page": (("page",), "page"), "drive:internal": (("body",), "vertical"),
    "cloud": (("disc",), "margin"),
}


def corner_spec(o):
    if o.id == "id-card":
        return ("body", 64)
    return CORNER.get(o.kind) if o.id != "folder-open" else None


# --------------------------------------------------------------------------------------------- renders
BLANK = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024"></svg>'


def _batch(R, objs, size, fn):
    """Render fn(o) for every icon in one call (ids are unique inside the call: each starts with its icon's id).
    Icons for which fn returns None come back as None."""
    idx = [k for k, o in enumerate(objs) if fn(o) is not None]
    arr = R.render([fn(objs[k]) for k in idx], size) if idx else []
    out = [None] * len(objs)
    for k, a in zip(idx, arr):
        out[k] = a
    return out


def renders_many(R, objs, want=None):
    """Every render the pixel checks need, per icon, keyed by purpose. Each key is its own render call, so two
    variants of one icon never share a document (duplicate ids would resolve to the first definition)."""
    W = lambda k: want is None or k in want
    rd = [dict() for _ in objs]

    def put(key, size, fn):
        if W(key):
            for d, a in zip(rd, _batch(R, objs, size, fn)):
                d[key] = a
    emb = lambda o: has_role(o, "emblem")
    host = lambda o: HOST[o.kind][0] if o.kind in HOST and emb(o) else None
    put("full", S, lambda o: object_svg(o))
    put("noemb", S, lambda o: object_svg(o, skip=("emblem",)) if emb(o) else None)
    put("emb", S, lambda o: object_svg(o, only=("emblem",)) if emb(o) else None)
    put("host", S, lambda o: object_svg(o, only=host(o)) if host(o) else None)
    put("fold", S, lambda o: object_svg(o, only=("fold",)) if o.kind == "page" else None)
    put("small256", S, lambda o: object_svg(o, small=True))
    put("semb256", S, lambda o: object_svg(o, small=True, only=("emblem",)) if emb(o) else None)
    put("shost", S, lambda o: object_svg(o, small=True, only=host(o)) if host(o) else None)
    put("sfold", S, lambda o: object_svg(o, small=True, only=("fold",)) if o.kind == "page" else None)
    for s in (32, 16):
        put(f"small{s}", s, lambda o: object_svg(o, small=True))
        put(f"semb{s}", s, lambda o: object_svg(o, small=True, only=("emblem",)) if emb(o) else None)
    put("femb16", 16, lambda o: object_svg(o, only=("emblem",)) if emb(o) else None)
    put("e128", 128, lambda o: object_svg(o))
    put("can", S, lambda o: object_svg(o, only=("front",)) if o.id in STATE_PAIR_MEMBERS else None)
    if W("corner"):
        for d, a in zip(rd, _batch(R, objs, 1024, lambda o: object_svg(o, only=(corner_spec(o)[0],)) if corner_spec(o) else None)):
            d["corner"] = a
    if W("sym220") or W("sym16"):
        vbs = [fit_viewbox(R, o) for o in objs]
        sy = [symbolic_svg(o, vb) for o, vb in zip(objs, vbs)]
        for d, a, b, vb, s_ in zip(rd, R.render(sy, 220), R.render(sy, 16), vbs, sy):
            d["sym220"], d["sym16"], d["vb"], d["symsvg"] = a, b, vb, s_
    for d, o in zip(rd, objs):
        d["svg"] = object_svg(o)
        d["svg_small"] = object_svg(o, small=True)
    return rd


# --------------------------------------------------------------------------------------------- hygiene and palette
def check_hygiene(o, svg, kind="full"):
    t = f"hygiene[{kind}]"
    out = []
    root = ET.fromstring(svg)
    tags = {e.tag.split("}")[-1] for e in root.iter()}
    bad = sorted(x for x in tags if x in FORBIDDEN or x.startswith("fe"))
    out.append(flag(f"{t}:no-text-filters-images-scripts", not bad, str(bad)))
    vb = [float(x) for x in root.get("viewBox").split()]
    if kind == "symbolic":
        out.append(flag(f"{t}:square-viewBox", abs(vb[2] - vb[3]) < 0.01 and vb[2] > 0, str(vb)))
    else:
        out.append(flag(f"{t}:viewBox-1024", vb == [0, 0, CANVAS, CANVAS], str(vb)))
    out.append(flag(f"{t}:accessible-name", bool(root.get("aria-label")) and root.get("role") == "img", str(root.get("aria-label"))))
    out.append(flag(f"{t}:size<12KB", len(svg) < 12_000, f"{len(svg)} bytes"))
    ids = re.findall(r' id="([^"]+)"', svg)
    out.append(flag(f"{t}:ids-prefixed-with-icon-id-and-unique", len(ids) == len(set(ids)) and all(i.startswith(o.id + "-") for i in ids), f"{len(ids)} ids"))
    out.append(flag(f"{t}:no-external-references", "http" not in re.sub(r'xmlns="[^"]+"', "", svg) and "xlink" not in svg, ""))
    if kind == "symbolic":
        body = re.sub(r"<mask .*?</mask>", "", svg, flags=re.S)          # masks use black and white as alpha, not as colour
        stray = re.findall(r"#[0-9a-fA-F]{3,8}\b|rgb\(", body)
        out.append(flag(f"{t}:currentColor-only", root.get("fill") == "currentColor" and not stray, f"{stray[:3]}"))
    return out


def _hue_dev(h, a):
    return abs((h - a + 180) % 360 - 180)


def check_palette(o, svg):
    """Every chromatic colour is the brand orchid/plum axis, the leaf green, or the hue the icon declares (a page's
    ink is the hue of the app that opens it; an avatar wears its own hue). The declared hue has to be used."""
    decl = o.meta.get("hue")
    decl = decl if isinstance(decl, (int, float)) else None
    stray, used = [], False
    for c in sorted(set(re.findall(r"#[0-9A-Fa-f]{6}", svg))):
        L, C, H = g.hex_to_oklch(c)
        if C < T["chroma_min"]:
            continue
        ok = _hue_dev(H, BRAND_H) <= T["hue_brand"] or _hue_dev(H, LEAF_H) <= T["hue_leaf"] or (decl is not None and _hue_dev(H, decl) <= T["hue_decl"])
        if decl is not None and _hue_dev(H, decl) <= 6 and C >= 0.06:
            used = True
        if not ok:
            stray.append(f"{c} hue {H:.0f}")
    out = [flag("palette:only-brand-leaf-or-declared-hues", not stray, "; ".join(stray))]
    if decl is not None:
        out.append(flag("palette:declared-hue-is-used", used, f"declared {decl}"))
    return out


# --------------------------------------------------------------------------------------------- pixels, one icon
def check_layout(o, rd):
    out = []
    e = _extents(rd["full"][..., 3])
    al = rd["full"][..., 3]
    out.append(num("layout:inside-safe-zone", e["reach"], hi=T["reach_max"]))
    out.append(num("layout:not-too-small", e["longest"], lo=T["longest_min"]))
    lim = T["pair_box_max"] if o.id in STATE_PAIR_MEMBERS else T["centre_box_max"]
    out.append(num("layout:box-centred" + ("(state pair: its mean is checked in states:)" if o.id in STATE_PAIR_MEMBERS else "(<=1.25%)"),
                   e["box"] * 100, hi=lim * 100, fmt=".2f"))
    out.append(num("layout:centre-of-mass-within-5%", e["mass"] * 100, hi=T["centre_mass_max"] * 100, fmt=".2f"))
    out.append(flag("layout:nothing-on-the-canvas-edge", max(al[0].max(), al[-1].max(), al[:, 0].max(), al[:, -1].max()) <= 8))
    return out


def check_small_layout(o, rd):
    e = _extents(rd["small256"][..., 3])
    return [num("small:cut-inside-safe-zone", e["reach"], hi=T["small_reach_max"]),
            num("small:cut-box-centred", e["box"] * 100, hi=(T["pair_box_max"] if o.id in STATE_PAIR_MEMBERS else T["small_box_max"]) * 100, fmt=".2f"),
            num("small:cut-centre-of-mass", e["mass"] * 100, hi=T["small_mass_max"] * 100, fmt=".2f")]


def check_emblem(o, rd):
    """Contrast of the emblem against the surface behind it, measured on its own pixels (eroded by one pixel so the
    anti-aliased rim does not count), and its place on that surface."""
    if rd.get("emb") is None:
        return []
    out = []
    ea = rd["emb"][..., 3]
    m = ndi.binary_erosion(ea > 0.8 * ea.max(), iterations=1)       # relative: the Guest's figure is drawn at 60% opacity
    if not m.any():
        return [flag("emblem:contrast-median", False, "no emblem pixels")]
    c = contrast_px(rd["full"][..., :3][m].astype(float), rd["noemb"][..., :3][m].astype(float))
    out.append(num("emblem:contrast-median", float(np.median(c)), lo=T["emb_med_min"], fmt=".2f"))
    out.append(num("emblem:contrast-10th-percentile", float(np.percentile(c, 10)), lo=T["emb_p10_min"], fmt=".2f"))
    if o.kind in HOST:
        pl = _place(o, rd["emb"], rd["host"], rd.get("fold"))
        if "dx" in pl:
            out.append(num("emblem:centred-horizontally-on-surface", pl["dx"] * 100, hi=T["emb_dx_max"] * 100, fmt=".2f"))
        if "dy" in pl:
            out.append(num("emblem:centred-vertically-on-surface", pl["dy"] * 100, hi=T["emb_dy_max"] * 100, fmt=".2f"))
        out.append(num("emblem:margin-to-surface-edge", pl["margin"] * 100, lo=T["emb_margin_min"] * 100, fmt=".2f"))
    return out


def _place(o, emb, host, fold):
    """Where the emblem sits on its surface: how far the middle of its bounding box is from the middle of the surface
    (dx, dy, share of the canvas) and its least distance to the surface's edge (margin). A page is held to its centre of
    mass vertically (the dog-ear takes a corner off the top); a drive's emblem is only held to the vertical middle
    because the LED sits on its right."""
    mode = HOST[o.kind][1]
    hm = host[..., 3] > 127
    em = emb[..., 3] > 127
    ys, xs = np.nonzero(em)
    ex, ey = (xs.min() + xs.max() + 1) / 2, (ys.min() + ys.max() + 1) / 2
    out = {}
    if mode in ("both", "vertical", "page"):
        hy, hx = np.nonzero(hm)
        if mode != "vertical":
            out["dx"] = abs(ex - (hx.min() + hx.max() + 1) / 2) / S
        # a page is held to its centre of mass (the dog-ear takes a corner off the top, so the mass is below the box middle)
        out["dy"] = abs(ey - (hy.mean() + 0.5 if mode == "page" else (hy.min() + hy.max() + 1) / 2)) / S
    dist = ndi.distance_transform_edt(np.pad(hm, 1))[1:-1, 1:-1]
    out["margin"] = float(dist[em].min()) / S
    return out


def check_small_emblem(o, rd):
    """The same placement checks on the small cut (its page border and cloud edge are thicker, so the margin is larger)."""
    pl = _place(o, rd["semb256"], rd["shost"], rd.get("sfold"))
    out = []
    if "dx" in pl:
        out.append(num("small:emblem-centred-horizontally", pl["dx"] * 100, hi=T["emb_dx_max"] * 100, fmt=".2f"))
    if "dy" in pl:
        out.append(num("small:emblem-centred-vertically", pl["dy"] * 100, hi=T["emb_dy_small_max"] * 100, fmt=".2f"))
    out.append(num("small:emblem-margin-to-surface-edge", pl["margin"] * 100, lo=T["small_margin_min"][o.kind] * 100, fmt=".2f",
                   label="small:emblem-margin-to-surface-edge(>=3.0 folders and drives, >=5.0 pages and cloud: they have a thick outline)"))
    return out


# the wallpapers are the brand kit's own
_WALL = {}
POS = [(x, y) for y in (100, 500, 900, 1250) for x in (150, 800, 1450, 2100)]      # 16 patches per wallpaper


def _walls():
    if not _WALL:
        for n in ("dusk", "dawn"):
            _WALL[n] = np.asarray(Image.open(ROOT / f"assets/brand/malva-{n}-2560x1440.jpg").convert("RGB"))
    return _WALL


def edge_ratios(icon, patch):
    """WCAG ratio between each pixel on the icon's outer edge and the wallpaper pixel just outside it."""
    a = icon[..., 3] / 255.0
    m = a > 0.98
    ring_in = m & ~ndi.binary_erosion(m, iterations=2)
    out = a < 0.02
    near = ndi.binary_dilation(~out, iterations=3) & out
    _, idx = ndi.distance_transform_edt(~near, return_indices=True)
    ys, xs = np.nonzero(ring_in)
    iy, ix = idx[0][ys, xs], idx[1][ys, xs]
    return contrast_px(icon[ys, xs, :3].astype(float), patch[iy, ix].astype(float))


def separation(icon128):
    res = {}
    for n, w in _walls().items():
        r = np.concatenate([edge_ratios(icon128, w[y:y + 128, x:x + 128]) for x, y in POS])
        res[n] = (float(np.median(r)), float(np.percentile(r, 10)))
    return res


def check_separation(o, rd):
    sp = separation(rd["e128"])
    return [num(f"wallpaper:edge-contrast-on-{n}", v[0], lo=T["sep_min"], fmt=".2f") for n, v in sp.items()]


def check_small(o, rd):
    out = []
    n32, n16 = int((rd["small32"][..., 3] > 127).sum()), int((rd["small16"][..., 3] > 127).sum())
    out.append(num("small:32px-ink-survives", n32, lo=T["ink32_min"], fmt=".0f"))
    out.append(num("small:16px-ink-survives", n16, lo=T["ink16_min"], fmt=".0f"))
    if rd.get("semb32") is not None:
        e32, e16 = int((rd["semb32"][..., 3] > 127).sum()), int((rd["semb16"][..., 3] > 127).sum())
        out.append(num("small:32px-emblem-survives", e32, lo=T["emb32_min"], fmt=".0f"))
        out.append(num("small:16px-emblem-survives", e16, lo=T["emb16_min"], fmt=".0f"))
        cov = lambda a: float(a[..., 3].sum()) / 255
        out.append(num("small:cut-emblem-heavier-than-full-cut-at-16px", cov(rd["semb16"]) / max(cov(rd["femb16"]), 1e-6), lo=T["heavier_min"], fmt=".2f"))
    return out


def _edge_left(a, rows):
    band = a[rows[0]:rows[1], :].mean(0)
    c = int(np.argmax(band >= 0.98))
    return c - float(band[max(0, c - 3):c].sum())


def _edge_bottom(a, cols):
    band = a[:, cols[0]:cols[1]].mean(1)
    r = int(len(band) - 1 - np.argmax(band[::-1] >= 0.98))
    return r + 1 + float(band[r + 1:r + 4].sum())


def corner_ratio(al, r):
    """Depth of the bottom-left corner along its diagonal, as a share of the corner box r, from a render at 1 px per
    canvas unit: a Balance-dial corner is sqrt(2)*m(N) = 0.225 for N = 4, a circular arc is 0.414."""
    a = al.astype(float) / 255
    ys, xs = np.nonzero(a > 0.5)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    ex = _edge_left(a, (y0 + r + 24, y1 - r - 24))
    ey = _edge_bottom(a, (x0 + r + 24, x1 - r - 24))
    t = np.arange(0, 3 * r, 0.05)
    v = ndi.map_coordinates(a, [ey - t / math.sqrt(2) - 0.5, ex + t / math.sqrt(2) - 0.5], order=1)
    k = int(np.argmax(v >= 0.5))
    if v[k] < 0.5:
        return float("nan")
    t0 = t[k - 1] + (0.5 - v[k - 1]) / max(v[k] - v[k - 1], 1e-9) * 0.05 if k else t[0]
    return t0 / r


EXPECT_CORNER = math.sqrt(2) * g.corner_fit(g.N)[2]


def check_corners(o, rd):
    sp = corner_spec(o)
    if not sp or rd.get("corner") is None:
        return []
    k = corner_ratio(rd["corner"][..., 3], sp[1]) / EXPECT_CORNER
    return [num("corners:balance-dial-superellipse(depth vs expected)", k, lo=1 - T["corner_tol"], hi=1 + T["corner_tol"], fmt=".3f")]


def check_symbolic(o, rd):
    out = []
    al = rd["sym220"][..., 3]
    clipped = max(al[0].max(), al[-1].max(), al[:, 0].max(), al[:, -1].max()) > 8
    out.append(flag("symbolic:nothing-clipped-by-the-canvas", not clipped))
    ys, xs = np.nonzero(al > 127)
    half = max(abs(xs.min() - 110), abs(xs.max() + 1 - 110), abs(ys.min() - 110), abs(ys.max() + 1 - 110)) / 110
    out.append(num("symbolic:ink-fills-canvas", half, lo=T["sym_fill"][0], hi=T["sym_fill"][1], fmt=".3f"))
    w = al.astype(float)
    cx, cy = (w.sum(0) * (np.arange(220) + .5)).sum() / w.sum() / 220 - .5, (w.sum(1) * (np.arange(220) + .5)).sum() / w.sum() / 220 - .5
    bx, by = (xs.min() + xs.max() + 1) / 220 / 2 - .5, (ys.min() + ys.max() + 1) / 220 / 2 - .5
    out.append(num("symbolic:box-centred", max(abs(bx), abs(by)) * 100, hi=T["sym_box_max"] * 100, fmt=".2f"))
    out.append(num("symbolic:centre-of-mass", max(abs(cx), abs(cy)) * 100, hi=T["sym_mass_max"] * 100, fmt=".2f"))
    out.append(num("symbolic:has-ink-at-16px", int((rd["sym16"][..., 3] > 127).sum()), lo=T["sym_ink16_min"], fmt=".0f"))
    # the one-colour drawing keeps the full drawing's outline: same silhouette once both are fitted to their bounding boxes
    out.append(num("symbolic:keeps-the-full-silhouette(IoU)", _sil_iou(rd["full"][..., 3] > 127, al > 20), lo=T["sym_sil_iou_min"], fmt=".3f"))
    return out


def _fit(mask, n=128):
    mask = convex_hull_image(ndi.binary_fill_holes(mask))      # the outer outline: cuts and notches inside a drawing do not count
    ys, xs = np.nonzero(mask)
    crop = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.uint8) * 255
    return np.asarray(Image.fromarray(crop).resize((n, n), Image.BILINEAR)) > 127


def _sil_iou(a, b):
    a, b = _fit(a), _fit(b)
    return float((a & b).sum() / max((a | b).sum(), 1))


def check_disc(o, rd):
    """Avatars, the group and the disc are circles: the outline fills the circle on its own bounding box."""
    if not (o.kind in ("person", "group", "disc") and o.id != "user-admin"):
        return []
    m = rd["full"][..., 3] > 127
    ys, xs = np.nonzero(m)
    w, h = xs.max() + 1 - xs.min(), ys.max() + 1 - ys.min()
    yy, xx = np.mgrid[0:S, 0:S]
    cx, cy, r = (xs.min() + xs.max() + 1) / 2, (ys.min() + ys.max() + 1) / 2, min(w, h) / 2
    circle = (xx + .5 - cx) ** 2 + (yy + .5 - cy) ** 2 <= r * r
    iou = (m & circle).sum() / (m | circle).sum()
    return [num("shape:disc-is-a-circle(IoU)", float(iou), lo=T["circle_iou_min"], fmt=".4f"),
            num("shape:disc-aspect(w/h)", w / h, lo=0.99, hi=1.01, fmt=".3f")]


def run_icon_checks(R, objs, agg=None, want=None):
    """Every per-icon check for these icons (or the subset `want` of render keys); returns the renders too."""
    agg = agg or Agg()
    rds = renders_many(R, objs, want)
    has = lambda rd, *k: all(x in rd and rd[x] is not None for x in k)
    for o, rd in zip(objs, rds):
        res = check_hygiene(o, rd["svg"], "full") + check_hygiene(o, rd["svg_small"], "small") + check_palette(o, rd["svg"])
        if "full" in rd:
            res += check_layout(o, rd) + check_disc(o, rd)
            if "e128" in rd:
                res += check_separation(o, rd)
            if has(rd, "emb", "noemb") and (o.kind not in HOST or has(rd, "host")) and (o.kind != "page" or has(rd, "fold")):
                res += check_emblem(o, rd)
            if "small256" in rd:
                res += check_small_layout(o, rd)
            if has(rd, "semb256") and o.kind in HOST and has(rd, "shost") and (o.kind != "page" or has(rd, "sfold")):
                res += check_small_emblem(o, rd)
            if "small32" in rd and "small16" in rd:
                res += check_small(o, rd)
            if "corner" in rd:
                res += check_corners(o, rd)
            if "sym220" in rd:
                res += check_symbolic(o, rd) + check_hygiene(o, rd["symsvg"], "symbolic")
        agg.add(o.id, res)
    return agg, rds


# --------------------------------------------------------------------------------------------- the set
def templates():
    ids = O.ORDER
    ob = O.OBJECTS
    return {
        "folders": [i for i in ids if ob[i].kind == "folder" and i != "folder-open"],
        "pages": [i for i in ids if ob[i].kind == "page"],
        "drives": [i for i in ids if ob[i].kind == "drive:internal"],
        "avatars": [i for i in ids if ob[i].kind == "person" and i != "user-admin"],
    }


def check_states(ids, rds):
    """Two states of one object (the bin empty and full) keep what they share where it is: the can does not jump when
    the papers appear, so the shift is common to both; and the pair as a whole sits on the middle of the canvas."""
    out = []
    for pair in STATE_PAIRS:
        if not all(p in ids for p in pair):
            continue
        a, b = (rds[ids.index(p)] for p in pair)
        boxes = []
        for rd in (a, b):
            ys, xs = np.nonzero(rd["can"][..., 3] > 127)
            boxes.append((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
        out.append(num(f"states:{pair[0]}/{pair[1]}-can-does-not-move", max(abs(u - v) for u, v in zip(*boxes)) / S * 100,
                       hi=T["state_move_max"] * 100, fmt=".2f"))
        ea, eb = _extents(a["full"][..., 3]), _extents(b["full"][..., 3])
        mean = [((ea["bbox"][k] + ea["bbox"][k + 2]) / 2 + (eb["bbox"][k] + eb["bbox"][k + 2]) / 2) / 2 - S / 2 for k in (0, 1)]
        out.append(num(f"states:{pair[0]}/{pair[1]}-mean-box-centred", max(abs(mean[0]), abs(mean[1])) / S * 100, hi=T["centre_box_max"] * 100, fmt=".2f"))
    return out


def check_templates(ids, rds):
    """Icons of one template share one outline and one weight: the silhouette of every member matches the first."""
    out = []
    for name, members in templates().items():
        members = [i for i in members if i in ids]
        if len(members) < 2:
            continue
        ref = rds[ids.index(members[0])]["full"][..., 3] > 127
        worst = 1.0
        for i in members[1:]:
            m = rds[ids.index(i)]["full"][..., 3] > 127
            worst = min(worst, (ref & m).sum() / (ref | m).sum())
        cov = np.array([(rds[ids.index(i)]["full"][..., 3] > 127).mean() for i in members])
        spread = float(np.max(np.abs(cov / np.median(cov) - 1)))
        out.append(num(f"template:{name}-share-one-silhouette(IoU)", float(worst), lo=T["iou_template_min"], fmt=".4f"))
        out.append(num(f"template:{name}-share-one-weight(max deviation)", spread, hi=T["weight_template_tol"], fmt=".3f"))
    return out


def check_weight(ids, rds):
    cov = {i: float((rds[k]["full"][..., 3] > 127).mean()) for k, i in enumerate(ids)}
    med = float(np.median(list(cov.values())))
    bad = [f"{i} {v / med:.2f}x" for i, v in cov.items() if not (T["weight_lo"] <= v / med <= T["weight_hi"])]
    spread = f"coverage {min(cov.values()) * 100:.1f}%..{max(cov.values()) * 100:.1f}% of the canvas, median {med * 100:.1f}%"
    return [flag(f"weight:every-icon-within-{T['weight_lo']:.2f}x..{T['weight_hi']:.1f}x-of-the-set-median", not bad, "; ".join(bad) or spread)]


def de2000_arr(l1, l2):
    L1, a1, b1 = l1[..., 0], l1[..., 1], l1[..., 2]
    L2, a2, b2 = l2[..., 0], l2[..., 1], l2[..., 2]
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cb ** 7 / (Cb ** 7 + 25.0 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p, h2p = np.degrees(np.arctan2(b1, a1p)) % 360, np.degrees(np.arctan2(b2, a2p)) % 360
    dLp, dCp, cc = L2 - L1, C2p - C1p, C1p * C2p
    dhp = h2p - h1p
    dhp = np.where(dhp > 180, dhp - 360, np.where(dhp < -180, dhp + 360, dhp))
    dhp = np.where(cc == 0, 0.0, dhp)
    dHp = 2 * np.sqrt(cc) * np.sin(np.radians(dhp / 2))
    Lbp, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    hs = h1p + h2p
    hbp = np.where(cc == 0, hs, np.where(np.abs(h1p - h2p) <= 180, hs / 2, np.where(hs < 360, (hs + 360) / 2, (hs - 360) / 2)))
    Tt = (1 - 0.17 * np.cos(np.radians(hbp - 30)) + 0.24 * np.cos(np.radians(2 * hbp)) + 0.32 * np.cos(np.radians(3 * hbp + 6))
          - 0.20 * np.cos(np.radians(4 * hbp - 63)))
    dth = 30 * np.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * np.sqrt(Cbp ** 7 / (Cbp ** 7 + 25.0 ** 7))
    Sl = 1 + 0.015 * (Lbp - 50) ** 2 / np.sqrt(20 + (Lbp - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cbp, 1 + 0.015 * Cbp * Tt
    Rt = -np.sin(np.radians(2 * dth)) * Rc
    return np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))


def rgb_to_lab_arr(rgb255):
    lin = g.srgb_to_lin(np.asarray(rgb255, float) / 255.0)
    X = lin @ np.array([0.4124564, 0.3575761, 0.1804375]) / 0.95047
    Y = lin @ np.array([0.2126729, 0.7151522, 0.0721750])
    Z = lin @ np.array([0.0193339, 0.1191920, 0.9503041]) / 1.08883
    ff = lambda t: np.where(t > (6 / 29) ** 3, np.cbrt(t), t / (3 * (6 / 29) ** 2) + 4 / 29)
    fx, fy, fz = ff(X), ff(Y), ff(Z)
    return np.stack([116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)], -1)


def simulate_arr(rgb255, kind):
    if kind == "normal":
        return np.asarray(rgb255, float)
    lin = g.srgb_to_lin(np.asarray(rgb255, float) / 255.0)
    return g.lin_to_srgb(np.clip(lin @ g.CVD[kind].T, 0, 1)) * 255


def pair_data(arrs32):
    """Small-cut renders at 32 px on neutral grey, in each vision type: Lab per pixel, and the opaque mask."""
    lab, mask = [], []
    for a in arrs32:
        al = a[..., 3:4].astype(float) / 255
        rgb = (a[..., :3] * al + 128.0 * (1 - al)).reshape(-1, 3)
        lab.append({v: rgb_to_lab_arr(simulate_arr(rgb, v)) for v in VISIONS})
        mask.append(a[..., 3].reshape(-1) > 127)
    return lab, mask


def pair_stats(lab, mask, i, j):
    union = mask[i] | mask[j]
    iou = float((mask[i] & mask[j]).sum() / max(union.sum(), 1))
    fr = min(float((de2000_arr(lab[i][v][union], lab[j][v][union]) >= (T["pair_de"] if v == "normal" else T["pair_de_cvd"])).mean()) for v in VISIONS)
    return iou, fr


def check_pairs(ids, rds):
    """Two icons are told apart if their outlines differ clearly, or if at least 2% of their shared area differs by
    dE00 >= 10 in every vision type (normal, protan, deutan, tritan): that covers a different emblem, a different
    page hue, a badge. Measured on the 32 px small cuts, the size a file manager shows them at."""
    lab, mask = pair_data([rd["small32"] for rd in rds])
    bad, lowest, worst_pair = [], 1e9, ""
    for a, b in combinations(range(len(ids)), 2):
        iou, fr = pair_stats(lab, mask, a, b)
        if not (iou <= T["pair_shape_iou"] or fr >= T["pair_frac_min"]):
            bad.append(f"{ids[a]}/{ids[b]} IoU {iou:.2f} differ {fr * 100:.1f}%")
        elif iou > T["pair_shape_iou"] and fr < lowest:
            lowest, worst_pair = fr, f"{ids[a]}/{ids[b]}"
    return [flag("distinct:every-pair-told-apart(outline IoU<=0.55 or >=2% of the shared area differs: dE00>=10 normal, >=4.5 colour-blind)", not bad,
                 "; ".join(bad[:6]) or f"{len(ids) * (len(ids) - 1) // 2} pairs; closest pair {worst_pair} differs in {lowest * 100:.1f}% of its area")]


def check_xdg(objs):
    """An installer copies each icon to share/icons/<theme>/<context>/<xdg name>.svg, so two icons under one name
    overwrite each other and one of them never shows. A name is optional (empty: no standard name), but never shared."""
    seen, dup, n = {}, [], 0
    for o in objs:
        if not o.xdg:
            continue
        n += 1
        if o.xdg in seen:
            dup.append(f"{o.xdg}: {seen[o.xdg]} and {o.id}")
        seen.setdefault(o.xdg, o.id)
    return [flag("manifest:icon-theme-names-are-unique", not dup, "; ".join(dup[:6]) or f"{n} names on {len(objs)} icons, none shared")]


# --------------------------------------------------------------------------------------------- the run
class Report:
    def __init__(self):
        self.lines, self.failed, self.total = [], 0, 0

    def extend(self, lines):
        for text, ok in lines:
            self.total += 1
            self.failed += 0 if ok else 1
            self.lines.append(text)

    def add(self, scope, results):
        for r in results:
            name, ok, info = r[0], r[1], r[2]
            self.extend([(f"{'PASS' if ok else 'FAIL'}  {scope:<8} {name}  {info}", ok)])


def run(report_path=None, negative=True):
    rep = Report()
    objs = [O.OBJECTS[i] for i in O.ORDER]
    with Renderer() as R:
        agg, rds = run_icon_checks(R, objs)
        lines, _ = agg.lines("icons")
        rep.extend(lines)
        rep.add("set", check_templates(O.ORDER, rds) + check_weight(O.ORDER, rds) + check_pairs(O.ORDER, rds) + check_states(O.ORDER, rds))
        allids = re.findall(r' id="([^"]+)"', "".join(rd["svg"] for rd in rds))
        rep.add("set", [flag("hygiene:ids-unique-across-the-whole-set", len(allids) == len(set(allids)), f"{len(allids)} ids")])
        rep.add("set", check_xdg(objs))
        neg = (negative_tests(R, objs, rds) + more_negative_tests(R, objs, rds)) if negative else []
    header = [f"object icons: {len(O.ORDER)}  checks: {rep.total}  failed: {rep.failed}  "
              f"negative tests (a broken icon must fail): {sum(1 for n in neg if n[1])}/{len(neg)}"]
    text = "\n".join(header + rep.lines + ["", "negative tests"] + [f"{'caught ' if ok else 'MISSED '} {n}  {info}" for n, ok, info in neg]) + "\n"
    if report_path:
        Path(report_path).write_text(text)
    return rep, neg, text


# --------------------------------------------------------------------------------------------- negative tests
def mutant(o, body=None, defs=None, scale=1.0, new_id=None, small=None, shift=None, sym=None):
    """A copy of an icon with a defect put in. body(role, svg, small) edits a part; scale shrinks or grows the drawing
    about the canvas centre; small(uid, small) replaces the whole parts list."""
    oid = new_id or o.id

    def build(uid, is_small):
        parts = small(uid, is_small) if small else o.build(uid, is_small)
        out = []
        for p in parts:
            b = body(p.role, p.body, is_small) if body else p.body
            if scale != 1.0:
                b = f'<g transform="translate(512 512) scale({scale}) translate(-512 -512)">{b}</g>'
            out.append(Part(p.role, b, defs(p.defs) if defs else p.defs))
        return out
    return Obj(oid, o.name, o.group, build, sym or o.sym, o.xdg, o.kind, o.emblem, o.meta, shift if shift is not None else o.shift)


@contextmanager
def patched(mod, **kw):
    old = {k: getattr(mod, k) for k in kw}
    for k, v in kw.items():
        setattr(mod, k, v)
    try:
        yield
    finally:
        for k, v in old.items():
            setattr(mod, k, v)


def _circ_rect(x, y, w, h, r):
    return (f"M{x + r} {y}H{x + w - r}A{r} {r} 0 0 1 {x + w} {y + r}V{y + h - r}A{r} {r} 0 0 1 {x + w - r} {y + h}"
            f"H{x + r}A{r} {r} 0 0 1 {x} {y + h - r}V{y + r}A{r} {r} 0 0 1 {x + r} {y}Z")


def _fails(res, prefix):
    names = [f"{r[0].split('(')[0]} = {r[2]}" if r[2] else r[0].split("(")[0] for r in res if not r[1] and r[0].startswith(prefix)]
    return bool(names), "; ".join(names)[:170]


def negative_tests(R, objs, rds) -> list:
    """Each broken icon must be rejected by the check that is meant to reject it."""
    out = []
    ob = O.OBJECTS

    def one(o, prefix, want=None, label=None, extra=None):
        agg, _ = run_icon_checks(R, [o], want=want)
        res = []
        for name, rows in agg.rows.items():
            res += [(name, r[1], r[2]) for r in rows]
        if extra:
            res += extra
        ok, info = _fails(res, prefix)
        out.append((label, ok, info))

    doc = ob["folder-documents"]
    # 1 emblem pushed off the surface's centre
    one(mutant(doc, body=lambda role, b, s: f'<g transform="translate(60 0)">{b}</g>' if role == "emblem" else b),
        "emblem:centred-horizontally", label="folder emblem 60 units off centre is rejected")
    one(mutant(doc, body=lambda role, b, s: f'<g transform="translate(0 70)">{b}</g>' if role == "emblem" else b),
        "emblem:centred-vertically", label="folder emblem 70 units too low is rejected")
    # 2 an emblem that barely differs from the panel it is engraved in
    one(mutant(ob["folder-music"], body=lambda role, b, s: b.replace('color="#3A1232"', 'color="#B0529C"') if role == "emblem" else b),
        "emblem:contrast", label="low-contrast emblem (about 1.3:1) is rejected")
    # 3 an emblem that outgrows its surface
    one(mutant(doc, body=lambda role, b, s: f'<g transform="translate(512 610) scale(2.3) translate(-512 -610)">{b}</g>' if role == "emblem" else b),
        "emblem:margin", label="emblem that spills over the folder front is rejected")
    # 4 a silhouette that is not the family's: a wider folder tab (checked as a template)
    with patched(O, F_TAB_R=540):
        odd = ob["folder-documents"]
        arr = R.render([object_svg(odd)], S)[0]
    ref = rds[O.ORDER.index("folder-documents")]["full"]
    fake_ids = ["folder", "folder-documents"]
    fake_rds = [{"full": ref}, {"full": arr}]
    res = check_templates(fake_ids, fake_rds)
    ok, info = _fails(res, "template:folders-share-one-silhouette")
    out.append(("folder with a different tab is rejected as a template member", ok, info))
    # 5 circular corners instead of the Balance dial's superellipse
    from objects import F_L, F_R, F_BOT, folder_front_path
    top = folder_front_path(False)[1]
    circ_d = _circ_rect(F_L, top, F_R - F_L, F_BOT - top, 64)
    one(mutant(doc, body=lambda role, b, s: re.sub(r'd="[^"]+"', f'd="{circ_d}"', b, count=1) if role == "front" else b),
        "corners:", label="circular corners (instead of the superellipse) are rejected")
    # 6 oversized and undersized
    one(mutant(doc, scale=1.15), "layout:inside-safe-zone", label="oversized icon (1.15x) is rejected")
    one(mutant(ob["file-text"], scale=0.5), "layout:not-too-small", label="undersized icon (0.5x) is rejected")
    one(mutant(ob["file-text"], shift=(40.0, 0.0)), "layout:box-centred", label="icon 40 units off centre is rejected")
    # the two states of one object: the full bin centred on its own (the can would jump when the papers appear), or both moved off
    full_bin = ob["trash-full"]
    jump = mutant(full_bin, shift=(full_bin.shift[0], full_bin.shift[1] + 40.0))
    rd_j = renders_many(R, [jump], want={"can", "full"})
    res = check_states(["trash-empty", "trash-full"], [rds[O.ORDER.index("trash-empty")], rd_j[0]])
    out.append(("a bin whose full state is moved 40 units on its own (the can jumps) is rejected", _fails(res, "states:trash-empty/trash-full-can-does-not-move")[0],
                _fails(res, "states:trash-empty/trash-full-can-does-not-move")[1]))
    both = [mutant(ob[i], shift=(ob[i].shift[0] + 60.0, ob[i].shift[1])) for i in ("trash-empty", "trash-full")]
    res = check_states(["trash-empty", "trash-full"], renders_many(R, both, want={"can", "full"}))
    out.append(("a bin pair moved 60 units sideways together is rejected", _fails(res, "states:trash-empty/trash-full-mean-box-centred")[0],
                _fails(res, "states:trash-empty/trash-full-mean-box-centred")[1]))
    # 7 weight: a tiny icon in the set
    tiny = mutant(ob["drive-internal"], scale=0.5, new_id="drive-tiny")
    agg, rd2 = run_icon_checks(R, [tiny], want={"full"})
    ids = O.ORDER + ["drive-tiny"]
    res = check_weight(ids, rds + rd2)
    out.append(("weight outlier (half-size drive) is rejected", not res[0][1], res[0][2][:120]))
    # 8 duplicates: the same icon twice under two names
    twin = mutant(ob["file-pdf"], new_id="file-pdf-copy")
    rd_t = renders_many(R, [twin], want={"small32"})
    res = check_pairs(["file-pdf", "file-pdf-copy"], [rds[O.ORDER.index("file-pdf")], rd_t[0]])
    out.append(("duplicate icon (same shape, same colour) is rejected", not res[0][1], res[0][2][:120]))
    # 9 hygiene
    svg = rds[O.ORDER.index("folder-documents")]["svg"]
    res = check_hygiene(doc, svg.replace("</svg>", "<text x='0' y='0'>x</text></svg>"))
    out.append(("an SVG with <text> is rejected", _fails(res, "hygiene[full]:no-text")[0], ""))
    res = check_hygiene(doc, svg.replace("<defs>", '<defs><filter id="folder-documents-f"><feGaussianBlur stdDeviation="4"/></filter>', 1))
    out.append(("an SVG with a filter is rejected", _fails(res, "hygiene[full]:no-text")[0], ""))
    res = check_hygiene(doc, svg.replace('id="folder-documents-back"', 'id="back"'))
    out.append(("an id without its icon's prefix is rejected", _fails(res, "hygiene[full]:ids")[0], ""))
    # 10 symbolic: canvas too tight (clips), hard-coded colour, off-centre canvas
    rdd = rds[O.ORDER.index("folder-documents")]
    for label, vb, pre in (("symbolic canvas that clips the ink is rejected", (300.0, 300.0, 424.0), "symbolic:nothing-clipped"),
                           ("symbolic canvas 90 units off centre is rejected", (rdd["vb"][0] + 90, rdd["vb"][1], rdd["vb"][2]), "symbolic:box-centred")):
        sv = symbolic_svg(doc, vb)
        a = R.render([sv], 220)[0]
        a16 = R.render([sv], 16)[0]
        res = check_symbolic(doc, {"sym220": a, "sym16": a16, "full": rdd["full"]})
        out.append((label, _fails(res, pre)[0], _fails(res, pre)[1]))
    lop = mutant(doc, sym=lambda: [O.P(O.circ(300, 512, 260)), O.P(O.rect(880, 492, 60, 40, 20))])      # box centred, mass 18 % to the left
    sv = symbolic_svg(lop, fit_viewbox(R, lop))
    res = check_symbolic(lop, {"sym220": R.render([sv], 220)[0], "sym16": rdd["sym16"], "full": rdd["full"]})
    out.append(("a symbolic drawing whose mass lies far from its box centre is rejected", _fails(res, "symbolic:centre-of-mass")[0], _fails(res, "symbolic:centre-of-mass")[1]))
    sv = rdd["symsvg"].replace('fill="currentColor"', 'fill="#FF0000"', 1)
    res = check_hygiene(doc, sv, "symbolic")
    out.append(("symbolic icon with a hard-coded colour is rejected", _fails(res, "hygiene[symbolic]:currentColor")[0], ""))
    # a symbolic drawing of the wrong object
    other = R.render([symbolic_svg(ob["optical-disc"], fit_viewbox(R, ob["optical-disc"]))], 220)[0]
    res = check_symbolic(doc, {"sym220": other, "sym16": rdd["sym16"], "full": rdd["full"]})
    out.append(("symbolic icon that is not the full icon's outline is rejected", _fails(res, "symbolic:keeps-the-full")[0], _fails(res, "symbolic:keeps-the-full")[1]))
    # 11 colour: a body that melts into the wallpaper, one that melts into the pale one
    def recolour(o, mapping):
        def fn(d):
            for a, b in mapping.items():
                d = d.replace(a, b)
            return d
        return mutant(o, defs=fn)
    dusk_like = {"#D06BBA": "#442440", "#A64C93": "#3C203A", "#9A4585": "#3F2239", "#7C3369": "#3A1E36"}
    dawn_like = {"#D06BBA": "#DCCFDA", "#A64C93": "#D4C6D2", "#9A4585": "#D8CAD6", "#7C3369": "#D0C2CE"}
    one(recolour(doc, dusk_like), "wallpaper:edge-contrast-on-dusk", want={"full", "e128"}, label="body as dark as the dusk wallpaper is rejected")
    one(recolour(doc, dawn_like), "wallpaper:edge-contrast-on-dawn", want={"full", "e128"}, label="body as pale as the dawn wallpaper is rejected")
    # 12 palette
    one(recolour(doc, {"#D06BBA": "#4A7BD0", "#A64C93": "#2F5AA8"}), "palette:only", want={"full"}, label="a blue folder is rejected by the palette check")
    pdf_t = ob["file-text"]
    one(mutant(pdf_t, body=lambda role, b, s: b.replace("#006A60", "#2255CC")), "palette:", want={"full"}, label="page ink in the wrong hue is rejected")
    # 13 the small cut: missing emblem, and no small cut at all (the full drawing reused)
    one(mutant(doc, small=lambda uid, s: [p for p in doc.build(uid, s) if not (s and p.role == "emblem")]),
        "small:16px-emblem-survives", want={"full", "small256", "small32", "small16", "semb32", "semb16", "femb16", "emb", "noemb"}, label="small cut without its emblem is rejected")
    one(mutant(doc, small=lambda uid, s: doc.build(uid, False)),
        "small:cut-emblem-heavier", want={"full", "small256", "small32", "small16", "semb32", "semb16", "femb16", "emb", "noemb"}, label="small cut that is just the full drawing is rejected")
    # 14 an avatar disc that is an ellipse
    one(mutant(ob["user"], body=lambda role, b, s: b.replace("a440 440", "a440 380") if role == "disc" else b),
        "shape:disc-is-a-circle", want={"full"}, label="elliptical avatar disc is rejected")
    return out


def more_negative_tests(R, objs, rds) -> list:
    """The rest of the checks, each with the defect it exists to catch."""
    out = []
    ob = O.OBJECTS
    doc = ob["folder-documents"]
    rd_doc = rds[O.ORDER.index("folder-documents")]

    def one(o, prefix, label, want=None):
        agg, _ = run_icon_checks(R, [o], want=want)
        res = [(name, r[1], r[2]) for name, rows in agg.rows.items() for r in rows]
        ok, info = _fails(res, prefix)
        out.append((label, ok, info))

    grow = lambda k: (lambda b: f'<g transform="translate(512 512) scale({k}) translate(-512 -512)">{b}</g>')
    # hygiene, one defect each
    svg = rd_doc["svg"]
    for label, bad_svg, pre in (
            ("an SVG whose viewBox is not 0 0 1024 1024 is rejected", svg.replace('viewBox="0 0 1024 1024"', 'viewBox="0 0 512 512"', 1), "hygiene[full]:viewBox"),
            ("an SVG without an accessible name is rejected", re.sub(r' aria-label="[^"]*"', "", svg, count=1), "hygiene[full]:accessible-name"),
            ("an SVG over 12 KB is rejected", svg.replace("</svg>", "<!--" + "x" * 12_000 + "--></svg>"), "hygiene[full]:size"),
            ("an SVG that loads something from the web is rejected", svg.replace("<defs>", '<defs><image href="http://example.com/a.png"/>', 1).replace("<image", "<path", 1), "hygiene[full]:no-external")):
        res = check_hygiene(doc, bad_svg)
        out.append((label, _fails(res, pre)[0], _fails(res, pre)[1]))
    res = check_hygiene(doc, rd_doc["symsvg"].replace('viewBox="', 'viewBox="0 0 ', 1).replace("0 0 0 0 ", "0 0 800 400 ", 1), "symbolic")
    out.append(("a symbolic SVG with a non-square canvas is rejected", _fails(res, "hygiene[symbolic]:square")[0], _fails(res, "hygiene[symbolic]:square")[1]))
    # layout: touching the canvas edge; the centre of mass alone
    one(mutant(doc, scale=1.3), "layout:nothing-on-the-canvas-edge", "icon that runs off the canvas is rejected", want={"full"})
    one(mutant(ob["file-text"], shift=(80.0, 0.0)), "layout:centre-of-mass", "centre of mass 7.8% off is rejected", want={"full"})
    # small cut: too big, off centre, too thin, emblem off its place
    one(mutant(doc, body=lambda role, b, s: grow(1.2)(b) if s else b), "small:cut-inside-safe-zone", "oversized small cut is rejected", want={"full", "small256"})
    one(mutant(doc, body=lambda role, b, s: f'<g transform="translate(60 0)">{b}</g>' if s else b), "small:cut-box-centred", "small cut 60 units off centre is rejected", want={"full", "small256"})
    one(mutant(doc, body=lambda role, b, s: grow(0.4)(b) if s else b), "small:16px-ink", "small cut that leaves under 40 px of ink at 16 px is rejected", want={"full", "small32", "small16"})
    one(mutant(doc, body=lambda role, b, s: f'<g transform="translate(60 0)">{b}</g>' if (s and role == "emblem") else b), "small:emblem-centred-horizontally",
        "small-cut emblem 60 units off centre is rejected")
    one(mutant(doc, body=lambda role, b, s: grow(1.5)(b) if (s and role == "emblem") else b), "small:emblem-margin", "small-cut emblem that overruns the folder is rejected")
    # symbolic: canvas far too loose, ink that vanishes at 16 px
    loose = (rd_doc["vb"][0] - 150, rd_doc["vb"][1] - 150, rd_doc["vb"][2] * 1.4)
    sv = symbolic_svg(doc, loose)
    a, a16 = R.render([sv], 220)[0], R.render([sv], 16)[0]
    res = check_symbolic(doc, {"sym220": a, "sym16": a16, "full": rd_doc["full"]})
    out.append(("symbolic canvas 40% too big (ink fills 63%) is rejected", _fails(res, "symbolic:ink-fills")[0], _fails(res, "symbolic:ink-fills")[1]))
    ring = mutant(doc, sym=lambda: [O.P(O.circ(512, 512, 400), stroke=14)])
    vb = fit_viewbox(R, ring)
    sv = symbolic_svg(ring, vb)
    a, a16 = R.render([sv], 220)[0], R.render([sv], 16)[0]
    res = check_symbolic(ring, {"sym220": a, "sym16": a16, "full": rd_doc["full"]})
    out.append(("hairline symbolic drawing (no ink at 16 px) is rejected", _fails(res, "symbolic:has-ink-at-16px")[0], _fails(res, "symbolic:has-ink-at-16px")[1]))
    # templates: same outline but a different weight
    small_f = R.render([object_svg(mutant(doc, scale=0.9))], S)[0]
    res = check_templates(["folder", "folder-documents"], [{"full": rds[O.ORDER.index("folder")]["full"]}, {"full": small_f}])
    out.append(("folder drawn 10% smaller than its siblings is rejected as a template member", _fails(res, "template:folders-share-one-weight")[0], _fails(res, "template:folders-share-one-weight")[1]))
    # pairs: a dot is not a difference
    pdf = ob["file-pdf"]
    dotted = mutant(pdf, new_id="file-pdf-dot", small=lambda uid, s: pdf.build(uid, s) + [Part("accent", f'<circle cx="512" cy="760" r="14" fill="#8C3274"/>')])
    rd_d = renders_many(R, [dotted], want={"small32"})
    res = check_pairs(["file-pdf", "file-pdf-dot"], [rds[O.ORDER.index("file-pdf")], rd_d[0]])
    out.append(("two pages that differ by a 14-unit dot are rejected as duplicates", not res[0][1], res[0][2][:120]))
    # ids across the set
    allids = re.findall(r' id="([^"]+)"', rd_doc["svg"] * 2)
    out.append(("the same icon included twice is rejected by the set-wide id check", len(allids) != len(set(allids)), f"{len(allids)} ids, {len(set(allids))} unique"))
    # icon-theme names: two icons under one name overwrite each other in an installed theme
    res = check_xdg([ob["file-text"], replace(ob["file"], xdg=ob["file-text"].xdg)])
    out.append(("two icons that share one icon-theme name are rejected", not res[0][1], res[0][2]))
    return out


if __name__ == "__main__":
    path = None
    if "--report" in sys.argv:
        path = sys.argv[sys.argv.index("--report") + 1]
    rep, neg, text = run(path, negative="--no-negative" not in sys.argv)
    print(text)
    sys.exit(1 if rep.failed or not all(n[1] for n in neg) else 0)
