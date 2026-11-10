"""The Malva object icons: folders, storage, people and files. Geometry is in canvas units (1024); see objfmt.py for
the format and emblems.py for the glyph vocabulary. Each template is one function; each icon is a template plus
parameters, so every folder has the same silhouette, every page the same outline, every drive the same body."""
from __future__ import annotations

import math
from dataclasses import replace

import mi_geom as g
import appfmt as A
from appfmt import E, P, Dm, K, circ, line, poly, rr
from objfmt import (Obj, Part, sqpoly, rect, rect_c, rect_top, lgrad, path, stroke_path, emblem_part, group, C0,
                    ORCHID_FRONT, ORCHID_BACK, LILAC, LILAC_FOLD, LEAF_SHEET, INK, PAGE_EDGE, ink_for_hue)
from emblems import EMBLEMS, invert, person

u = lambda uid, n: f"url(#{uid}-{n})"
LILAC_SOLID = "#F3E4F1"
LEAF_ON_LILAC_DARK = A.LEAF_ON_LILAC

# hardware is deep plum with a pink-lilac top face: the supplied tile gradient, so it is darker than the orchid
# containers and lighter than the dusk wallpaper, with a lid that catches the light
METAL_LID = ("#D99FCB", "#C07AB0")
METAL_BODY = (A.PLUM_LIGHT, "#6F2B5F")
METAL_DEEP = ("#8C3B78", A.PLUM_DARK)
PLUM_DISC = (A.PLUM_LIGHT, A.PLUM_DARK)           # the supplied tile gradient: people and cards wear it


def emb_els(name: str, small: bool):
    e = EMBLEMS[name]
    return (e.small if (small and e.small is not None) else e.els), e


# =============================================================================================== folders
F_L, F_R, F_TOP, F_BOT = 72, 952, 152, 872
F_BACK_TOP, F_TAB_R = 224, 432
F_FRONT_TOP = {False: 348, True: 372}
F_PANEL_R = 64
F_EMB = {False: 1.9, True: 2.3}


def folder_back_path():
    return sqpoly([(F_L, F_TOP), (F_TAB_R, F_TOP), (F_TAB_R, F_BACK_TOP), (F_R, F_BACK_TOP), (F_R, F_BOT), (F_L, F_BOT)],
                  [44, 40, 28, F_PANEL_R, F_PANEL_R, F_PANEL_R])


def folder_front_path(small: bool, open_: bool = False):
    top = F_FRONT_TOP[small] if not open_ else (412 if small else 396)
    if open_:
        return sqpoly([(190, top), (834, top), (F_R, F_BOT), (F_L, F_BOT)], [44, 44, F_PANEL_R, F_PANEL_R]), top
    return rect(F_L, top, F_R - F_L, F_BOT - top, F_PANEL_R), top


def folder_parts(uid: str, small: bool, emb: str | None = None, open_: bool = False):
    front_d, top = folder_front_path(small, open_)
    sheet = rect(150, 266, 724, 220, 36) if open_ else rect(128, 270, 768, 160, 36)
    sy = 266 if open_ else 270
    parts = [
        Part("back", path(folder_back_path(), u(uid, "back")), lgrad(uid, "back", ORCHID_BACK, y0=F_TOP, y1=F_BOT)),
    ]
    if open_:      # a lilac page leans behind the leaf one
        parts.append(Part("sheet", path(rect(214, 240, 640, 200, 32), u(uid, "lil"), tf="rotate(3 534 340)"),
                          lgrad(uid, "lil", LILAC, y0=240, y1=440)))
    parts += [
        Part("sheet", path(sheet, u(uid, "leaf")), lgrad(uid, "leaf", LEAF_SHEET, y0=sy, y1=sy + 160)),
        Part("front", path(front_d, u(uid, "front")), lgrad(uid, "front", ORCHID_FRONT, y0=top, y1=F_BOT)),
    ]
    if not small:     # the lit top edge: the front panel again, shifted 8 down, clipped to itself; 8 px of light remain
        parts.append(Part("rim",
                          f'<g clip-path="url(#{uid}-fc)">{path(front_d, u(uid, "rim"))}'
                          f'{path(front_d, u(uid, "front"), tf="translate(0 8)")}</g>',
                          lgrad(uid, "rim", [(0, "#FFFFFF", 0.5), (1, "#FFFFFF", 0)], y0=top, y1=top + 64)
                          + f'<clipPath id="{uid}-fc"><path d="{front_d}"/></clipPath>'))
    if emb and not open_:
        els, e = emb_els(emb, small)
        cy = top + (F_BOT - top) / 2 + e.dy
        parts.append(emblem_part(els, uid, C0 + e.dx, cy, F_EMB[small] * e.s, INK, deboss=True, small=small))
    return parts


def folder_sym(emb: str | None = None, open_: bool = False):
    front_d, top = folder_front_path(False, open_)
    els = [Dm(folder_back_path()), P(front_d)]
    if emb and not open_:
        e = EMBLEMS[emb]
        cy = top + (F_BOT - top) / 2 + e.dy
        s = F_EMB[False] * e.s
        els += [replace(x, tf=f"translate({C0 + e.dx:g} {cy:g}) scale({s:g}) {x.tf}".strip()) for x in invert([y for y in e.els])]
    return els


