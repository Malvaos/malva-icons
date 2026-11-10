"""Measured checks of the shipped icon theme (assets/icons/Malva): the files on disk, not the generators.

  python3 tools/icons/check_theme.py [--theme DIR] [--report PATH] [--no-negative]

What is checked, and how each check is proven to bite (a negative test breaks a copy of the theme in exactly the way
the check is for, and the check must fail):

  tree       only .svg, index.theme and manifest.json; no PNG, no symlink (a zip would lose them)
  manifest   lists every file and nothing else; sizes and SHA-256 match; is what the generator writes now
  build      every file is exactly what its generator makes now; building twice gives byte-identical files
  index      Directories = the folders that hold files; every folder has Context/Size/MinSize/MaxSize/Type=Scalable
  names      one file per name; aliases point at files, never at aliases; mirrored (-rtl) copies pair up and mirror
  coverage   every name on the reference list (required_names.json) is served, as a file or an alias
  lookup     the freedesktop icon lookup, run over the installed view (files + alias names), finds every name at every
             size from 16 to 512 inside a directory whose size range holds it (never "the closest size"), and picks a
             small cut only for 16-32 px; GTK's own has_icon agrees (libgtk-3 through ctypes, where installed)
  svg        well-formed, square viewBox, no raster, script, text, <use> or link, ids unique and every url(#) resolves,
             ids unique across the whole theme (so any number of icons can sit in one page), size budget per family
  render     every icon draws at 16 and 64 px; symbolic files take the text colour and nothing else; full-colour files
             ignore it; symbolic ink never touches the canvas edge; librsvg draws what Chromium draws

Measurements that are not pass or fail are listed after the checks.
"""
from __future__ import annotations

import argparse
import configparser
import hashlib
import json
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import theme_model as TM
from checkkit import Agg, Report, finish, flag, num, fails
from mi_render import Renderer

SIZES = (16, 22, 24, 32, 48, 64, 96, 128, 256, 512)
XR_SIZE = 128                              # the two engines place an anti-aliased edge a hair apart: compare where that is small
SVG_NS = "http://www.w3.org/2000/svg"
T = dict(
    bytes_glyph=2400, bytes_tile=4000, bytes_object=8000, bytes_app=8000, bytes_cut=6500, bytes_total=1_000_000,
    ink16_min=0.04,                       # share of a 16 px render that is ink: the thinnest glyph measures .07
    ring_max=0,                           # alpha in the outermost pixel ring of a symbolic file at 96 px: 0 everywhere
    colour_tol=3,                         # a symbolic pixel is the text colour to within this many levels
    rtl_iou_min=0.99,
    xr_iou_min=0.93, xr_alpha_max=0.035,  # librsvg against Chromium: the worst file measures .947 / .028
)
ALLOWED_TAGS = {"svg", "g", "defs", "path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "mask", "clipPath",
                "linearGradient", "radialGradient", "stop", "title", "desc"}
BAD_ATTRS = {"href", "style", "onload", "onclick", "onerror", "src"}


# ---------------------------------------------------------------------------------------------------------- the tree
@dataclass
class Tree:
    files: dict = field(default_factory=dict)        # relative path -> bytes (regular files)
    links: dict = field(default_factory=dict)        # relative path -> link target
    root: Path | None = None

    @classmethod
    def load(cls, root: Path) -> "Tree":
        import os
        t = cls(root=Path(root))
        for dp, _dn, fn in os.walk(root):
            for f in fn:
                p = Path(dp) / f
                rel = p.relative_to(root).as_posix()
                if p.is_symlink():
                    t.links[rel] = os.readlink(p)
                else:
                    t.files[rel] = p.read_bytes()
        return t

    def copy(self) -> "Tree":
        return Tree(dict(self.files), dict(self.links), None)

    def text(self, p: str) -> str:
        return self.files[p].decode()

    def svgs(self) -> list[str]:
        return sorted(p for p in self.files if p.endswith(".svg"))

    def manifest(self) -> dict:
        return json.loads(self.text("manifest.json"))

    def write(self, root: Path):
        for p, b in self.files.items():
            q = Path(root) / p
            q.parent.mkdir(parents=True, exist_ok=True)
            q.write_bytes(b)
        for p, tgt in self.links.items():
            q = Path(root) / p
            q.parent.mkdir(parents=True, exist_ok=True)
            q.symlink_to(tgt)


def parse_index(text: str):
    cp = configparser.ConfigParser(interpolation=None, strict=False)
    cp.optionxform = str
    cp.read_string(text)
    head = dict(cp["Icon Theme"])
    dirs = [d.strip() for d in head.get("Directories", "").split(",") if d.strip()]
    return head, dirs, {s: dict(cp[s]) for s in cp.sections() if s != "Icon Theme"}


def view_of(tree: Tree, man: dict) -> set:
    """Every file a lookup can open once the theme is installed: the files, and one per alias name."""
    return {p for p in tree.files if p.endswith(".svg")} | {a for a, _ in TM.alias_files(man)}


