"""Measured checks for the Settings-pane and category tiles (tiles.py). Pixels come from Chromium, nothing is judged
by eye, and every check has a negative test: a deliberately broken tile that the check must reject.

Run: python3 tools/icons/check_tiles.py [--report PATH] [--no-negative]

Thresholds sit between what the finished set measures and what the matching defect measures; both are in the report.
Where the app icons or the object icons set a standard (symbol size, tile edge against the wallpapers, WCAG 1.4.11
contrast for graphics) the tiles are held to it.
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).parent))
import tiles as TL
import check_objects as CO
from appfmt import app_icon_svg, Glyph, Tile
from checkkit import num, flag, Agg, Report, fails, finish
from mi_render import Renderer

S = 256
FORBIDDEN = {"text", "image", "script", "style", "foreignObject", "use", "a"}

T = dict(
    bytes_max=7000,                    # the set measures ~4.5 KB
    longest_min=0.46, longest_max=0.58,  # the apps measure 0.455..0.545; the tiles are normalised to 0.52 (clamped)
    box_max=0.0125,                    # the box of the symbol on the middle of the tile, as the object icons (optical.py leaves up to 1 % for a pull towards the mass)
    mass_max=0.090,                    # centre of mass: a guard against a lopsided symbol. A staircase of bars keeps its mass low and to the right (7.9 %); a slip of 120 units is 11.7 %
    contrast_med_min=3.0, contrast_p10_min=2.5,    # WCAG 1.4.11
    ink16_min=12.0, contrast16_min=2.2,     # the set measures >= 14; a stroke 35 % too thin measures 9..11
    sep_min=1.3,                       # the app tiles measure 1.3..1.7 against the brand wallpapers
    group_de_max=1.5,
    pair_shape_iou=0.55, pair_de=10.0, pair_de_cvd=4.5, pair_frac_min=0.02,
)


@dataclass
class Item:
    id: str
    svg: str            # what ships
    gsvg: str           # the symbol alone (no tile, no shadow)
    bsvg: str           # the tile alone (no symbol, no shadow)
    group: str


def build(i: str, tile: Tile | None = None, scale: float | None = None, shift=None, stroke: float | None = None, svg_edit=None) -> Item:
    sp = TL.BY_ID[i]
    gl = TL.glyph_of(i)
    if tile is not None:
        gl = replace(gl, tile=tile)
    if scale is not None:
        gl = replace(gl, scale=scale)
    if shift is not None:
        gl = replace(gl, shift=tuple(shift))
    if stroke is not None:
        gl = replace(gl, els=TL.els_of(sp.glyph, stroke))
    svg = app_icon_svg(gl, i, sp.name, "full")
    if svg_edit:
        svg = svg_edit(svg)
    return Item(i, svg,
                app_icon_svg(gl, i, i, "full", tile=False, shadow=False),
                app_icon_svg(replace(gl, els=[]), i, i, "full", shadow=False),
                sp.group)


# --------------------------------------------------------------------------------------------- renders
def render_items(R, items):
    out = [dict() for _ in items]
    for key, attr, size in (("full", "svg", S), ("glyph", "gsvg", S), ("base", "bsvg", S),
                            ("s32", "svg", 32), ("s16", "svg", 16), ("g16", "gsvg", 16), ("b16", "bsvg", 16), ("e128", "svg", 128)):
        arr = R.render([getattr(it, attr) for it in items], size)
        for rd, a in zip(out, arr):
            rd[key] = a
    return out


# --------------------------------------------------------------------------------------------- per-tile checks
def check_hygiene(it: Item):
    out = []
    try:
        root = ET.fromstring(it.svg)
    except ET.ParseError as e:
        return [flag("hygiene:well-formed-xml", False, str(e))]
    out.append(flag("hygiene:well-formed-xml", True))
    tags = {el.tag.split("}")[-1] for el in root.iter()}
    bad = sorted(tags & FORBIDDEN)
    out.append(flag("hygiene:no-text-image-script-style-use-or-links", not bad, ", ".join(bad)))
    ids = [el.get("id") for el in root.iter() if el.get("id")]
    stray = [x for x in ids if not x.startswith(it.id)]
    out.append(flag("hygiene:every-id-carries-the-icon-id(so SVGs can share a document)", not stray, ", ".join(stray[:3])))
    out.append(flag("hygiene:ids-are-unique", len(ids) == len(set(ids))))
    out.append(num("hygiene:file-size-bytes", len(it.svg.encode()), hi=T["bytes_max"], fmt=".0f"))
    vb = root.get("viewBox", "")
    out.append(flag("hygiene:viewBox-is-1024-square-and-no-fixed-size", vb == "0 0 1024 1024" and root.get("width") is None, vb))
    return out


def _extents(a):
    al = a[..., 3].astype(float) / 255
    ys, xs = np.nonzero(al > 0.5)
    n = al.shape[0]
    w, h = (xs.max() - xs.min() + 1) / n, (ys.max() - ys.min() + 1) / n
    bx, by = (xs.min() + xs.max() + 1) / 2 / n - 0.5, (ys.min() + ys.max() + 1) / 2 / n - 0.5
    mx = (al * np.arange(n)[None, :]).sum() / al.sum() / n + 0.5 / n - 0.5
    my = (al * np.arange(n)[:, None]).sum() / al.sum() / n + 0.5 / n - 0.5
    return dict(longest=max(w, h), box=float(max(abs(bx), abs(by))), mass=float(np.hypot(mx, my)))


def check_layout(rd):
    e = _extents(rd["glyph"])
    return [num("layout:symbol-longest-side-as-share-of-tile", e["longest"], lo=T["longest_min"], hi=T["longest_max"]),
            num("layout:box-centred(% of tile)", e["box"] * 100, hi=T["box_max"] * 100, fmt=".2f"),
            num("layout:centre-of-mass-within-9%", e["mass"] * 100, hi=T["mass_max"] * 100, fmt=".2f")]


def check_contrast(rd):
    ga = rd["glyph"][..., 3].astype(float)
    m = ndi.binary_erosion(ga > 0.8 * ga.max(), iterations=1)          # the dim parts and the anti-aliased rim do not count
    if not m.any():
        return [flag("contrast:symbol-pixels-exist", False)]
    c = CO.contrast_px(rd["full"][..., :3][m].astype(float), rd["base"][..., :3][m].astype(float))
    return [num("contrast:symbol-vs-tile-median(WCAG 1.4.11 graphics)", float(np.median(c)), lo=T["contrast_med_min"], fmt=".2f"),
            num("contrast:symbol-vs-tile-10th-percentile", float(np.percentile(c, 10)), lo=T["contrast_p10_min"], fmt=".2f")]


def check_small(rd):
    g = rd["g16"][..., 3].astype(float) / 255
    ink = float(g.sum())
    m = g > 0.6
    if m.sum() < 3:
        return [num("small:16px-symbol-ink", ink, lo=T["ink16_min"], fmt=".1f")]
    c = CO.contrast_px(rd["s16"][..., :3][m].astype(float), rd["b16"][..., :3][m].astype(float))
    return [num("small:16px-symbol-ink(px)", ink, lo=T["ink16_min"], fmt=".1f"),
            num("small:16px-symbol-vs-tile-contrast-median", float(np.median(c)), lo=T["contrast16_min"], fmt=".2f")]


def check_separation(rd):
    sp = CO.separation(rd["e128"])
    return [num(f"wallpaper:tile-edge-contrast-on-{n}", v[0], lo=T["sep_min"], fmt=".2f") for n, v in sp.items()]


def run_tile_checks(R, items, rds=None, agg=None):
    rds = rds or render_items(R, items)
    agg = agg or Agg()
    for it, rd in zip(items, rds):
        agg.add(it.id, check_hygiene(it) + check_layout(rd) + check_contrast(rd) + check_small(rd) + check_separation(rd))
    return agg, rds


# --------------------------------------------------------------------------------------------- set checks
def tile_colour(rd):
    a = rd["base"]
    m = a[..., 3] > 250
    return a[..., :3][m].astype(float).mean(0)


def check_groups(items, rds):
    """Every tile of a group is the group's colour; the colour is read from the tile alone (no symbol, no shadow)."""
    out, bad = [], []
    by = {}
    for it, rd in zip(items, rds):
        if it.group:
            by.setdefault(it.group, []).append((it.id, tile_colour(rd)))
    worst = 0.0
    for gname, mem in by.items():
        lab = CO.rgb_to_lab_arr(np.array([c for _, c in mem]))
        med = np.median(lab, 0)
        de = CO.de2000_arr(lab, np.broadcast_to(med, lab.shape))
        worst = max(worst, float(de.max()))
        bad += [f"{mem[k][0]} dE {de[k]:.1f}" for k in range(len(mem)) if de[k] > T["group_de_max"]]
    out.append(flag(f"group:every-tile-is-its-group's-colour(dE00<={T['group_de_max']})", not bad, "; ".join(bad[:5]) or f"{len(by)} groups, largest deviation dE {worst:.2f}"))
    return out


