"""Measured checks for the app icons. Everything here reads pixels rendered by Chromium or parses the
SVG; nothing is judged by eye. Run: python3 tools/icons/check_apps.py [--report PATH]"""
from __future__ import annotations

import copy
import math
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).parent))
import appfmt as A
import apps
import mi_geom as g
import hints as H
from mi_render import Renderer
from build_apps import icon_svg, symbolic_vb

ROOT = Path(__file__).resolve().parents[2]
S = 256                      # analysis size
FORBIDDEN = {"text", "image", "script", "style", "foreignObject", "use", "a"}
Res = tuple  # (name, ok, info)


# Centring is judged the way optical.py makes it: the BOX of the glyph on the middle of the tile (the rule leaves at most
# 1 % for a small pull towards the mass; whole units and pixels add the rest), and the centre of mass only as a guard
# against a lopsided drawing. Measured on the finished set, and what the defect (a glyph slid 40 units) measures.
BOX_MAX = 0.0125              # tile and small cut: the set measures <= 0.9 %
SMALL_BOX_MAX = 0.015
SYM_BOX_MAX = 0.015           # symbolic canvas
MASS_MAX = 0.050              # tile: the set measures <= 3.2 % (music, text editor)
SMALL_MASS_MAX = 0.060
SYM_MASS_MAX = 0.110          # symbolic: the glyph fills 84-92 % of its canvas, so offsets are larger in canvas terms

def empty(gl):
    return A.Glyph(gl.tile, [], gl.label, gl.scale)


def renders(R, i, gl):
    """All the renders one app needs, keyed by purpose."""
    stops = A.BRAND_TILE_STOPS if i == "malva" else None
    kw = {"brand_stops": stops} if stops else {}
    full = A.app_icon_svg(gl, i, i, **kw)
    tile = A.app_icon_svg(empty(gl), i, i, shadow=False, **kw)
    glyph_all = A.app_icon_svg(gl, i, i, tile=False, shadow=False, **kw)
    glyph_p = A.app_icon_svg(gl, i, i, tile=False, shadow=False, tones="p", **kw)
    glyph_t = A.app_icon_svg(gl, i, i, tile=False, shadow=False, tones="t", **kw)
    out = R.render([full, tile, glyph_all, glyph_p, glyph_t], S)
    return dict(zip(("full", "tile", "all", "p", "t"), out)), full


def lum(rgb):
    return g.rel_lum(rgb)


def contrast_px(fg, bg):
    """Per-pixel WCAG ratio between two HxWx3 arrays (0..255)."""
    def y(a):
        l = g.srgb_to_lin(a / 255.0)
        return 0.2126 * l[..., 0] + 0.7152 * l[..., 1] + 0.0722 * l[..., 2]
    a, b = y(fg.astype(float)), y(bg.astype(float))
    hi, lo = np.maximum(a, b), np.minimum(a, b)
    return (hi + 0.05) / (lo + 0.05)


def check_hygiene(i, svg) -> list[Res]:
    out = []
    root = ET.fromstring(svg)
    tags = {e.tag.split("}")[-1] for e in root.iter()}
    out.append(("hygiene:no-forbidden-elements", not (tags & FORBIDDEN), f"{sorted(tags & FORBIDDEN)}"))
    out.append(("hygiene:viewBox", root.get("viewBox") == "0 0 1024 1024", root.get("viewBox")))
    out.append(("hygiene:accessible-name", bool(root.get("aria-label")) and root.get("role") == "img", root.get("aria-label")))
    out.append(("hygiene:size<12KB", len(svg) < 12_000, f"{len(svg)} bytes"))
    ids = re.findall(r' id="([^"]+)"', svg)
    out.append(("hygiene:ids-prefixed-and-unique", len(ids) == len(set(ids)) and all(x.startswith(i + "-") for x in ids), f"{len(ids)} ids"))
    out.append(("hygiene:no-external-refs", "http" not in re.sub(r'xmlns="[^"]+"', "", svg) and "xlink" not in svg, ""))
    return out


def check_pixels(i, rd) -> list[Res]:
    out = []
    full, tile, allg, prim, acct = (rd[k] for k in ("full", "tile", "all", "p", "t"))
    # shape: everything drawn stays inside the tile (the shadow may not leak outside it)
    ta = tile[..., 3]
    grown = ta.copy()
    for _ in range(2):   # allow 2 px of edge anti-aliasing noise between the two renders
        p = np.pad(grown, 1, mode="edge")
        grown = np.max([p[dy:dy + S, dx:dx + S] for dy in range(3) for dx in range(3)], axis=0)
    leak = int(((full[..., 3].astype(int) - grown.astype(int)) > 8).sum())
    out.append(("shape:nothing-outside-tile", leak == 0, f"{leak} px outside the tile (+2 px AA band)"))
    # extents and centring of the glyph (all tones), measured on pixels
    m = allg[..., 3] > 127
    ys, xs = np.nonzero(m)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    half = S / 2
    reach = max(abs(x0 - half), abs(x1 + 1 - half), abs(y0 - half), abs(y1 + 1 - half)) / half
    out.append(("layout:inside-safe-zone(<=0.66)", reach <= 0.66, f"reach {reach:.3f} of half-tile"))
    wh = max(x1 + 1 - x0, y1 + 1 - y0) / S
    out.append(("layout:not-too-small(>=0.40)", wh >= 0.40, f"longest side {wh:.3f} of tile"))
    w = allg[..., 3].astype(float)
    cx, cy = (w * np.arange(S)[None, :]).sum() / w.sum(), (w * np.arange(S)[:, None]).sum() / w.sum()
    off = max(abs(cx + 0.5 - half), abs(cy + 0.5 - half)) / S
    box = max(abs((x0 + x1 + 1) / 2 - half), abs((y0 + y1 + 1) / 2 - half)) / S
    out.append(("layout:box-centred(<=1.25%)", box <= BOX_MAX, f"box off by {box * 100:.2f}% of tile"))
    out.append(("layout:centre-of-mass-within-5%", off <= MASS_MAX, f"centroid off by {off * 100:.2f}% of tile"))
    # contrast of the primary glyph against the tile behind it (WCAG 1.4.11 asks 3:1 for graphics)
    sel = prim[..., 3] > 250
    c = contrast_px(prim[..., :3][sel], tile[..., :3][sel])
    out.append(("contrast:glyph-vs-tile>=3.0", c.min() >= 3.0, f"min {c.min():.2f}, median {np.median(c):.2f}"))
    out.append(("contrast:glyph-vs-tile 5th percentile (info, target 4.5)", True, f"{np.percentile(c, 5):.2f}"))
    sel = acct[..., 3] > 250
    if sel.any():
        c = contrast_px(acct[..., :3][sel], tile[..., :3][sel])
        out.append(("contrast:leaf-accent-vs-tile>=2.0 (decorative only)", c.min() >= 2.0, f"min {c.min():.2f}"))
    return out