# ---------------------------------------------------------------------------------------------------------- tree, manifest, build
def check_tree(tree: Tree, allow_links=False):
    other = sorted(p for p in tree.files if not (p.endswith(".svg") or p in ("index.theme", "manifest.json")))
    return [flag("tree:only-svg-plus-index.theme-and-manifest.json", not other, f"{len(tree.files)} files" if not other else "; ".join(other[:5])),
            flag("tree:no-symlinks-in-the-shipped-tree", allow_links or not tree.links,
                 "none" if not tree.links else "; ".join(sorted(tree.links)[:4]))]


def check_manifest(tree: Tree, m: TM.Model):
    man = tree.manifest()
    listed = [i["file"] for i in man["icons"]]
    files = set(tree.svgs())
    miss, extra = sorted(set(listed) - files), sorted(files - set(listed))
    bad = [i["file"] for i in man["icons"] if i["file"] in tree.files and
           (hashlib.sha256(tree.files[i["file"]]).hexdigest() != i["sha256"] or len(tree.files[i["file"]]) != i["bytes"])]
    return [flag("manifest:lists-every-svg-and-nothing-else", not miss and not extra and len(listed) == len(set(listed)),
                 f"{len(listed)} listed" if not (miss or extra) else f"missing {miss[:3]} extra {extra[:3]}"),
            flag("manifest:sizes-and-sha256-match-the-files", not bad, "all match" if not bad else "; ".join(bad[:4])),
            flag("manifest:is-what-the-generator-writes-now", tree.text("manifest.json") == TM.manifest_text(m), "")]


def check_build(tree: Tree, m: TM.Model, m2: TM.Model | None):
    want = {e.path: e.svg for e in m.entries + m.smalls}
    stale = sorted(p for p, svg in want.items() if p not in tree.files or tree.files[p].decode() != svg)
    extra = sorted(p for p in tree.svgs() if p not in want)
    res = [flag("build:every-file-is-what-its-generator-makes-now", not stale and not extra,
                f"{len(want)} files" if not (stale or extra) else f"stale/missing {stale[:3]} unknown {extra[:3]}"),
           flag("build:index.theme-is-what-the-generator-writes-now", tree.text("index.theme") == TM.index_theme(m), "")]
    if m2 is not None:
        res.append(flag("build:a-second-build-is-byte-identical", m.digest() == m2.digest(), m.digest()[:12]))
    return res


# ---------------------------------------------------------------------------------------------------------- index.theme
def check_index(tree: Tree):
    head, dirs, secs = parse_index(tree.text("index.theme"))
    have = {p.rsplit("/", 1)[0] for p in tree.svgs()}
    keys = ("Context", "Size", "MinSize", "MaxSize", "Type")
    bad = []
    for d in dirs:
        s = secs.get(d, {})
        miss = [k for k in keys if k not in s]
        if miss:
            bad.append(f"{d} lacks {miss}")
            continue
        try:
            sz, lo, hi = int(s["Size"]), int(s["MinSize"]), int(s["MaxSize"])
        except ValueError:
            bad.append(f"{d}: size is not a number")
            continue
        if s["Type"] != "Scalable" or not (0 < lo <= sz <= hi) or s["Context"] not in TM.CTX_NAME.values():
            bad.append(f"{d}: {s['Type']} {lo}<={sz}<={hi} {s['Context']}")
    exp = (head.get("Name") == TM.THEME and "hicolor" in head.get("Inherits", "") and
           f"{head.get('Example', '')}.svg" in {p.rsplit('/', 1)[1] for p in tree.svgs()})
    return [flag("index:directories-are-exactly-the-folders-that-hold-files", set(dirs) == have and len(dirs) == len(set(dirs)),
                 f"{len(dirs)} directories" if set(dirs) == have else f"listed-not-present {sorted(set(dirs) - have)[:3]} present-not-listed {sorted(have - set(dirs))[:3]}"),
            flag("index:every-directory-has-context-size-range-and-type=Scalable", not bad, "; ".join(bad[:4]) or f"{len(dirs)} directories"),
            flag("index:name-inherits-hicolor-and-an-example-that-exists", exp, f"Name={head.get('Name')} Inherits={head.get('Inherits')} Example={head.get('Example')}")]


# ---------------------------------------------------------------------------------------------------------- names
def stems(tree: Tree):
    out = {}
    for p in tree.svgs():
        tier = p.split("/")[0]
        out.setdefault((p.rsplit("/", 1)[1][:-4], "small" if tier == "small" else "main"), []).append(p)
    return out