# =============================================================================================== trash bin
def bin_paths():
    body = sqpoly([(212, 344), (812, 344), (756, 884), (268, 884)], [30, 30, 56, 56])
    lid = rect(172, 236, 680, 84, 40)
    handle = rect(412, 172, 200, 84, 34)
    return body, lid, handle


def trash_parts(uid: str, small: bool, full: bool):
    body, lid, handle = bin_paths()
    parts = []
    if full:
        edge = f' stroke="{PAGE_EDGE}" stroke-width="12" stroke-linejoin="round"'
        sheets = (path(rect(268, 108, 250, 300, 28), u(uid, "leaf"), tf="rotate(-9 393 258)")
                  + path(rect(470, 132, 270, 290, 28), u(uid, "lil"), tf="rotate(8 605 277)", extra=edge))
        parts.append(Part("sheet", sheets, lgrad(uid, "leaf", LEAF_SHEET, y0=108, y1=408) + lgrad(uid, "lil", LILAC, y0=130, y1=420)))
    parts.append(Part("back", path(handle, u(uid, "back")) + path(lid, u(uid, "back")),
                      lgrad(uid, "back", ORCHID_BACK, y0=172, y1=320)))
    parts.append(Part("front", path(body, u(uid, "front")), lgrad(uid, "front", ORCHID_FRONT, y0=344, y1=884)))
    ribs = "".join(stroke_path(f"M{x} 450V{790}", INK, 34 if small else 26, 0.34) for x in (392, 512, 632))
    parts.append(Part("detail", ribs if not small else "".join(stroke_path(f"M{x} 460V780", INK, 44, 0.34) for x in (420, 604))))
    return parts


def trash_sym(full: bool):
    body, lid, handle = bin_paths()
    els = []
    if full:
        els += [Dm(rect(268, 108, 250, 300, 28), tf="rotate(-9 393 258)"), Dm(rect(470, 132, 270, 290, 28), tf="rotate(8 605 277)")]
    els += [P(handle), P(lid), P(body)]
    els += [K(f"M{x} 450V790", stroke=34) for x in (392, 512, 632)]
    return els


# =============================================================================================== drives
def _metal_grads(uid, lid_y, body_y0, body_y1):
    return (lgrad(uid, "lid", METAL_LID, y0=lid_y, y1=body_y0) + lgrad(uid, "body", METAL_BODY, y0=body_y0, y1=body_y1)
            + lgrad(uid, "leaf", LEAF_SHEET, y0=body_y0, y1=body_y1) + lgrad(uid, "pl", LILAC, y0=body_y0, y1=body_y1))


DRIVE = {  # kind: (x0, x1, lid_top, body_top, bottom)
    "internal": (72, 952, 296, 404, 728),
    "external": (72, 856, 232, 352, 792),
}


DRIVE_EMB_SMALL = {"locked": 0.86}


def drive_parts(uid: str, small: bool, kind: str = "internal", emb: str | None = None):
    x0, x1, lid_t, body_t, bot = DRIVE["external" if kind == "external" else "internal"]
    w = x1 - x0
    lid = rect_top(x0, lid_t, w, body_t - lid_t + 80, 76, 0)
    body = rect(x0, body_t, w, bot - body_t, 76)
    parts = []
    defs = _metal_grads(uid, lid_t, body_t, bot)
    if kind == "external":     # the cable plug sits behind the body: only its end shows
        plug = rect(x1 - 40, 500, 128, 124, 24)
        parts.append(Part("plug", path(plug, u(uid, "lid")) + path(rect(x1 + 36, 536, 36, 22, 6), INK, 0.55)
                          + path(rect(x1 + 36, 568, 36, 22, 6), INK, 0.55)))
    parts.append(Part("lid", path(lid, u(uid, "lid")), defs))
    parts.append(Part("body", path(body, u(uid, "body"))))
    cy = (body_t + bot) / 2
    if emb:      # network / encrypted: a lilac emblem on the front instead of the vents
        els, e = emb_els(emb, small)
        k = 1.55 if not small else 1.85 * DRIVE_EMB_SMALL.get(emb, 1.0)       # the lock is taller than the slab's small cut can hold at 1.85
        parts.append(emblem_part(els, uid, 396, cy, k * e.s, LILAC_SOLID, deboss=False, small=small))
    else:
        n, wid, gap = (4, 30 if not small else 40, 36 if not small else 40)
        slots = "".join(path(rect(x0 + 96 + k * (wid + gap), cy - (bot - body_t) * 0.26, wid, (bot - body_t) * 0.52, wid / 2), INK, 0.55)
                        for k in range(n - (1 if small else 0)))
        parts.append(Part("detail", slots))
    led_r = 30 if not small else 40
    parts.append(Part("accent", path(circ(x1 - 110, cy + (bot - body_t) * 0.2, led_r), u(uid, "leaf"))))
    return parts