def check_static() -> list[Res]:
    c = g.contrast(g.hex_to_rgb(A.LEAF_ON_LILAC), g.hex_to_rgb(A.LILAC_BOT))
    out = [("contrast:leaf-on-lilac>=3.0", c >= 3.0, f"{c:.2f} (#4F7A2F on #DEC3E0)")]
    c2 = g.contrast(g.hex_to_rgb(A.LILAC_BOT), g.hex_to_rgb(A.PLUM_LIGHT))
    out.append(("contrast:supplied-icon-glyph-vs-lightest-tile (info)", True, f"{c2:.2f}"))
    return out


def pair_checks(ids, rd, masks64) -> tuple[list[Res], dict]:
    lab = {}
    for i in ids:
        m = rd[i]["tile"][..., 3] > 250
        rgb = rd[i]["tile"][..., :3][m].mean(0)
        lab[i] = {"normal": rgb}
        for k in g.CVD:
            lab[i][k] = g.simulate(rgb, k)
    bad, stats = [], {"min_de": {"normal": 1e9, "protan": 1e9, "deutan": 1e9, "tritan": 1e9}, "max_iou": 0.0}
    for a, b in combinations(ids, 2):
        des = {}
        for k in ("normal", "protan", "deutan", "tritan"):
            des[k] = g.de2000(g.rgb_to_lab(lab[a][k]), g.rgb_to_lab(lab[b][k]))
            stats["min_de"][k] = min(stats["min_de"][k], des[k])
        ma, mb = masks64[a], masks64[b]
        iou = (ma & mb).sum() / max(1, (ma | mb).sum())
        stats["max_iou"] = max(stats["max_iou"], iou)
        # a pair is "told apart" if the shapes differ clearly, or the tiles differ in every vision type
        if not (iou <= 0.55 or min(des.values()) >= 8.0):
            bad.append(f"{a}/{b} iou {iou:.2f} minΔE {min(des.values()):.1f}")
    out = [("distinct:every-pair-told-apart(shape IoU<=0.55 or ΔE00>=8 in every vision)", not bad, "; ".join(bad) or "all pairs ok")]
    out.append(("distinct:max-glyph-IoU(info)", True, f"{stats['max_iou']:.2f}"))
    for k, v in stats["min_de"].items():
        out.append((f"distinct:min-tile-ΔE00-{k}(info)", True, f"{v:.1f}"))
    return out, stats


def check_weight(ids, rd) -> list[Res]:
    cov = {i: (rd[i]["all"][..., 3] > 127).mean() for i in ids}
    med = float(np.median(list(cov.values())))
    bad = [f"{i} {v / med:.2f}x" for i, v in cov.items() if not (0.55 <= v / med <= 1.7)]
    spread = f"coverage {min(cov.values()) * 100:.1f}%..{max(cov.values()) * 100:.1f}% of tile, median {med * 100:.1f}%"
    return [("weight:optical-weight-within-0.55x..1.7x-median", not bad, "; ".join(bad) or spread)]


def check_small(R, ids) -> list[Res]:
    out = []
    for s in (32, 16):
        svgs = [A.app_icon_svg(apps.GLYPHS[i], i, i, mode="small", tile=False, tones="p",
                               **({"brand_stops": A.BRAND_TILE_STOPS} if i == "malva" else {})) for i in ids]
        arr = R.render(svgs, s)
        bad = []
        for i, a in zip(ids, arr):
            m = a[..., 3] > 127
            ys, xs = np.nonzero(m)
            n, w = int(m.sum()), (xs.max() - xs.min() + 1) if n_ok(m) else 0
            if n < (60 if s == 32 else 14) or w < s * 0.30:
                bad.append(f"{i} ink {n}px width {w}")
        out.append((f"small:{s}px-primary-ink-survives", not bad, "; ".join(bad) or "all 16 ok"))
    big = [A.app_icon_svg(apps.GLYPHS[i], i, i, mode="small", tile=False, **({"brand_stops": A.BRAND_TILE_STOPS} if i == "malva" else {})) for i in ids]
    reach_bad = []
    for i, a in zip(ids, R.render(big, S)):
        ys, xs = np.nonzero(a[..., 3] > 127)
        r = max(abs(xs.min() - S / 2), abs(xs.max() + 1 - S / 2), abs(ys.min() - S / 2), abs(ys.max() + 1 - S / 2)) / (S / 2)
        if r > 0.74:
            reach_bad.append(f"{i} {r:.2f}")
    out.append(("small:boosted-glyph-inside-safe-zone(<=0.74)", not reach_bad, "; ".join(reach_bad) or "all 16 ok"))
    off_bad, box_bad, hi_box, hi_mass = [], [], (0.0, ""), (0.0, "")
    for i, a in zip(ids, R.render(big, S)):
        al = a[..., 3].astype(float)
        cx = (al * np.arange(S)[None, :]).sum() / al.sum() / S - 0.5
        cy = (al * np.arange(S)[:, None]).sum() / al.sum() / S - 0.5
        ys, xs = np.nonzero(al > 127)
        bx, by = (xs.min() + xs.max() + 1) / 2 / S - 0.5, (ys.min() + ys.max() + 1) / 2 / S - 0.5
        mo, bo = max(abs(cx), abs(cy)), max(abs(bx), abs(by))
        hi_box, hi_mass = max(hi_box, (bo, i)), max(hi_mass, (mo, i))
        if bo > SMALL_BOX_MAX:
            box_bad.append(f"{i} {bo * 100:.1f}%")
        if mo > SMALL_MASS_MAX:
            off_bad.append(f"{i} {mo * 100:.1f}%")
    out.append(("small:cut-box-centred(<=1.5%)", not box_bad, "; ".join(box_bad) or f"all 16 ok, highest {hi_box[0] * 100:.2f}% ({hi_box[1]})"))
    out.append(("small:cut-centre-of-mass(<=6%)", not off_bad, "; ".join(off_bad) or f"all 16 ok, highest {hi_mass[0] * 100:.2f}% ({hi_mass[1]})"))
    return out


