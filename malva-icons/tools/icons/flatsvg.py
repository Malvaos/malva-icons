"""Make a one-colour SVG safe for GTK's symbolic recolouring: no strokes, no masks, only filled shapes.

GTK forces `fill` onto every rect, circle and path of a symbolic icon (a style rule with !important) and knows nothing
else: a stroke keeps its own colour, and the white rectangle inside a <mask> takes the text colour too. So

  * every stroke becomes the filled outline of that stroke (svgstroke.py), in the element's own coordinates, so its
    transform stays as it was;
  * every <mask> that cuts holes becomes holes in the shapes it cut: the cut shapes are appended to the shape's path,
    which is then filled even-odd. That is exact when a cut lies wholly inside the shape or wholly outside it, which
    is what these icons do; any other case raises Unsupported and the caller keeps the masked drawing.

The caller compares the result with the original by rendering both (theme_model does, and check_theme repeats it).
"""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET

import numpy as np

import svgpath as sp
import svgstroke as ss

NS = "http://www.w3.org/2000/svg"
Q = lambda t: f"{{{NS}}}{t}"
ET.register_namespace("", NS)
IDENT = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


class Unsupported(Exception):
    pass


# ----------------------------------------------------------------------------- transforms
def _mul(m1, m2):
    """m1 after m2 (apply m2 first): the SVG matrix (a b c d e f) product."""
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (a1 * a2 + c1 * b2, b1 * a2 + d1 * b2, a1 * c2 + c1 * d2, b1 * c2 + d1 * d2,
            a1 * e2 + c1 * f2 + e1, b1 * e2 + d1 * f2 + f1)


def parse_transform(s: str | None):
    m = IDENT
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", s or ""):
        v = [float(x) for x in re.split(r"[\s,]+", args.strip()) if x]
        if name == "translate":
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0.0)
        elif name == "scale":
            t = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == "rotate":
            a = math.radians(v[0])
            r = (math.cos(a), math.sin(a), -math.sin(a), math.cos(a), 0, 0)
            t = r if len(v) < 3 else _mul(_mul((1, 0, 0, 1, v[1], v[2]), r), (1, 0, 0, 1, -v[1], -v[2]))
        elif name == "matrix":
            t = tuple(v)
        else:
            raise Unsupported(f"transform {name}")
        m = _mul(m, t)
    return m


def baked(el, matrix=IDENT):
    """The subpaths of a path element in the coordinates of its parent, its own transform applied."""
    m = _mul(matrix, parse_transform(el.get("transform")))
    subs = sp.parse(el.get("d", ""))
    return sp.transform(subs, m) if m != IDENT else subs


# ----------------------------------------------------------------------------- geometry
def _winding(polys, pts):
    """Non-zero winding number of each point against closed polygons."""
    P = np.asarray(pts, float)
    w = np.zeros(len(P), int)
    for _closed, poly in polys:
        if len(poly) < 3:
            continue
        a = np.asarray(poly, float)
        b = np.roll(a, -1, axis=0)
        ya, yb = a[:, 1][None, :], b[:, 1][None, :]
        xa, xb = a[:, 0][None, :], b[:, 0][None, :]
        py, px = P[:, 1][:, None], P[:, 0][:, None]
        left = (xb - xa) * (py - ya) - (px - xa) * (yb - ya)
        up = (ya <= py) & (yb > py) & (left > 0)
        down = (ya > py) & (yb <= py) & (left < 0)
        w += up.sum(1) - down.sum(1)
    return w


def _inside(polys, pts):
    return _winding(polys, pts) != 0


def _samples(poly, n=3):
    """Points of a flattened polygon: its vertices and the midpoints of its edges."""
    pts = list(poly)
    mids = [((pts[i][0] + pts[(i + 1) % len(pts)][0]) / 2, (pts[i][1] + pts[(i + 1) % len(pts)][1]) / 2) for i in range(len(pts))]
    return pts + mids


def relation(shape_subs, cut_sub, tol):
    """'inside' | 'outside' | 'partial': how one closed cut subpath lies against the filled region of a shape."""
    sp_polys = [(c, p) for c, p in sp.flatten(shape_subs, tol)]
    cp = sp.flatten([cut_sub], tol)[0][1]
    ins = _inside(sp_polys, _samples(cp))
    if ins.all():
        # the shape's own outline must not run through the cut: none of its vertices may be inside the cut
        verts = [p for _c, poly in sp_polys for p in poly]
        if verts and _inside([(True, cp)], verts).any():
            return "partial"
        return "inside"
    if not ins.any():
        verts = [p for _c, poly in sp_polys for p in poly]
        if verts and _inside([(True, cp)], verts).any():
            return "partial"
        return "outside"
    return "partial"