def _sil(rd):
    return rd["glyph"][..., 3] > 127


def check_pairs(items, rds):
    """Two tiles are told apart if their symbols differ clearly (silhouette IoU <= 0.55), or their tiles differ by dE00
    >= 10 in normal vision and >= 4.5 in each colour-blind simulation. Colour is the second cue, the symbol the first."""
    lab = []
    for rd in rds:
        c = tile_colour(rd)[None, :]
        lab.append({v: CO.rgb_to_lab_arr(CO.simulate_arr(c, v))[0] for v in CO.VISIONS})
    sils = [_sil(rd) for rd in rds]
    bad, closest = [], (0.0, "")
    for a, b in combinations(range(len(items)), 2):
        iou = float((sils[a] & sils[b]).sum() / max((sils[a] | sils[b]).sum(), 1))
        if iou <= T["pair_shape_iou"]:
            continue
        de = min(float(CO.de2000_arr(lab[a][v][None, :], lab[b][v][None, :])[0]) / (T["pair_de"] if v == "normal" else T["pair_de_cvd"]) for v in CO.VISIONS)
        if de < 1.0:
            bad.append(f"{items[a].id}/{items[b].id} IoU {iou:.2f}")
        if iou > closest[0]:
            closest = (iou, f"{items[a].id}/{items[b].id}")
    return [flag("distinct:every-pair-told-apart(symbol IoU<=0.55, or tile dE00>=10 normal and >=4.5 colour-blind)", not bad,
                 "; ".join(bad[:6]) or f"{len(items) * (len(items) - 1) // 2} pairs; most alike symbols {closest[1]} (IoU {closest[0]:.2f}) sit on tiles that differ")]