def drive_sym(kind="internal", emb=None):
    x0, x1, lid_t, body_t, bot = DRIVE["external" if kind == "external" else "internal"]
    w = x1 - x0
    els = []
    if kind == "external":
        els.append(P(rect(x1 - 40, 500, 128, 124, 24)))
    els += [Dm(rect_top(x0, lid_t, w, body_t - lid_t + 80, 76, 0)), P(rect(x0, body_t, w, bot - body_t, 76))]
    cy = (body_t + bot) / 2
    if emb:
        e = EMBLEMS[emb]
        els += [replace(x, tf=f"translate(396 {cy:g}) scale({1.55 * e.s:g}) {x.tf}".strip()) for x in invert(e.els)]
    else:
        els += [K(rect(x0 + 96 + k * 66, cy - (bot - body_t) * 0.26, 30, (bot - body_t) * 0.52, 15)) for k in range(4)]
    els.append(K(circ(x1 - 110, cy + (bot - body_t) * 0.2, 30)))
    return els


# =============================================================================================== removable media
def _rot(body: str, deg: float = -45.0) -> str:
    return f'<g transform="rotate({deg:g} {C0} {C0})">{body}</g>'


def usb_parts(uid: str, small: bool):
    """A stick lying on the diagonal (the pen of Text Editor and the key of Passwords lie on it too)."""
    defs = (lgrad(uid, "body", METAL_BODY, y0=C0 - 142, y1=C0 + 142) + lgrad(uid, "lid", METAL_LID, y0=C0 - 98, y1=C0 + 98)
            + lgrad(uid, "leaf", LEAF_SHEET, y0=C0 - 40, y1=C0 + 40))
    plug = rect(614, C0 - 98, 252, 196, 26)
    body = rect(160, C0 - 144, 486, 288, 72)
    holes = path(rect(770, C0 - 54, 62, 40, 8), INK, 0.6) + path(rect(770, C0 + 14, 62, 40, 8), INK, 0.6)
    hole = path(circ(268, C0, 76 if small else 64), INK, 0.45) + path(circ(268, C0, 46 if small else 38), u(uid, "leaf"))
    return [Part("plug", _rot(path(plug, u(uid, "lid")) + holes), defs),
            Part("body", _rot(path(body, u(uid, "body")))),
            Part("accent", _rot(hole))]


def usb_sym():
    plug = rect(614, C0 - 98, 252, 196, 26)
    body = rect(160, C0 - 144, 486, 288, 72)
    rot = f"rotate(-45 {C0} {C0})"
    return [P(plug, tf=rot), P(body, tf=rot), K(rect(770, C0 - 54, 62, 40, 8), tf=rot), K(rect(770, C0 + 14, 62, 40, 8), tf=rot),
            K(circ(268, C0, 46), tf=rot)]


SD_PTS = [(256, 128), (668, 128), (792, 252), (792, 896), (256, 896)]
SD_LABEL = (344, 520, 360, 290)      # a plain label: with text lines it read as a document
SD_R = [44, 34, 34, 44, 44]


def sd_parts(uid: str, small: bool):
    card = sqpoly(SD_PTS, SD_R)
    defs = (lgrad(uid, "body", METAL_BODY, y0=128, y1=896) + lgrad(uid, "lid", METAL_LID, y0=150, y1=270)
            + lgrad(uid, "pl", LILAC, y0=520, y1=810) + lgrad(uid, "leaf", LEAF_SHEET, y0=340, y1=460))
    pins = "".join(path(rect(312 + 58 * k, 150, 38 if not small else 44, 120, 9), u(uid, "lid")) for k in range(6 if not small else 5))
    label = path(rect(SD_LABEL[0], SD_LABEL[1], SD_LABEL[2], SD_LABEL[3], 30), u(uid, "pl"))
    return [Part("body", path(card, u(uid, "body")), defs), Part("detail", pins), Part("sheet", label),
            Part("accent", path(rect(248, 350, 44, 96, 12), u(uid, "leaf")))]


def sd_sym():
    return [P(sqpoly(SD_PTS, SD_R)), K("".join(rect(312 + 58 * k, 150, 38, 120, 9) for k in range(6))), K(rect(*SD_LABEL, 30))]


