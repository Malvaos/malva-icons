"""Contact sheets for the glyph kit: every glyph at 24 px and 48 px beside its name, one colour, on a dark and a light strip.

    python3 tools/icons/glyph_review.py OUT.png [ctx|prefix ...]      e.g.  glyph_review.py /tmp/net.png network- audio-

The sheet is built from the same svg_of() the theme builder uses, so what you look at is what ships."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import glyphkit as K
from mi_render import Renderer, _font

DARK, LIGHT = (28, 22, 30), (246, 240, 247)
INK_ON_DARK, INK_ON_LIGHT = "#F3E6F1", "#3A1232"


def render_set(R, svgs, size, color):
    return R.render(svgs, size, color=color)


def contact(ids, out, cols=10, big=48, small=24, title=None):
    gls = [K.GLYPHS[i] for i in ids]
    svgs = [K.svg(g) for g in gls]
    with Renderer() as R:
        bd = R.render(svgs, big, color=INK_ON_DARK)
        sd = R.render(svgs, small, color=INK_ON_DARK)
        bl = R.render(svgs, big, color=INK_ON_LIGHT)
        sl = R.render(svgs, small, color=INK_ON_LIGHT)
        tiny = R.render(svgs, 16, color=INK_ON_DARK)
    cw, ch = 118, big + 52
    rows = -(-len(gls) // cols)
    top = 30 if title else 6
    W, H = cols * cw + 12, top + rows * ch + 6
    im = Image.new("RGB", (W, H), DARK)
    d = ImageDraw.Draw(im)
    if title:
        d.text((10, 6), title, font=_font(14), fill=(235, 226, 233))
    for n, g in enumerate(gls):
        r, c = divmod(n, cols)
        x0, y0 = 6 + c * cw, top + r * ch
        d.rectangle([x0, y0, x0 + cw - 4, y0 + ch - 4], outline=(52, 44, 54))
        # light strip behind the right-hand big glyph
        d.rectangle([x0 + 58, y0 + 4, x0 + 58 + big - 1, y0 + 4 + big - 1], fill=LIGHT)

        def put(arr, ox, oy, bg):
            a = arr[..., 3:4].astype(float) / 255
            reg = np.array(im.crop((ox, oy, ox + arr.shape[1], oy + arr.shape[0]))).astype(float)
            im.paste(Image.fromarray((arr[..., :3] * a + reg * (1 - a)).round().astype(np.uint8)), (ox, oy))
        put(bd[n], x0 + 4, y0 + 4, DARK)
        put(bl[n], x0 + 58, y0 + 4, LIGHT)
        put(sd[n], x0 + 4, y0 + 4 + big + 4, DARK)
        put(tiny[n], x0 + 34, y0 + 4 + big + 8, DARK)
        d.text((x0 + 4, y0 + big + 30), g.id[:20], font=_font(10), fill=(206, 196, 205))
        if len(g.id) > 20:
            d.text((x0 + 4, y0 + big + 40), g.id[20:40], font=_font(10), fill=(206, 196, 205))
    im.save(out)
    return im


def zoom(ids, out, size=160, cols=6, grid=True):
    """Large renders, one colour on a light ground, with the 24-unit grid drawn over them: the view for judging one drawing."""
    gls = [K.GLYPHS[i] for i in ids]
    svgs = [K.svg(g) for g in gls]
    with Renderer() as R:
        big = R.render(svgs, size, color=INK_ON_LIGHT)
    cw, ch = size + 12, size + 26
    rows = -(-len(gls) // cols)
    im = Image.new("RGB", (cols * cw + 6, rows * ch + 6), DARK)
    d = ImageDraw.Draw(im)
    for n, g in enumerate(gls):
        r, c = divmod(n, cols)
        x0, y0 = 6 + c * cw, 6 + r * ch
        d.rectangle([x0, y0, x0 + size - 1, y0 + size - 1], fill=LIGHT)
        if grid:
            u = size / 24
            for k in range(25):
                col = (222, 205, 222) if k % 4 else (196, 170, 196)
                d.line([(x0 + k * u, y0), (x0 + k * u, y0 + size)], fill=col)
                d.line([(x0, y0 + k * u), (x0 + size, y0 + k * u)], fill=col)
        a = big[n][..., 3:4].astype(float) / 255
        reg = np.array(im.crop((x0, y0, x0 + size, y0 + size))).astype(float)
        im.paste(Image.fromarray((big[n][..., :3] * a + reg * (1 - a)).round().astype(np.uint8)), (x0, y0))
        d.text((x0, y0 + size + 4), g.id[:26], font=_font(10), fill=(206, 196, 205))
    im.save(out)
    return im


def select(args):
    ids = []
    for a in args:
        for i, g in K.GLYPHS.items():
            if (g.ctx == a or i.startswith(a)) and i not in ids:
                ids.append(i)
    return ids or list(K.GLYPHS)


if __name__ == "__main__":
    import glyphs_all                                    # noqa: F401  registers every glyph
    out = sys.argv[1]
    ids = select(sys.argv[2:])
    contact(ids, out, title=f"{len(ids)} glyphs")
    print("wrote", out, len(ids), "glyphs")
