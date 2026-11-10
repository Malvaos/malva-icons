"""Audit table for the app icons: what each glyph actually measures, so design rules can be set from data.
Run: python3 tools/icons/audit.py   (prints a table; writes nothing)"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).parent))
import appfmt as A
import apps
import mi_geom as g
from mi_render import Renderer

S = 512
ROOT = Path(__file__).resolve().parents[2]


def kw(i):
    return {"brand_stops": A.BRAND_TILE_STOPS} if i == "malva" else {}


def metrics(R, ids):
    glyph = R.render([A.app_icon_svg(apps.GLYPHS[i], i, i, tile=False, shadow=False, **kw(i)) for i in ids], S)
    full = R.render([A.app_icon_svg(apps.GLYPHS[i], i, i, shadow=False, **kw(i)) for i in ids], S)
    out = {}
    yy, xx = np.mgrid[0:S, 0:S]
    for i, a, f in zip(ids, glyph, full):
        al = a[..., 3] > 127
        sil = ndi.binary_fill_holes(al)
        ys, xs = np.nonzero(al)
        half = S / 2
        w = (xs.max() + 1 - xs.min()) / S
        h = (ys.max() + 1 - ys.min()) / S
        r_euc = np.hypot(xs + 0.5 - half, ys + 0.5 - half).max() / half
        r_cheb = max(abs(xs.min() - half), abs(xs.max() + 1 - half), abs(ys.min() - half), abs(ys.max() + 1 - half)) / half
        wt = a[..., 3].astype(float)
        cx = (wt * xx).sum() / wt.sum() + 0.5 - half
        cy = (wt * yy).sum() / wt.sum() + 0.5 - half
        bx = (xs.min() + xs.max() + 1) / 2 - half
        by = (ys.min() + ys.max() + 1) / 2 - half
        hull = _hull_area(xs, ys)
        # contrast of glyph pixels against the tile pixel behind them
        tile = R.render([A.app_icon_svg(apps.empty(apps.GLYPHS[i]) if hasattr(apps, "empty") else A.Glyph(apps.GLYPHS[i].tile, [], "x", 1.0), i, i, shadow=False, **kw(i))], S)[0]
        out[i] = dict(ink=al.sum() / S / S, sil=sil.sum() / S / S, w=w, h=h, r_euc=r_euc, r_cheb=r_cheb,
                      cen=(cx / half * 100, cy / half * 100), bbc=(bx / half * 100, by / half * 100),
                      solidity=al.sum() / max(hull, 1), holes=int(ndi.label(~sil & al | (sil & ~al))[1]),
                      comp=int(ndi.label(al)[1]))
        # glyph-vs-tile contrast
        ink = al & (a[..., 3] > 250)
        L = lambda arr: 0.2126 * _lin(arr[..., 0]) + 0.7152 * _lin(arr[..., 1]) + 0.0722 * _lin(arr[..., 2])
        lf, lt = L(f[..., :3] / 255.0)[ink], L(tile[..., :3] / 255.0)[ink]
        c = (np.maximum(lf, lt) + 0.05) / (np.minimum(lf, lt) + 0.05)
        out[i]["c5"], out[i]["c50"] = float(np.percentile(c, 5)), float(np.median(c))
    return out


def _lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _hull_area(xs, ys):
    import cv2
    pts = np.stack([xs, ys], 1).astype(np.int32)
    h = cv2.convexHull(pts)
    return cv2.contourArea(h)


def source_stats():
    """Stroke widths, rounding values and rr() corner radii used by each glyph, read from apps.py."""
    src = (Path(__file__).parent / "apps.py").read_text()
    blocks = re.split(r"\nadd\(", src)[1:]
    res = {}
    for b in blocks:
        i = re.match(r'"([a-z-]+)"', b).group(1)
        strokes = sorted({float(x) for x in re.findall(r"stroke=([0-9.]+)", b)})
        rnd = sorted({float(x) for x in re.findall(r"rnd=([0-9.]+)", b)})
        radii = sorted({float(m.group(1)) for m in re.finditer(r"rr\([^()]*?,\s*([0-9.]+)\)", b)})
        res[i] = dict(strokes=strokes, rnd=rnd, radii=radii)
    return res


def main():
    ids = apps.ORDER
    with Renderer() as R:
        m = metrics(R, ids)
    st = source_stats()
    med_ink = np.median([m[i]["ink"] for i in ids])
    med_sil = np.median([m[i]["sil"] for i in ids])
    print(f"{'icon':<16}{'ink%':>6}{'x med':>7}{'sil%':>6}{'x med':>7}{'w':>6}{'h':>6}{'reachE':>7}{'reachC':>7}{'cen%':>12}{'bbc%':>12}{'sol':>6}{'c5':>6}{'c50':>6}")
    for i in ids:
        r = m[i]
        print(f"{i:<16}{r['ink'] * 100:6.1f}{r['ink'] / med_ink:7.2f}{r['sil'] * 100:6.1f}{r['sil'] / med_sil:7.2f}{r['w']:6.2f}{r['h']:6.2f}{r['r_euc']:7.2f}{r['r_cheb']:7.2f}"
              f"{r['cen'][0]:6.1f},{r['cen'][1]:5.1f}{r['bbc'][0]:6.1f},{r['bbc'][1]:5.1f}{r['solidity']:6.2f}{r['c5']:6.2f}{r['c50']:6.2f}")
    print("\nstroke / rounding / corner radii used (local units):")
    for i in ids:
        s = st.get(i, {})
        print(f"{i:<16} strokes {s.get('strokes')}  rnd {s.get('rnd')}  rr {s.get('radii')}")


if __name__ == "__main__":
    main()
