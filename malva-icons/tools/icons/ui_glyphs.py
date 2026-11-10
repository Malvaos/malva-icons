"""Malva UI glyph pack: one geometry per glyph, drawn on a 24 x 24 grid.

Rules (enforced by check_ui.py):
  * stroke 2 (regular); light 1.5 and bold 2.5 reuse the identical path data
  * round caps and joins, no fills in the outline weights, ink inside 1..23
  * the corner of every box is the Balance-dial superellipse (exponent from balance.rs), never a circular arc
  * duotone = the same strokes plus a 22% fill of the glyph's main body (`fill` below)
"""
import math
from mi_geom import f, rr, corner_fit

# ------------------------------------------------------------------ path helpers (24 grid)
def R(x, y, w, h, r=4.0):
    return rr(x, y, w, h, r)

def C(cx, cy, r):
    return f"M{f(cx - r)} {f(cy)}a{f(r)} {f(r)} 0 1 0 {f(2 * r)} 0a{f(r)} {f(r)} 0 1 0 {f(-2 * r)} 0Z"

def L(x1, y1, x2, y2):
    return f"M{f(x1)} {f(y1)}L{f(x2)} {f(y2)}"

def D(x, y):
    return f"M{f(x)} {f(y)}h.01"

def P(*pts):
    return "M" + "L".join(f"{f(x)} {f(y)}" for x, y in pts)

def Pc(*pts):
    return P(*pts) + "Z"

def RP(pts, r=3.0, closed=False):
    """Polyline whose right-angle corners are Balance-dial superellipse corners of size r.
    Corners that are not about 90 degrees keep the round join."""
    a, b, m, _ = corner_fit()
    k = b / math.sqrt(2)
    V, H, M = (0.0, 1.0), (1.0, 0.0), (m, m)
    v2m = [V, (0.0, 1 - a), (m - k, m + k), M]
    m2h = [M, (m + k, m - k), (1 - a, 0.0), H]
    n = len(pts)
    out = []
    for i, p in enumerate(pts):
        interior = closed or 0 < i < n - 1
        if not interior:
            out.append(("pt", p))
            continue
        q0, q1 = pts[(i - 1) % n], pts[(i + 1) % n]
        u = (p[0] - q0[0], p[1] - q0[1]); lu = math.hypot(*u); u = (u[0] / lu, u[1] / lu)
        v = (q1[0] - p[0], q1[1] - p[1]); lv = math.hypot(*v); v = (v[0] / lv, v[1] / lv)
        cosang = u[0] * v[0] + u[1] * v[1]
        if abs(cosang) > 0.17:                      # not a right angle: plain join
            out.append(("pt", p))
            continue
        rr_ = min(r, lu / 2 if (closed or i - 1 > 0) else lu, lv / 2 if (closed or i + 1 < n - 1) else lv)

        def mp(X, Y):
            return (p[0] + rr_ * (X * v[0] - Y * u[0]), p[1] + rr_ * (X * v[1] - Y * u[1]))

        A = mp(*V)
        c1, c2, c3 = (mp(*q) for q in v2m[1:])
        c4, c5, c6 = (mp(*q) for q in m2h[1:])
        out.append(("cor", A, (c1, c2, c3), (c4, c5, c6)))
    d = ""
    for i, o in enumerate(out):
        if o[0] == "pt":
            d += ("M" if i == 0 else "L") + f"{f(o[1][0])} {f(o[1][1])}"
        else:
            _, A, s1, s2 = o
            d += ("M" if i == 0 else "L") + f"{f(A[0])} {f(A[1])}"
            for seg in (s1, s2):
                d += "C" + " ".join(f"{f(x)} {f(y)}" for x, y in seg)
    return d + ("Z" if closed else "")

def star(cx, cy, ro, ri, n=5):
    pts = []
    for i in range(2 * n):
        r = ro if i % 2 == 0 else ri
        a = -math.pi / 2 + i * math.pi / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return Pc(*pts)

def gear(cx, cy, tips=8, rt=9.4, rv=7.0, w_tip=9.0, w_val=13.0):
    pts = []
    for i in range(tips):
        a0 = i * 2 * math.pi / tips - math.pi / 2
        for da, r in ((-w_val, rv), (-w_tip, rt), (w_tip, rt), (w_val, rv)):
            a = a0 + math.radians(da)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return Pc(*pts)

