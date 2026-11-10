"""LEGACY (superseded by build_theme.py: one SVG per icon in assets/icons/Malva; this needs --legacy). Build the system app icons:
SVG (full / small / symbolic), PNG sizes, manifest and review sheets. The helpers in this file (symbolic_vb ...) are still used by the theme.
Run: python3 tools/icons/build_apps.py --legacy"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import appfmt as A
import optical as O
import apps
import hints
from mi_render import Renderer, sheet, _font

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets/app-icons"
DOCS = ROOT / "docs/icons"

# the app-format logo on the supplied brand colours (guideline: plum, lilac colour, dusk, leaf)
VARIANTS = {
    "plum": dict(brand_stops=A.BRAND_TILE_STOPS),
    "lilac": dict(brand_stops=("#F7ECF6", "#DDC3DC"), lilac_stops=("#C763B0", "#8C3274"),
                  leaf_tile="#274903", shadow_col="#5A1F4B", hl=0.55),
    "dusk": dict(brand_stops=("#34202F", "#170D16")),
    "leaf": dict(brand_stops=("#3F6B1C", "#1A3306")),
}


SYMBOLIC_FILL = A.SYMBOLIC_FILL


def symbolic_vb(R, i: str) -> tuple:
    """(half-size, shift x, shift y) of the symbolic canvas, measured from a render of the cut with no shift.
    The cut is centred on its own ink by the rule of optical.py (box on the middle, less a capped pull of the mass:
    the tile's shift is in the tile's units and says nothing about a glyph that fills 88 % of a small canvas), and the
    half-size makes the farthest edge from that centre fill SYMBOLIC_FILL of the canvas."""
    big = A.app_icon_svg(apps.GLYPHS[i], i, i, mode="symbolic", sym_vb=(150.0, 0.0, 0.0))
    al = R.render([big], 600)[0][..., 3].astype(float)
    k = 300 / 600                                                       # canvas units per pixel (the canvas is 300 units wide)
    ys, xs = np.nonzero(al > 20)
    x0, x1, y0, y1 = (xs.min() - 300) * k, (xs.max() + 1 - 300) * k, (ys.min() - 300) * k, (ys.max() + 1 - 300) * k
    mx = ((al * np.arange(600)[None, :]).sum() / al.sum() + 0.5 - 300) * k
    my = ((al * np.arange(600)[:, None]).sum() / al.sum() + 0.5 - 300) * k
    side = max(x1 - x0, y1 - y0) / SYMBOLIC_FILL                         # the canvas the pull is measured against
    sx, sy = O.shift((x0 + x1) / 2, mx, side), O.shift((y0 + y1) / 2, my, side)
    half = max(abs(x0 + sx), abs(x1 + sx), abs(y0 + sy), abs(y1 + sy))
    return (round(half / SYMBOLIC_FILL, 1), round(sx, 1), round(sy, 1))


def icon_svg(i: str, mode="full", uid: str | None = None, **kw):
    """`uid` prefixes every id in the file; give two cuts of one app different uids when they must share a page."""
    gl = apps.GLYPHS[i]
    if i == "malva" and "brand_stops" not in kw and mode not in ("mono", "symbolic"):
        kw["brand_stops"] = A.BRAND_TILE_STOPS
    return A.app_icon_svg(gl, uid or i, "Malva " + apps.NAMES[i] if i != "malva" else "Malva OS", mode=mode, **kw)


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def main():
    for d in ("png", "small", "symbolic", "malva-app-format"):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    manifest = []
    VB = {}
    with Renderer() as R:
        # --- per-app files
        for i in apps.ORDER:
            VB[i] = symbolic_vb(R, i)
            full, small, mono = icon_svg(i), icon_svg(i, "small"), icon_svg(i, "symbolic", sym_vb=VB[i])
            write(OUT / f"{i}.svg", full)
            write(OUT / "small" / f"{i}.svg", small)
            write(OUT / "symbolic" / f"{i}.svg", mono)
            for s in (512, 256, 128, 64):
                Image.fromarray(R.render([full], s)[0]).save(OUT / "png" / f"{i}-{s}.png", optimize=True)
            for s in (48, 32, 24, 22, 16):
                # small PNGs carry the pixel-snapping hint for that size when hints.json has one (SVGs never do)
                svg_s = icon_svg(i, "small", hint=hints.hint_for(i, s)) if hints.hint_for(i, s) else small
                Image.fromarray(R.render([svg_s], s)[0]).save(OUT / "png" / f"{i}-{s}.png", optimize=True)
            st = (A.BRAND_TILE_STOPS if i == "malva" else apps.GLYPHS[i].tile.stops())
            manifest.append({"id": i, "name": apps.NAMES[i], "tile_light": st[0], "tile_dark": st[1],
                             "svg": f"{i}.svg", "small": f"small/{i}.svg", "symbolic": f"symbolic/{i}.svg"})
        # --- the app-format logo variants
        for v, kw in VARIANTS.items():
            svg = icon_svg("malva", **kw)
            write(OUT / "malva-app-format" / f"malva-app-icon-{v}.svg", svg)
            for s in (1024, 512, 256, 128, 64):
                Image.fromarray(R.render([svg], s)[0]).save(OUT / "malva-app-format" / f"malva-app-icon-{v}-{s}.png", optimize=True)
        write(OUT / "malva-app-format" / "malva-app-icon-mono.svg", icon_svg("malva", "mono"))
        write(OUT / "malva-app-format" / "malva-app-icon-small.svg", icon_svg("malva", "small"))
        for s in (48, 32, 16):
            Image.fromarray(R.render([icon_svg("malva", "small")], s)[0]).save(OUT / "malva-app-format" / f"malva-app-icon-small-{s}.png", optimize=True)
        (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")

        # --- review sheets
        arr = R.render([icon_svg(i) for i in apps.ORDER], 176)
        for wp_name, fg in (("dusk", (240, 232, 238)), ("dawn", (40, 24, 38))):
            wp = Image.open(ROOT / f"assets/brand/malva-{wp_name}-2560x1440.jpg").convert("RGB").resize((1280, 720))
            W, H = 4 * 176 + 5 * 36, 4 * (176 + 34) + 36
            bg = wp.crop((0, 40, W, 40 + H)).copy() if W <= 1280 and 40 + H <= 720 else wp.resize((W, H))
            d = ImageDraw.Draw(bg)
            fnt = _font(13)
            for k, (i, a) in enumerate(zip(apps.ORDER, arr)):
                r, c = divmod(k, 4)
                x, y = 36 + c * (176 + 36), 36 + r * (176 + 34)
                tile = Image.fromarray(a)
                bg.paste(tile, (x, y), tile)
                nm = apps.NAMES[i]
                tw = d.textlength(nm, font=fnt)
                d.text((x + (176 - tw) / 2, y + 180), nm, fill=fg, font=fnt)
            bg.save(DOCS / f"apps-on-{wp_name}.png")
        # sizes sheet: 128 | 64 | 48 | 32 full | 32 small | 16 full | 16 small
        cols = [("128", 128, "full"), ("64", 64, "full"), ("48", 48, "full"), ("32 full", 32, "full"),
                ("32 small", 32, "small"), ("16 full", 16, "full"), ("16 small", 16, "small")]
        rows = {}
        for lab, s, mode in cols:
            rows[lab] = R.render([icon_svg(i, mode) for i in apps.ORDER], s)
        wide = 150 + sum(c[1] + 24 for c in cols)
        sh = Image.new("RGB", (wide, 36 + 16 * 144), (36, 24, 34))
        d = ImageDraw.Draw(sh)
        fnt = _font(12)
        x = 150
        for lab, s, _ in cols:
            d.text((x, 10), lab, fill=(230, 222, 228), font=fnt)
            x += s + 24
        for r, i in enumerate(apps.ORDER):
            y = 36 + r * 144
            d.text((8, y + 60), i, fill=(230, 222, 228), font=fnt)
            x = 150
            for lab, s, _ in cols:
                a = rows[lab][r]
                t = Image.fromarray(a)
                sh.paste(t, (x, y + (144 - s) // 2), t)
                x += s + 24
        sh.save(DOCS / "apps-sizes.png")
        # symbolic sheet
        mono = [icon_svg(i, "symbolic", sym_vb=VB[i]) for i in apps.ORDER]
        dark = R.render(mono, 72, color="#F3E6F2")
        light = R.render(mono, 72, color="#8C3274")
        items = [(i, a) for i, a in zip(apps.ORDER, dark)]
        sheet(items, 8, 88, bg=(36, 24, 34), title="symbolic glyphs (currentColor)", font_size=10).save(DOCS / "apps-symbolic-dark.png")
        items = [(i, a) for i, a in zip(apps.ORDER, light)]
        sheet(items, 8, 88, bg=(246, 236, 245), fg=(60, 30, 56), title="symbolic glyphs (currentColor)", font_size=10).save(DOCS / "apps-symbolic-light.png")
        # logo variants
        vs = [A.app_icon_svg(apps.GLYPHS["malva"], "m" + k, "Malva OS", **kw) for k, kw in VARIANTS.items()]
        va = R.render(vs, 220)
        mono_a = R.render([icon_svg("malva", "mono")], 120, color="#8C3274")[0]
        small = [R.render([icon_svg("malva", "small")], s)[0] for s in (48, 32, 24, 16)]
        items = [(k, a) for k, a in zip(VARIANTS, va)] + [("mono (currentColor)", mono_a)]
        items += [(f"small cut {s}px", a) for s, a in zip((48, 32, 24, 16), small)]
        sheet(items, 5, 236, bg=(240, 232, 240), fg=(50, 24, 46), title="Malva app-format logo", font_size=12).save(DOCS / "malva-app-format.png")
    print("built", len(apps.ORDER), "app icons")


if __name__ == "__main__":
    import sys
    if "--legacy" not in sys.argv:
        raise SystemExit("Superseded: every icon is one SVG in assets/icons/Malva (python3 tools/icons/build_theme.py); PNGs are exported "
                         "from it on demand (export_png.py). Pass --legacy to write the old assets/app-icons PNG layout again.")
    main()
