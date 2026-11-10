"""A small SVG path engine for the Malva icon tools (pure Python, no dependencies).

Why it exists: the glyph kit draws stroked outlines on a 24 grid, and a one-colour icon needs three operations that
a renderer cannot do for you without masks (masks break in GTK's symbolic recolouring, and Qt's SVG module ignores them):

  * cut     remove the part of a stroke that lies within `gap` of a line or a point, so a slash or a badge sits in
            a clean halo instead of crossing the drawing
  * mirror  write the right-to-left copy of a directional icon
  * stroke  turn a centre-line into the outline of its stroke (round caps and joins) as filled geometry, for the
            toolkits that only recolour `fill`

A path is parsed into subpaths of exact segments, never into dots, so a cut keeps the original curve:
    ("L", p0, p1)               line
    ("C", p0, c1, c2, p1)       cubic Bezier
    ("A", (cx, cy), r, a0, a1)  circular arc, angles in radians, y down, a1 > a0 is clockwise on screen
Only circular arcs are supported (the kit draws no ellipses); any other arc raises.
"""
from __future__ import annotations

import math
import re

TAU = 2 * math.pi
_NUM = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_TOK = re.compile(r"([MmLlHhVvCcSsQqTtAaZz])|([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)")


def fmt(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


class Sub:
    """One subpath: a list of segments, closed or open."""
    __slots__ = ("segs", "closed")

    def __init__(self, segs, closed=False):
        self.segs = segs
        self.closed = closed

    def start(self):
        return seg_point(self.segs[0], 0.0)

    def end(self):
        return seg_point(self.segs[-1], 1.0)


# ---------------------------------------------------------------- segment maths
def seg_point(s, t):
    k = s[0]
    if k == "L":
        (x0, y0), (x1, y1) = s[1], s[2]
        return (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
    if k == "C":
        (x0, y0), (x1, y1), (x2, y2), (x3, y3) = s[1:5]
        u = 1 - t
        a, b, c, d = u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t
        return (a * x0 + b * x1 + c * x2 + d * x3, a * y0 + b * y1 + c * y2 + d * y3)
    (cx, cy), r, a0, a1 = s[1], s[2], s[3], s[4]
    a = a0 + (a1 - a0) * t
    return (cx + r * math.cos(a), cy + r * math.sin(a))


def seg_slice(s, ta, tb):
    """The part of segment s between parameters ta < tb."""
    k = s[0]
    if k == "L":
        return ("L", seg_point(s, ta), seg_point(s, tb))
    if k == "A":
        c, r, a0, a1 = s[1], s[2], s[3], s[4]
        return ("A", c, r, a0 + (a1 - a0) * ta, a0 + (a1 - a0) * tb)
    p = [s[1], s[2], s[3], s[4]]

    def split(q, t):
        a = [(q[i][0] + (q[i + 1][0] - q[i][0]) * t, q[i][1] + (q[i + 1][1] - q[i][1]) * t) for i in range(3)]
        b = [(a[i][0] + (a[i + 1][0] - a[i][0]) * t, a[i][1] + (a[i + 1][1] - a[i][1]) * t) for i in range(2)]
        c = (b[0][0] + (b[1][0] - b[0][0]) * t, b[0][1] + (b[1][1] - b[0][1]) * t)
        return [q[0], a[0], b[0], c], [c, b[1], a[2], q[3]]
    if tb < 1.0:
        p = split(p, tb)[0]
    if ta > 0.0:
        p = split(p, ta / tb if tb < 1.0 else ta)[1]
    return ("C", p[0], p[1], p[2], p[3])


def seg_len(s, n=40):
    pts = [seg_point(s, i / n) for i in range(n + 1)]
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(n))


def arc_to_cubics(s):
    """Circular arc -> cubic Beziers (at most 90 degrees each)."""
    c, r, a0, a1 = s[1], s[2], s[3], s[4]
    n = max(1, math.ceil(abs(a1 - a0) / (math.pi / 2) - 1e-9))
    out = []
    for i in range(n):
        t0, t1 = a0 + (a1 - a0) * i / n, a0 + (a1 - a0) * (i + 1) / n
        k = 4 / 3 * math.tan((t1 - t0) / 4)
        p0 = (c[0] + r * math.cos(t0), c[1] + r * math.sin(t0))
        p3 = (c[0] + r * math.cos(t1), c[1] + r * math.sin(t1))
        c1 = (p0[0] - k * r * math.sin(t0), p0[1] + k * r * math.cos(t0))
        c2 = (p3[0] + k * r * math.sin(t1), p3[1] - k * r * math.cos(t1))
        out.append(("C", p0, c1, c2, p3))
    return out


# ---------------------------------------------------------------- parse
def _arc_from_endpoints(p0, p1, r, large, sweep):
    """SVG endpoint arc (circular, no rotation) -> ('A', centre, r, a0, a1)."""
    (x0, y0), (x1, y1) = p0, p1
    if (x0, y0) == (x1, y1):
        return None
    dx, dy = (x0 - x1) / 2, (y0 - y1) / 2
    d2 = dx * dx + dy * dy
    r = max(r, math.sqrt(d2))
    k2 = (r * r - d2) / d2 if d2 else 0.0
    k = math.sqrt(max(0.0, k2)) * (-1 if large == sweep else 1)
    cxp, cyp = k * dy, -k * dx
    cx, cy = cxp + (x0 + x1) / 2, cyp + (y0 + y1) / 2
    a0 = math.atan2(y0 - cy, x0 - cx)
    a1 = math.atan2(y1 - cy, x1 - cx)
    if sweep and a1 <= a0:
        a1 += TAU
    if not sweep and a1 >= a0:
        a1 -= TAU
    # a half circle comes out ambiguous when the radius is exactly half the chord: trust the flags' sweep direction
    return ("A", (cx, cy), r, a0, a1)


def parse(d: str) -> list[Sub]:
    toks = [(m.group(1), m.group(2)) for m in _TOK.finditer(d)]
    i, n = 0, len(toks)
    subs: list[Sub] = []
    cur: Sub | None = None
    pos = start = (0.0, 0.0)
    cmd = None
    last_c = None          # last cubic control point (for S)

    def num():
        nonlocal i
        v = float(toks[i][1]); i += 1
        return v

    def flag():
        v = num()
        if v not in (0.0, 1.0):
            raise ValueError("arc flags must be 0 or 1, separated by spaces")
        return int(v)

    while i < n:
        c, v = toks[i]
        if c:
            cmd = c; i += 1
            if cmd in "Zz":
                if cur is not None:
                    if cur.segs and math.dist(pos, start) > 1e-9:
                        cur.segs.append(("L", pos, start))
                    cur.closed = True
                    subs.append(cur); cur = None
                pos = start
                continue
        elif cmd is None:
            raise ValueError("path data must start with a command")
        rel = cmd.islower()
        C_ = cmd.upper()
        ox, oy = pos if rel else (0.0, 0.0)
        if C_ == "M":
            if cur is not None and cur.segs:
                subs.append(cur)
            x, y = num() + ox, num() + oy
            pos = start = (x, y)
            cur = Sub([], False)
            cmd = "l" if rel else "L"          # further pairs are implicit linetos
            continue
        if cur is None:
            cur = Sub([], False)
        if C_ == "L":
            q = (num() + ox, num() + oy)
            cur.segs.append(("L", pos, q)); pos = q
        elif C_ == "H":
            q = (num() + ox, pos[1]); cur.segs.append(("L", pos, q)); pos = q
        elif C_ == "V":
            q = (pos[0], num() + oy); cur.segs.append(("L", pos, q)); pos = q
        elif C_ == "C":
            c1 = (num() + ox, num() + oy); c2 = (num() + ox, num() + oy); q = (num() + ox, num() + oy)
            cur.segs.append(("C", pos, c1, c2, q)); pos = q; last_c = c2
            continue
        elif C_ == "S":
            c1 = (2 * pos[0] - last_c[0], 2 * pos[1] - last_c[1]) if last_c else pos
            c2 = (num() + ox, num() + oy); q = (num() + ox, num() + oy)
            cur.segs.append(("C", pos, c1, c2, q)); pos = q; last_c = c2
            continue
        elif C_ == "Q":
            qc = (num() + ox, num() + oy); q = (num() + ox, num() + oy)
            c1 = (pos[0] + 2 / 3 * (qc[0] - pos[0]), pos[1] + 2 / 3 * (qc[1] - pos[1]))
            c2 = (q[0] + 2 / 3 * (qc[0] - q[0]), q[1] + 2 / 3 * (qc[1] - q[1]))
            cur.segs.append(("C", pos, c1, c2, q)); pos = q
        elif C_ == "A":
            rx, ry = num(), num(); rot = num(); large = flag(); sweep = flag()
            q = (num() + ox, num() + oy)
            if abs(rx - ry) > 1e-6 or (abs(rot) > 1e-6 and abs(rx - ry) > 1e-6):
                raise ValueError("only circular arcs are supported")
            a = _arc_from_endpoints(pos, q, rx, large, sweep)
            if a is not None:
                cur.segs.append(a)
            pos = q
        else:
            raise ValueError(f"unsupported path command {cmd}")
        last_c = None
    if cur is not None and cur.segs:
        subs.append(cur)
    return subs


# ---------------------------------------------------------------- emit
def emit(subs: list[Sub]) -> str:
    out = []
    for sub in subs:
        if not sub.segs:
            continue
        x0, y0 = sub.start()
        out.append(f"M{fmt(x0)} {fmt(y0)}")
        n = len(sub.segs)
        for j, s in enumerate(sub.segs):
            k = s[0]
            if k == "L":
                if sub.closed and j == n - 1 and math.dist(s[2], (x0, y0)) < 1e-6:
                    continue                    # the closing line is what Z draws
                out.append(f"L{fmt(s[2][0])} {fmt(s[2][1])}")
            elif k == "C":
                out.append("C" + " ".join(f"{fmt(p[0])} {fmt(p[1])}" for p in s[2:5]))
            else:
                c, r, a0, a1 = s[1], s[2], s[3], s[4]
                span = a1 - a0
                parts = 2 if abs(span) > math.pi + 1e-6 else 1        # two pieces, so each is at most a half circle
                for q in range(parts):
                    b = a0 + span * (q + 1) / parts
                    out.append(f"A{fmt(r)} {fmt(r)} 0 0 {1 if span > 0 else 0} "
                               f"{fmt(c[0] + r * math.cos(b))} {fmt(c[1] + r * math.sin(b))}")
        if sub.closed:
            out.append("Z")
    return "".join(out)


# ---------------------------------------------------------------- transform
def _similarity(m):
    a, b, c, d, e, f_ = m
    return abs(a * a + b * b - (c * c + d * d)) < 1e-9 and abs(a * c + b * d) < 1e-9


def transform(subs: list[Sub], m) -> list[Sub]:
    """Apply the affine matrix (a b c d e f). Arcs survive a similarity (scale, rotation, reflection, shift);
    under any other matrix they are first turned into cubics."""
    a, b, c, d, e, f_ = m
    ap = lambda p: (a * p[0] + c * p[1] + e, b * p[0] + d * p[1] + f_)
    sim = _similarity(m)
    k = math.sqrt(abs(a * d - b * c))
    flip = (a * d - b * c) < 0
    rot = math.atan2(b, a)
    out = []
    for sub in subs:
        segs = []
        for s in sub.segs:
            if s[0] == "A" and not sim:
                for q in arc_to_cubics(s):
                    segs.append(("C",) + tuple(ap(p) for p in q[1:5]))
            elif s[0] == "A":
                a0, a1 = s[3], s[4]
                if flip:                          # a reflection reverses the sense of every angle
                    a0, a1 = -a0, -a1
                segs.append(("A", ap(s[1]), s[2] * k, a0 + rot, a1 + rot))
            elif s[0] == "L":
                segs.append(("L", ap(s[1]), ap(s[2])))
            else:
                segs.append(("C",) + tuple(ap(p) for p in s[1:5]))
        out.append(Sub(segs, sub.closed))
    return out


def mirror_x(subs: list[Sub], width: float = 24.0) -> list[Sub]:
    return transform(subs, (-1, 0, 0, 1, width, 0))


# ---------------------------------------------------------------- cut
def dist_seg(p, a, b):
    ax, ay = a; bx, by = b
    vx, vy = bx - ax, by - ay
    L2 = vx * vx + vy * vy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - ax) * vx + (p[1] - ay) * vy) / L2))
    return math.hypot(p[0] - (ax + t * vx), p[1] - (ay + t * vy))