def rays(cx, cy, r1, r2, n=8, off=0.0):
    d = ""
    for i in range(n):
        a = off + i * 2 * math.pi / n
        d += L(cx + r1 * math.cos(a), cy + r1 * math.sin(a), cx + r2 * math.cos(a), cy + r2 * math.sin(a))
    return d

# ------------------------------------------------------------------ registry
GLYPHS = {}   # id -> dict(strokes=[d...], fill=[d...], cat=..., tags=...)

def g(id_, cat, strokes, fill=None, tags=""):
    if isinstance(strokes, str):
        strokes = [strokes]
    GLYPHS[id_] = dict(strokes=strokes, fill=fill or [], cat=cat, tags=tags)

# ---- navigation
g("arrow-left", "navigation", [L(20, 12, 4, 12), P((10, 6), (4, 12), (10, 18))], tags="back previous")
g("arrow-right", "navigation", [L(4, 12, 20, 12), P((14, 6), (20, 12), (14, 18))], tags="forward next")
g("arrow-up", "navigation", [L(12, 20, 12, 4), P((6, 10), (12, 4), (18, 10))], tags="up")
g("arrow-down", "navigation", [L(12, 4, 12, 20), P((6, 14), (12, 20), (18, 14))], tags="down")
g("chevron-left", "navigation", P((15, 5.5), (8.5, 12), (15, 18.5)), tags="back")
g("chevron-right", "navigation", P((9, 5.5), (15.5, 12), (9, 18.5)), tags="forward")
g("chevron-up", "navigation", P((5.5, 15), (12, 8.5), (18.5, 15)), tags="collapse")
g("chevron-down", "navigation", P((5.5, 9), (12, 15.5), (18.5, 9)), tags="expand")
g("chevrons-up-down", "navigation", [P((7.5, 9.5), (12, 5), (16.5, 9.5)), P((7.5, 14.5), (12, 19), (16.5, 14.5))], tags="select dropdown")
g("external-link", "navigation", [RP([(11, 4.5), (4.5, 4.5), (4.5, 19.5), (19.5, 19.5), (19.5, 13)], 3.5), L(13, 11, 20, 4), P((14, 4), (20, 4), (20, 10))], tags="open new window")
g("refresh", "navigation", ["M4.5 10.5A7.5 7.5 0 0 1 17.6 6.4L20 8.8", "M19.5 13.5A7.5 7.5 0 0 1 6.4 17.6L4 15.2", P((20, 4), (20, 9), (15, 9)), P((4, 20), (4, 15), (9, 15))], tags="reload sync")
g("undo", "navigation", ["M9 14L4 9l5-5", "M4 9h10.5a5.5 5.5 0 0 1 0 11H11"], tags="back revert")
g("redo", "navigation", ["M15 14l5-5-5-5", "M20 9H9.5a5.5 5.5 0 0 0 0 11H13"], tags="forward repeat")

