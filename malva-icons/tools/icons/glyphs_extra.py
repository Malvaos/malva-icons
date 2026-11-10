"""Glyphs that the standard icon-naming lists ask for and the first four files did not draw: alarm, call states,
rotation lock, loading, spell-check, text direction, the emoji-picker categories, locked SIM, hardware switches.
Same kit, same rules (24 grid, stroke 2, one drawing for every size)."""
import math

from glyphkit import *      # noqa: F401,F403
from glyphkit import add, S, F, FS, Part, arc, slash, with_badge, bang, lock_badge, tick_badge, dimmed, xf, head, GLYPHS
from glyphs_status import wifi, _RUNE
from glyphs_status2 import arc_head
from glyphkit import outline

_HS = ("M6.500 4h3l1.500 4-2 1.500a10 10 0 0 0 5 5l1.500-2L20 14v3a2.500 2.500 0 0 1-2.500 2.500A15 15 0 0 1 4 6a2.500 2.500 0 0 1 2.500-2Z")


def parts_of(i):
    return list(GLYPHS[i].parts)


# ================================================================== status
# alarm clock: a face, two hands and two bells
add("alarm", "status", S(C(12, 13, 7), P((12, 9), (12, 13), (15, 15)), L(3, 6, 6, 3), L(21, 6, 18, 3)))

# calendar with a missed mark
_CAL = [R(3, 5, 18, 16, 4), L(3, 9, 21, 9), L(8, 3, 8, 7), L(16, 3, 16, 7)]
add("appointment-missed", "status", S(*_CAL, L(9.5, 13, 14.5, 18), L(14.5, 13, 9.5, 18)))

# SIM card, locked or missing
_SIM = S(RP([(6, 3), (14.5, 3), (19, 7.5), (19, 21), (6, 21)], 2.5, closed=True), R(9, 11, 6, 6, 1.5))
_SIM_LEFT = S(*[xf(p.d, 1.0, -2.0) for p in _SIM])       # shifted left to leave the corner for the padlock
_b, _r = lock_badge(18.5, 16)
add("auth-sim-locked", "status", with_badge(_SIM_LEFT, _b, _r))
add("auth-sim-missing", "status", slash(_SIM))

# hardware switch off: the dimmed drawing with a padlock, as for the camera, microphone and mobile data
_b, _r = lock_badge(18.5, 16)
add("bluetooth-hardware-disabled", "status", with_badge(dimmed(S(xf(_RUNE[0].d, 1.0, -2.0))), _b, _r))
add("network-wireless-hardware-disabled", "status", with_badge(dimmed(wifi(4)), _b, _r))

# calls: the handset smaller, an arrow or a cross in the top-right corner
_H = xf(_HS, 0.78, -2.5, 3.2)
_in = (L(21, 3, 14, 10), head(14, 10, -1, 1, 4.5))
_out = (L(14, 10, 21, 3), head(21, 3, 1, -1, 4.5))
_miss = (L(15, 4, 21, 10), L(21, 4, 15, 10))
add("call-incoming", "status", with_badge(S(_H), S(*_in), outline(*_in)))
add("call-outgoing", "status", with_badge(S(_H), S(*_out), outline(*_out)))
add("call-missed", "status", with_badge(S(_H), S(*_miss), outline(*_miss)))

# a screen with a bang on it
add("computer-fail", "status", S(R(3, 4, 18, 12, 3.5), L(12, 16, 12, 20), L(8, 20, 16, 20), L(12, 7, 12, 10.5), D(12, 13)))

# loading: a track and a quarter of it travelling
add("content-loading", "status", [Part(C(12, 12, 9), "S", dim=True)] + S(arc(12, 12, 9, -90, 0)))
add("image-loading", "status", dimmed(parts_of("insert-image")))
_b, _r = bang(19, 12, 15.5, 19)
add("image-missing", "status", with_badge(parts_of("insert-image"), _b, _r))
add("thunderbolt-acquiring", "status", dimmed(parts_of("thunderbolt")))

# mail that has been answered
_ENV = [R(2, 4, 18, 13, 4), P((3.5, 7.5), (11, 12.5), (18.5, 7.5))]
_rep = (P((15, 15), (12, 18), (15, 21)), "M12 18h5a3 3 0 0 0 3-3")
add("mail-replied", "status", with_badge(S(*_ENV), S(*_rep), outline(*_rep)))

# screen rotation: the arrow round a phone, or round a padlock
_RR = 6 * math.sqrt(2)          # the arrow head ends 6 left and 6 up from the centre: its arms land on whole units
_ring = S(arc(12, 11, _RR, -40, 225), arc_head(12, 11, _RR, 225, 3.5))
add("rotation-allowed", "status", _ring + S(R(9, 7, 6, 8, 1.5)))
_b, _r = lock_badge(12, 10.5)
add("rotation-locked", "status", _ring + _b)