def disc_parts(uid: str, small: bool):
    R_, hub = 424, 170
    w = 14 if not small else 44
    defs = (lgrad(uid, "lil", LILAC, y0=88, y1=936) + lgrad(uid, "body", METAL_BODY, y0=C0 - hub, y1=C0 + hub)
            + lgrad(uid, "leaf", LEAF_SHEET, y0=C0 - 70, y1=C0 + 70))
    a0, a1 = math.radians(-74), math.radians(-28)
    r1 = 392
    wedge = (f"M{C0 + 190 * math.cos(a0):.1f} {C0 + 190 * math.sin(a0):.1f}L{C0 + r1 * math.cos(a0):.1f} {C0 + r1 * math.sin(a0):.1f}"
             f"A{r1} {r1} 0 0 1 {C0 + r1 * math.cos(a1):.1f} {C0 + r1 * math.sin(a1):.1f}L{C0 + 190 * math.cos(a1):.1f} {C0 + 190 * math.sin(a1):.1f}"
             f"A190 190 0 0 0 {C0 + 190 * math.cos(a0):.1f} {C0 + 190 * math.sin(a0):.1f}Z")
    disc = (path(circ(C0, C0, R_), u(uid, "lil")) + stroke_path(f"M{C0 - R_ + w / 2} {C0}a{R_ - w / 2} {R_ - w / 2} 0 1 0 {2 * (R_ - w / 2)} 0a{R_ - w / 2} {R_ - w / 2} 0 1 0 {-2 * (R_ - w / 2)} 0Z", PAGE_EDGE, w, 0.9))
    parts = [Part("disc", disc, defs)]
    if not small:
        parts.append(Part("detail", stroke_path(f"M{C0 - 330} {C0}a330 330 0 1 0 660 0a330 330 0 1 0 -660 0Z", PAGE_EDGE, 6, 0.30)
                          + path(wedge, "#FFFFFF", 0.55)))
    parts.append(Part("body", path(circ(C0, C0, hub), u(uid, "body")) + stroke_path(f"M{C0 - hub} {C0}a{hub} {hub} 0 1 0 {2 * hub} 0a{hub} {hub} 0 1 0 {-2 * hub} 0Z", PAGE_EDGE, 10, 0.55)))
    parts.append(Part("accent", path(circ(C0, C0, 66 if not small else 84), u(uid, "leaf")) + path(circ(C0, C0, 26 if not small else 30), INK, 0.7)))
    return parts


def disc_sym():
    return [P(circ(C0, C0, 424)), K(circ(C0, C0, 170)), P(circ(C0, C0, 128)), K(circ(C0, C0, 48))]


CLOUD = [("rect", (104, 548, 816, 246, 123)), ("c", (354, 528, 150)), ("c", (560, 466, 202)), ("c", (746, 590, 130))]


CLOUD_ARROW = [P("M0 52V-48M-40 -8L0 -48L40 -8", stroke=20)]
# On the axis the stem lies on the edge between two pixels at 16 and 32 px, so it must be wider than one pixel to show: 30 x 2.3 = 69 units
# is 1.08 px, two pixels at 54 %. (At 20 wide it was 0.72 px, two pixels at 36 %: there was only a faint grey line.)
CLOUD_ARROW_SMALL = [P("M0 52V-48M-40 -8L0 -48L40 -8", stroke=30)]
CLOUD_AXIS = 512        # the arrow stands on the canvas axis, which is also the middle of the cloud's base (104..920)


def _cloud_shapes():
    return [rect(*a) if k == "rect" else circ(*a) for k, a in CLOUD]


def cloud_parts(uid: str, small: bool):
    w = 14 if not small else 40
    defs = lgrad(uid, "lil", LILAC, y0=262, y1=794)
    sh = _cloud_shapes()
    edge = "".join(f'<path d="{d}" fill="{PAGE_EDGE}" stroke="{PAGE_EDGE}" stroke-width="{2 * w}" stroke-linejoin="round"/>' for d in sh)
    fill = "".join(path(d, u(uid, "lil")) for d in sh)
    arrow = CLOUD_ARROW_SMALL if small else CLOUD_ARROW
    ar = (f'<g transform="translate({CLOUD_AXIS} {650 if not small else 630}) scale({1.9 if not small else 2.3})" color="{LEAF_ON_LILAC_DARK}">'
          f'{group(arrow, uid + "-a")[1]}</g>')
    return [Part("disc", edge + fill, defs), Part("emblem", ar, group(arrow, uid + "-a")[0])]


def cloud_sym():
    return ([P(d) for d in _cloud_shapes()]
            + [replace(x, tone="k", tf=f"translate({CLOUD_AXIS} 650) scale(1.9) {x.tf}".strip()) for x in CLOUD_ARROW])


# =============================================================================================== people
OUT_DISC = "M-200 -200H1224V1224H-200Z" + circ(C0, C0, 440)      # everything outside the avatar disc (opposite windings)


def shoulders(cx, cy, rx, ry, n=2.8):
    return A.superellipse_path(cx, cy, rx, ry, n, m=4)


# Eight same-shape discs cannot all be told apart by hue alone under a colour-blind simulation, so each hue also gets its
# own lightness (a search that maximises the worst dE00 over every pair and every vision type: 0.3 with one shared
# lightness, 5.2 with these). OKLCH chroma, light-stop and dark-stop lightness of the app-tile gradient.
AVATAR_TILE = {8: dict(c=0.126, l=0.498, ld=0.24), 36: dict(c=0.132, l=0.553, ld=0.379), 64: dict(c=0.17, l=0.621, ld=0.466),
               128: dict(c=0.17, l=0.442, ld=0.263), 184: dict(c=0.132, l=0.64, ld=0.267), 240: dict(c=0.141, l=0.518, ld=0.352),
               290: dict(c=0.17, l=0.443, ld=0.24)}