# ---- actions
g("plus", "action", [L(12, 5, 12, 19), L(5, 12, 19, 12)], tags="add new")
g("minus", "action", L(5, 12, 19, 12), tags="remove subtract")
g("close", "action", [L(6, 6, 18, 18), L(18, 6, 6, 18)], tags="dismiss x cancel")
g("check", "action", P((5, 12.5), (10, 17.5), (19, 7)), tags="done ok confirm")
g("check-circle", "action", [C(12, 12, 9), P((8, 12.3), (11, 15.3), (16.5, 9))], [C(12, 12, 9)], tags="success done")
g("x-circle", "action", [C(12, 12, 9), L(9, 9, 15, 15), L(15, 9, 9, 15)], [C(12, 12, 9)], tags="clear dismiss")
g("search", "action", [C(10.5, 10.5, 6.5), L(15.5, 15.5, 20, 20)], [C(10.5, 10.5, 6.5)], tags="find lens")
g("zoom-in", "action", [C(10.5, 10.5, 6.5), L(15.5, 15.5, 20, 20), L(7.8, 10.5, 13.2, 10.5), L(10.5, 7.8, 10.5, 13.2)], [C(10.5, 10.5, 6.5)], tags="magnify")
g("zoom-out", "action", [C(10.5, 10.5, 6.5), L(15.5, 15.5, 20, 20), L(7.8, 10.5, 13.2, 10.5)], [C(10.5, 10.5, 6.5)], tags="shrink")
g("menu", "action", [L(4, 7, 20, 7), L(4, 12, 20, 12), L(4, 17, 20, 17)], tags="hamburger navigation")
g("more-horizontal", "action", [D(5, 12), D(12, 12), D(19, 12)], tags="overflow ellipsis")
g("more-vertical", "action", [D(12, 5), D(12, 12), D(12, 19)], tags="overflow kebab")
g("filter", "action", Pc((4, 5), (20, 5), (14, 12.5), (14, 19), (10, 17), (10, 12.5)), [Pc((4, 5), (20, 5), (14, 12.5), (14, 19), (10, 17), (10, 12.5))], tags="funnel")
g("sliders", "action", [L(4, 7, 6.5, 7), C(9, 7, 2.5), L(11.5, 7, 20, 7), L(4, 17, 12.5, 17), C(15, 17, 2.5), L(17.5, 17, 20, 17)], tags="adjust controls")
g("sort", "action", [L(8, 4, 8, 20), P((4, 8), (8, 4), (12, 8)), L(16, 4, 16, 20), P((12, 16), (16, 20), (20, 16))], tags="order")
_pencil = "M4.5 19.5l1-4.2L16.4 4.4a2.1 2.1 0 0 1 3 3L8.5 18.5Z"
g("edit", "action", [_pencil, L(14, 6.8, 17.2, 10)], [_pencil], tags="pencil write")
_trash = "M6 7l.9 11.2a2 2 0 0 0 2 1.8h6.2a2 2 0 0 0 2-1.8L18 7Z"
g("trash", "action", [L(4, 7, 20, 7), P((9.5, 7), (9.5, 4.5), (14.5, 4.5), (14.5, 7)), _trash, L(10, 11, 10, 16), L(14, 11, 14, 16)], [_trash], tags="delete bin")
g("copy", "action", [R(9, 9, 11, 11, 3), RP([(15, 9), (15, 5), (4, 5), (4, 15), (9, 15)], 3)], [R(9, 9, 11, 11, 3)], tags="duplicate")
g("clipboard", "action", [RP([(9, 5), (5, 5), (5, 21), (19, 21), (19, 5), (15, 5)], 3), R(9, 3, 6, 4, 1.5)], [R(5, 5, 14, 16, 3)], tags="paste")
g("scissors", "action", [C(6, 6, 3), C(6, 18, 3), L(8.4, 8.4, 20, 20), L(8.4, 15.6, 20, 4)], tags="cut")
g("download", "action", [L(12, 4, 12, 15.5), P((7, 11), (12, 16), (17, 11)), RP([(4, 15), (4, 20), (20, 20), (20, 15)], 3)], tags="save get")
g("upload", "action", [L(12, 16, 12, 4.5), P((7, 9), (12, 4), (17, 9)), RP([(4, 15), (4, 20), (20, 20), (20, 15)], 3)], tags="send put")
g("share", "action", [C(18, 5.5, 2.5), C(6, 12, 2.5), C(18, 18.5, 2.5), L(8.2, 10.8, 15.8, 6.7), L(8.2, 13.2, 15.8, 17.3)], tags="network")
g("link", "action", ["M10 13.5a4.5 4.5 0 0 0 6.7.4l3-3a4.5 4.5 0 0 0-6.4-6.4l-1.2 1.2", "M14 10.5a4.5 4.5 0 0 0-6.7-.4l-3 3a4.5 4.5 0 0 0 6.4 6.4l1.2-1.2"], tags="chain url")
g("send", "action", [Pc((21, 3), (3, 10), (10.5, 13.5), (14, 21)), L(10.5, 13.5, 21, 3)], [Pc((21, 3), (3, 10), (10.5, 13.5), (14, 21))], tags="paper plane submit")
g("pin", "action", ["M12 21s6.5-5.8 6.5-11.2a6.5 6.5 0 0 0-13 0C5.5 15.200 12 21 12 21Z", C(12, 9.8, 2.5)], ["M12 21s6.5-5.8 6.5-11.2a6.5 6.5 0 0 0-13 0C5.5 15.200 12 21 12 21Z"], tags="location map marker")
_bm = Pc((6.5, 3.5), (17.5, 3.5), (17.5, 20.5), (12, 16), (6.5, 20.5))
g("bookmark", "action", _bm, [_bm], tags="save mark")
_st = star(12, 12.6, 9.3, 4.3)
g("star", "action", _st, [_st], tags="favourite rate")
_ht = "M12 20s-7.500-4.600-7.500-10.200A4.300 4.300 0 0 1 12 7.300a4.300 4.300 0 0 1 7.500 2.500C19.500 15.400 12 20 12 20Z"
g("heart", "action", _ht, [_ht], tags="like love")
_fl = Pc((5, 4), (18.5, 4), (15.5, 8.5), (18.5, 13), (5, 13))
g("flag", "action", [_fl, L(5, 3, 5, 21)], [_fl], tags="report mark")
g("tag", "action", [Pc((4, 4), (12, 4), (21, 13), (13, 21), (4, 12)), D(8.5, 8.5)], [Pc((4, 4), (12, 4), (21, 13), (13, 21), (4, 12))], tags="label")
_ey = "M3 12c2-4 5-6.500 9-6.500s7 2.500 9 6.500c-2 4-5 6.500-9 6.500S5 16 3 12Z"
g("eye", "action", [_ey, C(12, 12, 3)], [_ey], tags="view show visible")
g("eye-off", "action", [_ey, C(12, 12, 3), L(4.5, 19.5, 19.5, 4.5)], tags="hide hidden")
g("lock", "action", [R(5, 10.5, 14, 10, 3), "M8 10.5V8a4 4 0 0 1 8 0v2.5", L(12, 14.8, 12, 16.2)], [R(5, 10.5, 14, 10, 3)], tags="secure private")
g("unlock", "action", [R(5, 10.5, 14, 10, 3), "M8 10.5V8a4 4 0 0 1 7.700-1.500", L(12, 14.8, 12, 16.2)], [R(5, 10.5, 14, 10, 3)], tags="open")
g("key", "action", [C(7.5, 16.5, 4), L(10.6, 13.4, 20, 4), L(16.6, 7.4, 19.2, 10), L(13.8, 10.2, 16, 12.4)], tags="password credential")
g("trash-restore", "action", [], tags="") if False else None