def check_names(tree: Tree):
    man = tree.manifest()
    st = stems(tree)
    dup = sorted(f"{n}: {ps[:2]}" for (n, _t), ps in st.items() if len(ps) > 1)
    main = {n for (n, t) in st if t == "main"}
    small = {n for (n, t) in st if t == "small"}
    al = {a["name"]: a for a in man["aliases"]}
    bad = []
    for a in man["aliases"]:
        if a["target"] not in main:
            bad.append(f"{a['name']} -> {a['target']} (no such file)")
        elif a["target"] in al:
            bad.append(f"{a['name']} -> {a['target']} (an alias)")
        if a["name"] in main:
            bad.append(f"{a['name']} is both an alias and a file")
    names = sorted(main)
    rtl = [n for n in names if n.endswith("-symbolic-rtl")]
    orphan = [n for n in rtl if n[:-4] not in main]
    ltr_alias = [a["name"] for a in man["aliases"] if a["name"].endswith(("-ltr-symbolic-rtl", "-rtl-symbolic-rtl", "-ltr-symbolic", "-rtl-symbolic")) and a["name"].endswith("-rtl")]
    return [flag("names:one-file-per-name-in-the-whole-theme", not dup, "; ".join(dup[:4]) or f"{len(main)} names"),
            flag("names:every-small-cut-has-a-scalable-partner", small <= main, ", ".join(sorted(small - main)[:4]) or f"{len(small)} small cuts"),
            flag("names:aliases-point-at-files-never-at-aliases-and-never-shadow-a-file", not bad, "; ".join(bad[:4]) or f"{len(al)} alias names"),
            flag("names:every-rtl-file-has-its-left-to-right-original", not orphan and not ltr_alias, "; ".join(orphan[:4] + ltr_alias[:2]) or f"{len(rtl)} mirrored files")]


def check_coverage(tree: Tree, req: dict, m: TM.Model | None):
    man = tree.manifest()
    have = {p.rsplit("/", 1)[1][:-4] for p in tree.svgs() if not p.startswith("small/")} | {a["name"] for a in man["aliases"]}
    want, miss = 0, []
    for ctx, names in req["names"].items():
        skip = set(req["skip"].get(ctx, {}))
        for n in names:
            if n in skip:
                continue
            want += 1
            if n + "-symbolic" not in have:
                miss.append(f"{ctx}/{n}")
    res = [flag("coverage:every-name-on-the-reference-list-is-served", not miss,
                f"{want} names" if not miss else f"{len(miss)} missing: " + ", ".join(miss[:6]))]
    if m is not None:                                           # the generators' own sources: nothing built is left out
        import apps
        import objects as O
        import tiles as TI
        left = [f"app {i}" for i in apps.ORDER if i not in have] + [f"tile {i}" for i in TI.ORDER if i not in have] + \
               [f"object {i}" for i in O.ORDER if (O.OBJECTS[i].xdg or i) not in have]
        al = {a["name"] for a in man["aliases"]}
        import theme_aliases as TA
        left += [f"alias {a}" for a in list(TA.OBJECT_ALIASES) + list(TA.APP_ALIASES) if a not in al]
        res.append(flag("coverage:every-app-tile-object-and-listed-alias-is-in-the-theme", not left, "; ".join(left[:5]) or "complete"))
    return res


# ---------------------------------------------------------------------------------------------------------- lookup
def lookup(head_dirs, secs, view: set, name: str, size: int):
    """The freedesktop icon-theme lookup (spec 'Icon Lookup'): the first directory in order whose size range holds the
    request and that has the file; failing that the one with the smallest size distance. Returns (path, distance)."""
    best = (None, None)
    for d in head_dirs:
        p = f"{d}/{name}.svg"
        if p not in view or d not in secs:
            continue
        s = secs[d]
        lo, hi = int(s["MinSize"]), int(s["MaxSize"])
        dist = 0 if lo <= size <= hi else (lo - size if size < lo else size - hi)
        if dist == 0:
            return p, 0
        if best[0] is None or dist < best[1]:
            best = (p, dist)
    return best


def check_lookup(tree: Tree, man: dict, sizes=SIZES):
    head, dirs, secs = parse_index(tree.text("index.theme"))
    view = view_of(tree, man)
    names = sorted({p.rsplit("/", 1)[1][:-4] for p in view})
    has_small = any(p.startswith("small/") for p in view)
    miss, far, wrong, small_bad, n = [], [], [], [], 0
    for nm in names:
        for s in sizes:
            n += 1
            p, dist = lookup(dirs, secs, view, nm, s)
            if p is None:
                miss.append(f"{nm}@{s}")
            elif dist != 0:
                far.append(f"{nm}@{s} (nearest range is {dist} away)")
            else:
                small_ok = (p.startswith("small/")) == (has_small and 16 <= s <= 32 and f"small/{p.split('/', 1)[1]}" == p and True)
                if p.startswith("small/") and not 16 <= s <= 32:
                    small_bad.append(f"{nm}@{s} got the small cut")
                if has_small and 16 <= s <= 32 and f"small/{p.split('/', 1)[1]}" != p and f"small/{p.split('/', 1)[1].split('/', 1)[0]}/{nm}.svg" in view:
                    small_bad.append(f"{nm}@{s} missed its small cut")
    rtl = [nm for nm in names if nm.endswith("-symbolic-rtl")]
    rtl_bad = [nm for nm in rtl if lookup(dirs, secs, view, nm, 16)[0] is None]
    return [flag("lookup:every-name-is-found-at-16-to-512-px", not miss, f"{len(names)} names x {len(sizes)} sizes" if not miss else "; ".join(miss[:5])),
            flag("lookup:every-find-is-inside-a-directory-whose-size-range-holds-the-request", not far, "all exact" if not far else "; ".join(far[:4])),
            flag("lookup:small-cuts-are-chosen-for-16-to-32-px-and-only-then", not small_bad, "; ".join(small_bad[:4]) or ("no small cuts in this build" if not has_small else "ok")),
            flag("lookup:mirrored-files-are-reachable-by-name", not rtl_bad, f"{len(rtl)} files" if not rtl_bad else "; ".join(rtl_bad[:4]))]