def cut(subs: list[Sub], region, gap: float, samples: int = 64) -> list[Sub]:
    """Remove every part of the strokes that lies within `gap` of `region`: a point (x, y), a segment
    ((x0,y0),(x1,y1)) or an outline (a list of segments). The pieces that remain are open and keep their round caps,
    so the halo reads as an even gap."""
    if isinstance(region[0], (int, float)):                 # a point
        near = lambda p: math.dist(p, region) < gap
    elif isinstance(region[0][0], (int, float)):           # one segment
        ra, rb = region
        near = lambda p: dist_seg(p, ra, rb) < gap
    else:                                                  # an outline: a list of segments
        near = lambda p: any(dist_seg(p, a, b) < gap for a, b in region)

    def edge(s, t_out, t_in):
        """The parameter between a sample outside the region (t_out) and one inside it (t_in) where it is entered."""
        for _ in range(40):
            m = (t_out + t_in) / 2
            if near(seg_point(s, m)):
                t_in = m
            else:
                t_out = m
        return t_out

    ts = [i / samples for i in range(samples + 1)]
    out: list[Sub] = []
    for sub in subs:
        items = []                    # (segment index, kept slice, starts at t=0, ends at t=1)
        any_cut = False
        for k, s in enumerate(sub.segs):
            ins = [near(seg_point(s, t)) for t in ts]
            if not any(ins):
                items.append((k, s, True, True))
                continue
            any_cut = True
            i = 0
            while i <= samples:
                if ins[i]:
                    i += 1
                    continue
                j = i
                while j < samples and not ins[j + 1]:
                    j += 1
                ta = 0.0 if i == 0 else edge(s, ts[i], ts[i - 1])
                tb = 1.0 if j == samples else edge(s, ts[j], ts[j + 1])
                if tb - ta > 1e-4:
                    items.append((k, seg_slice(s, ta, tb) if (ta > 0 or tb < 1) else s, i == 0, j == samples))
                i = j + 1
        if not any_cut:
            out.append(sub)
            continue
        pieces = []                   # each: [segs, first item, last item]
        for it in items:
            if pieces:
                last = pieces[-1][2]
                if last[3] and it[2] and it[0] == last[0] + 1:
                    pieces[-1][0].append(it[1]); pieces[-1][2] = it
                    continue
            pieces.append([[it[1]], it, it])
        if (sub.closed and len(pieces) > 1 and pieces[0][1][0] == 0 and pieces[0][1][2]
                and pieces[-1][2][0] == len(sub.segs) - 1 and pieces[-1][2][3]):
            pieces[0][0] = pieces[-1][0] + pieces[0][0]          # the stretch that runs on across the start point
            pieces.pop()
        out += [Sub(p[0], False) for p in pieces]
    return out