# ---- status
g("info", "status", [C(12, 12, 9), L(12, 11, 12, 16.5), D(12, 7.6)], [C(12, 12, 9)], tags="about")
g("warning", "status", [Pc((12, 3.5), (21.5, 20), (2.5, 20)), L(12, 10, 12, 14.2), D(12, 17.2)], [Pc((12, 3.5), (21.5, 20), (2.5, 20))], tags="caution alert")
g("error", "status", [C(12, 12, 9), L(12, 7.2, 12, 12.6), D(12, 16.4)], [C(12, 12, 9)], tags="alert problem")
g("help", "status", [C(12, 12, 9), "M9.500 9.400a2.600 2.600 0 0 1 5 1c0 1.800-2.500 2.100-2.500 3.900", D(12, 17.4)], [C(12, 12, 9)], tags="question support")
_bell = "M6.500 17V11a5.500 5.500 0 0 1 11 0v6l1.700 2H4.800Z"
g("bell", "status", [_bell, "M10 21.600a2.200 2.200 0 0 0 4 0"], [_bell], tags="notification alert")
g("bell-off", "status", [_bell, "M10 21.600a2.200 2.200 0 0 0 4 0", L(4.5, 19.5, 19.5, 4.5)], tags="mute silent")
g("shield", "status", "M12 3l7.500 2.800v5.700c0 4.600-3.200 8-7.500 9.500-4.300-1.500-7.500-4.900-7.500-9.500V5.800Z", ["M12 3l7.500 2.800v5.700c0 4.600-3.200 8-7.500 9.500-4.300-1.500-7.500-4.900-7.500-9.500V5.800Z"], tags="security protect")

