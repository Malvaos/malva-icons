"""Device, UI-control, settings-pane, category and emblem glyphs (one-colour).
Places, file types and drives are not here: they come from the object icons, whose symbolic cuts the theme installs
(solid shapes, as the sidebar of a file manager shows them)."""
import math

from glyphkit import *      # noqa: F401,F403
from glyphkit import add, S, F, FS, Part, arc, slash, with_badge, bang, lock_badge, dimmed, xf, head, GLYPHS
from glyphs_status2 import arc_head, MOON, CLOUD, SHIELD, SUN, LOCK
import ui_glyphs as U

OLD = U.GLYPHS


def old(i):
    return S(*OLD[i]["strokes"])


def ellipse(cx, cy, rx, ry):
    """An ellipse as four cubic Beziers (the kit draws circles with arcs; an ellipse needs this)."""
    k = 0.5523
    return (f"M{cx - rx:g} {cy:g}C{cx - rx:g} {cy - k * ry:g} {cx - k * rx:g} {cy - ry:g} {cx:g} {cy - ry:g}"
            f"C{cx + k * rx:g} {cy - ry:g} {cx + rx:g} {cy - k * ry:g} {cx + rx:g} {cy:g}"
            f"C{cx + rx:g} {cy + k * ry:g} {cx + k * rx:g} {cy + ry:g} {cx:g} {cy + ry:g}"
            f"C{cx - k * rx:g} {cy + ry:g} {cx - rx:g} {cy + k * ry:g} {cx - rx:g} {cy:g}Z")


def alias_of(base, *names):
    GLYPHS[base].alias = tuple(GLYPHS[base].alias) + tuple(names)


# ================================================================== devices
add("computer", "devices", S(R(6, 3, 12, 18, 3), L(9, 8, 15, 8), D(12, 16.5)))
add("computer-laptop", "devices", S(R(5, 5, 14, 10, 2.5), L(3, 19, 21, 19)))
add("video-display", "devices", S(R(3, 4, 18, 12, 3.5), L(12, 16, 12, 20), L(8, 20, 16, 20)), alias=("preferences-desktop-display",))
add("video-single-display", "devices", S(R(3, 4, 18, 13, 3.5), L(9, 20, 15, 20), L(12, 17, 12, 20)))
add("video-joined-displays", "devices", S(R(2, 6, 8, 8, 2), R(14, 6, 8, 8, 2), L(6, 14, 6, 18), L(18, 14, 18, 18), L(3, 18, 9, 18), L(15, 18, 21, 18)))
add("display-projector", "devices", S(R(3, 7, 18, 9, 3), C(15, 12, 2.5), L(7, 16, 7, 19), L(17, 16, 17, 19), L(6, 12, 9, 12)))
add("tablet", "devices", S(R(5, 2, 14, 20, 3), D(12, 18.5)))
add("phone", "devices", S(R(7, 2, 10, 20, 3), L(10, 19, 14, 19)))
add("multimedia-player", "devices", S(R(6, 2, 12, 20, 3), R(9, 5, 6, 5, 1), C(12, 16, 2.6)))
add("input-keyboard", "devices", S(R(2, 6, 20, 12, 3), D(7, 10), D(12, 10), D(17, 10), L(8, 14, 16, 14)), alias=("preferences-desktop-keyboard",))
add("input-mouse", "devices", S(R(6, 3, 12, 18, 6), L(12, 7, 12, 10.5)))
add("input-touchpad", "devices", S(R(3, 5, 18, 14, 3), L(3, 15, 21, 15), L(12, 15, 12, 19)))
add("input-tablet", "devices", S(R(2, 6, 12, 13, 3), R(17, 3, 4, 11, 1.5), Pc((17, 14), (19, 18.5), (21, 14))))
add("input-gaming", "devices", S(RP([(7, 6), (17, 6), (21, 10), (21, 17), (18, 17), (16, 14), (8, 14), (6, 17), (3, 17), (3, 10)], 3, closed=True), L(8, 9.5, 8, 12.5), L(6.5, 11, 9.5, 11), D(15.5, 9.5), D(18, 12)))
add("input-dialpad", "devices", F(*[disc(x, y, 1.7) for y in (4.5, 9.5, 14.5) for x in (6, 12, 18)] + [disc(12, 19.5, 1.7)]))
add("audio-headphones", "devices", S("M4 15v-3a8 8 0 0 1 16 0v3", R(3, 14, 4, 7, 1.8), R(17, 14, 4, 7, 1.8)))
add("audio-headset", "devices", S("M4 14v-2a8 8 0 0 1 16 0v2", R(3, 13, 4, 6, 1.8), R(17, 13, 4, 6, 1.8), "M19 19c0 2-2 3-5 3h-1"))
add("audio-speakers", "devices", S(R(6, 2, 12, 20, 2.5), C(12, 15, 3.5), D(12, 7)))
add("audio-card", "devices", S(R(2, 5, 20, 10, 2.5), D(7, 10), L(10, 10, 18, 10), L(6, 15, 6, 19), L(10, 15, 10, 19)))
add("camera-video", "devices", S(R(2, 6, 13, 12, 3.5), "M15 10.5l6-3.5v10l-6-3.5"))
add("camera-web", "devices", S(C(12, 10, 7), C(12, 10, 2.4), L(12, 17, 12, 20), L(8, 20, 16, 20)))
add("scanner", "devices", S(R(3, 12, 18, 8, 2.5), P((5, 12), (7.5, 5), (16.5, 5), (19, 12)), D(7, 16), L(11, 16, 17, 16)))
add("modem", "devices", S(R(3, 13, 18, 7, 2.5), L(7, 13, 7, 6), L(17, 13, 17, 6), D(8, 16.5), D(12, 16.5)))
add("tv", "devices", S(R(3, 7, 18, 12, 3), L(8, 3, 12, 7), L(16, 3, 12, 7)))
add("thunderbolt", "devices", S(Pc((13, 3), (5, 14), (11, 14), (10, 21), (19, 10), (13, 10))))
add("uninterruptible-power-supply", "devices", S(R(4, 3, 16, 18, 3), P((12.5, 7), (9, 12), (14, 12), (11.5, 17))))
add("auth-fingerprint", "devices", S("M9 18v-4a3 3 0 0 1 6 0v3", "M6 19.500V14a6 6 0 0 1 12 0v2", "M2.500 16V14a9.500 9.500 0 0 1 19 0v1", L(12, 14, 12, 21.5)))
add("auth-face", "devices", S(RP([(9, 3), (3, 3), (3, 9)], 2.5), RP([(15, 3), (21, 3), (21, 9)], 2.5), RP([(21, 15), (21, 21), (15, 21)], 2.5), RP([(9, 21), (3, 21), (3, 15)], 2.5), D(9, 10), D(15, 10), L(12, 10, 12, 13.5), arc(12, 14, 3.6, 30, 150)))
add("auth-smartcard", "devices", S(R(3, 5, 18, 14, 3), R(6, 10, 5, 4, 1), L(14, 10, 18, 10), L(14, 14, 18, 14)))
add("auth-sim", "devices", S(RP([(6, 3), (14.5, 3), (19, 7.5), (19, 21), (6, 21)], 2.5, closed=True), R(9, 11, 6, 6, 1.5)))
add("preferences-system-devices", "apps", S(R(7, 3, 10, 14, 2.5), L(10, 3, 10, 7), L(14, 3, 14, 7), L(12, 17, 12, 21)))