# touch: a point with ripples
_TOUCH = S(R(4, 3, 16, 18, 3), D(8, 16), D(16, 8))                   # a touchscreen with two fingers on it
add("touch-disabled", "status", slash(_TOUCH))
add("touchpad-disabled", "status", slash(parts_of("input-touchpad")))

# ================================================================== actions
# text: "A" with a wavy underline = something to correct; "A" and a tick = spelling is fine; "A" with a colour bar = rich text
_A = [P((3, 17), (8, 5), (13, 17)), L(5.5, 12, 10.5, 12)]
add("error-correct", "actions", S(P((3, 15), (7, 4), (11, 15)), L(5, 11, 9, 11), P((3, 21), (5.5, 18.5), (8, 21), (10.5, 18.5), (13, 21), (15.5, 18.5), (18, 21), (20.5, 18.5))))
add("tools-check-spelling", "actions", S(P((2.5, 17), (7, 5), (11.5, 17)), L(4.5, 12, 9.5, 12), P((14, 15.5), (17, 18.5), (22, 11.5))))
add("format-text-rich", "actions", S(P((4, 16), (9.5, 4), (15, 16)), L(6.5, 11, 12.5, 11), L(3, 21, 21, 21)))

# paragraph with a writing direction
_PIL = ["M17 4H9.500a3.500 3.500 0 0 0 0 7H13", L(13, 4, 13, 12), L(17, 4, 17, 12)]
add("format-text-direction", "actions", S(*_PIL, L(4, 18, 20, 18), head(20, 18, 1, 0, 4)), rtl=True, alias=("format-text-direction-ltr",))

# a numbered list: a "1" and a "2" beside the rules
add("view-list-ordered", "actions", S(L(11, 6, 21, 6), L(11, 12, 21, 12), L(11, 18, 21, 18),
                                       P((4, 6.5), (6, 4.5), (6, 9)),
                                       "M4.500 15.800a2 2 0 0 1 4 .6c0 1.300-2 2-4 3.600H8.500"), rtl=True)

# ================================================================== categories: the emoji picker
add("emoji-people", "categories", S(C(12, 12, 9), D(9, 9.5), D(15, 9.5), arc(12, 12, 5, 30, 150)))
add("emoji-body", "categories", S(C(12, 4.5, 2.5), L(5, 11, 19, 11), L(12, 8, 12, 15), P((8, 21), (12, 15), (16, 21))))
add("emoji-nature", "categories", S("M4 20C4 11 9 4 20 4c0 11-7 16-16 16Z", L(4, 20, 13, 11)))
add("emoji-food", "categories", S("M6 3v5.500a3 3 0 0 0 6 0V3", L(9, 3, 9, 21), "M19 21V3c-2.800 1.600-4 4.600-4 8h4"))
add("emoji-travel", "categories", S(R(3, 10, 18, 7, 2.5), P((6.5, 10), (8.2, 6), (15.8, 6), (17.5, 10))) + F(disc(7.5, 17, 2.2), disc(16.5, 17, 2.2)))
add("emoji-activities", "categories", S("M7 4V9a5 5 0 0 0 10 0V4Z", "M7 6H4v2a3 3 0 0 0 3 3", "M17 6h3v2a3 3 0 0 1-3 3", L(12, 14, 12, 18), L(8, 20, 16, 20)))
add("emoji-objects", "categories", S(arc(12, 9, 6, 140, 400), "M7.400 12.900L9.500 16H14.500L16.600 12.900", L(10, 19, 14, 19), L(11, 22, 13, 22)))
add("emoji-symbols", "categories", S(L(9.500, 4, 7.500, 20), L(16.500, 4, 14.500, 20), L(4, 9, 20, 9), L(4, 15, 20, 15)))

# ================================================================== devices, legacy
_PRN = S(P((7, 6), (7, 3), (17, 3), (17, 6)), R(3, 6, 18, 9, 3), D(17, 10.5), L(12, 15, 12, 18), L(5, 18, 19, 18), L(5, 18, 5, 21), L(12, 18, 12, 21), L(19, 18, 19, 21))
add("printer-network", "devices", _PRN)
add("preferences-desktop-keyboard-shortcuts", "legacy", S(R(3, 3, 18, 18, 4), P((8, 15), (12, 10), (16, 15))))

# ================================================================== menu categories and Settings panes that had no glyph
# applications-internet is the globe of preferences-desktop-locale (glyphs_devices / MERGES), not a second drawing
add("applications-office", "categories", S(R(3, 8, 18, 12, 3), "M9 8V6a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2", L(3, 14, 21, 14)))
add("applications-development", "categories", S(P((8, 7), (3, 12), (8, 17)), P((16, 7), (21, 12), (16, 17)), L(14, 5, 10, 19)))
add("preferences-desktop-dock", "apps", S(R(3, 4, 18, 16, 3.5)) + F(R(7, 14.5, 10, 3, 1.5)))