# ---- places and objects
_home_body = [(6, 10), (6, 20), (18, 20), (18, 10)]
g("home", "object", ["M3.500 11.500L12 4l8.500 7.500", RP(_home_body, 3), P((10, 20), (10, 15), (14, 15), (14, 20))], [RP([(6, 9.5), (6, 20), (18, 20), (18, 9.5), (12, 4.2)], 3, closed=False) + "Z"], tags="start desktop")
_fo = RP([(3, 19), (3, 5), (9.500, 5), (11.500, 8), (21, 8), (21, 19)], 2.500, closed=True)
g("folder", "object", _fo, [_fo], tags="directory")
_fi = RP([(5, 3), (14, 3), (19, 8), (19, 21), (5, 21)], 3, closed=True)
g("file", "object", [_fi, P((14, 3), (14, 8), (19, 8))], [_fi], tags="document page")
g("file-text", "object", [_fi, P((14, 3), (14, 8), (19, 8)), L(8.500, 13, 15.500, 13), L(8.500, 17, 15.500, 17)], [_fi], tags="document text")
g("image", "object", [R(3, 4, 18, 16, 4), C(9, 9.500, 1.500), P((4.500, 19), (10, 13), (14, 17), (16.500, 14.500), (20, 18))], [R(3, 4, 18, 16, 4)], tags="photo picture")
_cam = RP([(3, 8), (7.500, 8), (9, 5.500), (15, 5.500), (16.500, 8), (21, 8), (21, 20), (3, 20)], 2.500, closed=True)
g("camera", "object", [_cam, C(12, 13.200, 3.600)], [_cam], tags="photo capture")
g("music", "object", [Pc((9, 5.5), (20, 3.5), (20, 9), (9, 11)), L(9, 11, 9, 17.5), L(20, 9, 20, 15.5), C(6.5, 17.5, 2.5), C(17.5, 15.5, 2.5)], [Pc((9, 5.5), (20, 3.5), (20, 9), (9, 11))], tags="audio note beam")
g("video", "object", [R(3, 6, 12.500, 12, 3.500), Pc((15.500, 10.500), (21, 7), (21, 17), (15.500, 13.500))], [R(3, 6, 12.500, 12, 3.500)], tags="film camcorder")
g("mic", "object", [R(9, 3, 6, 11, 3), "M5.500 11a6.500 6.500 0 0 0 13 0", L(12, 17.500, 12, 21), L(8.500, 21, 15.500, 21)], [R(9, 3, 6, 11, 3)], tags="microphone voice")
g("mic-off", "object", [R(9, 3, 6, 11, 3), "M5.500 11a6.500 6.500 0 0 0 13 0", L(12, 17.500, 12, 21), L(8.500, 21, 15.500, 21), L(4.500, 19.500, 19.500, 4.500)], tags="mute")
_sp = Pc((4, 9.500), (8, 9.500), (13, 5.500), (13, 18.500), (8, 14.500), (4, 14.500))
g("volume", "object", [_sp, "M16.200 9.200a4 4 0 0 1 0 5.600", "M18.800 6.500a7.500 7.500 0 0 1 0 11"], [_sp], tags="speaker sound")
g("volume-off", "object", [_sp, L(16.500, 9.500, 21.500, 14.500), L(21.500, 9.500, 16.500, 14.500)], [_sp], tags="mute")
g("calendar", "object", [R(3, 5, 18, 16, 4), L(3, 10, 21, 10), L(8, 3, 8, 7), L(16, 3, 16, 7)], [R(3, 5, 18, 16, 4)], tags="date schedule")
g("clock", "object", [C(12, 12, 9), P((12, 7), (12, 12), (15.500, 14))], [C(12, 12, 9)], tags="time")
g("globe", "object", [C(12, 12, 9), L(3, 12, 21, 12), "M12 3c2.800 2.500 4.200 5.500 4.200 9s-1.400 6.500-4.200 9c-2.800-2.500-4.200-5.500-4.200-9S9.200 5.500 12 3Z"], [C(12, 12, 9)], tags="web internet language")
g("mail", "object", [R(3, 5, 18, 14, 4), P((4.500, 8.500), (12, 13.500), (19.500, 8.500))], [R(3, 5, 18, 14, 4)], tags="email message")
_chat = RP([(3, 4), (21, 4), (21, 17), (12.500, 17), (8, 21), (8, 17), (3, 17)], 4, closed=True)
g("chat", "object", _chat, [_chat], tags="message comment")
g("phone", "object", [R(6.500, 2.500, 11, 19, 3.500), L(10.500, 18.500, 13.500, 18.500)], [R(6.500, 2.500, 11, 19, 3.500)], tags="mobile")
g("user", "object", [C(12, 8, 4), "M4.500 20a7.500 7.500 0 0 1 15 0"], [C(12, 8, 4)], tags="person account profile")
g("users", "object", [C(9, 8.500, 3.500), "M2.500 19.500a6.500 6.500 0 0 1 13 0", "M15 5.300a3.400 3.400 0 0 1 0 6.400", "M17.500 14.200a6 6 0 0 1 4 5.300"], [C(9, 8.500, 3.500)], tags="people group")
g("cloud", "object", "M7.500 18.500a4.500 4.500 0 0 1-.6-8.960 5.800 5.800 0 0 1 11.200 1.500A3.700 3.700 0 0 1 17.500 18.500Z", ["M7.500 18.500a4.500 4.500 0 0 1-.6-8.960 5.800 5.800 0 0 1 11.200 1.500A3.700 3.700 0 0 1 17.500 18.500Z"], tags="sync storage online")
g("archive", "object", [R(3, 4, 18, 5, 2), RP([(5, 9), (5, 20), (19, 20), (19, 9)], 3), L(10, 13, 14, 13)], [R(3, 4, 18, 5, 2)], tags="box store")
g("send-airplane", "object", [], tags="") if False else None
g("airplane", "object", "M10.500 5.500v5l-8 4.800v2.200l8-2v3.500l-2.200 1.600V22l3.700-1 3.700 1v-1.400l-2.200-1.600v-3.500l8 2v-2.200l-8-4.800v-5a1.500 1.500 0 0 0-3 0Z", tags="flight mode")

