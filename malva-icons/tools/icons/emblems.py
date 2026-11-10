"""The emblem vocabulary shared by folders, file pages and drives.

An emblem is drawn once, in a +-100 box, in the same tone model as the app glyphs: P solid, K cut (a hole through the
solid drawn before it), `detail` = dropped in the small cut. The same drawing is
  * engraved into an orchid folder (dark ink with a highlight below it),
  * printed on a lilac page in the hue of the app that opens the file,
  * cut out of a one-colour symbolic icon (P and K swap: the solid becomes the hole).
So "Pictures" on a folder, on an image file and in the symbolic sidebar is one drawing, and the Music, Video and
Image emblems are the Music, Video and Image Viewer app glyphs' own shapes.
Each drawing is centred on its own origin by emblem_shifts.json (centre_emblems.py measures it; emblemshift.py applies
it), so every host puts the origin on the middle of its surface and no emblem needs a hand offset.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

from appfmt import E, P, K, circ, line, poly, rr
import apps


@dataclass
class Emblem:
    els: list                       # full cut
    small: list | None = None       # heavier drawing for 16 to 32 px (None = the full one without its detail elements)
    s: float = 1.0                  # size multiplier against the template's default emblem scale
    dy: float = 0.0                 # no hand offsets: emblem_shifts.json centres every emblem (emblemshift.apply raises if set)
    dx: float = 0.0


def _tf(els, tf):
    return [replace(e, tf=(tf + " " + e.tf).strip()) for e in els]


def person(x: float, y: float = 0.0, k: float = 1.0):
    """A head-and-shoulders bust: (head circle, shoulder dome) centred on x. k scales it about (x, y)."""
    hd = circ(x, y - 34 * k, 22 * k)
    d = (f"M{x - 34 * k:.2f} {y + 62 * k:.2f}V{y + 38 * k:.2f}C{x - 34 * k:.2f} {y + 14 * k:.2f} {x - 18 * k:.2f} {y + 4 * k:.2f} {x:.2f} {y + 4 * k:.2f}"
         f"C{x + 18 * k:.2f} {y + 4 * k:.2f} {x + 34 * k:.2f} {y + 14 * k:.2f} {x + 34 * k:.2f} {y + 38 * k:.2f}V{y + 62 * k:.2f}Z")
    return hd, d


def _people(xs=(-40, 40), k=1.0, **kw):
    out = []
    for x in xs:
        hd, bd = person(x, 0, k)
        out += [P(hd), P(bd, rnd=6)]
    return out


def _music(M):
    sx, sy = apps.GLYPHS["music"].shift
    return _tf(apps._music_els(M, leaf=False), f"translate({sx:g} {sy:g})")


EMBLEMS: dict[str, Emblem] = {}

# ---- places and content kinds (folder emblems; the file kinds below reuse several of them)
EMBLEMS["documents"] = Emblem(
    [P(rr(-50, -70, 100, 140, 14)),
     K(line(-26, -30, 26, -30), stroke=12, detail=True), K(line(-26, -2, 26, -2), stroke=12, detail=True),
     K(line(-26, 26, 4, 26), stroke=12, detail=True)],
    [P(rr(-52, -72, 104, 144, 14)), K(line(-28, -18, 28, -18), stroke=18), K(line(-28, 22, 28, 22), stroke=18)])

EMBLEMS["downloads"] = Emblem(
    [P("M-16 -66H16V-6H44L0 44L-44 -6H-16Z", rnd=10), P(rr(-60, 62, 120, 14, 7))],
    [P("M-20 -68H20V-8H52L0 50L-52 -8H-20Z", rnd=12), P(rr(-64, 64, 128, 20, 8))])

EMBLEMS["pictures"] = Emblem(
    [P("M-72 58L-22 -14L12 34L34 8L72 58Z", rnd=8), P(circ(36, -36, 17))],
    [P("M-76 62L-22 -16L12 34L34 8L76 62Z", rnd=12), P(circ(40, -38, 22))])

EMBLEMS["music"] = Emblem(_music(apps.MUSIC), _music(apps.MUSIC_SMALL), s=0.95)

EMBLEMS["videos"] = Emblem(
    [P(rr(-76, -52, 152, 104, 18)), K(poly((-14, -24), (30, 0), (-14, 24)), rnd=12)],
    [P(rr(-78, -56, 156, 112, 18)), K(poly((-16, -28), (34, 0), (-16, 28)), rnd=15)])

EMBLEMS["desktop"] = Emblem(
    [P(rr(-76, -62, 152, 106, 14)), K(rr(-58, -44, 116, 70, 6)), P(rr(-14, 42, 28, 16, 0)), P(rr(-42, 56, 84, 12, 6))],
    [P(rr(-78, -64, 156, 110, 14)), K(rr(-54, -40, 108, 62, 6)), P(rr(-16, 44, 32, 18, 0)), P(rr(-46, 58, 92, 14, 7))])

EMBLEMS["home"] = Emblem(
    [P("M0 -74L82 -2H62V64H-62V-2H-82Z", rnd=10), K(rr(-15, 18, 30, 46, 6))],
    [P("M0 -78L86 -2H64V68H-64V-2H-86Z", rnd=12), K(rr(-18, 16, 36, 52, 6))])

EMBLEMS["shared"] = Emblem(_people(), _people(k=1.08), s=1.0)

EMBLEMS["locked"] = Emblem(
    [P("M-32 -2V-28A32 32 0 0 1 32 -28V-2", stroke=18), P(rr(-54, -6, 108, 84, 16)), K(circ(0, 26, 12)), K(line(0, 30, 0, 52), stroke=9)],
    [P("M-34 0V-28A34 34 0 0 1 34 -28V0", stroke=22), P(rr(-58, -6, 116, 88, 16)), K(circ(0, 28, 14)), K(line(0, 32, 0, 54), stroke=12)])

EMBLEMS["code"] = Emblem(
    [P("M-30 -46L-76 0L-30 46", stroke=18), P("M30 -46L76 0L30 46", stroke=18), P("M12 -62L-12 62", stroke=14)],
    [P("M-30 -46L-72 0L-30 46", stroke=24), P("M30 -46L72 0L30 46", stroke=24), P("M14 -64L-14 64", stroke=18)])

# ---- file kinds that have no folder (page emblems)
EMBLEMS["text"] = Emblem(
    [P(line(-56, -45, 56, -45), stroke=13), P(line(-56, -15, 56, -15), stroke=13), P(line(-56, 15, 56, 15), stroke=13),
     P(line(-56, 45, 8, 45), stroke=13)],
    [P(line(-58, -38, 58, -38), stroke=26), P(line(-58, 0, 58, 0), stroke=26), P(line(-58, 38, 6, 38), stroke=26)])

EMBLEMS["document"] = Emblem(
    [P(rr(-58, -62, 46, 46, 9)), P(line(8, -50, 58, -50), stroke=12), P(line(8, -28, 58, -28), stroke=12),
     P(line(-58, 6, 58, 6), stroke=12), P(line(-58, 32, 58, 32), stroke=12), P(line(-58, 58, 12, 58), stroke=12)],
    [P(rr(-60, -64, 50, 50, 9)), P(line(10, -52, 60, -52), stroke=26), P(line(-60, 12, 60, 12), stroke=26),
     P(line(-60, 52, 12, 52), stroke=26)])

EMBLEMS["pdf"] = Emblem(            # three lines centred on the page body; the leaf ribbon hangs from the top edge above them
    [P(line(-50, -30, 50, -30), stroke=13), P(line(-50, 0, 50, 0), stroke=13), P(line(-50, 30, 4, 30), stroke=13)],
    [P(line(-54, -22, 54, -22), stroke=26), P(line(-54, 22, 8, 22), stroke=26)])

EMBLEMS["spreadsheet"] = Emblem(
    [P(rr(-72, -62, 144, 124, 14)), K(line(-72, -18, 72, -18), stroke=10), K(line(-72, 24, 72, 24), stroke=10),
     K(line(-14, -62, -14, 62), stroke=10)],
    [P(rr(-74, -64, 148, 128, 14)), K(line(-74, -2, 74, -2), stroke=16), K(line(-8, -64, -8, 64), stroke=16)])

EMBLEMS["presentation"] = Emblem(
    [P(rr(-76, -60, 152, 100, 12)), K(rr(-52, -6, 22, 32, 4)), K(rr(-12, -26, 22, 52, 4)), K(rr(28, -40, 22, 66, 4)),
     P(line(0, 40, 0, 66), stroke=12), P(line(-34, 68, 34, 68), stroke=12)],
    [P(rr(-78, -62, 156, 104, 12)), K(rr(-52, -2, 26, 30, 4)), K(rr(-13, -24, 26, 52, 4)), K(rr(26, -40, 26, 68, 4)),
     P(line(0, 42, 0, 68), stroke=16), P(line(-38, 70, 38, 70), stroke=16)])


def _zip():
    """A zipper: two rows of teeth interlocking down a channel, and the slider with its pull."""
    els = []
    for k in range(5):
        y = -74 + k * 27
        els.append(P(rr(-31, y, 29, 15, 4)))
        els.append(P(rr(2, y + 13.5, 29, 15, 4)))
    els.append(P(rr(-21, 56, 42, 54, 13)))
    els.append(K(rr(-8, 70, 16, 26, 5)))
    return els


EMBLEMS["archive"] = Emblem(_zip(), [P(rr(-34, -74, 68, 24, 5)), P(rr(-34, -40, 68, 24, 5)), P(rr(-34, -6, 68, 24, 5)),
                                    P(rr(-24, 40, 48, 64, 14)), K(rr(-9, 56, 18, 30, 5))], s=0.9)


EMBLEMS["network"] = Emblem(
    [P(circ(0, -42, 20)), P(circ(-50, 38, 20)), P(circ(50, 38, 20)),
     P("M0 -42L-50 38M0 -42L50 38M-50 38H50", stroke=11)],
    [P(circ(0, -44, 25)), P(circ(-52, 40, 25)), P(circ(52, 40, 25)),
     P("M0 -44L-52 40M0 -44L52 40M-52 40H52", stroke=15)])

# ---- more folder emblems
EMBLEMS["search"] = Emblem(
    [P(circ(-20, -20, 50)), K(circ(-20, -20, 29)), P(line(18, 18, 62, 62), stroke=24)],
    [P(circ(-22, -22, 52)), K(circ(-22, -22, 27)), P(line(18, 18, 64, 64), stroke=30)])

EMBLEMS["template"] = Emblem(
    [P(rr(-54, -70, 108, 140, 14)), K(line(0, -26, 0, 26), stroke=14), K(line(-26, 0, 26, 0), stroke=14)],
    [P(rr(-56, -72, 112, 144, 14)), K(line(0, -28, 0, 28), stroke=20), K(line(-28, 0, 28, 0), stroke=20)])

EMBLEMS["drop"] = Emblem(
    [P("M-22 -70H22V-4H58L0 62L-58 -4H-22Z", rnd=10)],
    [P("M-26 -72H26V-6H64L0 68L-64 -6H-26Z", rnd=12)])

# ---- more file kinds (page emblems)
def _gear_pts(n=8, ro=70, ri=52):
    pts = []
    pitch = 2 * math.pi / n
    for i in range(n):
        a = i * pitch
        for da, r in ((-0.30, ri), (-0.17, ro), (0.17, ro), (0.30, ri)):
            pts.append((r * math.cos(a + da * pitch * 2.0 - math.pi / 2), r * math.sin(a + da * pitch * 2.0 - math.pi / 2)))
    return pts


def _chip(pins, pl, pw, body=44, hole=20):
    els = [P(rr(-body, -body, 2 * body, 2 * body, 12)), K(rr(-hole, -hole, 2 * hole, 2 * hole, 6))]
    for v in pins:
        els += [P(line(v, -body - pl, v, -body + 2), stroke=pw), P(line(v, body - 2, v, body + pl), stroke=pw),
                P(line(-body - pl, v, -body + 2, v), stroke=pw), P(line(body - 2, v, body + pl, v), stroke=pw)]
    return els


EMBLEMS["certificate"] = Emblem(_tf(
    [P(poly((-38, 18), (-10, 28), (-14, 80), (-30, 66), (-50, 78)), rnd=6), P(poly((38, 18), (10, 28), (14, 80), (30, 66), (50, 78)), rnd=6),
     P(circ(0, -22, 48)), K("M-22 -20L-6 -4L24 -42", stroke=13)], "translate(0 -5)"),
    _tf([P(poly((-40, 16), (-8, 28), (-12, 82), (-30, 66), (-52, 80)), rnd=8), P(poly((40, 16), (8, 28), (12, 82), (30, 66), (52, 80)), rnd=8),
         P(circ(0, -22, 50)), K("M-24 -20L-6 -2L26 -42", stroke=17)], "translate(0 -5) scale(.93)"))

EMBLEMS["feed"] = Emblem(
    [P(circ(-38, 38, 15)), P("M-38 -4A42 42 0 0 1 4 38", stroke=20), P("M-38 -44A82 82 0 0 1 44 38", stroke=20)],
    [P(circ(-38, 38, 18)), P("M-38 -4A42 42 0 0 1 4 38", stroke=26), P("M-38 -44A82 82 0 0 1 44 38", stroke=26)])

EMBLEMS["puzzle"] = Emblem(_tf(
    [P(rr(-46, -34, 92, 92, 12)), P(circ(0, -46, 18)), P(circ(46, 12, 18)), K(circ(-46, 12, 18)), K(circ(0, 58, 18))], "translate(-9 3)"),
    _tf([P(rr(-48, -34, 96, 94, 12)), P(circ(0, -48, 20)), P(circ(48, 12, 20)), K(circ(-48, 12, 20)), K(circ(0, 60, 20))], "translate(-9 3)"))

EMBLEMS["box"] = Emblem(
    [P(poly((0, -72), (62, -36), (62, 34), (0, 70), (-62, 34), (-62, -36)), rnd=8), K("M-62 -36L0 0L62 -36", stroke=10), K(line(0, 0, 0, 70), stroke=10)],
    [P(poly((0, -76), (66, -38), (66, 36), (0, 74), (-66, 36), (-66, -38)), rnd=10), K("M-66 -38L0 0L66 -38", stroke=14), K(line(0, 0, 0, 74), stroke=14)])

EMBLEMS["gear"] = Emblem(
    [P(poly(*_gear_pts()), rnd=8), K(circ(0, 0, 24))],
    [P(poly(*_gear_pts(8, 74, 54)), rnd=10), K(circ(0, 0, 24))])

EMBLEMS["chip"] = Emblem(_chip((-26, 0, 26), 18, 14), _chip((-20, 20), 20, 20, body=42, hole=18))

EMBLEMS["library"] = Emblem(
    [P(rr(-70, -56, 38, 116, 8)), P(rr(-19, -72, 38, 132, 8)), P(poly((30, -50), (62, -58), (78, 56), (46, 64)), rnd=8),
     K(line(-70, -22, -32, -22), stroke=9, detail=True), K(line(-70, 30, -32, 30), stroke=9, detail=True), K(line(-19, -34, 19, -34), stroke=9, detail=True)],
    _tf([P(rr(-72, -56, 42, 116, 8)), P(rr(-21, -72, 42, 132, 8)), P(poly((32, -50), (66, -58), (82, 56), (48, 64)), rnd=8)], "translate(-7 0)"))

EMBLEMS["font"] = Emblem(
    [P("M-60 62L0 -68L60 62", stroke=24), P(line(-34, 22, 34, 22), stroke=20)],
    _tf([P("M-62 64L0 -70L62 64", stroke=30), P(line(-36, 24, 36, 24), stroke=26)], "scale(.93)"))

_hd, _bd = person(0, 0, 1.2)
EMBLEMS["contact"] = Emblem(_tf([P(_hd), P(_bd, rnd=6)], "translate(0 -4)"))

EMBLEMS["calendar"] = Emblem(_tf(
    [P(rr(-68, -52, 136, 122, 16)), K(line(-68, -14, 68, -14), stroke=12), P(line(-36, -76, -36, -42), stroke=16), P(line(36, -76, 36, -42), stroke=16)]
    + [K(rr(x, y, 24, 20, 4), detail=True) for x, y in ((-48, 6), (-12, 6), (24, 6), (-48, 36), (-12, 36))], "translate(0 5)"),
    _tf([P(rr(-70, -52, 140, 124, 16)), K(line(-70, -10, 70, -10), stroke=16), P(line(-36, -78, -36, -42), stroke=20), P(line(36, -78, 36, -42), stroke=20),
         K(rr(-44, 14, 30, 26, 4)), K(rr(14, 14, 30, 26, 4))], "translate(0 5)"))

EMBLEMS["shapes"] = Emblem(
    [P(circ(-34, -38, 30)), P(rr(2, -4, 66, 66, 10)), P(poly((-74, 66), (-38, 4), (-2, 66)), rnd=8)],
    [P(circ(-34, -38, 32)), P(rr(2, -4, 68, 68, 10)), P(poly((-76, 68), (-38, 2), (-2, 68)), rnd=10)])

EMBLEMS["globe"] = Emblem(
    [P(circ(0, 0, 66)), K(line(-66, 0, 66, 0), stroke=10), K("M0 -66A30 66 0 1 0 0 66A30 66 0 1 0 0 -66Z", stroke=10)],
    [P(circ(0, 0, 68)), K(line(-68, 0, 68, 0), stroke=14), K("M0 -68A30 68 0 1 0 0 68A30 68 0 1 0 0 -68Z", stroke=14)])

EMBLEMS["disc"] = Emblem(
    [P(circ(0, 0, 66)), K(circ(0, 0, 20)), K("M0 -42A42 42 0 0 1 42 0", stroke=9)],
    [P(circ(0, 0, 68)), K(circ(0, 0, 22)), K("M0 -44A44 44 0 0 1 44 0", stroke=13)])

EMBLEMS["book"] = Emblem(
    [P(rr(-74, -52, 68, 104, 8)), P(rr(6, -52, 68, 104, 8)),
     K(line(-58, -22, -22, -22), stroke=9, detail=True), K(line(-58, 4, -22, 4), stroke=9, detail=True), K(line(22, -22, 58, -22), stroke=9, detail=True), K(line(22, 4, 58, 4), stroke=9, detail=True)],
    [P(rr(-76, -54, 70, 108, 8)), P(rr(6, -54, 70, 108, 8))])

EMBLEMS["prompt"] = Emblem(
    _tf([P("M-60 -40L-14 0L-60 40", stroke=22), P(line(4, 46, 62, 46), stroke=22)], "translate(0 -3)"),
    _tf([P("M-62 -42L-14 0L-62 42", stroke=28), P(line(4, 48, 64, 48), stroke=28)], "translate(0 -3)"))

# the page emblems that are the folder emblems
EMBLEMS["image"] = replace(EMBLEMS["pictures"])
EMBLEMS["audio"] = EMBLEMS["music"]
EMBLEMS["video"] = EMBLEMS["videos"]


def invert(els):
    """The symbolic form of an emblem cut out of a solid: its solid parts become holes and its holes become solid
    again (a hole inside the emblem is the solid body showing through, so it is drawn back after the cut)."""
    cut = [replace(e, tone="k") for e in els if e.tone in ("p", "d")]
    back = [replace(e, tone="p") for e in els if e.tone == "k"]
    return cut + back


import emblemshift                                         # noqa: E402  every emblem on the middle of its own box
emblemshift.apply(EMBLEMS)