def n_ok(m):
    return bool(m.any())


def check_fidelity(R) -> list[Res]:
    sup = (ROOT / "assets/brand/logo/malva-app-icon.svg").read_text()
    a = R.render([sup], 512)[0].astype(int)
    gl = apps.GLYPHS["malva"]
    b = R.render([A.app_icon_svg(gl, "malva", "Malva OS", brand_stops=A.BRAND_TILE_STOPS, shadow=False)], 512)[0].astype(int)
    d = np.abs(a[..., :3] - b[..., :3])
    m = (a[..., 3] > 0) | (b[..., 3] > 0)
    mean, p999 = d[m].mean(), np.percentile(d[m], 99.9)
    ia = (a[..., 3] > 127) & (b[..., 3] > 127)
    iou = ia.sum() / ((a[..., 3] > 127) | (b[..., 3] > 127)).sum()
    return [("fidelity:rebuilt-malva-icon-matches-supplied-svg(mean<=0.5, p99.9<=20, IoU>=0.999)",
             mean <= 0.5 and p999 <= 20 and iou >= 0.999,
             f"mean abs diff {mean:.3f}/255, 99.9th percentile {p999:.0f}, tile IoU {iou:.5f}")]


@dataclass
class Report:
    lines: list
    failed: int = 0
    total: int = 0

    def add(self, scope, results):
        for name, ok, info in results:
            self.total += 1
            if not ok:
                self.failed += 1
            self.lines.append(f"{'PASS' if ok else 'FAIL'}  {scope:<16} {name}  {info}")


def check_symbolic(R, ids, vbs=None, tag=""):
    """Symbolic (currentColor) icons: nothing clipped by the canvas, glyph fills 84-92% of it, centred,
    and the same primary shapes survive at 16 px."""
    out = []
    vbs = vbs or {i: symbolic_vb(R, i) for i in ids}
    svgs = [A.app_icon_svg(apps.GLYPHS[i], i, i, mode="symbolic", sym_vb=vbs[i]) for i in ids]
    arr = R.render(svgs, 220)
    a16 = R.render(svgs, 16)
    clipped, fill_bad, off, thin, boxoff = [], [], [], [], []
    hi_b, hi_m = (0.0, ""), (0.0, "")
    for i, a, s in zip(ids, arr, a16):
        al = a[..., 3]
        if max(al[0].max(), al[-1].max(), al[:, 0].max(), al[:, -1].max()) > 8:
            clipped.append(i)
        ys, xs = np.nonzero(al > 127)
        half = max(abs(xs.min() - 110), abs(xs.max() + 1 - 110), abs(ys.min() - 110), abs(ys.max() + 1 - 110)) / 110
        if not 0.84 <= half <= 0.92:
            fill_bad.append(f"{i} {half:.2f}")
        cx = (al * np.arange(220)[None, :]).sum() / al.sum() / 220 - 0.5
        cy = (al * np.arange(220)[:, None]).sum() / al.sum() / 220 - 0.5
        bo = max(abs((xs.min() + xs.max() + 1) / 2 / 220 - 0.5), abs((ys.min() + ys.max() + 1) / 2 / 220 - 0.5))
        mo = max(abs(cx), abs(cy))
        hi_b, hi_m = max(hi_b, (bo, i)), max(hi_m, (mo, i))
        if bo > SYM_BOX_MAX:
            boxoff.append(f"{i} {bo * 100:.1f}%")
        if mo > SYM_MASS_MAX:
            off.append(f"{i} {mo * 100:.1f}%")
        if (s[..., 3] > 127).sum() < 18:
            thin.append(i)
    out.append((f"symbolic{tag}:nothing-clipped-by-the-canvas", not clipped, ", ".join(clipped) or f"{len(ids)} ok"))
    out.append((f"symbolic{tag}:glyph-fills-84-92%-of-canvas", not fill_bad, "; ".join(fill_bad) or f"{len(ids)} ok"))
    out.append((f"symbolic{tag}:box-centred(<=1.5%)", not boxoff, "; ".join(boxoff) or f"{len(ids)} ok, highest {hi_b[0] * 100:.2f}% ({hi_b[1]})"))
    out.append((f"symbolic{tag}:centre-of-mass-within-11%", not off, "; ".join(off) or f"{len(ids)} ok, highest {hi_m[0] * 100:.2f}% ({hi_m[1]})"))
    out.append((f"symbolic{tag}:has-ink-at-16px(>=18 px)", not thin, ", ".join(thin) or f"{len(ids)} ok"))
    return out


MUSIC_PX = None


def _music_alpha(R, M, which):
    heads, fillets, body, leaf, slope = apps.music_parts(M)
    els = {"heads": heads, "body": [body], "all": heads + fillets + [body]}[which]
    gl = A.Glyph(apps.GLYPHS["music"].tile, els, "m", 1.3)
    return R.render([A.app_icon_svg(gl, "mu", "m", tile=False, shadow=False)], 1024)[0][..., 3] > 127