# ---- device and system
g("wifi", "system", ["M2.500 9.500a14 14 0 0 1 19 0", "M5.500 13a9.500 9.500 0 0 1 13 0", "M8.700 16.300a5 5 0 0 1 6.600 0", D(12, 19.500)], tags="network wireless")
g("wifi-off", "system", ["M2.500 9.500a14 14 0 0 1 19 0", "M5.500 13a9.500 9.500 0 0 1 13 0", "M8.700 16.300a5 5 0 0 1 6.600 0", D(12, 19.500), L(4.500, 19.500, 19.500, 4.500)], tags="offline")
g("bluetooth", "system", P((7, 7.500), (17, 16.500), (12, 21), (12, 3), (17, 7.500), (7, 16.500)), tags="wireless")
g("battery", "system", [R(2.500, 7, 17, 10, 2.500), L(22, 10.500, 22, 13.500), L(6.500, 12, 11.500, 12)], [R(2.500, 7, 17, 10, 2.500)], tags="power level")
g("battery-charging", "system", [R(2.500, 7, 17, 10, 2.500), L(22, 10.500, 22, 13.500), P((11.500, 9), (9, 12.500), (13.500, 12.500), (11, 16))], [R(2.500, 7, 17, 10, 2.500)], tags="plugged")
g("power", "system", [L(12, 3, 12, 11), "M17.500 6.500a8 8 0 1 1-11 0"], tags="shutdown on off")
g("moon", "system", "M20 14.500A8.500 8.500 0 1 1 9.500 4a6.600 6.600 0 0 0 10.500 10.500Z", ["M20 14.500A8.500 8.500 0 1 1 9.500 4a6.600 6.600 0 0 0 10.500 10.500Z"], tags="dark night sleep")
g("sun", "system", [C(12, 12, 4), rays(12, 12, 7.600, 9.800)], [C(12, 12, 4)], tags="light day brightness")
g("display", "system", [R(3, 4, 18, 12, 3.500), L(12, 16, 12, 20), L(8, 20, 16, 20)], [R(3, 4, 18, 12, 3.500)], tags="monitor screen")
g("laptop", "system", [R(5, 5, 14, 10, 2.500), L(2.500, 18.500, 21.500, 18.500)], [R(5, 5, 14, 10, 2.500)], tags="computer")
g("keyboard", "system", [R(2.500, 6, 19, 12, 3), D(7, 10), D(12, 10), D(17, 10), L(8, 14.500, 16, 14.500)], [R(2.500, 6, 19, 12, 3)], tags="type")
g("mouse", "system", [R(6.500, 3, 11, 18, 5.500), L(12, 7, 12, 10.500)], [R(6.500, 3, 11, 18, 5.500)], tags="pointer")
g("printer", "system", [P((7, 8), (7, 3.500), (17, 3.500), (17, 8)), R(3, 8, 18, 9, 3), P((7, 17), (7, 20.500), (17, 20.500), (17, 17)), D(17.500, 11.500)], [R(3, 8, 18, 9, 3)], tags="print")
g("settings", "system", [gear(12, 12), C(12, 12, 3)], [gear(12, 12)], tags="gear preferences")
g("terminal", "system", [R(3, 4, 18, 16, 4), P((7.500, 9.500), (11, 13), (7.500, 16.500)), L(13, 16.500, 17, 16.500)], [R(3, 4, 18, 16, 4)], tags="console shell")
g("code", "system", [P((8.500, 7), (3.500, 12), (8.500, 17)), P((15.500, 7), (20.500, 12), (15.500, 17)), L(13.500, 5.500, 10.500, 18.500)], tags="develop")
g("grid", "system", [R(3.500, 3.500, 7, 7, 2.500), R(13.500, 3.500, 7, 7, 2.500), R(3.500, 13.500, 7, 7, 2.500), R(13.500, 13.500, 7, 7, 2.500)], [R(3.500, 3.500, 7, 7, 2.500), R(13.500, 13.500, 7, 7, 2.500)], tags="apps launcher")
g("list", "system", [D(4.500, 7), L(9, 7, 20, 7), D(4.500, 12), L(9, 12, 20, 12), D(4.500, 17), L(9, 17, 20, 17)], tags="rows")
g("layers", "system", [Pc((12, 3.500), (21, 8.500), (12, 13.500), (3, 8.500)), P((3, 12.500), (12, 17.500), (21, 12.500)), P((3, 16.500), (12, 21.500), (21, 16.500))], [Pc((12, 3.500), (21, 8.500), (12, 13.500), (3, 8.500))], tags="stack")
g("window", "system", [R(3, 4, 18, 16, 4), L(3, 9, 21, 9)], [R(3, 4, 18, 16, 4)], tags="app")
g("sidebar", "system", [R(3, 4, 18, 16, 4), L(9.500, 4, 9.500, 20)], [R(3, 4, 9.500, 16, 4)], tags="panel")
g("fullscreen", "system", [RP([(9, 4), (4, 4), (4, 9)], 2.500), RP([(15, 4), (20, 4), (20, 9)], 2.500), RP([(20, 15), (20, 20), (15, 20)], 2.500), RP([(9, 20), (4, 20), (4, 15)], 2.500)], tags="expand maximise")
g("minimize", "system", [P((9, 4), (9, 9), (4, 9)), P((15, 4), (15, 9), (20, 9)), P((20, 15), (15, 15), (15, 20)), P((4, 15), (9, 15), (9, 20))], tags="shrink restore")