# ---------------------------------------------------------------- measure
def flatten(subs: list[Sub], tol: float = 0.02) -> list[tuple[bool, list]]:
    out = []
    for sub in subs:
        pts = []
        for s in sub.segs:
            n = 1 if s[0] == "L" else max(8, int(seg_len(s) / (6 * tol ** 0.5)) + 1)
            n = min(n, 400)
            for i in range(n + 1):
                p = seg_point(s, i / n)
                if not pts or math.dist(pts[-1], p) > 1e-9:
                    pts.append(p)
        out.append((sub.closed, pts))
    return out


def bounds(subs: list[Sub], pad: float = 0.0):
    pts = [p for _, ps in flatten(subs) for p in ps]
    if not pts:
        return None
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)


def axis_lines(subs: list[Sub]):
    """The axis-aligned straight segments of a path: [(orientation, coordinate, lo, hi)], orientation 'h' (y fixed)
    or 'v' (x fixed). A stroke of width 2 is pixel-crisp at 24 px when its centre-line coordinate is an integer."""
    out = []
    for sub in subs:
        for s in sub.segs:
            if s[0] != "L":
                continue
            (x0, y0), (x1, y1) = s[1], s[2]
            if abs(y0 - y1) < 1e-6 and abs(x0 - x1) > 1e-6:
                out.append(("h", y0, min(x0, x1), max(x0, x1)))
            elif abs(x0 - x1) < 1e-6 and abs(y0 - y1) > 1e-6:
                out.append(("v", x0, min(y0, y1), max(y0, y1)))
    return out