def _components(mask, step=4):
    m = mask[::step, ::step]
    seen = np.zeros_like(m, bool)
    n = 0
    for y, x in zip(*np.nonzero(m)):
        if seen[y, x]:
            continue
        n += 1
        st = [(y, x)]
        seen[y, x] = True
        while st:
            cy, cx = st.pop()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = cy + dy, cx + dx
                    if 0 <= yy < m.shape[0] and 0 <= xx < m.shape[1] and m[yy, xx] and not seen[yy, xx]:
                        seen[yy, xx] = True
                        st.append((yy, xx))
    return n


def _alpha_els(R, els, scale, tones=None, size=1024, mode="full", tile=None):
    """Alpha of just the glyph elements (no tile, no shadow, no optical shift): local unit u maps to size/1024*UNIT*scale px."""
    gl = A.Glyph(tile or apps.GLYPHS["music"].tile, els, "x", scale)
    return R.render([A.app_icon_svg(gl, "xx", "x", mode=mode, tile=False, shadow=False, tones=tones)], size)[0][..., 3]


def _closing_added(mask, rpx):
    """Pixels a morphological closing with a disc of radius rpx adds: sharp inside corners and thin notches show up here."""
    offs = [(dy, dx) for dy in range(-rpx, rpx + 1) for dx in range(-rpx, rpx + 1) if dy * dy + dx * dx <= rpx * rpx]
    H_, W_ = mask.shape
    pad = np.pad(mask, rpx)
    dil = np.zeros_like(mask)
    for dy, dx in offs:
        dil |= pad[rpx + dy:rpx + dy + H_, rpx + dx:rpx + dx + W_]
    pad2 = np.pad(dil, rpx, constant_values=True)
    clo = np.ones_like(mask)
    for dy, dx in offs:
        clo &= pad2[rpx + dy:rpx + dy + H_, rpx + dx:rpx + dx + W_]
    return int((clo & ~mask).sum())


def _ray_radius(a, cx, cy, ang, t0, t1, step=0.1):
    """Outermost crossing of alpha 0.5 along a ray from (cx, cy) in px, with sub-pixel interpolation."""
    t = np.arange(t0, t1, step)
    v = ndi.map_coordinates(a, [cy + t * math.sin(math.radians(ang)) - 0.5, cx + t * math.cos(math.radians(ang)) - 0.5], order=1)
    idx = np.nonzero(v > 0.5)[0]                 # pixel centres sit at integer array indices, hence the - 0.5
    return float(t[idx.max()]) if len(idx) else None


def _superellipse_radius(ang_deg, n):
    """Distance from the centre to the boundary of |x|^n + |y|^n = 1 along a ray at this angle."""
    c, s = abs(math.cos(math.radians(ang_deg))), abs(math.sin(math.radians(ang_deg)))
    return (c ** n + s ** n) ** (-1.0 / n)


def _grid_els(L, move=None, grow=None, cell=None, disc_move=(0.0, 0.0), hole_in=None, shift=(0.0, 0.0)):
    """Test-only: the Launcher layout of apps.launcher_els with one defect put in, for the negative tests."""
    L = {**apps.LAUNCHER, **L}
    cells, _ = apps.launcher_geom(L)
    c, d = L["c"], ""
    for r, q, x, y in cells:
        if r == 1 and q == 1:
            continue
        dx, dy = (move or {}).get((r, q), (0.0, 0.0))
        cc = c + (grow or {}).get((r, q), 0.0)
        px_, py_ = x + c / 2 + dx + shift[0], y + c / 2 + dy + shift[1]
        d += cell(px_, py_, cc) if cell else A.superellipse_path(px_, py_, cc / 2, cc / 2, A.TILE_N)
    els = [A.P(d)]
    if hole_in:
        els.append(A.K(A.circ(*hole_in)))
    els.append(A.At(A.circ(disc_move[0] + shift[0], disc_move[1] + shift[1], c / 2 * L["disc"])))
    return els


def _gap_dip(a_s, s_, SL, sc, hint=(0.0, 0.0, 1.0)):
    """Weakest gap in a small-cut render of the Launcher (alpha 0..1, s_ px square). Along the 3 rows and the 3 columns
    through the cell centres: 1 - (darkest pixel near the gap centre) / (the weaker neighbouring cell's peak).
    1 = the gap is fully open, 0 = it has closed up. hint = (dx_px, dy_px, k) as applied to a pixel-hinted PNG.
    Returns (dip, gap width in px)."""
    dx, dy, kk = hint
    us = A.UNIT * sc * A.SMALL_BOOST * s_ / 1024 * kk
    pitch, hc = (SL["c"] + SL["gap"]) * us, SL["c"] * us / 2
    cxs = [s_ / 2 + dx + (k - 1) * pitch for k in range(3)]
    cys = [s_ / 2 + dy + (k - 1) * pitch for k in range(3)]
    idx = np.arange(s_)
    worst = 1.0
    for vertical in (False, True):
        along, across = (cys, cxs) if vertical else (cxs, cys)     # centres along the profile / of the lines it runs through
        for pos in across:
            coords = [np.full(s_, pos - 0.5), idx] if not vertical else [idx, np.full(s_, pos - 0.5)]
            prof = ndi.map_coordinates(a_s, coords, order=1)
            peaks = [prof[(idx + 0.5 >= c_ - hc - 0.5) & (idx + 0.5 <= c_ + hc + 0.5)].max() for c_ in along]
            for k in range(2):
                g_ = (along[k] + along[k + 1]) / 2
                valley = prof[np.abs(idx + 0.5 - g_) <= 0.75].min()
                worst = min(worst, 1 - valley / max(min(peaks[k], peaks[k + 1]), 1e-6))
    return worst, SL["gap"] * us


