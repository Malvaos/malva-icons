"""Stroke -> outline: the filled shape a stroked path covers (round caps, round joins), as path data.

Why: GTK recolours a symbolic icon by forcing `fill` on every rect, circle and path (a style rule with !important).
A drawing made of strokes comes out filled in and half black. Every symbolic file in the theme therefore carries
only filled shapes, and the same file works in GTK, Qt, browsers, resvg and Slint.

Method (no boolean operations, nothing that can leave a hole):
  * a subpath is cut into smooth chains at its corners (a tangent break of more than about half a degree);
  * a smooth open chain becomes ONE closed outline: its left offset curve forward, a half-circle cap, its right
    offset curve backward, a half-circle cap. Lines offset to lines, circular arcs to concentric arcs (exact), cubic
    Beziers to cubics (handle lengths scaled by the curvature, split until the offset is within `tol` of exact);
  * a smooth closed chain becomes a ring: the two offset loops, wound opposite ways;
  * at a corner the two chains simply overlap, and their round caps make the round join.
Every piece is wound the same way (interior on the right of the direction of travel), so a path made of many pieces
fills as their union under the default non-zero rule, wherever pieces overlap.
"""
from __future__ import annotations

import math

import svgpath as sp
from svgpath import Sub

TAU = math.tau


def _unit(v):
    n = math.hypot(*v)
    return (v[0] / n, v[1] / n) if n > 1e-12 else (1.0, 0.0)


def _normal(t):
    """The left normal of a unit tangent: the tangent rotated a quarter turn."""
    return (-t[1], t[0])


def _cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def _add(a, b, k=1.0):
    return (a[0] + k * b[0], a[1] + k * b[1])


# ----------------------------------------------------------------------------- tangents
def tangent_at(s, end: bool):
    k = s[0]
    if k == "L":
        return _unit(_sub(s[2], s[1]))
    if k == "A":
        th = s[4] if end else s[3]
        sg = 1.0 if s[4] > s[3] else -1.0
        return (-math.sin(th) * sg, math.cos(th) * sg)
    p0, p1, p2, p3 = s[1:5]
    if end:
        v = _sub(p3, p2)
        if math.hypot(*v) < 1e-9:
            v = _sub(p3, p1)
        return _unit(v)
    v = _sub(p1, p0)
    if math.hypot(*v) < 1e-9:
        v = _sub(p2, p0)
    return _unit(v)


def seg_end(s):
    return sp.seg_point(s, 1.0)


def seg_start(s):
    return sp.seg_point(s, 0.0)


def reverse_seg(s):
    k = s[0]
    if k == "L":
        return ("L", s[2], s[1])
    if k == "A":
        return ("A", s[1], s[2], s[4], s[3])
    return ("C", s[4], s[3], s[2], s[1])


# ----------------------------------------------------------------------------- offsetting
def _cubic_pt(P, t):
    return sp.seg_point(("C",) + tuple(P), t)


def _nearest_dist(P, q, n=48):
    """Distance from point q to the cubic P (sampled, then refined by golden-section search)."""
    best, bt = 1e18, 0.0
    for i in range(n + 1):
        t = i / n
        d = math.dist(_cubic_pt(P, t), q)
        if d < best:
            best, bt = d, t
    lo, hi = max(0.0, bt - 1.0 / n), min(1.0, bt + 1.0 / n)
    g = (math.sqrt(5) - 1) / 2
    for _ in range(30):
        a, b = hi - g * (hi - lo), lo + g * (hi - lo)
        if math.dist(_cubic_pt(P, a), q) < math.dist(_cubic_pt(P, b), q):
            hi = b
        else:
            lo = a
    return min(best, math.dist(_cubic_pt(P, (lo + hi) / 2), q))


def offset_cubic(P, d, tol, depth=0):
    """Segments (cubics) that follow the cubic P at distance d to its left, within tol of exact."""
    P0, P1, P2, P3 = P
    u0, u3 = tangent_at(("C",) + tuple(P), False), tangent_at(("C",) + tuple(P), True)
    n0, n3 = _normal(u0), _normal(u3)
    Q0, Q3 = _add(P0, n0, d), _add(P3, n3, d)
    a, b, c = _sub(P1, P0), _sub(P2, P1), _sub(P3, P2)
    la, lc = math.hypot(*a), math.hypot(*c)
    k0 = (2.0 / 3.0) * _cross(a, b) / la ** 3 if la > 1e-9 else 0.0
    k3 = (2.0 / 3.0) * _cross(b, c) / lc ** 3 if lc > 1e-9 else 0.0
    h0 = la if la > 1e-9 else math.hypot(*_sub(P2, P0)) / 3
    h3 = lc if lc > 1e-9 else math.hypot(*_sub(P3, P1)) / 3
    Q1 = _add(Q0, u0, (1.0 - d * k0) * h0)
    Q2 = _add(Q3, u3, -(1.0 - d * k3) * h3)
    Q = (Q0, Q1, Q2, Q3)
    err = 0.0
    for i in range(1, 12):
        q = _cubic_pt(Q, i / 12)
        err = max(err, abs(_nearest_dist(P, q) - abs(d)))
    if err <= tol or depth >= 7:
        return [("C",) + Q]
    # split the source at its middle and offset the halves: each half keeps its own exact end normals
    ab = [_add(P0, _sub(P1, P0), 0.5), _add(P1, _sub(P2, P1), 0.5), _add(P2, _sub(P3, P2), 0.5)]
    abc = [_add(ab[0], _sub(ab[1], ab[0]), 0.5), _add(ab[1], _sub(ab[2], ab[1]), 0.5)]
    m = _add(abc[0], _sub(abc[1], abc[0]), 0.5)
    left, right = (P0, ab[0], abc[0], m), (m, abc[1], ab[2], P3)
    return offset_cubic(left, d, tol, depth + 1) + offset_cubic(right, d, tol, depth + 1)


