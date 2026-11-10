"""Measured checks for the symbolic glyph kit. Everything here reads pixels rendered by Chromium or parses the SVG;
nothing is judged by eye. Every check has a negative test: a deliberately broken glyph that the check has to reject.

Run: python3 tools/icons/check_glyphs.py [--report PATH] [--no-negative] [--measure]

How the numbers were chosen: each threshold sits between what the finished set measures and what the matching
defect measures (both are printed), never at the edge of the set. --measure prints the distributions.
Measurement resolution: layout is read from a 96 px render (a quarter unit per pixel), so the margin limit is the
design rule (1 unit) minus that quarter unit.
"""
from __future__ import annotations

import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import glyphs_all                                        # noqa: F401  registers every glyph
import glyphkit as K
import svgpath as sp
from checkkit import num, flag, Agg, Report, fails, finish
from mi_render import Renderer

SIZES = (16, 24, 48, 96)
VALID_CTX = {"status", "actions", "devices", "places", "mimetypes", "categories", "emblems", "ui", "apps", "emotes", "legacy"}
NAME_RE = re.compile(r"^[a-z0-9]+(?:[-+.][a-z0-9]+)*$")

# --------------------------------------------------------------------------------------------- thresholds
T = dict(
    bytes_max=2400,           # the biggest glyph measures about 1.4 KB; a glyph padded with a comment measures more
    margin_min=0.75,          # units: the design rule is 1.0; the render resolves a quarter unit
    longest_min=13.0, longest_min_ui=9.0, longest_max=22.5,
    centre_max=0.75,          # units: the better of the box centre and the box-mass mean, against the centre of the grid (was 1.25: a whole unit high went unnoticed)
    soft_max=0.10,            # mean "softness" of axis-aligned strokes at 24 px (0 = whole pixels, 1 = every edge half a pixel)
    ink16_min=6.0,            # px of ink at 16 px
    sharp16_min=0.55,         # sum(a^2)/sum(a) at 16 px: 1 = every ink pixel solid, small = smeared grey
    runs16_min=0.55,          # ink runs per scanline at 16 px / at 96 px: 1 = every stroke and gap survives; the closest real glyph measures 0.71
    dup_min=0.03,             # L1 distance / ink between two different glyphs; the deliberate variants measure 0.034 and up, a repeated drawing 0.023 and down
    rtl_tol=0.012, rtl_asym_min=0.01,
    anchor_slack=0.5,         # units: a series member may not reach beyond the full drawing's box by more than this
)
DIRECTIONAL = ("go-previous", "go-next", "go-first", "go-last", "go-jump", "edit-undo", "edit-redo", "edit-clear", "format-indent",
               "format-justify-left", "format-justify-right", "view-sort", "view-list-bullet", "mail-reply", "mail-forward",
               "mail-send-receive", "system-log-out", "system-switch-user", "media-skip", "media-seek", "media-playback-start",
               "document-revert", "document-send", "pan-start", "pan-end", "sidebar-show")


# --------------------------------------------------------------------------------------------- svg parsing
def parse_svg(svg):
    """(root, [(kind, dim, evenodd, subpaths)]) from SVG text; kind S | F | FS."""
    root = ET.fromstring(svg)
    parts = []
    for el in root:
        if el.tag.split("}")[-1] != "path":
            continue
        a = el.attrib
        fill = a.get("fill", root.attrib.get("fill", "none"))
        stroke = a.get("stroke", root.attrib.get("stroke", "none"))
        kind = "FS" if (fill != "none" and stroke != "none") else ("F" if fill != "none" else "S")
        parts.append((kind, a.get("opacity") is not None, a.get("fill-rule") == "evenodd", sp.parse(a["d"])))
    return root, parts


# --------------------------------------------------------------------------------------------- rendering
def render_items(R, items):
    """items: [(key, svg, has_dim_parts_svg_or_None)] -> {key: {size: alpha, 'w48', 'b48', 'nodim16'}}."""
    keys = [k for k, _, _ in items]
    svgs = [s for _, s, _ in items]
    out = {k: {} for k in keys}
    for size in SIZES:
        for k, a in zip(keys, R.render(svgs, size)):
            out[k][size] = a[..., 3].astype(float) / 255
    for k, a in zip(keys, R.render(svgs, 48, color="#ffffff")):
        out[k]["w48"] = a
    for k, a in zip(keys, R.render(svgs, 48, color="#000000")):
        out[k]["b48"] = a
    return out


