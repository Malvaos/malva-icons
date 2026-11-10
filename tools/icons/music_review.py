"""Contact sheet for the Music icon: before / after, every size and cut, on both wallpapers, symbolic.
Output: docs/icons/music-review.png (reproducible: python3 tools/icons/music_review.py)"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).parent))
import appfmt as A, apps
from appfmt import P, At, rr, poly
from apps import ell, _poly
from mi_render import Renderer, _font
from build_apps import symbolic_vb

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/icons/music-review.png"

# the first version, kept only so the sheet can show what changed
OLD = A.Glyph(apps.GLYPHS["music"].tile, [
    P(ell(-40, 52, 26, 20), tf="rotate(-20 -40 52)"), P(ell(40, 36, 26, 20), tf="rotate(-20 40 36)"),
    P(rr(-19, -42, 14, 96, 6)), P(rr(61, -58, 14, 94, 6)),
    P(_poly((-19, -40), (75, -62), (75, -34), (-19, -12)), rnd=6)], "Music", 1.15, (-17.3, -4.3))

def crop_wall(name, w, h, ox=0, oy=0):
    im = Image.open(ROOT / "assets/brand" / name).convert("RGBA")
    return im.crop((ox, oy, ox + w, oy + h))

def main():
    new = apps.GLYPHS["music"]
    W, H = 1400, 880
    sheet = Image.new("RGBA", (W, H), (28, 19, 27, 255))
    d = ImageDraw.Draw(sheet)
    F, Fs = _font(18), _font(13)
    with Renderer() as R:
        def icon(gl, s, mode="full"):
            return Image.fromarray(R.render([A.app_icon_svg(gl, "mu", "Music", mode=mode, shadow=(mode == "full"))], s)[0])
        # before / after
        d.text((30, 18), "before", font=F, fill=(200, 170, 195)); d.text((470, 18), "after", font=F, fill=(240, 225, 238))
        sheet.alpha_composite(icon(OLD, 400), (30, 50)); sheet.alpha_composite(icon(new, 400), (470, 50))
        notes = ["foot of each stem pokes out of its head", "beam notch where it meets the stem", "stems, beam, heads are separate shapes",
                 "no brand accent"]
        for k, t in enumerate(notes):
            d.text((30, 462 + 20 * k), "- " + t, font=Fs, fill=(190, 160, 185))
        notes = ["stems end inside the heads; right edge flush on the head tangent", "every inside corner filleted r4; beam corners equal true radius r7",
                 "beam parallel to the line through the heads (measured)", "leaf second beam (sixteenth note); the small cut is a heavier drawing"]
        for k, t in enumerate(notes):
            d.text((470, 462 + 20 * k), "- " + t, font=Fs, fill=(225, 205, 222))
        # on wallpapers
        for k, wall in enumerate(("malva-dusk-2560x1440.jpg", "malva-dawn-2560x1440.jpg")):
            try:
                bg = crop_wall(wall, 440, 200, 900, 700 + 0)
            except FileNotFoundError:
                bg = Image.new("RGBA", (440, 200), (60, 40, 60, 255))
            for j, s in enumerate((128, 64, 48)):
                pass
            x0 = 930; y0 = 50 + k * 220
            sheet.alpha_composite(bg, (x0, y0))
            xx = x0 + 20
            for s in (128, 64, 48, 32):
                im = icon(new, s, "full" if s > 32 else "small")
                sheet.alpha_composite(im, (xx, y0 + 100 - s // 2)); xx += s + 24
        d.text((930, 18), "on the dusk and dawn wallpapers (128 / 64 / 48 full, 32 small)", font=Fs, fill=(200, 170, 195))
        # size ladder with the 16 px pixels blown up
        d.text((30, 580), "size ladder (full 128, 64, 48; small 32, 16) and 16 px enlarged 8x", font=Fs, fill=(200, 170, 195))
        x = 30
        for s, mode in ((128, "full"), (64, "full"), (48, "full"), (32, "small"), (16, "small")):
            sheet.alpha_composite(icon(new, s, mode), (x, 610)); x += s + 26
        big16 = icon(new, 16, "small").resize((128, 128), Image.NEAREST)
        sheet.alpha_composite(big16, (x + 10, 610))
        # symbolic
        d.text((470, 760), "symbolic (currentColor), dark and light panels at 64 and 24 px", font=Fs, fill=(200, 170, 195))
        vb = symbolic_vb(R, "music")
        svg = A.app_icon_svg(new, "mu", "Music", mode="symbolic", sym_vb=vb)
        x = 470
        for fg, bgc in (((243, 230, 242), (46, 30, 44)), ((140, 50, 116), (246, 236, 245))):
            for s in (64, 24):
                a = R.render([svg], s, color="#%02X%02X%02X" % fg)[0]
                tile = Image.new("RGBA", (s + 24, s + 24), bgc + (255,))
                tile.alpha_composite(Image.fromarray(a), (12, 12))
                sheet.alpha_composite(tile, (x, 785)); x += s + 36
    sheet.convert("RGB").save(OUT)
    print("wrote", OUT)

if __name__ == "__main__":
    main()