def check_names(items):
    ids = [it.id for it in items]
    ok_fmt = all(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", i) for i in ids)
    bad_sym = [i for i in ids if TL.BY_ID[i].glyph not in TL.EXTRA and TL.BY_ID[i].glyph not in TL.K.GLYPHS]
    return [flag("names:ids-are-lowercase-hyphenated-and-unique", ok_fmt and len(ids) == len(set(ids))),
            flag("names:every-symbol-exists-in-the-glyph-kit", not bad_sym, ", ".join(bad_sym))]


def check_determinism(items):
    again = [build(it.id).svg for it in items]
    bad = [it.id for it, s in zip(items, again) if s != it.svg]
    return [flag("determinism:building-twice-gives-the-same-bytes", not bad, ", ".join(bad[:5]))]


def run(report_path=None, negative=True):
    ids = TL.ORDER
    items = [build(i) for i in ids]
    rep = Report()
    with Renderer() as R:
        agg, rds = run_tile_checks(R, items)
        lines, _ = agg.lines("tiles")
        rep.extend(lines)
        rep.add("set", check_groups(items, rds) + check_pairs(items, rds) + check_names(items) + check_determinism(items))
        neg = negative_tests(R, items, rds) if negative else []
    text = finish(rep, neg, f"tiles: {len(items)}", report_path)
    return rep, neg, text


# --------------------------------------------------------------------------------------------- negative tests
def _fail_of(res, prefix):
    return fails(res, prefix)


def negative_tests(R, items, rds):
    neg = []
    ids = [it.id for it in items]

    def one(it_id, **kw):
        it = build(it_id, **kw)
        rd = render_items(R, [it])[0]
        return it, rd

    def expect(name, res, prefix):
        bad, info = _fail_of(res, prefix)
        neg.append((name, bad, info))

    it, rd = one("preferences-system-wifi", shift=(30.0, 0.0))
    expect("symbol 30 units off the middle", check_layout(rd), "layout:box-centred")
    it, rd = one("preferences-system-wifi", shift=(120.0, 0.0))
    expect("symbol 120 units off the middle (mass 11 % off)", check_layout(rd), "layout:centre-of-mass")
    it, rd = one("preferences-system-wifi", scale=1.15 * 1.5)
    expect("symbol 1.5x too large", check_layout(rd), "layout:symbol-longest-side")
    it, rd = one("preferences-system-wifi", scale=1.15 * 0.6)
    expect("symbol 0.6x too small", check_layout(rd), "layout:symbol-longest-side")
    it, rd = one("preferences-system-wifi", tile=Tile(h=250, l=0.93, c=0.03, ld=0.90, cd=0.03))
    expect("pale tile: the lilac symbol has no contrast", check_contrast(rd), "contrast:symbol-vs-tile-median")
    it, rd = one("preferences-system-wifi", stroke=0.5)
    expect("hairline strokes: nothing left at 16 px", check_small(rd), "small:16px-symbol-ink")
    it, rd = one("preferences-system-wifi", stroke=1.4)
    expect("strokes 40 % too thin", check_small(rd), "small:16px-symbol-ink")
    it, rd = one("preferences-system-wifi", tile=Tile(h=250, l=0.93, c=0.03, ld=0.90, cd=0.03))
    expect("pale tile against the light wallpaper: no edge", check_separation(rd), "wallpaper:tile-edge-contrast")
    it = build("preferences-system-wifi", svg_edit=lambda s: s.replace("</svg>", "<text>x</text></svg>"))
    expect("a <text> element", check_hygiene(it), "hygiene:no-text")
    it = build("preferences-system-wifi", svg_edit=lambda s: s.replace('id="preferences-system-wifi', 'id="other-', 1))
    expect("an id that does not carry the icon id", check_hygiene(it), "hygiene:every-id-carries")
    it = build("preferences-system-wifi", svg_edit=lambda s: s.replace("</svg>", "<!--" + "x" * 8000 + "--></svg>"))
    expect("a 12 KB file", check_hygiene(it), "hygiene:file-size")
    it = build("preferences-system-wifi", svg_edit=lambda s: s.replace('viewBox="0 0 1024 1024"', 'width="64" height="64" viewBox="0 0 1024 1024"'))
    expect("a fixed pixel size", check_hygiene(it), "hygiene:viewBox")

    # one tile of a group in another colour
    k = ids.index("preferences-system-bluetooth")
    drift, drd = one("preferences-system-bluetooth", tile=Tile(h=275))
    its = list(items)
    its[k] = drift
    rds2 = list(rds)
    rds2[k] = drd
    expect("one tile of Network 25 degrees off its group's hue", check_groups(its, rds2), "group:every-tile")

    # two tiles with one symbol in one colour
    a = ids.index("preferences-system-wifi")
    b = ids.index("preferences-system-bluetooth")
    twin = build("preferences-system-bluetooth")
    twin_rd = render_items(R, [build("preferences-system-wifi")])[0]
    its = list(items)
    its[b] = replace(twin, gsvg=items[a].gsvg, bsvg=items[a].bsvg)
    rds2 = list(rds)
    rds2[b] = rds[a]
    expect("two panes with the same symbol on the same tile", check_pairs(its, rds2), "distinct:every-pair")
    return neg


if __name__ == "__main__":
    rp = None
    if "--report" in sys.argv:
        rp = sys.argv[sys.argv.index("--report") + 1]
    rep, neg, text = run(rp, negative="--no-negative" not in sys.argv)
    print(text)
    sys.exit(1 if rep.failed or any(not ok for _, ok, _ in neg) else 0)