def bbox(a, thr=0.5):
    ys, xs = np.nonzero(a > thr)
    if not len(xs):
        return None
    k = 24.0 / a.shape[0]
    return xs.min() * k, ys.min() * k, (xs.max() + 1) * k, (ys.max() + 1) * k


def has_dim(gl):
    return any(p.dim for p in gl.parts)


def box_of(gl, a):
    return bbox(a, 0.5 * (K.DIM if has_dim(gl) else 1.0))


# --------------------------------------------------------------------------------------------- per-glyph checks
def check_hygiene(svg):
    try:
        root, parts = parse_svg(svg)
    except Exception as e:                                     # noqa: BLE001
        return [flag("hygiene:parses", False, str(e)[:80])]
    r = [flag("hygiene:parses", True),
         flag("hygiene:viewBox", root.attrib.get("viewBox") == "0 0 24 24", root.attrib.get("viewBox", "none"))]
    want = {"fill": "none", "stroke": "currentColor", "stroke-width": "2", "stroke-linecap": "round", "stroke-linejoin": "round"}
    bad = [k for k, v in want.items() if root.attrib.get(k) != v]
    r.append(flag("hygiene:stroke-rules-2-round", not bad, ",".join(bad)))
    tags = {el.tag.split("}")[-1] for el in root.iter()} - {"svg", "path"}
    r.append(flag("hygiene:only-paths", not tags, ",".join(sorted(tags))))
    colours = re.findall(r"#[0-9a-fA-F]{3,8}\b|rgb\(|hsl\(|url\(", svg)
    r.append(flag("hygiene:no-colour-but-currentColor", not colours, ",".join(colours)))
    extra = set()
    for el in root.iter():
        if el.tag.split("}")[-1] == "path":
            extra |= set(el.attrib) - {"d", "fill", "stroke", "fill-rule", "opacity"}
    r.append(flag("hygiene:path-attributes", not extra, ",".join(sorted(extra))))
    ops = {el.attrib["opacity"] for el in root.iter() if el.tag.split("}")[-1] == "path" and "opacity" in el.attrib}
    r.append(flag("hygiene:dim-is-35-percent", ops <= {"0.35", ".35"}, ",".join(sorted(ops))))
    r.append(num("hygiene:size-bytes", len(svg.encode()), None, T["bytes_max"], fmt=".0f"))
    return r


def mass_centre(a):
    k = 24.0 / a.shape[0]
    s = a.sum()
    return ((a * np.arange(a.shape[1])[None, :]).sum() / s + 0.5) * k, ((a * np.arange(a.shape[0])[:, None]).sum() / s + 0.5) * k


def check_layout(gl, rd, centre=True):
    b = box_of(gl, rd[96])
    if b is None:
        return [flag("layout:has-ink", False)]
    x0, y0, x1, y1 = b
    longest = max(x1 - x0, y1 - y0)
    mx, my = mass_centre(rd[96])
    # centred by its box, or halfway between its box and its mass: a window by its box, a play triangle (mass on the
    # middle, box to the right of it) and an arrow over a sun (one high, one low) by the mean
    off = min(math.hypot((x0 + x1) / 2 - 12, (y0 + y1) / 2 - 12), math.hypot((x0 + x1) / 4 + mx / 2 - 12, (y0 + y1) / 4 + my / 2 - 12))
    lo = T["longest_min_ui"] if gl.ctx == "ui" else T["longest_min"]
    out = [num("layout:ink-inside-the-1-unit-margin", min(x0, y0, 24 - x1, 24 - y1), T["margin_min"], None, fmt=".2f"),
           num("layout:longest-side-units", longest, lo, T["longest_max"], fmt=".1f")]
    if centre and "anchored" not in gl.tags.split():
        out.append(num("layout:centred-by-box-or-mean-units", off, None, T["centre_max"], fmt=".2f"))
    return out