def offset_seg(s, d, tol):
    """The segment shifted by d to its left (to the right if d < 0)."""
    k = s[0]
    if k == "L":
        n = _normal(tangent_at(s, False))
        return [("L", _add(s[1], n, d), _add(s[2], n, d))]
    if k == "A":
        sg = 1.0 if s[4] > s[3] else -1.0
        r2 = s[2] - d * sg
        if r2 < 1e-6:
            raise ValueError("an arc tighter than the stroke")
        return [("A", s[1], r2, s[3], s[4])]
    return offset_cubic(s[1:5], d, tol)


def _cap(c, n, hw):
    """The half circle about c from c + hw*n round the far side to c - hw*n (angles decreasing: same winding as the body)."""
    a0 = math.atan2(n[1], n[0])
    return ("A", c, hw, a0, a0 - math.pi)


# ----------------------------------------------------------------------------- chains
def _break(s0, s1, tol_rad=0.01):
    t0, t1 = tangent_at(s0, True), tangent_at(s1, False)
    return abs(math.atan2(_cross(t0, t1), t0[0] * t1[0] + t0[1] * t1[1])) > tol_rad


def chains_of(sub: Sub):
    """(chains, ring): smooth chains of segments; `ring` is True for a closed subpath with no corner at all."""
    segs = [s for s in sub.segs if sp.seg_len(s) > 1e-9]
    if not segs:
        return [], False
    n = len(segs)
    breaks = [_break(segs[i], segs[(i + 1) % n]) for i in range(n)]      # breaks[i]: between segment i and the next
    if sub.closed and not any(breaks) and n >= 1 and math.dist(seg_end(segs[-1]), seg_start(segs[0])) < 1e-6:
        return [segs], True
    if not sub.closed:
        breaks[-1] = True
    elif math.dist(seg_end(segs[-1]), seg_start(segs[0])) > 1e-6:       # a closed path whose last point is not its first
        breaks[-1] = True
    start = next((i + 1 for i in range(n) if breaks[i]), 0) % n         # begin just after a break
    out, cur = [], []
    for j in range(n):
        i = (start + j) % n
        cur.append(segs[i])
        if breaks[i]:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out, False


def _chain_piece(chain, hw, tol):
    left, right = [], []
    for s in chain:
        left += offset_seg(s, hw, tol)
        right += offset_seg(s, -hw, tol)
    right = [reverse_seg(s) for s in reversed(right)]
    a, b = chain[0], chain[-1]
    cap_end = _cap(seg_end(b), _normal(tangent_at(b, True)), hw)
    n0 = _normal(tangent_at(a, False))
    cap_start = _cap(seg_start(a), (-n0[0], -n0[1]), hw)
    return Sub(left + [cap_end] + right + [cap_start], True)


def _disc(c, hw):
    return Sub([("A", c, hw, 0.0, -math.pi), ("A", c, hw, -math.pi, -TAU)], True)


def stroke_outline(subs, hw=1.0, tol=0.004, dot=0.05):
    """The outline subpaths of the strokes of `subs` (a list of svgpath.Sub), width 2*hw."""
    out = []
    for sub in subs:
        length = sum(sp.seg_len(s) for s in sub.segs)
        if length < dot:                                      # a dot: a stroke with no length is its round cap
            out.append(_disc(sub.start(), hw))
            continue
        chains, ring = chains_of(sub)
        if ring:
            ch = chains[0]
            left = [x for s in ch for x in offset_seg(s, hw, tol)]
            right = [reverse_seg(s) for s in reversed([x for s in ch for x in offset_seg(s, -hw, tol)])]
            out += [Sub(left, True), Sub(right, True)]
            continue
        for ch in chains:
            try:
                out.append(_chain_piece(ch, hw, tol))
            except ValueError:                                # an arc tighter than the stroke: stroke it as short chords
                pts = sp.flatten([Sub(list(ch), False)], 0.01)[0][1]
                for i in range(len(pts) - 1):
                    out.append(_chain_piece([("L", pts[i], pts[i + 1])], hw, tol))
    return out


def outline_d(d: str, hw=1.0, tol=0.004, prec=3) -> str:
    """Path data of the filled outline of the stroke of path data `d`."""
    return sp.emit_compact(stroke_outline(sp.parse(d), hw, tol), prec)