SHIELD = "M-70 -64H-12L0 -52L12 -64H70V10C70 54 36 80 0 96C-36 80 -70 54 -70 10Z"
CHECK = "M-30 8L-8 30L32 -16"


def avatar_parts(uid: str, small: bool, hue=None, variant: str = "user"):
    disc = circ(C0, C0, 440)
    if variant == "guest":
        stops = (g.oklch_to_hex(0.55, 0.045, 338), g.oklch_to_hex(0.33, 0.045, 338))
    else:
        stops = PLUM_DISC if hue is None else A.Tile(h=hue, **AVATAR_TILE[hue]).stops()
    hd_y, hd_r, sh_y, sh_rx, sh_ry = (396, 132, 836, 300, 250) if not small else (386, 152, 856, 330, 280)
    defs = (f'<linearGradient id="{uid}-av" gradientUnits="userSpaceOnUse" x1="200" y1="100" x2="824" y2="924">'
            f'<stop offset="0" stop-color="{stops[0]}"/><stop offset="1" stop-color="{stops[1]}"/></linearGradient>'
            f'<radialGradient id="{uid}-hl" cx=".3" cy=".18" r=".7"><stop offset="0" stop-color="#fff" stop-opacity=".22"/>'
            f'<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
            + lgrad(uid, "lil", LILAC, y0=220, y1=940) + f'<clipPath id="{uid}-c"><path d="{disc}"/></clipPath>')
    op = ' opacity=".82"' if variant == "guest" else ""
    person_svg = (f'<g clip-path="url(#{uid}-c)"{op}>{path(shoulders(C0, sh_y, sh_rx, sh_ry), u(uid, "lil"))}</g>'
                  f'<g{op}>{path(circ(C0, hd_y, hd_r), u(uid, "lil"))}</g>')
    core = path(disc, u(uid, "av")) + path(disc, u(uid, "hl"))
    parts = []
    if variant == "admin":
        bx, by = 772, 772
        defs += (f'<mask id="{uid}-bm" maskUnits="userSpaceOnUse" x="0" y="0" width="1024" height="1024"><rect width="1024" height="1024" fill="#fff"/>'
                 f'<circle cx="{bx}" cy="{by}" r="{188 if not small else 204}" fill="#000"/></mask>' + lgrad(uid, "leaf", LEAF_SHEET, y0=by - 150, y1=by + 150))
        parts.append(Part("disc", f'<g mask="url(#{uid}-bm)">{core}</g>', defs))
        parts.append(Part("emblem", f'<g mask="url(#{uid}-bm)">{person_svg}</g>'))
        sc = 1.5 if not small else 1.7
        edge = f' stroke="{LEAF_SHEET[1]}" stroke-width="10" stroke-linejoin="round"'
        shield = (f'<g transform="translate({bx} {by - 6}) scale({sc})">{path(SHIELD, u(uid, "leaf"), extra=edge)}'
                  f'{stroke_path(CHECK, INK, 15 if not small else 19, 0.85)}</g>')
        parts.append(Part("accent", shield))
    else:
        parts.append(Part("disc", core, defs))
        parts.append(Part("emblem", person_svg))
    return parts


def avatar_sym(variant: str = "user"):
    els = [P(circ(C0, C0, 440))]
    cuts = [K(circ(C0, 396, 132)), K(shoulders(C0, 836, 300, 250))]
    if variant == "guest":      # an outline figure: the person is cut out, then drawn back smaller, leaving a line
        return els + cuts + [P(circ(C0, 396, 132 - 34)), P(shoulders(C0, 836, 300 - 34, 250 - 34)), K(OUT_DISC)]
    if variant == "admin":
        cuts.append(K(circ(772, 772, 188)))
        return els + cuts + [P(SHIELD, rnd=10, tf="translate(772 766) scale(1.5)"), K(CHECK, stroke=15, tf="translate(772 766) scale(1.5)")]
    return els + cuts