def check_launcher(R, L=None, SL=None, els=None):
    """Construction checks for the Launcher (a 3x3 grid of tiles around a leaf disc), measured on 1024 px renders
    (1 local unit = u px). `els` lets a negative test hand in a deliberately broken drawing."""
    L = {**apps.LAUNCHER, **(L or {})}
    SL = {**apps.LAUNCHER_SMALL, **(SL or {})}
    sc = apps.GLYPHS["launcher"].scale
    u = A.UNIT * sc
    els = els if els is not None else apps.launcher_els(L)
    lil = _alpha_els(R, els, sc, tones="p").astype(float) / 255.0          # the eight cells
    acc = _alpha_els(R, els, sc, tones="t").astype(float) / 255.0          # the leaf disc
    both = np.maximum(lil, acc)
    out = []
    # 1 nine separate pieces: eight cells and the disc, none touching
    lab, ncomp = ndi.label(both > 0.5)
    out.append(("launcher:nine-separate-tiles", ncomp == 9, f"{ncomp} pieces"))
    if ncomp != 9:
        return out
    ids = list(range(1, 10))
    area = np.array(ndi.sum(both, lab, ids))
    cm = np.array(ndi.center_of_mass(both, lab, ids)) + 0.5                # (y, x) px; the centre of pixel i is i + 0.5
    order = np.argsort(cm[:, 0])
    rows = [sorted(order[3 * r:3 * r + 3], key=lambda k: cm[k, 1]) for r in range(3)]
    xs = np.array([[cm[k, 1] for k in row] for row in rows]) / u
    ys = np.array([[cm[k, 0] for k in row] for row in rows]) / u
    disc_k = rows[1][1]
    cell_ks = [k for k in range(9) if k != disc_k]
    # 2 the eight cells are the same size
    a8 = area[cell_ks]
    spread = (a8.max() - a8.min()) / a8.mean()
    out.append(("launcher:eight-cells-equal-area(<=0.5%)", spread <= 0.005, f"{spread * 100:.2f}% spread, {a8.mean() / u / u:.0f} units2 each"))
    # 3 they sit on a regular lattice: columns and rows aligned, both pitches equal, x pitch = y pitch
    col = max(np.ptp(xs[:, q]) for q in range(3))
    row = max(np.ptp(ys[r, :]) for r in range(3))
    px_ = (xs[:, 1] - xs[:, 0]).mean(), (xs[:, 2] - xs[:, 1]).mean()
    py_ = (ys[1, :] - ys[0, :]).mean(), (ys[2, :] - ys[1, :]).mean()
    dev = max(col, row, abs(px_[0] - px_[1]), abs(py_[0] - py_[1]), abs(np.mean(px_) - np.mean(py_)))
    out.append(("launcher:cells-on-a-regular-lattice(<=0.3 unit)", dev <= 0.3, f"worst deviation {dev:.2f} unit, pitch {np.mean(px_):.2f} / {np.mean(py_):.2f}"))
    # 4 four-fold symmetry about the canvas centre: turning it a quarter turn or mirroring it changes (almost) nothing
    m = both > 0.5
    i_rot = (m & np.rot90(m)).sum() / (m | np.rot90(m)).sum()
    i_mir = (m & m[:, ::-1]).sum() / (m | m[:, ::-1]).sum()
    out.append(("launcher:four-fold-symmetric-about-the-tile-centre(IoU>=0.995)", min(i_rot, i_mir) >= 0.995, f"quarter turn {i_rot:.4f}, mirror {i_mir:.4f}"))
    # 5 the block fills the square keyline (160 units)
    yy, xx = np.nonzero(lil > 0.5)
    w_u, h_u = (xx.max() + 1 - xx.min()) / u, (yy.max() + 1 - yy.min()) / u
    out.append(("launcher:block-fills-the-square-keyline(160 +-1.5 units)", abs(w_u - 160) <= 1.5 and abs(h_u - 160) <= 1.5, f"{w_u:.1f} x {h_u:.1f} units"))
    # 6 every cell is a miniature of the tile: its outline follows the tile's superellipse (exponent TILE_N)
    half = L["c"] * u / 2
    worst = 0.0
    for k in cell_ks:
        for ang in range(0, 360, 3):
            r_ = _ray_radius(lil, cm[k, 1], cm[k, 0], ang, 0.7 * half, 1.4 * half)
            if r_ is None:
                worst = 9.9
                break
            worst = max(worst, abs(r_ - _superellipse_radius(ang, A.TILE_N) * half) / half)
    out.append(("launcher:cells-follow-the-tile's-own-superellipse(<=0.8%)", worst <= 0.008, f"worst radial deviation {worst * 100:.2f}% of the half-cell ({worst * half:.2f} px) over 8 cells x 120 rays"))
    # 7 the leaf disc: concentric with the block, circular, and inscribed in the centre cell (diameter = cell, up to +8%)
    mid = np.mean([cm[k] for k in (rows[0][1], rows[2][1], rows[1][0], rows[1][2])], axis=0)
    off = math.hypot(*(cm[disc_k] - mid)) / u
    out.append(("launcher:disc-concentric-with-the-block(<=0.3 unit)", off <= 0.3, f"{off:.2f} units"))
    r_disc = L["c"] / 2 * L["disc"] * u
    rs = np.array([_ray_radius(acc, cm[disc_k, 1], cm[disc_k, 0], a_, 0.6 * r_disc, 1.4 * r_disc) or 0.0 for a_ in range(0, 360, 4)])
    circ_dev = (rs.max() - rs.min()) / rs.mean()
    ratio = 2 * rs.mean() / u / L["c"]
    out.append(("launcher:disc-is-a-circle(radius spread<=0.8%)", circ_dev <= 0.008, f"{circ_dev * 100:.2f}% over {len(rs)} rays"))
    out.append(("launcher:disc-inscribed-in-the-centre-cell(1.00..1.08 x cell)", 1.0 <= ratio <= 1.08, f"disc {ratio:.3f} x cell"))
    # 8 no enclosed counter anywhere: nothing can be read as a ring or lens (the shape that made the old icon look like Search)
    holes = int((ndi.binary_fill_holes(m) & ~m).sum())
    out.append(("launcher:no-ring-or-lens(no enclosed counters)", holes == 0, f"{holes} px enclosed"))
    # 9 the <= 32 px cut keeps every gap visible at 16, 24, 32 and 48 px (unhinted, i.e. in any renderer):
    #   along each of the 3 rows and 3 columns, the dip between neighbouring cells is >= 40% of the weaker cell's peak
    sels = apps.launcher_els(SL)
    bad, seen = [], []
    for s_ in (16, 24, 32, 48):
        a_s = _alpha_els(R, sels, sc, size=s_, mode="small").astype(float) / 255.0
        worst_dip, gap_px = _gap_dip(a_s, s_, SL, sc)
        seen.append(f"{s_}px dip {worst_dip:.2f} (gap {gap_px:.2f} px)")
        if worst_dip < 0.40:
            bad.append(f"{s_}px: gaps show only {worst_dip:.2f} of the cell peak (gap {gap_px:.2f} px, need >= 0.40)")
    out.append(("launcher:small-cut-keeps-all-nine-tiles-apart(16/24/32/48 px, dip>=0.40)", not bad, "; ".join(bad) or "; ".join(seen)))
    return out


