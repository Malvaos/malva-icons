"""Status glyphs: what the panel (taskbar), the quick settings and the notifications show.
Names are the icon-naming-spec / GNOME / UPower names, so a toolkit that asks for `battery-level-50-symbolic` finds it."""
from glyphkit import *      # noqa: F401,F403
from glyphkit import add, S, F, FS, Part, arc, slash, with_badge, bang, lock_badge, tick_badge, dot_badge, dimmed, DIM

# ================================================================== network: Wi-Fi
_WX, _WY = 12, 19


def _wifi_els():
    return [D(_WX, _WY), arc(_WX, _WY, 5, -135, -45), arc(_WX, _WY, 9.5, -135, -45), arc(_WX, _WY, 14, -135, -45)]


def wifi(n=4):
    """Dot and three arcs; the first n of the four are lit."""
    return [Part(d, "S", dim=(i >= n)) for i, d in enumerate(_wifi_els())]


for _lv, _nm in enumerate(["none", "weak", "ok", "good", "excellent"]):
    add(f"network-wireless-signal-{_nm}", "status", wifi(_lv), group="wifi", level=_lv,
        alias=("network-wireless-offline", "network-wireless-acquiring") if _lv == 0 else
        (("network-wireless", "network-wireless-connected") if _lv == 4 else ()))
add("network-wireless-disabled", "status", slash(wifi(4)))
_b, _r = bang(20, 13, 16.5, 20)
add("network-wireless-no-route", "status", with_badge(wifi(4), _b, _r))
_b, _r = lock_badge(18.5, 16)
add("network-wireless-encrypted", "status", with_badge(wifi(4), _b, _r))
add("network-wireless-hotspot", "status", S(*_wifi_els()[1:]) + F(disc(_WX, _WY - 0.5, 2.6)))

# ================================================================== network: cellular, wired, VPN, airplane
_BARS = [(4, 16), (9, 12), (14, 8), (19, 4)]


def bars(n=4):
    return [Part(L(x, 19, x, top), "S", dim=(i >= n)) for i, (x, top) in enumerate(_BARS)]


for _lv, _nm in enumerate(["none", "weak", "ok", "good", "excellent"]):
    add(f"network-cellular-signal-{_nm}", "status", bars(_lv), group="cell", level=_lv,
        alias=("network-cellular-acquiring",) if _lv == 0 else (("network-cellular-connected", "network-cellular") if _lv == 4 else ()))
add("network-cellular-disabled", "status", slash(bars(4)), alias=("network-cellular-offline",))
add("network-cellular-no-route", "status", bars(3)[:3] + S(L(19, 4, 19, 14), D(19, 19)))
_b, _r = lock_badge(18.5, 16)
add("network-cellular-hardware-disabled", "status", with_badge(dimmed(bars(4)), _b, _r))

_port = S(RP([(3, 20), (3, 6), (8, 6), (8, 3), (16, 3), (16, 6), (21, 6), (21, 20)], 2.5, closed=True), L(8, 12, 8, 15), L(12, 12, 12, 15), L(16, 12, 16, 15))
add("network-wired", "devices", _port, alias=("network-wired-connected",))
add("network-wired-disconnected", "status", slash(_port), alias=("network-wired-offline",))
_b, _r = bang(20, 13, 16.5, 20)
add("network-wired-no-route", "status", with_badge(_port, _b, _r))
add("network-wired-acquiring", "status", dimmed(_port))
add("network-workgroup", "places", S(R(9, 3, 6, 5, 2), R(2, 16, 6, 5, 2), R(16, 16, 6, 5, 2), "M12 8v4M5 16v-4h14v4"), alias=("preferences-system-network",))


def _arrows(down, up):
    return ([Part(L(8, 5, 8, 19) + P((4, 15), (8, 19), (12, 15)), "S", dim=not down),
             Part(L(16, 19, 16, 5) + P((12, 9), (16, 5), (20, 9)), "S", dim=not up)])


add("network-idle", "status", _arrows(False, False), group="net-io", level=0)
add("network-receive", "status", _arrows(True, False), group="net-io", level=1)
add("network-transmit", "status", _arrows(False, True), group="net-io", level=1)
add("network-transmit-receive", "status", _arrows(True, True), group="net-io", level=2)