# ----------------------------------------------------------------------------- strokes
def _fmt_d(subs, prec):
    return sp.emit_compact(subs, prec)


def convert_strokes(root, prec=1, tol=0.08):
    """Replace every stroked path by filled paths: the stroke's outline, and the fill if there was one."""
    parent = {c: p for p in root.iter() for c in p}
    for el in list(root.iter(Q("path"))):
        stroke = el.get("stroke")
        if not stroke or stroke == "none":
            continue
        w = float(el.get("stroke-width", "1"))
        subs = sp.parse(el.get("d", ""))
        if el.get("stroke-linecap", "butt") != "round" and any(not s.closed for s in subs):
            raise Unsupported("an open stroke with butt caps")
        if el.get("stroke-linejoin", "miter") != "round":
            raise Unsupported("a stroke that is not round-joined")
        outline = ET.Element(Q("path"))
        outline.set("d", _fmt_d(ss.stroke_outline(subs, w / 2, tol), prec))
        outline.set("fill", stroke)
        if el.get("transform"):
            outline.set("transform", el.get("transform"))
        if el.get("opacity"):
            outline.set("opacity", el.get("opacity"))
        outline.set("data-outline", "1")
        fill = el.get("fill", "black")
        par = parent[el]
        idx = list(par).index(el)
        pieces = []
        if fill != "none":
            fp = ET.Element(Q("path"))
            for k, v in el.attrib.items():
                if not k.startswith("stroke"):
                    fp.set(k, v)
            pieces.append(fp)
        pieces.append(outline)
        par.remove(el)
        for j, pc in enumerate(pieces):
            par.insert(idx + j, pc)


# ----------------------------------------------------------------------------- masks
def _leaf_paths(el):
    for c in el.iter():
        if c.tag == Q("path"):
            yield c


def apply_cuts(root, tol=0.08, prec=1):
    masks = {m.get("id"): m for m in root.iter(Q("mask"))}
    for g in list(root.iter(Q("g"))):
        ref = g.get("mask")
        if not ref:
            continue
        mid = re.search(r"url\(#([^)]+)\)", ref).group(1)
        mask = masks[mid]
        cuts = []
        for c in mask:
            if c.tag == Q("rect"):
                continue
            if c.tag != Q("path") or c.get("fill") in (None, "none"):
                raise Unsupported("a mask shape that is not a filled path")
            cuts += [s for s in baked(c) if s.segs]
        if not cuts:
            raise Unsupported("an empty mask")
        for t in _leaf_paths(g):
            tsubs = baked(t)
            add = []
            for c in cuts:
                rel = relation(tsubs, c, tol)
                if rel == "partial":
                    raise Unsupported("a cut that crosses the edge of a shape")
                if rel == "inside":
                    add.append(c)
            if add:
                if t.get("data-outline") and len(tsubs) > 1:
                    raise Unsupported("a cut inside a stroke outline")
                t.set("d", _fmt_d(tsubs + add, prec))
                if t.get("transform"):
                    del t.attrib["transform"]
                t.set("fill-rule", "evenodd")
        del g.attrib["mask"]
    for d in root.iter(Q("defs")):
        for m in [m for m in d if m.tag == Q("mask")]:
            d.remove(m)
    for par in list(root.iter()):
        for d in [c for c in par if c.tag == Q("defs") and len(c) == 0]:
            par.remove(d)


def _unwrap(root):
    """A <g> with no attributes only groups: let its children stand in its place."""
    changed = True
    while changed:
        changed = False
        for par in list(root.iter()):
            for g in [c for c in par if c.tag == Q("g") and not c.attrib]:
                i = list(par).index(g)
                par.remove(g)
                for j, c in enumerate(list(g)):
                    par.insert(i + j, c)
                changed = True


def flatten_svg(svg: str, prec: int = 1, tol: float = 0.08) -> str:
    """The same one-colour drawing as filled shapes only. Raises Unsupported where that cannot be done exactly."""
    root = ET.fromstring(svg)
    convert_strokes(root, prec, tol)
    apply_cuts(root, tol, prec)
    for el in root.iter(Q("path")):
        if el.get("data-outline"):
            del el.attrib["data-outline"]
        elif el.get("d"):
            try:
                el.set("d", _fmt_d(sp.parse(el.get("d")), prec))
            except ValueError:
                pass
    _unwrap(root)
    out = ET.tostring(root, encoding="unicode")
    return re.sub(r"\s*/>", "/>", out)