def check_launcher_hints(R, override=None, SL=None):
    """The Launcher's pixel-snapping hints: bounded, never blurrier than the plain render, still centred, and
    every gap between the nine tiles still open in the hinted render (dip >= 0.40, as for the plain small cut)."""
    SL = {**apps.LAUNCHER_SMALL, **(SL or {})}
    sc = apps.GLYPHS["launcher"].scale
    out, bad, notes = [], [], []
    for s in H.SIZES:
        h = override if override is not None else H.hint_for("launcher", s)
        if h is None:
            continue
        h = (s,) + tuple(h[1:]) if len(h) == 4 else (s,) + tuple(h)
        _, dx, dy, kk = h
        if abs(dx) > H.LIMIT_SHIFT + 1e-6 or abs(dy) > H.LIMIT_SHIFT + 1e-6 or not (H.K_MIN - 1e-6 <= kk <= H.K_MAX + 1e-6):
            bad.append(f"{s}px: hint outside limits (dx {dx:+.2f} dy {dy:+.2f} k {kk:.2f})")
            continue
        plain = H.render_glyph(R, "launcher", s)[0]
        hinted = H.render_glyph(R, "launcher", s, hint=h)[0]
        bp, bh = H.blur_mass(plain), H.blur_mass(hinted)
        al = hinted.astype(float)
        cx = (al * np.arange(s)[None, :]).sum() / al.sum() / s - 0.5 + 0.5 / s
        cy = (al * np.arange(s)[:, None]).sum() / al.sum() / s - 0.5 + 0.5 / s
        if bh > bp * 1.001:
            bad.append(f"{s}px: hinted blur mass {bh:.3f} is worse than plain {bp:.3f}")
        if max(abs(cx), abs(cy)) > 0.045:
            bad.append(f"{s}px: hinted glyph off centre by {max(abs(cx), abs(cy)) * 100:.1f}%")
        dip, _ = _gap_dip(hinted.astype(float) / 255.0, s, SL, sc, hint=(dx, dy, kk))
        if dip < 0.40:
            bad.append(f"{s}px: hinted gaps show only {dip:.2f} of the cell peak (need >= 0.40)")
        notes.append(f"{s}px {bp:.3f}->{bh:.3f} (gap dip {dip:.2f})")
    out.append(("launcher:small-png-hints-bounded-never-blurrier-centred-gaps-open", (not bad) and bool(notes), "; ".join(bad) or "blur mass " + ", ".join(notes)))
    return out


def check_music(R, M=None):
    """Construction checks for the Music icon, measured on 1024 px renders (1 local unit = 3.27 px)."""
    M = M or apps.MUSIC
    u = A.UNIT * 1.3
    px = lambda v: 512 + v * u
    body, heads, both = (_music_alpha(R, M, w) for w in ("body", "heads", "all"))
    xr, yt = apps.head_tangent(M)
    out = []
    # 1 no stem foot below a head: stem pixels outside the heads must all lie above the head's tangent line
    bad = 0
    for (hx, hy) in (M["h1"], M["h2"]):
        y0 = int(px(hy + yt + 1.0))
        x0, x1 = int(px(hx + xr - M["stem_w"] - 3)), int(px(hx + xr + 3))
        bad += int((body & ~heads)[y0:, x0:x1].sum())
    out.append(("music:stems-end-inside-the-heads(no foot pokes out)", bad <= 6, f"{bad} stem px below a head's tangent line"))
    # 2 the beam runs parallel to the line through the two heads
    (x1_, y1_), (x2_, y2_) = M["h1"], M["h2"]
    head_ang = math.degrees(math.atan2(y2_ - y1_, x2_ - x1_))
    cols = range(int(px(x1_ + xr + 6)), int(px(x2_ + xr - M["stem_w"] - 6)))
    xs, ys = [], []
    for x in cols:
        nz = np.nonzero(body[:, x])[0]
        if len(nz):
            xs.append(x); ys.append(nz.min())
    ang = math.degrees(math.atan(np.polyfit(xs, ys, 1)[0]))
    out.append(("music:beam-parallel-to-the-heads(<=0.6deg)", abs(ang - head_ang) <= 0.6, f"beam {ang:.2f} deg, heads {head_ang:.2f} deg"))
    # 3 heads, stems and beam are one piece
    n = _components(both)
    out.append(("music:one-connected-silhouette", n == 1, f"{n} components"))
    # 3b no sharp inside corner: closing the silhouette with a disc of 2 local units adds (almost) nothing
    rpx = int(round(2.0 * u))
    added = _closing_added(both, rpx)
    out.append(("music:no-sharp-inside-corner(closing adds <=8 px)", added <= 8, f"closing with r={rpx} px adds {added} px"))
    # 4 the two heads are the same size
    a1 = int(heads[:, :int(px(2))].sum()); a2 = int(heads[:, int(px(2)):].sum())
    out.append(("music:heads-equal-area(<=1%)", abs(a1 - a2) / max(a1, a2) <= 0.01, f"{a1} vs {a2} px"))
    return out