def group_parts(uid: str, small: bool):
    """Two people, the one in front larger: the pair reads at 16 px where a trio turns into three blobs."""
    disc = circ(C0, C0, 440)
    defs = (f'<linearGradient id="{uid}-av" gradientUnits="userSpaceOnUse" x1="200" y1="100" x2="824" y2="924">'
            f'<stop offset="0" stop-color="{PLUM_DISC[0]}"/><stop offset="1" stop-color="{PLUM_DISC[1]}"/></linearGradient>'
            f'<radialGradient id="{uid}-hl" cx=".3" cy=".18" r=".7"><stop offset="0" stop-color="#fff" stop-opacity=".22"/>'
            f'<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
            + lgrad(uid, "lil", LILAC, y0=220, y1=940) + f'<clipPath id="{uid}-c"><path d="{disc}"/></clipPath>')
    G = GROUP[small]
    # a ring of plum cut around the front figure keeps it apart from the one behind (mask on the back group)
    ring = (f'<mask id="{uid}-rm" maskUnits="userSpaceOnUse" x="0" y="0" width="1024" height="1024"><rect width="1024" height="1024" fill="#fff"/>'
            f'<path d="{circ(*G["fh"], G["fr"] + 28)}" fill="#000"/><path d="{shoulders(*G["fs"])}" fill="#000" stroke="#000" stroke-width="56" stroke-linejoin="round"/></mask>')
    back = (path(circ(*G["bh"], G["br"]), u(uid, "lil")) + f'<g clip-path="url(#{uid}-c)">{path(shoulders(*G["bs"]), u(uid, "lil"))}</g>')
    front = (path(circ(*G["fh"], G["fr"]), u(uid, "lil")) + f'<g clip-path="url(#{uid}-c)">{path(shoulders(*G["fs"]), u(uid, "lil"))}</g>')
    return [Part("disc", path(disc, u(uid, "av")) + path(disc, u(uid, "hl")), defs + ring),
            Part("detail", f'<g opacity="{G["op"]}" mask="url(#{uid}-rm)">{back}</g>'),
            Part("emblem", front)]


GROUP = {False: dict(fh=(412, 392), fr=116, fs=(412, 846, 262, 250), bh=(668, 366), br=88, bs=(668, 806, 196, 214), op=0.72),
         True: dict(fh=(410, 388), fr=128, fs=(410, 858, 280, 262), bh=(672, 362), br=98, bs=(672, 818, 210, 226), op=0.78)}


def group_sym():
    G = GROUP[False]
    return [P(circ(C0, C0, 440)), K(circ(*G["bh"], G["br"])), K(shoulders(*G["bs"])), K(circ(*G["fh"], G["fr"] + 28)),
            K(shoulders(G["fs"][0], G["fs"][1], G["fs"][2] + 28, G["fs"][3] + 28)),
            P(circ(*G["fh"], G["fr"])), P(shoulders(*G["fs"])), K(OUT_DISC)]


def card_parts(uid: str, small: bool):
    body = rect(72, 232, 880, 560, 64)
    slot = rect_c(C0, 276, 150, 30, 15)
    defs = (f'<linearGradient id="{uid}-av" gradientUnits="userSpaceOnUse" x1="140" y1="232" x2="884" y2="792">'
            f'<stop offset="0" stop-color="{PLUM_DISC[0]}"/><stop offset="1" stop-color="{PLUM_DISC[1]}"/></linearGradient>'
            f'<radialGradient id="{uid}-hl" cx=".3" cy=".18" r=".7"><stop offset="0" stop-color="#fff" stop-opacity=".22"/>'
            f'<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
            f'<mask id="{uid}-sm" maskUnits="userSpaceOnUse" x="0" y="0" width="1024" height="1024"><rect width="1024" height="1024" fill="#fff"/>'
            f'<path d="{slot}" fill="#000"/></mask>' + lgrad(uid, "lil", LILAC, y0=330, y1=700) + lgrad(uid, "leaf", LEAF_SHEET, y0=560, y1=650))
    ph = rect(132, 336, 262, 330, 30)
    hd, bd = person(0, 0, 1.0)
    k = 2.4
    rnd = f' stroke="{PLUM_DISC[1]}" stroke-width="6" stroke-linejoin="round"'      # the shoulder dome's rounded corners
    pic = (f'<g transform="translate(263 {666 - 62 * k:g}) scale({k})">'
           f'{path(hd, PLUM_DISC[1])}{path(bd, PLUM_DISC[1], extra=rnd)}</g>')
    ln_w = 34 if not small else 44
    lines = (stroke_path("M452 376H868", "#F3E4F1", ln_w, 0.92) + stroke_path("M452 466H868", "#F3E4F1", ln_w, 0.92)
             + (stroke_path("M452 556H676", "#F3E4F1", ln_w, 0.92) if not small else ""))
    chip = path(rect(452, 586, 120, 90, 20), u(uid, "leaf"))
    return [Part("body", f'<g mask="url(#{uid}-sm)">{path(body, u(uid, "av"))}{path(body, u(uid, "hl"))}</g>', defs),
            Part("sheet", f'<g clip-path="url(#{uid}-pc)">{path(ph, u(uid, "lil"))}{pic}</g>'
                 f'<clipPath id="{uid}-pc"><path d="{ph}"/></clipPath>'),
            Part("detail", lines), Part("accent", chip)]


def card_sym():
    k = 2.4
    hd, bd = person(0, 0, 1.0)
    pt = f"translate(263 {666 - 62 * k:g}) scale({k})"
    return [P(rect(72, 232, 880, 560, 64)), K(rect_c(C0, 276, 150, 30, 15)), K(rect(132, 336, 262, 330, 30)),
            P(hd, tf=pt), P(bd, rnd=6, tf=pt),
            K("M452 376H868M452 466H868M452 556H676", stroke=34), K(rect(452, 586, 120, 90, 20))]


