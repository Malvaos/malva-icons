"""Pixel-snapping hints for the small PNG sizes.

For one icon and one size, search a small shift (dx, dy in pixels) and scale k of the glyph (never the tile)
and keep the one whose edges fall most cleanly on the pixel grid (coarse grid, then a fine grid around the winner). Score = "blur mass": the sum over pixels of
min(alpha, 1 - alpha) divided by the ink mass (lower = crisper). The search is bounded so the drawing is not
changed in any way a person would notice: |dx|,|dy| <= 0.375 px, 0.95 <= k <= 1.05.

    python3 tools/icons/hints.py launcher        # writes the result into tools/icons/hints.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import appfmt as A
import apps
from mi_render import Renderer

HINTS = Path(__file__).with_name("hints.json")
LIMIT_SHIFT, K_MIN, K_MAX = 0.375, 0.95, 1.05
SIZES = (16, 22, 24, 32, 48)


def blur_mass(alpha: np.ndarray) -> float:
    a = alpha.astype(float) / 255.0
    return float(np.minimum(a, 1 - a).sum() / max(a.sum(), 1e-9))


def render_glyph(R, i, size, hint=None, mode="small"):
    kw = {"brand_stops": A.BRAND_TILE_STOPS} if i == "malva" else {}
    svgs = hint if isinstance(hint, list) else [hint]
    out = R.render([A.app_icon_svg(apps.GLYPHS[i], i, i, mode=mode, tile=False, shadow=False, hint=h, **kw) for h in svgs], size)
    return [o[..., 3] for o in out]


def search(R, i, size):
    """Two stages inside the same bounds: a coarse grid (0.125 px, k step 0.025), then a fine grid around the winner
    (0.03125 px, k step 0.00625). Edge alignment is a narrow optimum, so the coarse grid alone can miss it."""
    base = blur_mass(render_glyph(R, i, size)[0])

    def best_of(cands):
        alphas = render_glyph(R, i, size, hint=cands)
        # a tiny pull toward "no change" so noise-level differences do not move the drawing
        return min((blur_mass(a) + 0.004 * (abs(c[1]) + abs(c[2]) + 4 * abs(c[3] - 1.0)), c) for c, a in zip(cands, alphas))[1]

    shifts = np.arange(-LIMIT_SHIFT, LIMIT_SHIFT + 1e-9, 0.125)
    ks = (0.95, 0.975, 1.0, 1.025, 1.05)
    coarse = [(size, float(dx), float(dy), float(k)) for dx in shifts for dy in shifts for k in ks]
    b = best_of(coarse)
    clip = lambda v, lo, hi: float(min(hi, max(lo, v)))
    fs = np.arange(-0.125, 0.125 + 1e-9, 0.03125)
    fk = np.arange(-0.025, 0.025 + 1e-9, 0.00625)
    fine = {(size, clip(b[1] + a, -LIMIT_SHIFT, LIMIT_SHIFT), clip(b[2] + c, -LIMIT_SHIFT, LIMIT_SHIFT), clip(b[3] + k, K_MIN, K_MAX))
            for a in fs for c in fs for k in fk}
    fine.add(b)
    best = best_of(sorted(fine))
    return base, blur_mass(render_glyph(R, i, size, hint=best)[0]), best


def load():
    return json.loads(HINTS.read_text()) if HINTS.exists() else {}


def hint_for(i, size):
    h = load().get(i, {}).get(str(size))
    return (size, h[0], h[1], h[2]) if h else None


def main():
    ids = sys.argv[1:] or ["launcher"]
    data = load()
    with Renderer() as R:
        for i in ids:
            data.setdefault(i, {})
            for s in SIZES:
                base, new, best = search(R, i, s)
                data[i][str(s)] = [round(best[1], 3), round(best[2], 3), round(best[3], 3)]
                print(f"{i:<10} {s:>2}px  blur mass {base:.3f} -> {new:.3f}  ({(1 - new / base) * 100:+.0f}%)  dx {best[1]:+.3f} dy {best[2]:+.3f} k {best[3]:.3f}")
    HINTS.write_text(json.dumps(data, indent=1) + "\n")


if __name__ == "__main__":
    main()