# ================================================================== UI controls
add("checkbox", "ui", S(R(4, 4, 16, 16, 3.5)))
add("checkbox-checked", "ui", S(R(4, 4, 16, 16, 3.5), P((8, 12.5), (11, 15.5), (16.5, 9))))
add("checkbox-mixed", "ui", S(R(4, 4, 16, 16, 3.5), L(8.5, 12, 15.5, 12)))
add("radio", "ui", S(C(12, 12, 8)))
add("radio-checked", "ui", S(C(12, 12, 8)) + F(disc(12, 12, 3.6)))
add("radio-mixed", "ui", S(C(12, 12, 8), L(8.5, 12, 15.5, 12)))
add("list-drag-handle", "ui", F(*[disc(x, y, 1.7) for y in (6, 12, 18) for x in (9, 15)]))

# ================================================================== settings panes, applications, accessories (legacy names)
add("preferences-system", "categories", S(gear(12, 12, rt=9 / math.cos(math.radians(9))), C(12, 12, 3)), alias=("emblem-system", "applications-system"))
add("preferences-color", "apps", S("M12 3a9 9 0 1 0 0 18c1.500 0 2-1 2-2s-1-1.500-1-2.500S14 15 15.500 15H18a3 3 0 0 0 3-3 9 9 0 0 0-9-9Z", D(7.5, 12), D(9, 7.5), D(14, 6.5)))
add("preferences-desktop-accessibility", "apps", S(C(12, 12, 9), D(12, 7), L(7, 10, 17, 10), L(12, 10, 12, 14), L(12, 14, 9.5, 18), L(12, 14, 14.5, 18)))
add("preferences-desktop-appearance", "apps", S(C(12, 12, 9)) + F("M12 3a9 9 0 0 0 0 18Z"))
add("preferences-desktop-locale", "apps", S(C(12, 12, 9), L(3, 12, 21, 12), "M12 3c2.800 2.500 4.200 5.500 4.200 9s-1.400 6.500-4.200 9c-2.800-2.500-4.200-5.500-4.200-9S9.200 5.500 12 3Z"), alias=("web-browser", "applications-internet"))
add("preferences-desktop-multitasking", "apps", S(R(3, 7, 14, 12, 3), RP([(8, 7), (8, 5), (21, 5), (21, 15), (17, 15)], 2.5)))
add("preferences-desktop-screensaver", "apps", S(R(3, 4, 18, 12, 3.5), L(12, 16, 12, 20), L(8, 20, 16, 20), xf(MOON, 0.42, -0.3, -4.4)))
add("preferences-desktop-remote-desktop", "apps", S(R(3, 4, 18, 12, 3.5), L(12, 16, 12, 20), L(8, 20, 16, 20), P((9, 12), (15, 8)), P((12, 8), (15, 8), (15, 11))))
add("preferences-system-network-proxy", "apps", S(C(12, 12, 9), L(3, 12, 21, 12), L(12, 3, 12, 21)))
add("preferences-system-parental-controls", "apps", S(SHIELD, C(12, 10, 2.5), "M8 17a4 4 0 0 1 8 0"))
add("preferences-system-privacy", "apps", S("M3 12c2-4 5-6.500 9-6.500s7 2.500 9 6.500c-2 4-5 6.500-9 6.500S5 16 3 12Z", C(12, 12, 3), L(5, 19, 19, 5)))
add("system-file-manager", "apps", S(RP([(3, 19), (3, 5), (9.5, 5), (11.5, 8), (21, 8), (21, 19)], 2.5, closed=True)))
add("system-software-install", "apps", S("M5 7.500L12 3.500l7 4v9l-7 4-7-4Z", L(12, 11, 12, 20.500), L(5, 7.500, 12, 11.500), L(19, 7.500, 12, 11.500)))
add("system-users", "apps", old("users"))
add("avatar-default", "status", old("user"), alias=("user-info",))
add("accessories-calculator", "apps", S(R(5, 2, 14, 20, 3), R(9, 6, 6, 3, 1), D(9, 13), D(12, 13), D(15, 13), D(9, 17), D(12, 17), D(15, 17)))
add("accessories-character-map", "apps", S("M5 19h4.500v-1.800A7.500 7.500 0 1 1 14.500 17.200V19H19"))
add("accessories-dictionary", "apps", S(R(5, 3, 14, 18, 2.5), L(9, 3, 9, 21), L(12, 8, 16, 8), L(12, 12, 16, 12)), alias=("help-contents",))
add("applets-screenshooter", "apps", S(RP([(9, 4), (4, 4), (4, 9)], 2.5), RP([(15, 4), (20, 4), (20, 9)], 2.5), RP([(20, 15), (20, 20), (15, 20)], 2.5), RP([(9, 20), (4, 20), (4, 15)], 2.5), D(12, 12)))
add("multimedia-volume-control", "apps", S(Pc((4, 9), (7, 9), (11, 5), (11, 19), (7, 15), (4, 15)), arc(11, 12, 4, -45, 45), arc(11, 12, 8, -45, 45)))
add("applications-graphics", "categories", S("M4 20l1-4L16.500 4.500a2.100 2.100 0 0 1 3 3L8 19Z", L(13.500, 7.500, 16.500, 10.500)))
add("applications-multimedia", "categories", S(C(12, 12, 9), Pc((10, 8), (16, 12), (10, 16))))
add("applications-science", "categories", S(xf(ellipse(12, 12, 9.5, 3.6), 1, 0, 0, 45), xf(ellipse(12, 12, 9.5, 3.6), 1, 0, 0, -45)) + F(disc(12, 12, 1.8)))
add("applications-engineering", "categories", S(L(4, 20, 20, 4), P((4, 20), (4, 14), (10, 20)), P((13, 4), (20, 4), (20, 11))))
add("applications-utilities", "categories", S(arc(16.5, 7.5, 4.5, -5, 285), L(13.3, 10.7, 5.5, 18.5), D(4.8, 19.2)))

# ================================================================== emblems
add("emblem-documents", "emblems", S(RP([(5, 3), (14, 3), (19, 8), (19, 21), (5, 21)], 3, closed=True), P((14, 3), (14, 8), (19, 8))))
add("emblem-music", "emblems", S(*OLD["music"]["strokes"]))
add("emblem-symbolic-link", "emblems", S(L(5, 19, 19, 5), P((10, 5), (19, 5), (19, 14))))
add("emblem-new", "emblems", S(L(12, 3, 12, 21), L(3, 12, 21, 12), L(5.7, 5.7, 18.3, 18.3), L(18.3, 5.7, 5.7, 18.3)))

alias_of("input-gaming", "applications-games")