def gtk_has_icon(tree: Tree, man: dict, names: list[str]):
    """Ask libgtk-3 itself (through ctypes) whether the installed theme has each name. Returns (missing names, control ok)
    or None where GTK cannot be loaded."""
    import ctypes
    try:
        gtk = ctypes.CDLL("libgtk-3.so.0")
    except OSError:
        return None
    with tempfile.TemporaryDirectory(prefix="malva-gtk-") as td:
        tree.write(Path(td) / TM.THEME)
        TM.link_alias_files(man, Path(td) / TM.THEME, "symlink")
        gtk.gtk_icon_theme_new.restype = ctypes.c_void_p
        gtk.gtk_icon_theme_has_icon.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        gtk.gtk_icon_theme_set_search_path.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_char_p), ctypes.c_int]
        gtk.gtk_icon_theme_set_custom_theme.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        th = gtk.gtk_icon_theme_new()
        gtk.gtk_icon_theme_set_search_path(th, (ctypes.c_char_p * 1)(td.encode()), 1)
        gtk.gtk_icon_theme_set_custom_theme(th, TM.THEME.encode())
        missing = [n for n in names if not gtk.gtk_icon_theme_has_icon(th, n.encode())]
        control = not gtk.gtk_icon_theme_has_icon(th, b"no-such-icon-name-for-the-control")
    return missing, control


def check_gtk(tree: Tree, man: dict):
    names = sorted({p.rsplit("/", 1)[1][:-4] for p in view_of(tree, man) if not p.startswith("small/")})
    r = gtk_has_icon(tree, man, names)
    if r is None:
        return [flag("lookup:gtk-3-agrees-NOT-RUN-libgtk-3-not-installed", True, "")]
    missing, control = r
    return [flag("lookup:gtk-3-finds-every-name-in-the-installed-theme", not missing and control,
                 f"{len(names)} names" if not missing else f"{len(missing)} missing: " + ", ".join(missing[:5]))]


# ---------------------------------------------------------------------------------------------------------- svg
def svg_report(text: str):
    """(problems, ids, refs) for one file."""
    probs = []
    if re.search(r"<!(DOCTYPE|ENTITY)", text):
        probs.append("DOCTYPE or ENTITY")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        return [f"not well-formed XML ({e})"], [], []
    if root.tag != f"{{{SVG_NS}}}svg":
        probs.append("root is not an svg in the SVG namespace")
    vb = root.attrib.get("viewBox", "").split()
    try:
        w, h = float(vb[2]), float(vb[3])
        if len(vb) != 4 or w <= 0 or w != h:
            probs.append(f"viewBox {' '.join(vb)} is not a square")
    except (IndexError, ValueError):
        probs.append("no usable viewBox")
    ids, refs = [], []
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag not in ALLOWED_TAGS:
            probs.append(f"<{tag}> is not allowed")
        for k, v in el.attrib.items():
            k = k.split("}")[-1]
            if k in BAD_ATTRS or k.startswith("on"):
                probs.append(f"attribute {k}")
            if re.search(r"(data:|https?:|javascript:)", v):
                probs.append(f"{k} carries a URL")
            if k == "id":
                ids.append(v)
            refs += re.findall(r"url\(#([^)]+)\)", v)
            if re.search(r"\b(nan|inf)\b", v, re.I):
                probs.append("a non-number")
    return probs, ids, refs


def budget(rec: dict) -> int:
    fam, var = rec["family"], rec["variant"]
    if var.startswith("symbolic") and fam in ("object", "app"):
        return T["bytes_cut"]
    return {"glyph": T["bytes_glyph"], "tile": T["bytes_tile"], "object": T["bytes_object"], "app": T["bytes_app"]}[fam] if not (fam == "tile" and var.startswith("symbolic")) else T["bytes_glyph"]


