"""LEGACY (superseded by build_theme.py, one SVG per icon in assets/icons/Malva; needs --legacy). Build the object icons: SVG (full / small / symbolic), PNG sizes and the manifest.
Run: python3 tools/icons/build_objects.py --legacy        (review sheets: python3 tools/icons/objects_review.py)

assets/object-icons/
  <id>.svg                full colour, 1024 canvas (use at 48 px and up)
  small/<id>.svg          heavier drawing for 16 to 32 px
  symbolic/<id>.svg       one colour (currentColor), square canvas fitted to the ink
  png/<id>-<size>.png     512, 256, 128, 64 from the full drawing; 48, 32, 24, 22, 16 from the small one
  manifest.json           id, name, group, template, emblem, icon-theme name (xdg, empty if none), hue, files
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import objects as O
from objfmt import object_svg, symbolic_svg, fit_viewbox
from mi_render import Renderer

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets/object-icons"
BIG = (512, 256, 128, 64)
SMALL = (48, 32, 24, 22, 16)


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def manifest_entry(o, vb) -> dict:
    """One manifest.json record. The checker builds the same record and compares it with the shipped file."""
    return {"id": o.id, "name": o.name, "group": o.group, "template": o.kind, "emblem": o.emblem,
            "xdg": o.xdg, "hue": o.meta.get("hue"), "svg": f"{o.id}.svg", "small": f"small/{o.id}.svg",
            "symbolic": f"symbolic/{o.id}.svg", "symbolic_viewbox": list(vb)}


def build(out: Path = OUT, ids=None):
    ids = ids or O.ORDER
    objs = [O.OBJECTS[i] for i in ids]
    for d in ("png", "small", "symbolic"):
        (out / d).mkdir(parents=True, exist_ok=True)
    full = [object_svg(o) for o in objs]
    small = [object_svg(o, small=True) for o in objs]
    manifest = []
    with Renderer() as R:
        vbs = [fit_viewbox(R, o) for o in objs]
        sym = [symbolic_svg(o, vb) for o, vb in zip(objs, vbs)]
        for o, f_, s_, y_, vb in zip(objs, full, small, sym, vbs):
            write(out / f"{o.id}.svg", f_)
            write(out / "small" / f"{o.id}.svg", s_)
            write(out / "symbolic" / f"{o.id}.svg", y_)
            manifest.append(manifest_entry(o, vb))
        # one render call per (size, cut): ids are unique inside a call because every id starts with its icon's id
        for s in BIG:
            for o, a in zip(objs, R.render(full, s)):
                Image.fromarray(a).save(out / "png" / f"{o.id}-{s}.png", optimize=True)
        for s in SMALL:
            for o, a in zip(objs, R.render(small, s)):
                Image.fromarray(a).save(out / "png" / f"{o.id}-{s}.png", optimize=True)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    return manifest


if __name__ == "__main__":
    import sys
    if "--legacy" not in sys.argv:
        raise SystemExit("Superseded: every icon is one SVG in assets/icons/Malva (python3 tools/icons/build_theme.py); PNGs are exported "
                         "from it on demand (export_png.py). Pass --legacy to write the old assets/object-icons PNG layout again.")
    m = build()
    print("built", len(m), "object icons ->", OUT)