# ---- media
g("play", "media", Pc((7, 4.500), (19, 12), (7, 19.500)), [Pc((7, 4.500), (19, 12), (7, 19.500))], tags="start")
g("pause", "media", [L(8, 5, 8, 19), L(16, 5, 16, 19)], tags="hold")
g("stop", "media", R(5, 5, 14, 14, 3.500), [R(5, 5, 14, 14, 3.500)], tags="end")
g("skip-next", "media", [Pc((5, 5), (15, 12), (5, 19)), L(19, 5, 19, 19)], [Pc((5, 5), (15, 12), (5, 19))], tags="forward")
g("skip-previous", "media", [Pc((19, 5), (9, 12), (19, 19)), L(5, 5, 5, 19)], [Pc((19, 5), (9, 12), (19, 19))], tags="back")
g("shuffle", "media", ["M3 7h3c2.400 0 3.500 1.200 4.700 3.100l2.600 4.800c1.100 1.900 2.400 3.100 4.700 3.100H21", "M3 17h3c1.500 0 2.600-.5 3.600-1.500", "M14.400 8.500c1-.9 2.100-1.500 3.600-1.500H21", P((18, 4), (21, 7), (18, 10)), P((18, 14), (21, 17), (18, 20))], tags="random")
g("repeat", "media", [RP([(4, 11), (4, 6.500), (20, 6.500)], 3), RP([(20, 13), (20, 17.500), (4, 17.500)], 3), P((17, 3.500), (20, 6.500), (17, 9.500)), P((7, 14.500), (4, 17.500), (7, 20.500))], tags="loop")


def order():
    return list(GLYPHS)
