"""Export PNGs from the SVGs, at any size, when a program needs a raster. The theme itself never ships any.

  # one or more icons, any sizes
  python3 tools/icons/export_png.py assets/icons/Malva/scalable/apps/files.svg --size 64 128 256 -o out/

  # a one-colour glyph in the colour you want (symbolic files draw in `currentColor`)
  python3 tools/icons/export_png.py assets/icons/Malva/symbolic/status/battery-level-50-symbolic.svg --size 24 --color "#F3E6F2"

  # the whole theme as a classic raster theme: out/<size>x<size>/<context>/<name>.png
  python3 tools/icons/export_png.py --theme assets/icons/Malva --size 16 24 32 48 64 128 256 --color "#2E2230" -o out/ --aliases

Renderers: rsvg-convert, resvg and inkscape are used when they are on PATH (in that order); otherwise headless Chromium
through Playwright (what the review sheets use). --backend picks one. The output of different renderers differs in the
last grey level of an edge, never in shape.
"""
from __future__ import annotations

import argparse
import io
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

BACKENDS = ("rsvg", "resvg", "inkscape", "chromium")
EXE = {"rsvg": "rsvg-convert", "resvg": "resvg", "inkscape": "inkscape"}


def pick_backend(want: str = "auto") -> str:
    import rsvg_render
    if want != "auto":
        if want == "rsvg" and not shutil.which(EXE["rsvg"]) and rsvg_render.available():
            return "librsvg"
        if want in EXE and not shutil.which(EXE[want]):
            raise SystemExit(f"{EXE[want]} is not on PATH")
        return want
    for b in ("rsvg", "resvg", "inkscape"):
        if shutil.which(EXE[b]):
            return b
    if rsvg_render.available():
        return "librsvg"
    return "chromium"


def command(backend: str, src: Path, dst: Path, size: int) -> list[str]:
    """The command line of an external renderer: one SVG file in, one PNG file out, square, `size` px."""
    if backend == "rsvg":
        return [EXE[backend], "-w", str(size), "-h", str(size), "-f", "png", "-o", str(dst), str(src)]
    if backend == "resvg":
        return [EXE[backend], "-w", str(size), "-h", str(size), str(src), str(dst)]
    if backend == "inkscape":
        return [EXE[backend], str(src), "-w", str(size), "-h", str(size), "--export-type=png", f"--export-filename={dst}"]
    raise ValueError(backend)


def with_color(svg: str, color: str) -> str:
    """External renderers have no CSS context to take `currentColor` from: put the colour in."""
    return svg.replace("currentColor", color)


def sized(svg: str, size: int) -> str:
    """The same drawing with width and height set to `size` (the viewBox keeps the proportions)."""
    import re
    head = re.match(r"<svg [^>]*>", svg).group(0)
    new = re.sub(r'\s(width|height)="[^"]*"', "", head)
    new = new.replace("<svg ", f'<svg width="{size}" height="{size}" ', 1)
    return svg.replace(head, new, 1)


def render_png(svgs: list[str], size: int, color: str = "#000000", bg: str | None = None, backend: str = "auto") -> list[bytes]:
    """PNG bytes for each SVG text at size x size."""
    from PIL import Image
    backend = pick_backend(backend)
    out: list[bytes] = []
    if backend == "librsvg":
        import rsvg_render
        import numpy as np
        for svg in svgs:
            arr = rsvg_render.render(sized(with_color(svg, color), size), size)
            im = Image.fromarray(np.asarray(arr)).convert("RGBA")
            if bg:
                base = Image.new("RGBA", im.size, bg)
                base.alpha_composite(im)
                im = base
            buf = io.BytesIO()
            im.save(buf, "PNG", optimize=True)
            out.append(buf.getvalue())
        return out
    if backend == "chromium":
        from mi_render import Renderer
        import numpy as np
        step = max(1, (4096 // size) * (4096 // size))        # keep one screenshot under 4096 px each way
        with Renderer() as R:
            for i in range(0, len(svgs), step):
                for a in R.render(svgs[i:i + step], size, bg=bg, color=color):
                    buf = io.BytesIO()
                    Image.fromarray(np.asarray(a)).save(buf, "PNG", optimize=True)
                    out.append(buf.getvalue())
        return out
    with tempfile.TemporaryDirectory(prefix="export-png-") as td:
        for k, svg in enumerate(svgs):
            src, dst = Path(td) / f"{k}.svg", Path(td) / f"{k}.png"
            src.write_text(sized(with_color(svg, color), size))
            subprocess.run(command(backend, src, dst, size), check=True, capture_output=True)
            im = Image.open(dst).convert("RGBA")
            if bg:
                base = Image.new("RGBA", im.size, bg)
                base.alpha_composite(im)
                im = base
            buf = io.BytesIO()
            im.save(buf, "PNG", optimize=True)
            out.append(buf.getvalue())
    return out


def export_files(files: list[Path], sizes: list[int], out: Path, color: str, bg: str | None, backend: str) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    svgs = [p.read_text() for p in files]
    done = []
    for s in sizes:
        for p, png in zip(files, render_png(svgs, s, color, bg, backend)):
            dst = out / f"{p.stem}-{s}.png"
            dst.write_bytes(png)
            done.append(dst)
    return done


def export_theme(theme: Path, sizes: list[int], out: Path, color: str, bg: str | None, backend: str, aliases: bool) -> int:
    man = json.loads((theme / "manifest.json").read_text())
    icons = man["icons"]
    n = 0
    for s in sizes:
        pick = {i["name"]: i for i in icons if i["variant"] != "small"}
        if 16 <= s <= 32:                                   # the optional small cut, where the theme has one
            pick.update({i["name"]: i for i in icons if i["variant"] == "small"})
        recs = sorted(pick.values(), key=lambda r: r["file"])
        pngs = render_png([(theme / r["file"]).read_text() for r in recs], s, color, bg, backend)
        for r, png in zip(recs, pngs):
            d = out / f"{s}x{s}" / r["context"]
            d.mkdir(parents=True, exist_ok=True)
            (d / f"{r['name']}.png").write_bytes(png)
            n += 1
            if aliases:
                for a in man["aliases"]:
                    if a["target"] == r["name"]:
                        (d / f"{a['name']}.png").write_bytes(png)
                        n += 1
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", type=Path, help="SVG files to export")
    ap.add_argument("--theme", type=Path, help="export a whole theme folder (needs its manifest.json)")
    ap.add_argument("--size", "-s", nargs="+", type=int, default=[48], help="pixel sizes (square)")
    ap.add_argument("--color", default="#000000", help="colour of one-colour (symbolic) icons")
    ap.add_argument("--bg", default=None, help="background colour; transparent when omitted")
    ap.add_argument("--backend", choices=("auto",) + BACKENDS, default="auto")
    ap.add_argument("-o", "--out", type=Path, default=Path("png-export"))
    ap.add_argument("--aliases", action="store_true", help="with --theme: also write the alias names")
    a = ap.parse_args(argv)
    if not a.files and not a.theme:
        ap.error("give SVG files or --theme DIR")
    if any(s < 1 or s > 4096 for s in a.size):
        ap.error("sizes run from 1 to 4096")
    if a.theme:
        n = export_theme(a.theme, a.size, a.out, a.color, a.bg, a.backend, a.aliases)
        print(f"{n} PNGs -> {a.out} ({pick_backend(a.backend)})")
    if a.files:
        done = export_files(a.files, a.size, a.out, a.color, a.bg, a.backend)
        print(f"{len(done)} PNGs -> {a.out} ({pick_backend(a.backend)})")


if __name__ == "__main__":
    main()
