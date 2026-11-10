"""Build the Malva icon theme: assets/icons/Malva/ (SVG only).

  python3 tools/icons/build_theme.py                    build into assets/icons/Malva
  python3 tools/icons/build_theme.py --small-cuts       also write the optional 16-32 px drawings (small/)
  python3 tools/icons/build_theme.py --out DIR          build somewhere else
  python3 tools/icons/build_theme.py --aliases symlink  also create the alias names in the tree (install_theme.py does
                                                        this for an installed copy; a tree meant for a zip keeps none)

Nothing here is rasterised. PNG sizes are made on demand by export_png.py.
"""
from __future__ import annotations

import argparse
import gzip
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import theme_model as TM

LOGO_DIR = TM.ROOT / "assets/icons/malva-app-format"


def clear(out: Path):
    """Remove a previous build, but only a folder that is one: an index.theme that names this theme."""
    if not out.exists():
        return
    idx = out / "index.theme"
    if not (idx.exists() and f"Name={TM.THEME}" in idx.read_text()):
        raise SystemExit(f"{out} exists and is not a {TM.THEME} icon theme; refusing to delete it")
    shutil.rmtree(out)


def write_theme(m: TM.Model, out: Path, aliases: str = "none") -> None:
    clear(out)
    for e in m.entries + m.smalls:
        p = out / e.path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(e.svg)
    (out / "index.theme").write_text(TM.index_theme(m))
    (out / "manifest.json").write_text(TM.manifest_text(m))
    if aliases != "none":
        link_aliases(m, out, aliases)


def link_aliases(m: TM.Model, out: Path, how: str) -> int:
    """Materialise the alias names next to the files they serve: a relative symlink, or a copy where links are not allowed."""
    return TM.link_alias_files(TM.manifest(m), out, how)


def write_logo_variants(R, out: Path = LOGO_DIR) -> list[str]:
    """The app-format logo on the four brand colourways, and its one-colour and small cuts. SVG only."""
    import build_apps as BA
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    names = []
    for v, kw in BA.VARIANTS.items():
        (out / f"malva-app-icon-{v}.svg").write_text(BA.icon_svg("malva", **kw))
        names.append(f"malva-app-icon-{v}.svg")
    (out / "malva-app-icon-mono.svg").write_text(BA.icon_svg("malva", "mono"))
    (out / "malva-app-icon-small.svg").write_text(BA.icon_svg("malva", "small"))
    return names + ["malva-app-icon-mono.svg", "malva-app-icon-small.svg"]


def size_report(m: TM.Model) -> str:
    rows = {}
    for e in m.entries + m.smalls:
        b = e.svg.encode()
        r = rows.setdefault((e.family, e.variant), [0, 0, 0])
        r[0] += 1
        r[1] += len(b)
        r[2] += len(gzip.compress(b, 9, mtime=0))
    lines = [f"{'family':8} {'variant':14} {'files':>5} {'bytes':>9} {'gzip':>9} {'avg':>6}"]
    tot = [0, 0, 0]
    for (fam, var), (n, b, z) in sorted(rows.items()):
        lines.append(f"{fam:8} {var:14} {n:5d} {b:9d} {z:9d} {b // n:6d}")
        tot = [tot[0] + n, tot[1] + b, tot[2] + z]
    lines.append(f"{'total':8} {'':14} {tot[0]:5d} {tot[1]:9d} {tot[2]:9d} {tot[1] // max(tot[0], 1):6d}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=TM.OUT)
    ap.add_argument("--small-cuts", action="store_true")
    ap.add_argument("--aliases", choices=("none", "symlink", "copy"), default="none")
    ap.add_argument("--no-logo", action="store_true", help="do not write the app-format logo variants")
    a = ap.parse_args(argv)
    from mi_render import Renderer
    with Renderer() as R:
        m = TM.build_model(R, small_cuts=a.small_cuts)
        write_theme(m, a.out, a.aliases)
        if not a.no_logo and a.out == TM.OUT:
            write_logo_variants(R)
    print(size_report(m))
    print(f"{len(m.entries) + len(m.smalls)} files, {len(m.aliases)} alias names -> {a.out}")
    return m


if __name__ == "__main__":
    main()