def check_svgs(tree: Tree):
    man = tree.manifest()
    recs = {i["file"]: i for i in man["icons"]}
    agg = Agg()
    all_ids = {}
    for p in tree.svgs():
        text = tree.text(p)
        probs, ids, refs = svg_report(text)
        rec = recs.get(p)
        res = [flag("svg:well-formed-square-viewBox-only-allowed-elements-no-links", not probs, "; ".join(probs[:3])),
               flag("svg:ids-unique-inside-the-file", len(ids) == len(set(ids)), ""),
               flag("svg:every-url(#id)-resolves", all(r in set(ids) for r in refs), ", ".join(sorted({r for r in refs if r not in set(ids)})[:3]))]
        if rec:
            res.append(num("svg:bytes-within-the-family-budget", len(text.encode()), None, budget(rec), fmt=".0f"))
        agg.add(p.rsplit("/", 1)[1][:-4] + f" [{p.split('/')[0]}]", res)
        for i in ids:
            all_ids.setdefault(i, []).append(p)
    clash = sorted(f"{i} in {len(ps)} files" for i, ps in all_ids.items() if len(set(ps)) > 1)
    lines, failed = agg.lines("files")
    extra = [flag("svg:ids-unique-across-the-whole-theme", not clash, "; ".join(clash[:4]) or f"{len(all_ids)} ids"),
             num("svg:whole-theme-size-in-bytes", sum(len(b) for p, b in tree.files.items() if p.endswith(".svg")), None, T["bytes_total"], fmt=".0f")]
    return lines, extra


# ---------------------------------------------------------------------------------------------------------- rendering
def _px(R, svgs, size, color="#000000"):
    return R.render(svgs, size, color=color) if svgs else []


def render_checks(R, items, glyph_ring=True):
    """items: [(rec, svg text)]. Pixel checks on the written files."""
    agg = Agg()
    svgs = [s for _r, s in items]
    a16, a64 = _px(R, svgs, 16), _px(R, svgs, 64)
    sym = [i for i, (r, _s) in enumerate(items) if r["variant"].startswith("symbolic")]
    col = [i for i, (r, _s) in enumerate(items) if r["variant"] in ("colour", "small")]
    c1, c2 = "#FF00FF", "#00A050"
    s48 = {c: _px(R, [svgs[i] for i in sym], 48, c) for c in (c1, c2)}
    k48 = {c: _px(R, [svgs[i] for i in col], 48, c) for c in (c1, c2)}
    ring = _px(R, [svgs[i] for i in sym], 96)
    for k, (r, s) in enumerate(items):
        nm = r["name"] + f" [{r['file'].split('/')[0]}]"
        ink16 = float((a16[k][..., 3] > 20).mean())
        agg.add(nm, [num("render:ink-at-16px-share(min)", ink16, T["ink16_min"], None, fmt=".3f", label=f"render:draws-at-16-px(ink share>={T['ink16_min']})"),
                     flag("render:draws-at-64-px", bool((a64[k][..., 3] > 20).any()), "")])
    for j, i in enumerate(sym):
        r = items[i][0]
        nm = r["name"] + f" [{r['file'].split('/')[0]}]"
        a, b = s48[c1][j].astype(int), s48[c2][j].astype(int)
        alpha_same = int(np.abs(a[..., 3] - b[..., 3]).max())
        solid = a[..., 3] >= 200
        want_a = np.array([255, 0, 255]); want_b = np.array([0, 160, 80])
        dev = max(int(np.abs(a[..., :3][solid] - want_a).max()) if solid.any() else 0,
                  int(np.abs(b[..., :3][b[..., 3] >= 200] - want_b).max()) if (b[..., 3] >= 200).any() else 0)
        edge = max(int(ring[j][..., 3][0].max()), int(ring[j][..., 3][-1].max()), int(ring[j][..., 3][:, 0].max()), int(ring[j][..., 3][:, -1].max()))
        agg.add(nm, [num("render:symbolic-pixels-are-the-text-colour(levels off)", dev, None, T["colour_tol"], fmt=".0f"),
                     num("render:symbolic-shape-does-not-depend-on-the-colour(levels)", alpha_same, None, 1, fmt=".0f")])
        if glyph_ring:
            agg.add(nm, [num("render:symbolic-ink-clear-of-the-canvas-edge(alpha)", edge, None, T["ring_max"], fmt=".0f")])
    for j, i in enumerate(col):
        r = items[i][0]
        nm = r["name"] + f" [{r['file'].split('/')[0]}]"
        d = int(np.abs(k48[c1][j].astype(int) - k48[c2][j].astype(int)).max())
        agg.add(nm, [num("render:colour-icons-ignore-the-text-colour(levels)", d, None, 1, fmt=".0f")])
    return agg


def mirror_checks(R, tree: Tree):
    man = tree.manifest()
    rec = {i["name"]: i for i in man["icons"] if i["variant"] != "small"}
    pairs = [(n, n[:-4]) for n in rec if n.endswith("-symbolic-rtl") and n[:-4] in rec]
    if not pairs:
        return [flag("render:rtl-files-are-the-mirror-image-of-their-originals", True, "no mirrored files")]
    a = _px(R, [tree.text(rec[n[1]]["file"]) for n in pairs], 48)
    b = _px(R, [tree.text(rec[n[0]]["file"]) for n in pairs], 48)
    bad, lo = [], 1.0
    for (rn, on), x, y in zip(pairs, a, b):
        m1, m2 = x[..., 3][:, ::-1] > 20, y[..., 3] > 20
        iou = (m1 & m2).sum() / max((m1 | m2).sum(), 1)
        lo = min(lo, iou)
        if iou < T["rtl_iou_min"]:
            bad.append(f"{rn} {iou:.3f}")
    return [flag("render:rtl-files-are-the-mirror-image-of-their-originals", not bad, f"{len(pairs)} pairs, lowest IoU {lo:.4f}" if not bad else "; ".join(bad[:4]))]