def run(report_path=None, negative=True):
    rep = Report([])
    with Renderer() as R:
        rd, svgs = {}, {}
        for i in apps.ORDER:
            rd[i], svgs[i] = renders(R, i, apps.GLYPHS[i])
        ids = apps.ORDER
        for i in ids:
            rep.add(i, check_hygiene(i, svgs[i]) + check_pixels(i, rd[i]))
        rep.add("set", check_static() + check_weight(ids, rd) + check_fidelity(R) + check_small(R, ids))
        rep.add("music", check_music(R))
        rep.add("launcher", check_launcher(R) + check_launcher_hints(R))
        rep.add("set", check_symbolic(R, ids))
        m64 = {}
        arr = R.render([A.app_icon_svg(apps.GLYPHS[i], i, i, tile=False, shadow=False, **({"brand_stops": A.BRAND_TILE_STOPS} if i == "malva" else {})) for i in ids], 64)
        for i, a in zip(ids, arr):
            m64[i] = a[..., 3] > 127
        res, _ = pair_checks(ids, rd, m64)
        rep.add("set", res)
        allids = re.findall(r' id="([^"]+)"', "".join(svgs.values()))
        rep.add("set", [("hygiene:ids-unique-across-the-whole-set", len(allids) == len(set(allids)), f"{len(allids)} ids")])
        neg = negative_tests(R, rd, m64) if negative else []
    header = [f"app icons: {len(apps.ORDER)}  checks: {rep.total}  failed: {rep.failed}  "
              f"negative tests (a broken icon must fail): {sum(1 for n in neg if n[1])}/{len(neg)}"]
    text = "\n".join(header + rep.lines + ["", "negative tests"] + [f"{'caught ' if ok else 'MISSED '} {n}  {info}" for n, ok, info in neg]) + "\n"
    if report_path:
        Path(report_path).write_text(text)
    return rep, neg, text