# =============================================================================================== file pages
PAGE_PTS = [(192, 96), (640, 96), (832, 288), (832, 928), (192, 928)]
PAGE_R = [56, 30, 30, 56, 56]
FOLD = [(640, 96), (832, 288), (640, 288)]
PAGE_EMB = {False: 2.5, True: 3.1}
PAGE_EMB_Y = 526          # the page's centre of mass: the page is (192,96)..(832,928) less the dog-ear's corner, so its mass sits 12.6 units
                          # below the middle of its box. A symbol on the box middle (512) reads a touch high under the fold; one on the
                          # middle of the face below the fold (608) reads low, with a wide empty top.


def page_parts(uid: str, small: bool, emb: str | None = None, hue: float | None = None, ribbon: bool = False):
    pg = sqpoly(PAGE_PTS, PAGE_R)
    fold = sqpoly(FOLD, [0, 0, 22])
    w = 14 if not small else 44
    ink = PAGE_EDGE if hue is None else ink_for_hue(hue) if hue != "neutral" else g.oklch_to_hex(0.36, 0.03, 330)
    defs = (lgrad(uid, "lil", LILAC, y0=96, y1=928) + f'<clipPath id="{uid}-pc"><path d="{pg}"/></clipPath>'
            + lgrad(uid, "rib", ("#6E9A4B", LEAF_ON_LILAC_DARK), y0=96, y1=310))
    parts = [Part("page", path(pg, u(uid, "lil")), defs)]
    if ribbon:
        rx0, rx1, rb = (296, 380, 330) if not small else (288, 392, 352)
        rd = f"M{rx0} 96H{rx1}V{rb}L{(rx0 + rx1) / 2:g} {rb - 40}L{rx0} {rb}Z"
        parts.append(Part("accent", path(rd, u(uid, "rib"))))
    parts.append(Part("fold", f'<g clip-path="url(#{uid}-pc)">{path(fold, LILAC_FOLD)}'
                      f'{stroke_path("M640 96V288H832", PAGE_EDGE, w * 0.8, 0.9, cap="butt")}</g>'))
    parts.append(Part("edge", f'<g clip-path="url(#{uid}-pc)"><path d="{pg}" fill="none" stroke="{PAGE_EDGE}" stroke-width="{2 * w}" '
                      f'stroke-linejoin="round" opacity=".9"/></g>'))
    if emb:
        els, e = emb_els(emb, small)
        parts.append(emblem_part(els, uid, C0 + e.dx, PAGE_EMB_Y + e.dy, PAGE_EMB[small] * e.s, ink, deboss=False, small=small))
    return parts


def page_sym(emb: str | None = None, ribbon: bool = False):
    els = [P(sqpoly(PAGE_PTS, PAGE_R)), K("M640 110V288H818", stroke=22)]
    if emb:
        e = EMBLEMS[emb]
        s = PAGE_EMB[False] * e.s
        els += [replace(x, tf=f"translate({C0 + e.dx:g} {PAGE_EMB_Y + e.dy:g}) scale({s:g}) {x.tf}".strip()) for x in invert(e.els)]
    if ribbon:
        els.insert(1, K("M296 90H380V330L338 290L296 330Z"))
    return els


# =============================================================================================== registry
OBJECTS: dict[str, Obj] = {}
GROUPS: dict[str, list] = {"folders": [], "storage": [], "people": [], "files": []}


def _reg(o: Obj):
    assert o.id not in OBJECTS, o.id
    OBJECTS[o.id] = o
    GROUPS[o.group].append(o.id)


def _folder(i, name, emb=None, open_=False, xdg=""):
    _reg(Obj(i, name, "folders", lambda uid, small: folder_parts(uid, small, emb, open_), lambda: folder_sym(emb, open_), xdg, "folder", emb or ""))


def _trash(i, name, full, xdg):
    _reg(Obj(i, name, "folders", lambda uid, small: trash_parts(uid, small, full), lambda: trash_sym(full), xdg, "bin"))


def _drive(i, name, kind, emb, xdg):
    _reg(Obj(i, name, "storage", lambda uid, small: drive_parts(uid, small, kind, emb), lambda: drive_sym(kind, emb), xdg, "drive:" + kind, emb or ""))


def _page(i, name, emb, hue, xdg, ribbon=False):
    _reg(Obj(i, name, "files", lambda uid, small: page_parts(uid, small, emb, hue, ribbon), lambda: page_sym(emb, ribbon), xdg, "page", emb or "", {"hue": hue}))


_folder("folder", "Folder", None, False, "folder")
_folder("folder-open", "Open Folder", None, True, "folder-open")
_folder("folder-documents", "Documents", "documents", False, "folder-documents")
_folder("folder-downloads", "Downloads", "downloads", False, "folder-download")
_folder("folder-pictures", "Pictures", "pictures", False, "folder-pictures")
_folder("folder-music", "Music", "music", False, "folder-music")
_folder("folder-videos", "Videos", "videos", False, "folder-videos")
_folder("folder-desktop", "Desktop", "desktop", False, "user-desktop")
_folder("folder-home", "Home", "home", False, "user-home")
_folder("folder-shared", "Shared", "shared", False, "folder-publicshare")
_folder("folder-locked", "Private", "locked", False)
_folder("folder-projects", "Projects", "code", False)
_trash("trash-empty", "Trash", False, "user-trash")
_trash("trash-full", "Trash (full)", True, "user-trash-full")