def xrender_checks(R, items):
    import rsvg_render as RR
    if not RR.available():
        return None
    svgs = [s for _r, s in items]
    ch = _px(R, svgs, XR_SIZE, "#7A3C6E")
    agg = Agg()
    for (r, s), c in zip(items, ch):
        try:
            l = RR.render(s, XR_SIZE, css="svg{color:#7A3C6E}")
        except Exception as e:                                     # noqa: BLE001
            agg.add(r["name"], [flag("xrender:librsvg-draws-it", False, str(e)[:60])])
            continue
        a1, a2 = c[..., 3] > 20, l[..., 3] > 20
        iou = float((a1 & a2).sum() / max((a1 | a2).sum(), 1))
        da = float(np.abs(c[..., 3].astype(float) - l[..., 3].astype(float)).mean() / 255)
        agg.add(r["name"] + f" [{r['file'].split('/')[0]}]",
                [num("xrender:librsvg-outline-overlap", iou, T["xr_iou_min"], None, fmt=".3f", label=f"xrender:librsvg-outline-matches-chromium(IoU>={T['xr_iou_min']})"),
                 num("xrender:librsvg-alpha-difference", da, None, T["xr_alpha_max"], fmt=".4f", label=f"xrender:librsvg-alpha-matches-chromium(mean diff<={T['xr_alpha_max']})")])
    return agg


def gtk_recolour_measure(R, items):
    """Not a pass/fail check: how many symbolic files keep their shape when GTK recolours them. GTK injects a style
    rule `rect,circle,path { fill: <colour> !important }`; a stroke drawing then fills its open paths."""
    import rsvg_render as RR
    if not RR.available():
        return None
    out = {}
    for r, s in items:
        if r["variant"] not in ("symbolic", "symbolic-rtl"):
            continue
        a = RR.render(s, 64, css="svg{color:#7A3C6E}")[..., 3] > 20
        b = RR.render(s, 64, css=RR.GTK_SYMBOLIC_CSS((122, 60, 110)))[..., 3] > 20
        iou = (a & b).sum() / max((a | b).sum(), 1)
        k = out.setdefault(r["family"], [0, 0])
        k[0] += 1
        k[1] += 1 if iou < 0.9 else 0
    return out


# ---------------------------------------------------------------------------------------------------------- run
def run(theme: Path = TM.OUT, report_path=None, negative=True):
    tree = Tree.load(theme)
    man = tree.manifest()
    rep = Report()
    with Renderer() as R:
        m = TM.build_model(R, small_cuts=man.get("small_cuts", False))
        m2 = TM.build_model(R, small_cuts=man.get("small_cuts", False))
        rep.add("tree", check_tree(tree))
        rep.add("manifest", check_manifest(tree, m))
        rep.add("build", check_build(tree, m, m2))
        rep.add("index", check_index(tree))
        rep.add("names", check_names(tree))
        import check_glyphs
        rep.add("coverage", check_coverage(tree, check_glyphs.load_required(), m))
        rep.add("lookup", check_lookup(tree, man))
        rep.add("lookup", check_gtk(tree, man))
        lines, extra = check_svgs(tree)
        rep.extend(lines)
        rep.add("svg", extra)
        items = [(r, tree.text(r["file"])) for r in man["icons"]]
        lines, _ = render_checks(R, items).lines("files")
        rep.extend(lines)
        rep.add("render", mirror_checks(R, tree))
        xr = xrender_checks(R, items)
        if xr is None:
            rep.add("xrender", [flag("xrender:librsvg-agrees-NOT-RUN-librsvg-not-installed", True, "")])
        else:
            rep.extend(xr.lines("files")[0])
        info = []
        gm = gtk_recolour_measure(R, items)
        if gm:
            info.append("GTK recolouring (a style rule that sets fill on every path): symbolic files whose shape changes: " +
                        ", ".join(f"{fam} {bad} of {n}" for fam, (n, bad) in sorted(gm.items())))
        neg = negative_tests(R, tree, m) if negative else []
    text = finish(rep, neg, f"theme {theme.name}: {len(man['icons'])} files, {len(man['aliases'])} alias names", report_path)
    if info:
        text += "\nmeasurements (not pass or fail)\n" + "\n".join(info) + "\n"
        if report_path:
            Path(report_path).write_text(text)
    return rep, neg, text


# ---------------------------------------------------------------------------------------------------------- negative tests
def _drop(tree: Tree, path: str, manifest_too=True) -> Tree:
    t = tree.copy()
    del t.files[path]
    if manifest_too:
        man = t.manifest()
        man["icons"] = [i for i in man["icons"] if i["file"] != path]
        t.files["manifest.json"] = (json.dumps(man, indent=1) + "\n").encode()
    return t


def _edit(tree: Tree, path: str, fn) -> Tree:
    t = tree.copy()
    t.files[path] = fn(t.text(path)).encode()
    return t