def _segments(parts):
    """Every stroked segment, flattened: (place, polyline, dim, segment); place = (part, subpath, index, subpath length, closed)."""
    out = []
    for pi, (kind, dim, _, subs) in enumerate(parts):
        if kind == "F":
            continue
        for si, sub in enumerate(subs):
            for gi, s in enumerate(sub.segs):
                n = 1 if s[0] == "L" else 24
                out.append(((pi, si, gi, len(sub.segs), sub.closed), [sp.seg_point(s, i / n) for i in range(n + 1)], dim, s))
    return out


def _dist_pt_poly(p, pts):
    return min(sp.dist_seg(p, pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def softness(parts, a24):
    """For each axis-aligned stroke (not dimmed) at least 2.5 long, sampled where no other stroke, not even its own neighbour, is within 3.2 units:
    how far its 24 px cross-section is from whole pixels. A 2-unit stroke on whole pixels reads 0; every edge on a
    half pixel reads 1."""
    flat = _segments(parts)
    res = []
    for k, (place, pts, dim, s) in enumerate(flat):
        if s[0] != "L" or dim:
            continue
        (x0, y0), (x1, y1) = s[1], s[2]
        horiz = abs(y0 - y1) < 1e-6 and abs(x0 - x1) > 1e-6
        vert = abs(x0 - x1) < 1e-6 and abs(y0 - y1) > 1e-6
        if not (horiz or vert):
            continue
        c = y0 if horiz else x0
        lo, hi = (min(x0, x1), max(x0, x1)) if horiz else (min(y0, y1), max(y0, y1))
        t = lo + 1.0
        while t <= hi - 1.0:
            p = (t, c) if horiz else (c, t)
            if all(_dist_pt_poly(p, q) > 3.2 for (pl, q, _, _) in flat if pl != place):
                i0 = int(c) - 2
                if 0 <= i0 and i0 + 4 <= 24 and 0 <= int(t) < 24:
                    prof = [a24[j, int(t)] for j in range(i0, i0 + 4)] if horiz else [a24[int(t), j] for j in range(i0, i0 + 4)]
                    res.append(sum(min(v, 1 - v) for v in prof))
            t += 0.5
    return res


def check_grid(parts, a24):
    segs = []
    for kind, _, _, subs in parts:
        if kind != "F":
            segs += sp.axis_lines(subs)
    off = [abs(c - round(c)) for _, c, lo, hi in segs if hi - lo >= 2.5]
    soft = softness(parts, a24)
    return [num("grid:straight-strokes-on-whole-units", max(off) if off else 0.0, None, 0.02, fmt=".2f"),
            num("grid:axis-strokes-whole-pixels-at-24px", float(np.mean(soft)) if soft else 0.0, None, T["soft_max"], fmt=".3f")]


def _runs(m):
    """Ink runs along every row and every column of a boolean image."""
    t = 0
    for arr in (m, m.T):
        t += int((np.diff(np.concatenate([np.zeros((arr.shape[0], 1), bool), arr], axis=1).astype(int), axis=1) == 1).sum())
    return t


def check_small(rd, dim):
    """Ink at 16 px for every glyph; the number of strokes and gaps that survive at 16 px; sharpness where nothing is
    dimmed (a dimmed part is faint on purpose)."""
    a16 = rd[16]
    ink = float(a16.sum())
    r96 = _runs(rd[96] > 0.5) / (2 * 96)
    kept = (_runs(a16 > 0.5) / (2 * 16)) / r96 if r96 else 1.0
    out = [num("small:ink-at-16px", ink, T["ink16_min"], None, fmt=".1f"),
           num("small:strokes-and-gaps-survive-at-16px", kept, T["runs16_min"], None, fmt=".3f")]
    if not dim:
        out.append(num("small:detail-stays-crisp-at-16px", float((a16 * a16).sum() / ink), T["sharp16_min"], None, fmt=".3f"))
    return out


def check_recolour(rd):
    w, b = rd["w48"], rd["b48"]
    d = np.abs(w[..., 3].astype(int) - b[..., 3].astype(int)).max()
    ink = b[..., 3] > 240
    wr = np.abs(w[..., :3][ink].astype(int) - 255).max() if ink.any() else 0
    br = np.abs(b[..., :3][ink].astype(int)).max() if ink.any() else 0
    return [num("recolour:alpha-is-colour-independent", float(d), None, 1.0, fmt=".0f"),
            num("recolour:ink-takes-the-requested-colour", float(max(wr, br)), None, 3.0, fmt=".0f")]


def full_member(gls):
    """{group: the Gl with the most ink} for every level series."""
    return {}


def series_roles(gls, data):
    """(full member per group, set of ids that are series members but not the full one)."""
    groups = defaultdict(list)
    for g in gls:
        if g.group:
            groups[g.group].append(g)
    full = {name: max(ms, key=lambda g: float(data[g.id][48].sum())) for name, ms in groups.items()}
    members = {g.id for name, ms in groups.items() for g in ms if g.id != full[name].id}
    return full, members


def run_glyph_checks(R, gls, svgs=None, data=None, members=None):
    """Per-glyph checks for a list of Gl. svgs: {id: svg} (default: what the kit writes)."""
    svgs = svgs or {g.id: K.svg(g) for g in gls}
    if data is None:
        data = render_items(R, [(g.id, svgs[g.id], None) for g in gls])
    if members is None:
        _, members = series_roles(gls, data)
    agg = Agg()
    for g in gls:
        rd = data[g.id]
        rs = check_hygiene(svgs[g.id])
        if rs[0][1]:
            _, parts = parse_svg(svgs[g.id])
            rs += check_layout(g, rd, centre=g.id not in members) + check_grid(parts, rd[24]) + check_small(rd, has_dim(g)) + check_recolour(rd)
        agg.add(g.id, rs)
    return agg, data


# --------------------------------------------------------------------------------------------- set checks
def check_series(gls, data):
    out = []
    groups = defaultdict(list)
    for g in gls:
        if g.group:
            groups[g.group].append(g)
    for name, members in groups.items():
        ink = {g.id: float(data[g.id][48].sum()) for g in members}
        ms = sorted(members, key=lambda g: g.level)
        ok, why = True, ""
        slack = -0.015 * max(ink.values()) if name.endswith("charging") else 0.5   # the bolt is XOR-ed out of the fill: neighbours may tie
        for a in ms:
            for b in ms:
                if a.level < b.level and not ink[a.id] < ink[b.id] - slack:
                    ok, why = False, f"{a.id} ({ink[a.id]:.0f}) is not lighter than {b.id} ({ink[b.id]:.0f})"
        out.append(flag(f"series:{name}-ink-grows-with-level", ok, why or f"{len(ms)} levels"))
    return out


def check_anchor(gls, data):
    """A series member never reaches outside the full drawing's box: the levels of one icon sit on one anchor."""
    out = []
    full, members = series_roles(gls, data)
    bad = []
    for g in gls:
        if g.id in members:
            f = full[g.group]
            bf, bg = box_of(f, data[f.id][96]), box_of(g, data[g.id][96])
            over = max(bf[0] - bg[0], bf[1] - bg[1], bg[2] - bf[2], bg[3] - bf[3])
            if over > T["anchor_slack"]:
                bad.append(f"{g.id} reaches {over:.2f} beyond {f.id}")
    out.append(flag("series:levels-share-the-anchor-of-the-full-drawing", not bad, "; ".join(bad[:6])))
    return out


def check_duplicates(gls, data):
    ids = [g.id for g in gls]
    A = np.stack([data[i][48].ravel() for i in ids])
    ink = A.sum(1)
    grp = {g.id: g.group for g in gls}
    pairs, best = [], (9.0, ("", ""))
    for i in range(len(ids)):
        d = np.abs(A[i][None, :] - A[i + 1:]).sum(1) / np.maximum(ink[i], ink[i + 1:])
        for k in np.nonzero(d < T["dup_min"] * 3)[0]:
            j = i + 1 + int(k)
            if grp[ids[i]] and grp[ids[i]] == grp[ids[j]]:
                continue
            if d[k] < best[0]:
                best = (float(d[k]), (ids[i], ids[j]))
            if d[k] < T["dup_min"]:
                pairs.append((ids[i], ids[j], float(d[k])))
    return [num("set:no-two-glyphs-are-the-same-drawing", best[0], T["dup_min"], None, fmt=".3f"),
            flag("set:duplicate-pairs-listed", not pairs, "; ".join(f"{a}~{b} ({d:.3f})" for a, b, d in pairs[:12]) or f"closest {best[1][0]} / {best[1][1]}")]


def check_rtl(gls, data):
    bad, pointless, missing = [], [], []
    for g in gls:
        a = data[g.id][48]
        asym = float(np.abs(a - a[:, ::-1]).sum() / a.sum())
        if g.rtl:
            if asym < T["rtl_asym_min"]:
                pointless.append(f"{g.id} ({asym:.3f})")
            m = data.get(g.id + "@rtl")
            if m is not None:
                d = float(np.abs(m[48] - a[:, ::-1]).mean())
                if d > T["rtl_tol"]:
                    bad.append(f"{g.id} ({d:.3f})")
        elif asym >= 0.05 and g.id.startswith(DIRECTIONAL):
            missing.append(f"{g.id} ({asym:.2f})")
    return [flag("rtl:copies-are-exact-mirrors", not bad, "; ".join(bad)),
            flag("rtl:only-asymmetric-glyphs-have-a-copy", not pointless, "; ".join(pointless)),
            flag("rtl:directional-glyphs-have-a-copy", not missing, "; ".join(missing[:10]))]


def check_names(gls):
    seen, bad, dup = {}, [], []
    for g in gls:
        for n in (g.id,) + tuple(g.alias):
            if not NAME_RE.match(n) or n.endswith("-symbolic"):
                bad.append(n)
            if n in seen:
                dup.append(f"{n} ({seen[n]} and {g.id})")
            seen[n] = g.id
    ctxs = [g.id for g in gls if g.ctx not in VALID_CTX]
    return [flag("names:lowercase-kebab-no-symbolic-suffix", not bad, ",".join(bad[:8])),
            flag("names:unique-across-ids-and-aliases", not dup, "; ".join(dup[:8])),
            flag("names:every-glyph-has-a-theme-context", not ctxs, ",".join(ctxs[:8]))]


def load_required():
    p = Path(__file__).with_name("required_names.json")
    return json.loads(p.read_text()) if p.exists() else {"names": {}, "skip": {}}


def check_coverage(have: set, req: dict):
    """The reference is a snapshot of the symbolic names Adwaita ships (what GNOME Shell and GTK apps ask for), minus a
    skip list in which every entry has a reason. `have` is every name the theme provides, from any source."""
    out = []
    for ctx, names in req["names"].items():
        skip = set(req["skip"].get(ctx, {}))
        want = [n for n in names if n not in skip]
        miss = sorted(n for n in want if n not in have)
        out.append(flag(f"coverage:{ctx}-names-asked-for-by-gnome-shell-and-gtk-apps", not miss,
                        f"{len(want) - len(miss)}/{len(want)} ({len(skip)} skipped on purpose)" + (f"; missing {', '.join(miss[:14])}" if miss else "")))
    return out


def theme_names(gls):
    """Every name the theme ships: the glyph kit's ids and aliases, and the object icons' standard names."""
    have = {n for g in gls for n in (g.id,) + tuple(g.alias)}
    try:
        import objects
        for o in objects.OBJECTS.values():
            if o.xdg:
                have.add(o.xdg)
            have.update(getattr(o, "alias", ()) or ())
        import theme_aliases
        have |= theme_aliases.alias_names()
    except Exception:                                        # noqa: BLE001
        pass
    return have


# --------------------------------------------------------------------------------------------- run
def run(report_path=None, negative=True, measure=False):
    gls = list(K.GLYPHS.values())
    rep = Report()
    with Renderer() as R:
        agg, data = run_glyph_checks(R, gls)
        rtl = [g for g in gls if g.rtl]
        rd = render_items(R, [(g.id + "@rtl", K.svg(g, rtl=True), None) for g in rtl])
        for g in rtl:
            data[g.id + "@rtl"] = rd[g.id + "@rtl"]
        lines, _ = agg.lines("glyphs")
        rep.extend(lines)
        rep.add("set", check_series(gls, data) + check_anchor(gls, data) + check_duplicates(gls, data) + check_rtl(gls, data)
                + check_names(gls) + check_coverage(theme_names(gls), load_required()))
        if measure:
            return rep, data, gls
        neg = negative_tests(R, gls, data) if negative else []
    text = finish(rep, neg, f"glyphs: {len(gls)}", report_path)
    return rep, neg, text


# --------------------------------------------------------------------------------------------- negative tests
def _shifted(parts, dx, dy, k=1.0):
    return [replace(p, d=sp.emit(sp.transform(sp.parse(p.d), (k, 0, 0, k, dx + 12 - 12 * k, dy + 12 - 12 * k)))) for p in parts]


def negative_tests(R, gls, data):
    out = []
    ids = {g.id: g for g in gls}
    base = ids["go-first"]
    mk = lambda id_, parts, **kw: K.Gl(id_, "actions", parts, **kw)

    def one(label, g, svg, prefix):
        agg, _ = run_glyph_checks(R, [g], {g.id: svg}, members=set())
        res = [(n, r[1], r[2]) for n, rows in agg.rows.items() for r in rows]
        ok, info = fails(res, prefix)
        out.append((label, ok, info))

    svg = K.svg(base)
    one("a glyph with a hard-coded colour is rejected", base, svg.replace("<path d=", '<path fill="#C763B0" d=', 1), "hygiene:no-colour")
    one("a glyph with a <text> element is rejected", base, svg.replace("</svg>", '<text x="3" y="9">A</text></svg>'), "hygiene:only-paths")
    one("a glyph on a 16 x 16 viewBox is rejected", base, svg.replace("0 0 24 24", "0 0 16 16"), "hygiene:viewBox")
    one("a glyph drawn with stroke 3 is rejected", base, svg.replace('stroke-width="2"', 'stroke-width="3"'), "hygiene:stroke-rules")
    one("a glyph with a style attribute is rejected", base, svg.replace("<path ", '<path style="stroke:red" ', 1), "hygiene:path-attributes")
    one("a glyph at 70% opacity (not the 35% dim) is rejected", base, svg.replace("<path ", '<path opacity=".7" ', 1), "hygiene:dim-is-35")
    one("a glyph padded to 3 KB is rejected", base, svg.replace("</svg>", "<!--" + "x" * 3000 + "--></svg>"), "hygiene:size")
    # layout: the shift is written into the path data, so the kit's own geometry is what moves
    for label, parts, prefix in (
            ("a glyph pushed 6 units to the right, out of the live area, is rejected", _shifted(base.parts, 6, 0), "layout:ink-inside"),
            ("a glyph shifted 2.5 units off centre is rejected", _shifted(base.parts, -2.5, 0), "layout:centred-by"),
            ("a glyph a whole unit and a half off centre is rejected", _shifted(base.parts, 0, 1.5), "layout:centred-by"),
            ("a glyph drawn at 45% size is rejected", _shifted(base.parts, 0, 0, 0.45), "layout:longest-side"),
            ("a glyph drawn 1.6x too big is rejected", _shifted(base.parts, 0, 0, 1.6), "layout:ink-inside")):
        g = mk("probe", parts)
        one(label, g, K.svg_of(parts), prefix)
    box = ids["window-new"]                       # a window frame: long straight edges
    moved = _shifted(box.parts, 0.5, 0.5)
    one("a box moved half a unit off the grid is rejected (geometry)", mk("probe", moved), K.svg_of(moved), "grid:straight")
    one("a box moved half a unit off the grid is rejected (pixels)", mk("probe", moved), K.svg_of(moved), "grid:axis")
    comb = mk("comb", K.S(*[K.L(6 + 2.6 * i, 6, 6 + 2.6 * i, 18) for i in range(6)]))
    one("a comb whose teeth merge at 16 px is rejected", comb, K.svg(comb), "small:strokes-and-gaps-survive")
    speck = mk("speck", K.S(K.L(11.9, 12, 12.1, 12)))
    one("a speck that leaves no ink at 16 px is rejected", speck, K.svg(speck), "small:ink-at-16px")
    one("a glyph painted with a fixed grey is rejected", base, svg.replace('stroke="currentColor"', 'stroke="#808080"', 1), "recolour:")
    anchored = mk("tag", K.S(K.L(5, 18, 19, 18)), tags="anchored")
    agg, _ = run_glyph_checks(R, [anchored], members=set())
    out.append(("a low bar is only allowed off-centre when it is tagged `anchored`",
                not any(n.startswith("layout:centred-by") for n in agg.rows), "tagged: centring not asked"))
    plain = mk("tag", K.S(K.L(5, 18, 19, 18)))
    one("the same low bar without the tag is rejected", plain, K.svg(plain), "layout:centred-by")
    # series
    sub = sorted([g for g in gls if g.group == "battery"], key=lambda g: g.level)
    a, b = sub[3], sub[7]
    swapped = [replace(a, level=b.level), replace(b, level=a.level)] + [g for g in sub if g.id not in (a.id, b.id)]
    r = check_series(swapped, data)[0]
    out.append(("a battery series with two levels swapped is rejected", not r[1], r[2][:100]))
    wifi = sorted([g for g in gls if g.group == "wifi"], key=lambda g: g.level)
    stray = replace(wifi[1], id="stray", parts=_shifted(wifi[1].parts, 0, -4))
    d2 = dict(data)
    agg, d3 = run_glyph_checks(R, [stray], {"stray": K.svg_of(stray.parts)}, members=set())
    d2["stray"] = d3["stray"]
    r = check_anchor([g for g in wifi if g.id != wifi[1].id] + [stray], d2)[0]
    out.append(("a Wi-Fi level that sits 4 units off the anchor of the full drawing is rejected", not r[1], r[2][:100]))
    # duplicates
    twin = replace(ids["go-next"], id="go-next-twin", alias=())
    d4 = dict(data)
    d4["go-next-twin"] = data["go-next"]
    r = check_duplicates([ids["go-next"], twin, ids["go-up"]], d4)
    out.append(("the same drawing under two names is rejected", not r[0][1], r[1][2][:100]))
    # rtl
    r = check_rtl([replace(ids["go-previous"], rtl=False, id="go-previous-y")], {"go-previous-y": data["go-previous"]})
    out.append(("a directional glyph (go-previous) without a mirrored copy is rejected", not r[2][1], r[2][2]))
    r = check_rtl([ids["go-previous"]], {"go-previous": data["go-previous"], "go-previous@rtl": data["go-previous"]})
    out.append(("an rtl copy that is not a mirror of the original is rejected", not r[0][1], r[0][2]))
    r = check_rtl([replace(ids["go-up"], rtl=True)], {"go-up": data["go-up"], "go-up@rtl": data["go-up"]})
    out.append(("an rtl copy of a symmetric glyph is rejected as pointless", not r[1][1], r[1][2]))
    # names
    r = check_names([replace(ids["go-up"], alias=("go-down",)), ids["go-down"]])
    out.append(("an alias that collides with another glyph's name is rejected", not r[1][1], r[1][2]))
    r = check_names([replace(ids["go-up"], id="Go_Up")])
    out.append(("a name that is not lowercase-kebab is rejected", not r[0][1], r[0][2]))
    req = load_required()
    if req["names"]:
        have = theme_names(gls) - {"battery-level-50"}
        r = check_coverage(have, {"names": {"status": ["battery-level-50", "audio-volume-high"]}, "skip": {}})
        out.append(("a missing standard name is reported", not r[0][1], r[0][2]))
    return out


if __name__ == "__main__":
    path = sys.argv[sys.argv.index("--report") + 1] if "--report" in sys.argv else None
    if "--measure" in sys.argv:
        rep, data, gls = run(measure=True)
        print("\n".join(rep.lines))
        sys.exit(0)
    rep, neg, text = run(path, negative="--no-negative" not in sys.argv)
    print(text)
    sys.exit(1 if rep.failed or not all(n[1] for n in neg) else 0)
