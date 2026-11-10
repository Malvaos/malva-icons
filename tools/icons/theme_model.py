"""The Malva icon theme as data: every file it ships, every alias name, and the index.theme that describes them.

The theme is SVG only. One file per icon serves every size: a rasteriser is given the size, the drawing never changes
with it. PNGs are never shipped; export_png.py makes any size on demand.

  scalable/<context>/<name>.svg             full colour: apps, Settings tiles, folders, drives, files, people
  symbolic/<context>/<name>-symbolic.svg    one colour (currentColor): the panel, toolbar and menu glyphs, and one-colour cuts
  symbolic/<context>/<name>-symbolic-rtl.svg   the mirrored drawing, where mirroring is right (arrows, lists, sliders)
  small/<context>/<name>.svg                OPTIONAL (build_theme.py --small-cuts): a heavier drawing for 16-32 px

A drawing is stored once, under one canonical name. The other names that mean the same picture (a CD, a DVD and a
Blu-ray are all "a disc") are aliases: install_theme.py links each one to its file, manifest.json lists them all.

Which source wins when two want one name: the glyph kit wins every `-symbolic` name (stroke drawings made for panels),
the objects' and apps' own one-colour cuts fill the names the kit does not have.
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import glyphs_all                                    # noqa: F401  registers the symbolic kit
import glyphkit as K
import objects as O
import apps
import tiles as T
import theme_aliases as TA
from objfmt import object_svg, symbolic_svg, fit_viewbox

THEME = "Malva"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets/icons" / THEME

# the directory ("context") an object family is filed under
OBJECT_CTX = {"folders": "places", "storage": "devices", "files": "mimetypes", "people": "status"}
CTX_NAME = {"actions": "Actions", "apps": "Applications", "categories": "Categories", "devices": "Devices",
            "emblems": "Emblems", "legacy": "Legacy", "mimetypes": "MimeTypes", "places": "Places",
            "status": "Status", "ui": "UI"}
# numbered portraits are pictures, not glyphs: they have no one-colour cut in the theme
NO_SYMBOLIC = ("avatar-",)

# index.theme sizes. Every directory is Type=Scalable: the range says what it may be scaled to.
FULL = dict(Size=128, MinSize=8, MaxSize=1024)
SYMBOLIC = dict(Size=16, MinSize=8, MaxSize=512)          # as Adwaita's symbolic directories
SMALL = dict(Size=24, MinSize=16, MaxSize=32)

SMALL_FAMILIES = ("app", "object")                        # the families that have a lighter drawing for 16-32 px


@dataclass(frozen=True)
class Entry:
    path: str                    # relative to the theme root, "/" separators
    name: str                    # the icon-theme name: the file stem
    variant: str                 # colour | symbolic | symbolic-rtl | small
    ctx: str
    family: str                  # glyph | tile | object | app
    source: str                  # id inside its family
    label: str
    svg: str
    meta: tuple = ()             # ((key, value), ...) kept in the manifest

    @property
    def dir(self) -> str:
        return self.path.rsplit("/", 1)[0]

    def sha(self) -> str:
        return hashlib.sha256(self.svg.encode()).hexdigest()


@dataclass(frozen=True)
class Alias:
    name: str                    # another standard name for the drawing
    target: str                  # the canonical Entry.name it is served by (never another alias)
    variant: str                 # colour | symbolic | symbolic-rtl
    family: str


class Model:
    def __init__(self, small_cuts: bool = False):
        self.small_cuts = small_cuts
        self.entries: list[Entry] = []
        self.smalls: list[Entry] = []
        self.aliases: list[Alias] = []
        self.by_name: dict[str, Entry] = {}
        self.alias_of: dict[str, Alias] = {}

    # ---- adding
    def taken(self, name: str) -> bool:
        return name in self.by_name or name in self.alias_of

    def add(self, e: Entry):
        if e.variant == "small":
            self.smalls.append(e)
            return
        if self.taken(e.name):
            raise ValueError(f"the name {e.name!r} is used twice (second: {e.family}/{e.source})")
        self.entries.append(e)
        self.by_name[e.name] = e

    def alias(self, a: Alias):
        if self.taken(a.name):
            raise ValueError(f"the alias {a.name!r} is already a name (target {a.target})")
        if a.target not in self.by_name:
            raise ValueError(f"alias {a.name!r} points at {a.target!r}, which is not a file")
        self.aliases.append(a)
        self.alias_of[a.name] = a

    # ---- reading
    def resolve(self, name: str) -> Entry | None:
        if name in self.by_name:
            return self.by_name[name]
        a = self.alias_of.get(name)
        return self.by_name[a.target] if a else None

    def names(self) -> set[str]:
        return set(self.by_name) | set(self.alias_of)

    def symbolic_partner(self, name: str) -> Entry | None:
        """The one-colour drawing that goes with a coloured name, if the theme has one."""
        return self.resolve(name + "-symbolic")

    def dirs(self) -> list[str]:
        """Directories in lookup order: the small cuts first, so a 16-32 px request finds them before the scalable ones."""
        small = sorted({e.dir for e in self.smalls})
        rest = sorted({e.dir for e in self.entries}, key=lambda d: (d.split("/")[0] != "scalable", d))
        return small + rest

    def digest(self) -> str:
        h = hashlib.sha256()
        for e in sorted(self.entries + self.smalls, key=lambda e: e.path):
            h.update(e.path.encode() + b"\0" + e.svg.encode() + b"\0")
        for a in sorted(self.aliases, key=lambda a: a.name):
            h.update(f"{a.name}>{a.target}\0".encode())
        return h.hexdigest()


# ------------------------------------------------------------------------------------------------ the sources
def _add_glyphs(m: Model):
    for g in sorted(K.GLYPHS.values(), key=lambda g: (g.ctx, g.id)):
        base = K.theme_name(g)
        m.add(Entry(f"symbolic/{g.ctx}/{base}.svg", base, "symbolic", g.ctx, "glyph", g.id, g.id, K.svg(g)))
        if g.rtl:
            m.add(Entry(f"symbolic/{g.ctx}/{base}-rtl.svg", base + "-rtl", "symbolic-rtl", g.ctx, "glyph", g.id, g.id,
                        K.svg(g, rtl=True)))
    for g in sorted(K.GLYPHS.values(), key=lambda g: (g.ctx, g.id)):
        base = K.theme_name(g)
        for a in g.alias:
            m.alias(Alias(f"{a}-symbolic", base, "symbolic", "glyph"))
            # a mirrored copy of a name that says which way it points would be a lie: "...-ltr" stays left to right
            if g.rtl and not a.endswith(("-ltr", "-rtl")):
                m.alias(Alias(f"{a}-symbolic-rtl", base + "-rtl", "symbolic-rtl", "glyph"))


def _add_tiles(m: Model):
    for i in T.ORDER:
        sp = T.BY_ID[i]
        m.add(Entry(f"scalable/categories/{i}.svg", i, "colour", "categories", "tile", i, sp.name, T.tile_svg(i),
                    (("group", sp.group or "category"),)))
    # each tile's one-colour partner is the symbol it carries; it is an alias of the kit's drawing wherever the kit has one
    for i in T.ORDER:
        sym = i + "-symbolic"
        if m.taken(sym):
            continue
        sp = T.BY_ID[i]
        if sp.glyph in K.GLYPHS:
            base = K.theme_name(K.GLYPHS[sp.glyph])
            m.alias(Alias(sym, base, "symbolic", "tile"))
            if base + "-rtl" in m.by_name and not m.taken(sym + "-rtl"):
                m.alias(Alias(sym + "-rtl", base + "-rtl", "symbolic-rtl", "tile"))
        else:
            m.add(Entry(f"symbolic/categories/{sym}.svg", sym, "symbolic", "categories", "tile", i, sp.name,
                        K.svg_of(T.EXTRA[sp.glyph])))


def _object_name(o) -> str:
    return o.xdg or o.id


def _add_objects(m: Model, R):
    objs = [O.OBJECTS[i] for i in O.ORDER]
    vbs = {o.id: fit_viewbox(R, o) for o in objs}
    for o in objs:
        ctx, name = OBJECT_CTX[o.group], _object_name(o)
        meta = (("group", o.group), ("template", o.kind), ("emblem", o.emblem), ("id", o.id), ("hue", o.meta.get("hue")))
        m.add(Entry(f"scalable/{ctx}/{name}.svg", name, "colour", ctx, "object", o.id, o.name, object_svg(o), meta))
        if m.small_cuts:
            m.add(Entry(f"small/{ctx}/{name}.svg", name, "small", ctx, "object", o.id, o.name, object_svg(o, small=True), meta))
    for o in objs:
        ctx, name = OBJECT_CTX[o.group], _object_name(o)
        sym = name + "-symbolic"
        if o.id.startswith(NO_SYMBOLIC) or m.taken(sym):
            continue
        m.add(Entry(f"symbolic/{ctx}/{sym}.svg", sym, "symbolic", ctx, "object", o.id, o.name, symbolic_svg(o, vbs[o.id])))


def _add_apps(m: Model, R):
    import build_apps as BA
    for i in apps.ORDER:
        label = "Malva " + apps.NAMES[i] if i != "malva" else "Malva OS"
        m.add(Entry(f"scalable/apps/{i}.svg", i, "colour", "apps", "app", i, label, BA.icon_svg(i)))
        if m.small_cuts:
            m.add(Entry(f"small/apps/{i}.svg", i, "small", "apps", "app", i, label, BA.icon_svg(i, "small", uid=f"{i}-small")))
    for i in apps.ORDER:
        sym = i + "-symbolic"
        if m.taken(sym):
            continue
        label = "Malva " + apps.NAMES[i] if i != "malva" else "Malva OS"
        m.add(Entry(f"symbolic/apps/{sym}.svg", sym, "symbolic", "apps", "app", i, label,
                    BA.icon_svg(i, "symbolic", uid=f"{i}-sym", sym_vb=BA.symbolic_vb(R, i))))


def _add_name_aliases(m: Model):
    """Standard names served by another icon (theme_aliases.py), and the one-colour partner of each where there is one."""
    pairs = [(a, t, "object") for a, t in TA.OBJECT_ALIASES.items()] + [(a, t, "app") for a, t in TA.APP_ALIASES.items()]
    for alias, target, fam in pairs:
        tname = _object_name(O.OBJECTS[target]) if fam == "object" else target
        if tname not in m.by_name:
            raise ValueError(f"alias {alias!r} -> {target!r}: no file named {tname!r}")
        m.alias(Alias(alias, tname, "colour", fam))
        partner = m.symbolic_partner(tname)
        if partner is not None and not m.taken(alias + "-symbolic"):
            m.alias(Alias(alias + "-symbolic", partner.name, "symbolic", fam))


def build_model(R=None, small_cuts: bool = False) -> Model:
    from mi_render import Renderer
    m = Model(small_cuts)
    own = R is None
    if own:
        R = Renderer().__enter__()
    try:
        _add_glyphs(m)
        _add_tiles(m)
        _add_objects(m, R)
        _add_apps(m, R)
        _add_name_aliases(m)
    finally:
        if own:
            R.__exit__(None, None, None)
    return m


# ------------------------------------------------------------------------------------------------ index.theme, manifest
def index_theme(m: Model) -> str:
    kinds = {}
    for e in m.entries + m.smalls:
        kinds[e.dir] = e
    lines = ["[Icon Theme]", f"Name={THEME}",
             "Comment=Malva icons. One scalable SVG per icon serves every size; symbolic glyphs take the text colour.",
             "Inherits=Adwaita,hicolor", "Example=folder", f"Directories={','.join(m.dirs())}", ""]
    for d in m.dirs():
        tier, ctx = d.split("/")
        size = {"scalable": FULL, "symbolic": SYMBOLIC, "small": SMALL}[tier]
        lines += [f"[{d}]", f"Context={CTX_NAME[ctx]}"] + [f"{k}={v}" for k, v in size.items()] + ["Type=Scalable", ""]
    return "\n".join(lines)


def manifest(m: Model) -> dict:
    icons = []
    for e in sorted(m.entries + m.smalls, key=lambda e: e.path):
        rec = {"name": e.name, "variant": e.variant, "family": e.family, "source": e.source, "label": e.label,
               "context": e.ctx, "file": e.path, "bytes": len(e.svg.encode()), "sha256": e.sha()}
        meta = {k: v for k, v in e.meta if v not in (None, "")}
        if meta:
            rec["meta"] = meta
        icons.append(rec)
    return {"theme": THEME, "small_cuts": m.small_cuts,
            "aliases": [{"name": a.name, "target": a.target, "variant": a.variant, "family": a.family}
                        for a in sorted(m.aliases, key=lambda a: a.name)],
            "icons": icons}


def manifest_text(m: Model) -> str:
    return json.dumps(manifest(m), indent=1) + "\n"


def alias_files(man: dict) -> list[tuple[str, str]]:
    """(alias file, target file) for every alias of a manifest, relative to the theme root. An alias sits in its target's
    directory; where the target also has a small cut, the alias has one too."""
    files: dict[str, dict[str, str]] = {}
    for i in man["icons"]:
        files.setdefault(i["name"], {})["small" if i["variant"] == "small" else "main"] = i["file"]
    out = []
    for a in man["aliases"]:
        for tf in files[a["target"]].values():
            out.append((f"{tf.rsplit('/', 1)[0]}/{a['name']}.svg", tf))
    return sorted(out)


def link_alias_files(man: dict, root: Path, how: str = "symlink") -> int:
    """Create every alias of a manifest under `root`: relative symlinks, or copies of the target (how="copy")."""
    import os
    import shutil
    n = 0
    for alias, target in alias_files(man):
        dst = Path(root) / alias
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        if how == "symlink":
            os.symlink(os.path.basename(target), dst)
        else:
            shutil.copyfile(Path(root) / target, dst)
        n += 1
    return n