_globe = S(C(12, 12, 9), L(3, 12, 21, 12), "M12 3c2.800 2.500 4.200 5.500 4.200 9s-1.400 6.500-4.200 9c-2.800-2.500-4.200-5.500-4.200-9S9.200 5.500 12 3Z")
add("network-offline", "status", slash(_globe), alias=("network-no-route",))
_b, _r = bang(19, 12, 15.5, 19)
add("network-error", "status", with_badge(_globe, _b, _r))

_plane = S("M10 4.5v5L2 14.3v2.2l8-2V18l-2.2 1.6V21L12 20l4.2 1v-1.4L14 18v-3.5l8 2v-2.2l-8-4.8v-5a2 2 0 0 0-4 0Z")
add("airplane-mode", "status", _plane)
add("airplane-mode-disabled", "status", slash(_plane))

# ================================================================== audio
_SPK = Pc((3, 9), (6, 9), (10, 5), (10, 19), (6, 15), (3, 15))
_W = [arc(10, 12, r, -45, 45) for r in (4, 8, 12)]
add("audio-volume-muted", "status", S(_SPK, L(15, 9, 21, 15), L(21, 9, 15, 15)))
add("audio-volume-low", "status", S(_SPK, _W[0]), group="volume", level=1)
add("audio-volume-medium", "status", S(_SPK, _W[0], _W[1]), group="volume", level=2)
add("audio-volume-high", "status", S(_SPK, *_W), group="volume", level=3)
add("audio-volume-overamplified", "status", FS(_SPK) + S(*_W), group="volume", level=4)

_MIC = S(R(9, 3, 6, 11, 3), "M5 11a7 7 0 0 0 14 0", L(12, 18, 12, 21), L(8, 21, 16, 21))
add("audio-input-microphone", "devices", _MIC, group="mic", level=0)
add("microphone-sensitivity-muted", "status", slash(_MIC), alias=("microphone-disabled",))
add("microphone-sensitivity-low", "status", _MIC + S(D(12, 11)), group="mic", level=1)
add("microphone-sensitivity-medium", "status", _MIC + S(L(12, 8.5, 12, 11)), group="mic", level=2)
add("microphone-sensitivity-high", "status", _MIC + S(L(12, 6, 12, 11)), group="mic", level=3)
_b, _r = lock_badge(18.5, 16)
add("microphone-hardware-disabled", "status", with_badge(S(R(9, 3, 6, 11, 3), "M5 11a7 7 0 0 0 14 0"), _b, _r))

# ================================================================== battery
_BAT = S(R(2, 7, 17, 10, 3), L(22, 11, 22, 13))
_BOLT = Pc((13.5, 8.5), (9.5, 12.5), (12, 12.5), (10.5, 15.5), (14.5, 11.5), (12, 11.5))


def battery(level, charging=False):
    parts = list(_BAT)
    if level > 0:
        w = max(2, int(13.0 * level / 100.0 + 0.5))
        fill = R(4, 9, w, 6, 1)
        parts += F(fill + (_BOLT if charging else ""), eo=charging)
    elif charging:
        parts += F(_BOLT)
    return parts


for _l in range(0, 101, 10):
    add(f"battery-level-{_l}", "status", battery(_l), group="battery", level=_l, alias=("battery", "battery-good") if _l == 70 else ())
    if _l < 100:
        add(f"battery-level-{_l}-charging", "status", battery(_l, True), group="battery-charging", level=_l)
add("battery-level-100-charged", "status", battery(100, True))
add("battery-missing", "status", slash(_BAT))
add("battery-caution", "status", _BAT + S(L(11, 9.8, 11, 12), D(11, 14.4)))
add("ac-adapter", "devices", S(L(8, 3, 8, 7), L(16, 3, 16, 7), RP([(5, 7), (19, 7), (19, 11), (12, 17), (5, 11)], 2, closed=True), L(12, 17, 12, 21)))

# ================================================================== bluetooth
_RUNE = S(P((7, 8), (17, 16), (12, 21), (12, 3), (17, 8), (7, 16)))
add("bluetooth-active", "status", _RUNE, alias=("bluetooth",))
add("bluetooth-disabled", "status", slash(_RUNE))
add("bluetooth-disconnected", "status", dimmed(_RUNE))