def _first(tree: Tree, pred):
    return next(i for i in tree.manifest()["icons"] if pred(i))


def negative_tests(R, tree: Tree, m: TM.Model):
    out = []

    def case(label, ok, info=""):
        out.append((label, bool(ok), info))

    man = tree.manifest()
    glyph = _first(tree, lambda i: i["family"] == "glyph" and i["variant"] == "symbolic")
    colour = _first(tree, lambda i: i["family"] == "app" and i["variant"] == "colour")
    rtl = _first(tree, lambda i: i["variant"] == "symbolic-rtl")

    t = tree.copy(); t.files["scalable/apps/files-64.png"] = b"\x89PNG"
    case("a PNG in the tree is rejected", fails(check_tree(t), "tree:only-svg")[0])
    t = tree.copy(); t.links["scalable/places/x.svg"] = "folder.svg"
    case("a symlink in the shipped tree is rejected", fails(check_tree(t), "tree:no-symlinks")[0])
    t = _drop(tree, glyph["file"], manifest_too=False)
    case("a file missing from the tree but listed in the manifest is rejected", fails(check_manifest(t, m), "manifest:lists")[0])
    t = tree.copy(); t.files["scalable/apps/stray.svg"] = tree.files[colour["file"]]
    case("a file that the manifest does not list is rejected", fails(check_manifest(t, m), "manifest:lists")[0])
    t = _edit(tree, colour["file"], lambda s: s.replace("<path", "<path data-x='1'", 1))
    r = check_manifest(t, m) + check_build(t, m, None)
    case("a file edited by hand is rejected (hash and generator)", fails(r, "manifest:sizes")[0] and fails(r, "build:every-file")[0],
         fails(r, "build:every-file")[1])
    t = tree.copy(); man2 = t.manifest(); man2["icons"][0]["label"] = "tampered"
    t.files["manifest.json"] = (json.dumps(man2, indent=1) + "\n").encode()
    case("a manifest record changed by hand is rejected", fails(check_manifest(t, m), "manifest:is-what")[0])

    head, dirs, secs = parse_index(tree.text("index.theme"))
    t = _edit(tree, "index.theme", lambda s: re.sub(r"(Directories=)[^,\n]+,", r"\1", s, count=1))
    case("a directory missing from Directories is rejected", fails(check_index(t), "index:directories-are")[0])
    t = _edit(tree, "index.theme", lambda s: s.replace("Type=Scalable\n", "", 1))
    case("a directory without Type is rejected", fails(check_index(t), "index:every-directory")[0])
    t = _edit(tree, "index.theme", lambda s: s.replace("MaxSize=1024", "MaxSize=100", 1))
    case("a size range that stops short of 512 px is rejected", fails(check_lookup(t, man), "lookup:every-find")[0])
    t = _edit(tree, "index.theme", lambda s: s.replace("Name=Malva", "Name=Other", 1))
    case("a wrong theme name is rejected", fails(check_index(t), "index:name")[0])

    t = tree.copy(); t.files["symbolic/ui/" + glyph["file"].rsplit("/", 1)[1]] = tree.files[glyph["file"]]
    case("one name in two folders is rejected", fails(check_names(t), "names:one-file-per-name")[0])
    t = tree.copy(); m3 = t.manifest(); m3["aliases"].append({"name": "x-alias", "target": "no-such-file", "variant": "colour", "family": "app"})
    t.files["manifest.json"] = (json.dumps(m3, indent=1) + "\n").encode()
    case("an alias that points at nothing is rejected", fails(check_names(t), "names:aliases")[0])
    t = tree.copy(); m3 = t.manifest(); m3["aliases"].append({"name": "x2", "target": m3["aliases"][0]["name"], "variant": "colour", "family": "app"})
    t.files["manifest.json"] = (json.dumps(m3, indent=1) + "\n").encode()
    case("an alias of an alias is rejected", fails(check_names(t), "names:aliases")[0])
    t = tree.copy(); m3 = t.manifest(); m3["aliases"].append({"name": colour["name"], "target": colour["name"], "variant": "colour", "family": "app"})
    t.files["manifest.json"] = (json.dumps(m3, indent=1) + "\n").encode()
    case("an alias that shadows a real file is rejected", fails(check_names(t), "names:aliases")[0])
    t = _drop(tree, rtl["file"].replace("-rtl.svg", ".svg"))
    case("a mirrored file whose original is gone is rejected", fails(check_names(t), "names:every-rtl")[0])
    sample = rtl["file"].replace("-rtl.svg", ".svg")
    t = tree.copy(); t.files[rtl["file"]] = tree.files[sample]
    case("a mirrored file that is not mirrored is rejected", fails(mirror_checks(R, t), "render:rtl")[0])

    req = __import__("check_glyphs").load_required()
    bat = _first(tree, lambda i: i["name"] == "battery-level-50-symbolic")
    t = _drop(tree, bat["file"])
    case("a name on the reference list that is not served is rejected", fails(check_coverage(t, req, None), "coverage:every-name")[0])

    t = _edit(tree, colour["file"], lambda s: s.replace("<defs>", '<defs><image href="data:image/png;base64,AAAA"/>', 1))
    case("an SVG with an embedded raster is rejected", check_svgs(t)[0] and any("FAIL" in l[0] for l in check_svgs(t)[0]))
    t = _edit(tree, glyph["file"], lambda s: s[:-12])
    case("a truncated SVG is rejected", any("FAIL" in l[0] for l in check_svgs(t)[0]))
    t = _edit(tree, colour["file"], lambda s: s.replace("<defs>", "<defs><text>x</text>", 1))
    case("an SVG with text in it is rejected", any("FAIL" in l[0] for l in check_svgs(t)[0]))
    t = _edit(tree, glyph["file"], lambda s: s.replace('d="', 'fill="url(#nowhere)" d="', 1))
    case("a url(#id) that resolves to nothing is rejected", any("FAIL" in l[0] for l in check_svgs(t)[0]))
    other = _first(tree, lambda i: i["family"] == "tile" and i["variant"] == "colour")
    ida = re.search(r' id="([^"]+)"', tree.text(colour["file"])).group(1)
    t = _edit(tree, other["file"], lambda s: s.replace("<defs>", f'<defs><linearGradient id="{ida}"/>', 1))
    case("an id used by two files is rejected", fails(check_svgs(t)[1], "svg:ids-unique-across")[0])
    t = _edit(tree, glyph["file"], lambda s: s.replace("</svg>", "<path d=\"M0 0" + "L1 1" * 900 + "\"/></svg>"))
    case("a glyph over its size budget is rejected", any("FAIL" in l[0] for l in check_svgs(t)[0]))
    t = tree.copy(); t.files["scalable/apps/big.svg"] = b"<svg>" + b" " * 2_000_000 + b"</svg>"
    case("a theme over its size budget is rejected", fails(check_svgs(t)[1], "svg:whole-theme")[0])

    def mk(svg, rec):
        return [(dict(rec), svg)]

    def breaks(svg, rec):
        """Does at least one pixel check fail for this one file?"""
        return any(not ok for _t, ok in render_checks(R, mk(svg, rec)).lines("x")[0])

    own = tree.text(glyph["file"]).replace('stroke="currentColor"', 'stroke="#FF0000"', 1)
    case("a symbolic file with a colour of its own is rejected", breaks(own, glyph))
    leak = tree.text(colour["file"]).replace("</svg>", '<rect x="400" y="400" width="200" height="200" fill="currentColor"/></svg>')
    case("a full-colour file that follows the text colour is rejected", breaks(leak, colour))
    blank = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"></svg>'
    case("a blank file is rejected", breaks(blank, glyph))
    edge = tree.text(glyph["file"]).replace('<path', '<path transform="translate(-12 0)"', 1)
    case("a symbolic glyph that touches the canvas edge is rejected", breaks(edge, glyph))

    # the cross-engine check must bite: pair each of two different icons with the other's picture
    import rsvg_render as RR
    if RR.available():
        a_rec = _first(tree, lambda i: i["name"] == "go-next-symbolic")
        b_rec = _first(tree, lambda i: i["name"] == "edit-find-symbolic")
        a_svg, b_svg = tree.text(a_rec["file"]), tree.text(b_rec["file"])
        ca = _px(R, [a_svg], XR_SIZE, "#7A3C6E")[0]
        lb = RR.render(b_svg, XR_SIZE, css="svg{color:#7A3C6E}")
        m1, m2 = ca[..., 3] > 20, lb[..., 3] > 20
        iou = float((m1 & m2).sum() / max((m1 | m2).sum(), 1))
        case("two different drawings fail the librsvg-against-Chromium comparison", iou < T["xr_iou_min"], f"IoU {iou:.2f}")
    # GTK's own lookup must notice a missing file
    r = gtk_has_icon(_drop(tree, colour["file"]), man, [colour["name"]])
    if r is not None:
        case("GTK's lookup notices a file that is gone", bool(r[0]))
    else:
        case("GTK's lookup notices a file that is gone (NOT RUN: libgtk-3 not installed)", True)
    # a build that changes between runs must be noticed
    from dataclasses import replace
    m4 = TM.Model(m.small_cuts)
    m4.entries = [replace(e, svg=e.svg + " ") if k == 0 else e for k, e in enumerate(m.entries)]
    m4.smalls, m4.aliases = list(m.smalls), list(m.aliases)
    case("two builds that differ by a byte are noticed", m.digest() != m4.digest())
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", type=Path, default=TM.OUT)
    ap.add_argument("--report", type=Path, default=None)
    ap.add_argument("--no-negative", action="store_true")
    a = ap.parse_args(argv)
    rep, neg, text = run(a.theme, a.report, negative=not a.no_negative)
    print(text if a.report is None else text.split("\n", 1)[0])
    if a.report:
        print("report:", a.report)
    sys.exit(1 if rep.failed or any(not ok for _n, ok, _i in neg) else 0)


if __name__ == "__main__":
    main()
