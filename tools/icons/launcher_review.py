"""Contact sheet for the Launcher icon: before / after, the alternatives that were rejected, every size as shipped,
on both wallpapers, symbolic. Output: docs/icons/launcher-review.png
(reproducible: python3 tools/icons/launcher_review.py; needs docs/icons/launcher-before-magnifier.png, a one-off
render of the previous version that read as the Search icon)"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).parent))
import appfmt as A, apps
import mi_geom as g
from appfmt import P, At, circ
from mi_render import Renderer, _font
from build_apps import symbolic_vb

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/icons/launcher-review.png"
BEFORE = ROOT / "docs/icons/launcher-before-magnifier.png"
PNG = ROOT / "assets/app-icons/png"


def crop_wall(name, w, h, ox=0, oy=0):
    im = Image.open(ROOT / "assets/brand" / name).convert("RGBA")
    return im.crop((ox, oy, ox + w, oy + h))


def alt_glyph(kind):
    """The alternatives that were looked at and rejected, built on the same geometry (same block, same tile colour)."""
    L = apps.LAUNCHER
    cells, T = apps.launcher_geom(L)
    c = L["c"]
    mid = lambda r, q: r == 1 and q == 1
    if kind == "dots":
        els = [P("".join(circ(x + c / 2, y + c / 2, c / 2 * 0.8) for r, q, x, y in cells if not mid(r, q))), At(circ(0, 0, c / 2 * 0.8))]
    elif kind == "plus":
        els = [P("".join(A.superellipse_path(x + c / 2, y + c / 2, c / 2, c / 2, A.TILE_N) for r, q, x, y in cells if (r == 1) != (q == 1))), At(circ(0, 0, c / 2 * 1.04))]
    elif kind == "rr13":
        els = [P("".join(g.rr(x, y, c, c, 13.0) for r, q, x, y in cells if not mid(r, q))), At(circ(0, 0, c / 2 * 1.04))]
    else:  # "leafcell": the centre cell is a leaf-green tile, not a disc
        els = [P("".join(A.superellipse_path(x + c / 2, y + c / 2, c / 2, c / 2, A.TILE_N) for r, q, x, y in cells if not mid(r, q))),
               At(A.superellipse_path(0, 0, c / 2, c / 2, A.TILE_N))]
    return A.Glyph(apps.GLYPHS["launcher"].tile, els, "Launcher", apps.GLYPHS["launcher"].scale)


def main():
    new = apps.GLYPHS["launcher"]
    W, H = 1400, 1010
    sheet = Image.new("RGBA", (W, H), (28, 19, 27, 255))
    d = ImageDraw.Draw(sheet)
    F, Fs = _font(18), _font(13)
    dim, hi = (190, 160, 185), (225, 205, 222)
    with Renderer() as R:
        def icon(gl, s, mode="full"):
            return Image.fromarray(R.render([A.app_icon_svg(gl, "la", "Launcher", mode=mode, shadow=(mode == "full"))], s)[0])

        # before / after
        d.text((30, 18), "before: a magnifier, read as Search", font=F, fill=(200, 170, 195))
        d.text((470, 18), "after: an app grid", font=F, fill=(240, 225, 238))
        sheet.alpha_composite(Image.open(BEFORE).convert("RGBA").resize((400, 400)), (30, 50))
        sheet.alpha_composite(icon(new, 400), (470, 50))
        before = ["a ring with a handle is the Search symbol in every system",
                  "well built (filleted junction, glint) but the wrong idea",
                  "the leaf accent became a glint on a lens",
                  "ink 10.4% of the tile, one of the lightest glyphs"]
        after = ["3 x 3 tiles: the symbol for apps; no ring, no handle, no counter",
                 "each cell is the icon tile's own squircle (exponent 5), within 0.3 px",
                 "leaf disc inscribed in the centre cell: the brand accent of Camera, Settings, Passwords",
                 "block = the 160-unit square keyline; ink 16.0% (set median 13.2%)"]
        for k, t in enumerate(before):
            d.text((30, 462 + 20 * k), "- " + t, font=Fs, fill=dim)
        for k, t in enumerate(after):
            d.text((470, 462 + 20 * k), "- " + t, font=Fs, fill=hi)

        # on wallpapers
        d.text((930, 18), "on the dusk and dawn wallpapers (128 / 64 / 48 full, 32 small)", font=Fs, fill=(200, 170, 195))
        for k, wall in enumerate(("malva-dusk-2560x1440.jpg", "malva-dawn-2560x1440.jpg")):
            x0, y0 = 930, 50 + k * 220
            sheet.alpha_composite(crop_wall(wall, 440, 200, 900, 700), (x0, y0))
            xx = x0 + 20
            for s in (128, 64, 48, 32):
                sheet.alpha_composite(icon(new, s, "full" if s > 32 else "small"), (xx, y0 + 100 - s // 2))
                xx += s + 24

        # every size as shipped, then the 16 px cut enlarged: plain SVG render against the shipped (hinted) PNG
        d.text((30, 580), "as shipped: 128, 64 (full cut), 48, 32, 24, 22, 16 (small cut, pixel-hinted PNGs); 16 px enlarged 8x: plain / shipped",
               font=Fs, fill=(200, 170, 195))
        x = 30
        for s in (128, 64, 48, 32, 24, 22, 16):
            sheet.alpha_composite(Image.open(PNG / f"launcher-{s}.png").convert("RGBA"), (x, 610 + (128 - s) // 2))
            x += s + 22
        plain = icon(new, 16, "small").resize((128, 128), Image.NEAREST)
        shipped = Image.open(PNG / "launcher-16.png").convert("RGBA").resize((128, 128), Image.NEAREST)
        sheet.alpha_composite(plain, (x + 10, 610)); sheet.alpha_composite(shipped, (x + 150, 610))

        # alternatives that were rejected
        d.text((30, 770), "considered and rejected (same block and tile colour)", font=Fs, fill=(200, 170, 195))
        notes = {"dots": "dots: the generic menu glyph;\nround, not the tile's shape",
                 "plus": "plus of five: reads as add,\nnot as a launcher",
                 "rr13": "rounded-rect cells (r13): corners\nare 5.4% off the tile's curve",
                 "leafcell": "leaf-green centre tile: a close\nsecond; the disc is the brand's accent"}
        x = 30
        for kind, txt in notes.items():
            sheet.alpha_composite(icon(alt_glyph(kind), 150), (x, 795))
            for j, line in enumerate(txt.split("\n")):
                d.text((x, 952 + 16 * j), line, font=Fs, fill=dim)
            x += 215

        # symbolic
        d.text((930, 770), "symbolic (currentColor), dark and light panels at 64 and 24 px", font=Fs, fill=(200, 170, 195))
        vb = symbolic_vb(R, "launcher")
        svg = A.app_icon_svg(new, "la", "Launcher", mode="symbolic", sym_vb=vb)
        x = 930
        for fg, bgc in (((243, 230, 242), (46, 30, 44)), ((140, 50, 116), (246, 236, 245))):
            for s in (64, 24):
                a = R.render([svg], s, color="#%02X%02X%02X" % fg)[0]
                tile = Image.new("RGBA", (s + 24, s + 24), bgc + (255,))
                tile.alpha_composite(Image.fromarray(a), (12, 12))
                sheet.alpha_composite(tile, (x, 800)); x += s + 36
    sheet.convert("RGB").save(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