def negative_tests(R, rd, m64) -> list[Res]:
    """Each broken icon must be rejected by the check that is meant to reject it."""
    out = []
    base = apps.GLYPHS["files"]

    def fails(gl, which, i="files"):
        r2, svg = renders(R, i, gl)
        res = check_pixels(i, r2) + check_hygiene(i, svg)
        return [n for n, ok, _ in res if not ok and n.startswith(which)]

    # 1 glyph pushed off centre
    gl = copy.deepcopy(base)
    for e in gl.els:
        e.tf = (e.tf + " " if e.tf else "") + "translate(40 0)"
    out.append(("glyph shifted 40 units right is rejected", bool(fails(gl, "layout:")), str(fails(gl, "layout:"))))
    # 2 pale tile under a pale glyph
    gl = copy.deepcopy(base)
    gl.tile = A.Tile(h=128, l=0.90, c=0.04, ld=0.84, cd=0.03)
    out.append(("pale tile (contrast < 3:1) is rejected", bool(fails(gl, "contrast:glyph-vs-tile>=3.0")), str(fails(gl, "contrast:glyph-vs-tile>=3.0"))))
    # 3 glyph too small
    gl = copy.deepcopy(base)
    gl.scale = 0.6
    out.append(("tiny glyph is rejected", bool(fails(gl, "layout:not-too-small")), str(fails(gl, "layout:not-too-small"))))
    # 4 glyph too big (touches the tile corners)
    gl = copy.deepcopy(base)
    gl.scale = 1.9
    out.append(("oversized glyph is rejected", bool(fails(gl, "layout:inside-safe-zone")), str(fails(gl, "layout:inside-safe-zone"))))
    # 5 an element that forbids rendering portability (text)
    r2, svg = renders(R, "files", base)
    bad = svg.replace("</svg>", "<text x='0' y='0'>x</text></svg>")
    res = check_hygiene("files", bad)
    out.append(("an SVG with <text> is rejected", any(n == "hygiene:no-forbidden-elements" and not ok for n, ok, _ in res), ""))
    # 6 id collision between two icons
    res = check_hygiene("files", svg.replace('id="files-bg"', 'id="bg"'))
    out.append(("an unprefixed id is rejected", any(n.startswith("hygiene:ids") and not ok for n, ok, _ in res), ""))
    # 7 two icons with the same glyph and a similar tile cannot be told apart
    ids = ["files", "files_twin"]
    rdx = {"files": rd["files"], "files_twin": rd["files"]}
    res, _ = pair_checks(ids, rdx, {"files": m64["files"], "files_twin": m64["files"]})
    out.append(("duplicate icon (same shape, same colour) is rejected", any(not ok for n, ok, _ in res if n.startswith("distinct:every")), ""))
    # 8 tile exponent 4 instead of 5 no longer matches the supplied shape
    sup = (ROOT / "assets/brand/logo/malva-app-icon.svg").read_text()
    gl = apps.GLYPHS["malva"]
    good = A.app_icon_svg(gl, "malva", "m", brand_stops=A.BRAND_TILE_STOPS, shadow=False)
    sq4 = good.replace(A.tile_path(), A.superellipse_path(512, 512, 512, 512, 4.0))
    a, b, c = R.render([sup, good, sq4], 512)
    iou = lambda x, y: ((x[..., 3] > 127) & (y[..., 3] > 127)).sum() / ((x[..., 3] > 127) | (y[..., 3] > 127)).sum()
    out.append(("tile with exponent 4 differs measurably from the supplied exponent-5 tile", iou(a, b) >= 0.999 and iou(a, c) < 0.99, f"IoU n=5 {iou(a, b):.5f}, n=4 {iou(a, c):.5f}"))
    # 12 Music without the stem/head fillet leaves sharp inside corners
    r = check_music(R, {**apps.MUSIC, "fillet": 0.0})
    out.append(("music without stem/head fillets is rejected", any(not ok for n, ok, _ in r if "sharp-inside" in n), str([i for n, ok, i in r if "sharp-inside" in n])))
    # 11 symbolic canvas too tight clips the glyph
    r = check_symbolic(R, ["music"], {"music": 60.0}, tag="-tight")
    out.append(("symbolic canvas that clips the glyph is rejected", any(not ok for n, ok, _ in r if "clipped" in n), str([i for n, ok, i in r if "clipped" in n])))
    # 9 Music: a stem that runs 26 units past its head (the old foot) must fail the foot check
    r = check_music(R, {**apps.MUSIC, "foot_extra": 26.0})
    out.append(("music stem foot poking out of a head is rejected", any(not ok for n, ok, _ in r if "stems-end" in n), str([i for n, ok, i in r if "stems-end" in n])))
    # 10 Music: a beam 0.1 slope off the heads' line must fail the parallel check
    r = check_music(R, {**apps.MUSIC, "beam_dslope": 0.1})
    out.append(("music beam out of parallel with the heads is rejected", any(not ok for n, ok, _ in r if "parallel" in n), str([i for n, ok, i in r if "parallel" in n])))
    # 19 Launcher hints: a hint that shifts the glyph by almost a pixel and scales it 15% is outside the limits
    r = check_launcher_hints(R, (16, 0.9, 0.0, 1.15))
    out.append(("launcher pixel hint outside its limits is rejected", any(not ok for n, ok, _ in r), str([i for n, ok, i in r])))
    # 20 Launcher hints: a half-pixel diagonal shift makes the 16 px render blurrier than the plain one
    r = check_launcher_hints(R, (16, -0.375, 0.375, 1.0))
    out.append(("launcher pixel hint that blurs the render is rejected", any(not ok for n, ok, _ in r), str([i for n, ok, i in r])))
    # 20b Launcher hints: a small cut whose gaps have closed up must fail the hinted-PNG check too (identity hint)
    gl_ = apps.GLYPHS["launcher"]
    keep = gl_.small_els
    try:
        gl_.small_els = apps.launcher_els({**apps.LAUNCHER_SMALL, "gap": 4.0})
        r = check_launcher_hints(R, (16, 0.0, 0.0, 1.0), {"gap": 4.0})
    finally:
        gl_.small_els = keep
    out.append(("launcher hinted PNGs whose gaps close up are rejected", any(not ok for n, ok, _ in r), str([i for n, ok, i in r])[:200]))
    # 13 Launcher: cells that touch (gap 0) are no longer nine separate tiles
    r = check_launcher(R, {"gap": 0.0})
    out.append(("launcher with touching cells is rejected", any(not ok for n, ok, _ in r if "nine-separate" in n), str([i for n, ok, i in r if "nine-separate" in n])))
    # 14 Launcher: one cell 3 units off its lattice place
    r = check_launcher(R, els=_grid_els({}, move={(0, 2): (3.0, 2.0)}))
    out.append(("launcher with one cell off the lattice is rejected", any(not ok for n, ok, _ in r if "regular-lattice" in n), str([i for n, ok, i in r if "regular-lattice" in n])))
    # 15 Launcher: one cell 4 units bigger than the rest
    r = check_launcher(R, els=_grid_els({}, grow={(2, 1): 4.0}))
    out.append(("launcher with one oversized cell is rejected", any(not ok for n, ok, _ in r if "equal-area" in n), str([i for n, ok, i in r if "equal-area" in n])))
    # 16 Launcher: rounded-rectangle cells (corner radius 13) are not miniatures of the tile
    r = check_launcher(R, els=_grid_els({}, cell=lambda x, y, c: g.rr(x - c / 2, y - c / 2, c, c, 13.0)))
    out.append(("launcher with rounded-rectangle cells is rejected", any(not ok for n, ok, _ in r if "superellipse" in n), str([i for n, ok, i in r if "superellipse" in n])))
    # 16b the same for circular cells (a dot grid): another family the tile does not belong to
    r = check_launcher(R, els=_grid_els({}, cell=lambda x, y, c: A.circ(x, y, c / 2)))
    out.append(("launcher with round dots instead of tiles is rejected", any(not ok for n, ok, _ in r if "superellipse" in n), str([i for n, ok, i in r if "superellipse" in n])))
    # 17 Launcher: the whole block pushed 6 units right of the tile centre
    r = check_launcher(R, els=_grid_els({}, shift=(6.0, 0.0)))
    out.append(("launcher block off the tile centre is rejected", any(not ok for n, ok, _ in r if "four-fold" in n), str([i for n, ok, i in r if "four-fold" in n])))
    # 18 Launcher: a block far smaller than the square keyline
    r = check_launcher(R, {"c": 36.0})
    out.append(("launcher block much smaller than the keyline is rejected", any(not ok for n, ok, _ in r if "keyline" in n), str([i for n, ok, i in r if "keyline" in n])))
    # 19b Launcher: disc 4 units off the block centre
    r = check_launcher(R, els=_grid_els({}, disc_move=(4.0, 0.0)))
    out.append(("launcher disc off the block centre is rejected", any(not ok for n, ok, _ in r if "concentric" in n), str([i for n, ok, i in r if "concentric" in n])))
    # 19c Launcher: a disc much smaller than its cell floats in a hole of the grid
    r = check_launcher(R, {"disc": 0.6})
    out.append(("launcher with a small disc is rejected", any(not ok for n, ok, _ in r if "inscribed" in n), str([i for n, ok, i in r if "inscribed" in n])))
    # 19d Launcher: a hole punched in a cell makes a ring, the shape of the old search icon
    cx_ = -80.0 + 22.5
    r = check_launcher(R, els=_grid_els({}, hole_in=(cx_, cx_, 12.0)))
    out.append(("launcher with a ring-shaped cell is rejected", any(not ok for n, ok, _ in r if "no-ring" in n), str([i for n, ok, i in r if "no-ring" in n])))
    # 19e Launcher: a small-cut gap of 4 units (0.24 px at 16 px) closes up
    r = check_launcher(R, None, {"gap": 4.0})
    out.append(("launcher small cut whose gaps close up is rejected", any(not ok for n, ok, _ in r if "small-cut" in n), str([i for n, ok, i in r if "small-cut" in n])))
    return out


if __name__ == "__main__":
    path = None
    if "--report" in sys.argv:
        path = sys.argv[sys.argv.index("--report") + 1]
    rep, neg, text = run(path)
    print(text)
    sys.exit(1 if rep.failed or not all(n[1] for n in neg) else 0)