_drive("drive-internal", "Internal Drive", "internal", None, "drive-harddisk")
_drive("drive-external", "External Drive", "external", None, "drive-harddisk-usb")
_drive("drive-network", "Network Drive", "internal", "network", "network-server")
_drive("drive-encrypted", "Encrypted Drive", "internal", "locked", "")
_reg(Obj("usb-stick", "USB Stick", "storage", usb_parts, usb_sym, "drive-removable-media-usb", "usb"))
_reg(Obj("sd-card", "SD Card", "storage", sd_parts, sd_sym, "media-flash", "card"))
_reg(Obj("optical-disc", "Disc", "storage", disc_parts, disc_sym, "media-optical", "disc"))
_reg(Obj("cloud-storage", "Cloud Storage", "storage", cloud_parts, cloud_sym, "", "cloud"))

_reg(Obj("user", "User", "people", lambda uid, small: avatar_parts(uid, small), lambda: avatar_sym(), "avatar-default", "person"))
_reg(Obj("user-admin", "Administrator", "people", lambda uid, small: avatar_parts(uid, small, None, "admin"), lambda: avatar_sym("admin"), "", "person"))
_reg(Obj("user-guest", "Guest", "people", lambda uid, small: avatar_parts(uid, small, None, "guest"), lambda: avatar_sym("guest"), "", "person"))
_reg(Obj("users", "Group", "people", group_parts, group_sym, "system-users", "group"))
_reg(Obj("id-card", "ID Card", "people", card_parts, card_sym, "", "card"))
AVATAR_HUES = (8, 36, 64, 128, 184, 240, 290)
for _k, _h in enumerate(AVATAR_HUES, start=2):
    _reg(Obj(f"avatar-{_k}", f"Avatar {_k}", "people", (lambda h: lambda uid, small: avatar_parts(uid, small, h))(_h), lambda: avatar_sym(), "", "person", "", {"hue": _h}))

_page("file", "File", None, None, "application-x-generic")
_page("file-text", "Text File", "text", 184, "text-x-generic")
_page("file-document", "Document", "document", 240, "x-office-document")
_page("file-pdf", "PDF", "pdf", 240, "application-pdf", ribbon=True)
_page("file-spreadsheet", "Spreadsheet", "spreadsheet", 150, "x-office-spreadsheet")
_page("file-presentation", "Presentation", "presentation", 28, "x-office-presentation")
_page("file-image", "Image", "image", 64, "image-x-generic")
_page("file-audio", "Audio", "audio", 36, "audio-x-generic")
_page("file-video", "Video", "video", 312, "video-x-generic")
_page("file-archive", "Archive", "archive", 94, "package-x-generic")
_page("file-code", "Source Code", "code", "neutral", "text-x-script")

# ---- more folders and file kinds: the standard places and the file types a desktop meets
_folder("folder-remote", "Network Folder", "network", False, "folder-remote")
_folder("folder-saved-search", "Saved Search", "search", False, "folder-saved-search")
_folder("folder-templates", "Templates", "template", False, "folder-templates")
_folder("folder-drag-accept", "Drop Target", "drop", False, "folder-drag-accept")

_page("file-html", "Web Page", "globe", 200, "text-html")
_page("file-script", "Shell Script", "prompt", "neutral", "application-x-shellscript")
_page("file-executable", "Program", "gear", "neutral", "application-x-executable")
_page("file-library", "Library", "library", "neutral", "application-x-sharedlib")
_page("file-firmware", "Firmware", "chip", "neutral", "application-x-firmware")
_page("file-appliance", "Virtual Appliance", "box", 240, "application-x-appliance")
_page("file-disk-image", "Disk Image", "disc", 64, "application-x-cd-image")
_page("file-addon", "Add-on", "puzzle", 150, "application-x-addon")
_page("file-certificate", "Certificate", "certificate", 94, "application-certificate")
_page("file-feed", "Feed", "feed", 28, "application-rss+xml")
_page("file-font", "Font", "font", 312, "font-x-generic")
_page("file-calendar", "Calendar", "calendar", 8, "x-office-calendar")
_page("file-contacts", "Contacts", "contact", 184, "x-office-address-book")
_page("file-drawing", "Drawing", "shapes", 290, "x-office-drawing")
_page("file-ebook", "E-book", "book", 36, "application-epub+zip")

ORDER = [i for grp in GROUPS.values() for i in grp]

# optical centring offsets measured from the rendered pixels (tools/icons/centre_objects.py)
import json as _json
from pathlib import Path as _P
_sh = _P(__file__).with_name("object_shifts.json")
if _sh.exists():
    for _k, _v in _json.loads(_sh.read_text()).items():
        OBJECTS[_k].shift = tuple(_v)
