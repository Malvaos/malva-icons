"""Measure each app glyph on rendered pixels and store the shift that centres it (glyph_shifts.json), by the one rule
of optical.py: the box on the middle of the tile, less a capped pull of the mass.
Run after changing a glyph: python3 tools/icons/centre.py"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import appfmt as A
import optical as O
import apps
from mi_render import Renderer

S = 512
def main():
    shifts = {}
    with Renderer() as R:
        for i in apps.ORDER:
            if i == "malva":
                continue
            gl = apps.GLYPHS[i]
            gl.shift = (0.0, 0.0)
            a = R.render([A.app_icon_svg(gl, i, i, tile=False, shadow=False)], S)[0][..., 3].astype(float)
            cx = (a * np.arange(S)[None, :]).sum() / a.sum() + 0.5
            cy = (a * np.arange(S)[:, None]).sum() / a.sum() + 0.5
            ys, xs = np.nonzero(a > 127)
            bx, by = (xs.min() + xs.max() + 1) / 2, (ys.min() + ys.max() + 1) / 2
            ox = O.shift(bx - S / 2, cx - S / 2, S)                 # pixels: box on the middle, less the capped pull of the mass
            oy = O.shift(by - S / 2, cy - S / 2, S)
            px_per_unit = S / 1024 * A.UNIT * gl.scale
            shifts[i] = [float(round(ox / px_per_unit, 1)), float(round(oy / px_per_unit, 1))]
    (Path(__file__).with_name("glyph_shifts.json")).write_text(json.dumps(shifts, indent=1) + "\n")
    print(shifts)

if __name__ == "__main__":
    main()