# ---------------------------------------------------------------- emit, compact
def _num(v: float, prec: int) -> str:
    """A number as short as it can be written: no trailing zeros, no leading zero."""
    s = f"{v:.{prec}f}".rstrip("0").rstrip(".")
    if s in ("-0", ""):
        return "0"
    if s.startswith("0."):
        s = s[1:]
    elif s.startswith("-0."):
        s = "-" + s[2:]
    return s


def emit_compact(subs: list[Sub], prec: int = 3) -> str:
    """The same path as emit(), written short: relative commands, H and V for axis-aligned lines, no leading zeros.
    Each point is rounded once as an absolute coordinate and the relative numbers are differences of rounded values,
    so the rounding error never accumulates along a path."""
    out = []
    q = lambda v: round(v, prec)
    for sub in subs:
        if not sub.segs:
            continue
        x0, y0 = q(sub.start()[0]), q(sub.start()[1])
        cx, cy = x0, y0
        out.append(f"M{_num(x0, prec)} {_num(y0, prec)}")
        n = len(sub.segs)

        def put(cmd, nums):
            body = ""
            for t in nums:
                if not body:
                    body = t
                elif t.startswith("-") or (t.startswith(".") and "." in body.rsplit(" ", 1)[-1].rsplit("-", 1)[-1]):
                    body += t                                   # a sign, or a second decimal point, ends a number
                else:
                    body += " " + t
            out.append(cmd + body)
        for j, s in enumerate(sub.segs):
            k = s[0]
            if k == "L":
                ex, ey = q(s[2][0]), q(s[2][1])
                if sub.closed and j == n - 1 and math.dist(s[2], sub.start()) < 1e-6:
                    continue
                dx, dy = ex - cx, ey - cy
                if abs(dy) < 1e-9:
                    put("h", [_num(dx, prec)])
                elif abs(dx) < 1e-9:
                    put("v", [_num(dy, prec)])
                else:
                    put("l", [_num(dx, prec), _num(dy, prec)])
                cx, cy = ex, ey
            elif k == "C":
                pts = [(q(p[0]), q(p[1])) for p in s[2:5]]
                put("c", [_num(v, prec) for px, py in pts for v in (px - cx, py - cy)])
                cx, cy = pts[2]
            else:
                c, r, a0, a1 = s[1], s[2], s[3], s[4]
                span = a1 - a0
                parts = 2 if abs(span) > math.pi + 1e-6 else 1
                for qn in range(parts):
                    b = a0 + span * (qn + 1) / parts
                    ex, ey = q(c[0] + r * math.cos(b)), q(c[1] + r * math.sin(b))
                    put("a", [_num(r, prec), _num(r, prec), "0", "0", "1" if span > 0 else "0", _num(ex - cx, prec), _num(ey - cy, prec)])
                    cx, cy = ex, ey
        if sub.closed:
            out.append("z")
            cx, cy = x0, y0
    return "".join(out)
