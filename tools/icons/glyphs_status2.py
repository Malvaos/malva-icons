"""Status glyphs, part two: display, notifications, session and power, presence, security, dialogs, privacy
indicators, mail, weather, printing, updates, favourites."""
import math

from glyphkit import *      # noqa: F401,F403
from glyphkit import add, S, F, FS, Part, arc, slash, with_badge, bang, lock_badge, tick_badge, dot_badge, dimmed, xf, head, clip_half, cloud, outline, cut_parts, crescent
import glyphs_status as G1

# ================================================================== shared shapes
SUN = [C(12, 12, 4), rays(12, 12, 7.6, 9.8)]
MOON = "M20 14.5A8.5 8.5 0 1 1 9.5 4a6.6 6.6 0 0 0 10.5 10.5Z"
CLOUD = cloud((7, 15, 4), (12, 11, 6), (17, 15, 4))                 # the overcast cloud: 18 wide, 14 high
LOCK = [R(5, 11, 14, 10, 3), "M8 11V8a4 4 0 0 1 8 0v3", L(12, 15, 12, 17)]
UNLOCK = [R(5, 11, 14, 10, 3), "M8 11V8a4 4 0 0 1 7.5-1.9", L(12, 15, 12, 17)]
SHIELD = "M12 3l7 2.800v5.700c0 4.600-3 8-7 9.500-4-1.500-7-4.900-7-9.500V5.800Z"
BELL = "M6 15V9a6 6 0 0 1 12 0v6l2 2H4Z"
BELL_CLAPPER = "M10 20a2.200 2.200 0 0 0 4 0"

# ---- network: the lock reads better than a shield for a VPN
add("network-vpn-disabled", "status", slash(S(*LOCK)), alias=("network-vpn-disconnected",))
add("network-vpn-acquiring", "status", dimmed(S(*LOCK)))
_b, _r = bang(20, 13, 16.5, 20)
add("network-vpn-no-route", "status", with_badge(S(R(3, 11, 13, 10, 3), "M6 11V8a4 4 0 0 1 8 0v3"), _b, _r))

# ================================================================== display, brightness, night light
add("display-brightness", "status", S(*SUN), alias=("weather-clear",))
add("keyboard-brightness", "status", S(R(2, 12, 20, 9, 3), D(7, 16.5), D(12, 16.5), D(17, 16.5), L(12, 3, 12, 6), L(5.5, 5, 7.5, 7.2), L(18.5, 5, 16.5, 7.2)))
add("night-light", "status", S(xf(MOON, 0.82, -0.5, 2.2), L(18, 3, 18, 7), L(16, 5, 20, 5)))
add("night-light-disabled", "status", slash(S(MOON)))
add("system-suspend", "status", S(MOON))
add("weather-clear-night", "status", S(xf(MOON, 0.88, 0.7, 0.3), D(19.5, 4.5)))

_hz, _half = L(2.5, 19, 21.5, 19), arc(12, 19, 5, 180, 360)
_diag = [L(5.2, 12.2, 6.9, 13.9), L(18.8, 12.2, 17.1, 13.9)]
add("daytime-sunrise", "status", S(_hz, _half, *_diag, L(12, 3, 12, 8), P((9, 5.5), (12, 2.5), (15, 5.5))))
add("daytime-sunset", "status", S(_hz, _half, *_diag, L(12, 2.5, 12, 7.5), P((9, 5), (12, 8), (15, 5))))

# ================================================================== notifications
add("notification", "status", S(BELL, BELL_CLAPPER), alias=("preferences-system-notifications",))
_dot, _rg = dot_badge(19, 5, 3.0)
add("notification-new", "status", with_badge(S(BELL, BELL_CLAPPER), _dot, _rg, gap=5.4))
add("notifications-disabled", "status", slash(S(BELL, BELL_CLAPPER)))

# ================================================================== session and power
_PWR = [L(12, 3, 12, 11), arc(12, 13, 8, -50, 230)]
add("system-shutdown", "status", S(*_PWR))
def arc_head(cx, cy, r, a_end, size=4.0, cw=True):
    """Arrow head at the end of an arc that stops at angle a_end (degrees); cw = the arc runs clockwise."""
    t = math.radians(a_end)
    k = 1 if cw else -1
    return head(cx + r * math.cos(t), cy + r * math.sin(t), -k * math.sin(t), k * math.cos(t), size)


add("system-reboot", "status", S(arc(12, 12, 8, -40, 235), arc_head(12, 12, 8, 235)))
add("system-lock-screen", "status", S(*LOCK), alias=("channel-secure", "changes-prevent", "network-vpn", "emblem-readonly"))
add("channel-insecure", "status", S(*UNLOCK), alias=("changes-allow",))
add("system-log-out", "status", S(RP([(10, 4), (5, 4), (5, 20), (10, 20)], 2.5), L(10, 12, 20, 12), head(20, 12, 1, 0, 4.5)), rtl=True,
    alias=("application-exit",))
add("system-switch-user", "status", S(L(4, 8, 20, 8), head(20, 8, 1, 0, 4.5), L(20, 16, 4, 16), head(4, 16, -1, 0, 4.5)), rtl=True)
add("system-run", "status", S(R(3, 4, 18, 16, 4), P((7.5, 9), (11, 13), (7.5, 17)), L(13, 17, 17, 17)), alias=("utilities-terminal",))


def _gauge(angle):
    a = math.radians(angle)
    return S(arc(12, 17, 9, 180, 360), L(3, 17, 21, 17), L(12, 17, 12 + 6.5 * math.cos(a), 17 + 6.5 * math.sin(a)))


add("power-profile-power-saver", "status", _gauge(-150))
add("power-profile-balanced", "status", _gauge(-90))
add("power-profile-performance", "status", _gauge(-30))

# ================================================================== presence
_ring = C(12, 12, 9)
add("user-available", "status", S(_ring, P((8, 12.5), (11, 15.5), (16.5, 9))), alias=("emblem-default", "emblem-ok-circle"))
add("user-away", "status", S(_ring, P((12, 7), (12, 12), (15.5, 14))), alias=("preferences-system-time", "appointment-soon"))
add("user-busy", "status", S(_ring, L(8, 12, 16, 12)))
add("user-idle", "status", S(_ring, xf(MOON, 0.45, -0.3, -0.3)))
add("user-invisible", "status", S(*[arc(12, 12, 9, 45 * k + 12, 45 * k + 33) for k in range(8)]))
add("user-offline", "status", S(_ring) + F(disc(12, 12, 3)))
add("user-status-pending", "status", S(_ring, D(8, 12), D(12, 12), D(16, 12)))

# ================================================================== security and dialogs
add("security-high", "status", S(SHIELD, P((8.5, 12), (11, 14.5), (15.5, 9.5))), alias=("mail-mark-notjunk",))
add("security-medium", "status", S(SHIELD, L(9, 12, 15, 12)))
add("security-low", "status", S(SHIELD, L(12, 8.5, 12, 12.5), D(12, 15.7)))
add("dialog-password", "status", S(C(7.5, 16.5, 4), L(10.6, 13.4, 20, 4), L(16.6, 7.4, 19.2, 10), L(13.8, 10.2, 16, 12.4)))
add("dialog-information", "status", S(C(12, 12, 9), L(12, 11, 12, 16.5), D(12, 7.6)), alias=("preferences-system-details",))
add("dialog-warning", "status", S(Pc((12, 3.5), (21.5, 20), (2.5, 20)), L(12, 10, 12, 14.2), D(12, 17.2)), alias=("weather-severe-alert",))
add("dialog-error", "status", S(C(12, 12, 9), L(12, 7.2, 12, 12.6), D(12, 16.4)), alias=("software-update-urgent", "emblem-important"))
add("dialog-question", "status", S(C(12, 12, 9), "M9.500 9.400a2.600 2.600 0 0 1 5 1c0 1.800-2.500 2.100-2.500 3.900", D(12, 17.4)))

# ================================================================== privacy indicators
_CAM = S(RP([(3, 8), (7.5, 8), (9, 5), (15, 5), (16.5, 8), (21, 8), (21, 20), (3, 20)], 2.5, closed=True), C(12, 13.2, 3.6))
add("camera-photo", "devices", _CAM)
add("camera-disabled", "status", slash(_CAM))
_b, _r = lock_badge(18.5, 16)
add("camera-hardware-disabled", "status", with_badge(_CAM, _b, _r))
add("location-services-active", "status", S(Pc((12, 3), (20, 20), (12, 16), (4, 20))))
add("location-services-disabled", "status", slash(S(Pc((12, 3), (20, 20), (12, 16), (4, 20)))))
add("screen-shared", "status", S(R(3, 4, 18, 12, 3.5), L(12, 16, 12, 20), L(8, 20, 16, 20)) + F(disc(12, 10, 2.6)))

# ================================================================== mail
_ENV = [R(3, 5, 18, 14, 4), P((4.5, 8.5), (12, 13.5), (19.5, 8.5))]
add("mail-unread", "status", with_badge(S(*_ENV), *dot_badge(19, 5, 3.4), gap=5.6))
add("mail-read", "status", S("M3 10l9-6.500 9 6.500v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z", P((3.5, 10.5), (12, 15.5), (20.5, 10.5))))
add("mail-attachment", "status", S("M19 11.500l-7 7a4.500 4.500 0 0 1-6.400-6.400l7.500-7.500a3 3 0 0 1 4.200 4.200l-7.200 7.200a1.500 1.500 0 0 1-2.100-2.100l6.200-6.200"))

# ================================================================== favourites
_STAR = star(12, 12.6, 9.3, 4.3)
add("starred", "status", FS(_STAR))
add("non-starred", "status", S(_STAR))
_sp_pts = [(12 + (9.3 if i % 2 == 0 else 4.3) * math.cos(-math.pi / 2 + i * math.pi / 5),
            12.6 + (9.3 if i % 2 == 0 else 4.3) * math.sin(-math.pi / 2 + i * math.pi / 5)) for i in range(10)]
add("semi-starred", "status", S(_STAR) + F(Pc(*clip_half(_sp_pts, 12.0, True))))

# ================================================================== weather
# Three cloud sizes, all built by cloud(): arcs and one baseline on a whole unit.
CLOUD_M = cloud((7, 11, 3), (12, 8.5, 5.5), (17, 11, 3))                # for rain, snow, storm and fog: 16 wide, 11 high
CLOUD_S = cloud((12, 16, 3), (15, 13.5, 4.5), (18, 16, 3))              # in front of the sun or the moon: 12 wide, 10 high
_SUN_S = [C(9, 9, 3), rays(9, 9, 5.6, 7.1)]
_MOON_S = crescent((6.5, 6.5, 4.6), (9.4, 4.2, 4.2))          # a solid crescent for the night icons


def _behind(parts, front, gap=3.25):
    """What a cloud hides: the strokes of `parts` are cleared around the cloud's outline, crumbs dropped."""
    return cut_parts(parts, outline(front), gap, min_len=1.0) + S(front)


add("weather-overcast", "status", S(CLOUD))
add("weather-few-clouds", "status", _behind(S(*_SUN_S), CLOUD_S))
add("weather-few-clouds-night", "status", F(_MOON_S) + S(CLOUD_S))
add("weather-showers", "status", S(CLOUD_M, L(8, 17.5, 7, 21), L(12, 17.5, 11, 21), L(16, 17.5, 15, 21)))
add("weather-showers-scattered", "status", S(CLOUD_M, L(9, 17.5, 8, 21), L(15, 17.5, 14, 21)))
add("weather-snow", "status", S(CLOUD_M, D(8, 18.5), D(12, 21), D(16, 18.5)))
add("weather-storm", "status", S(CLOUD_M) + F(Pc((13.5, 16.2), (9.6, 20), (12.4, 20), (10.4, 23), (15.2, 18.2), (12.4, 18.2))))
add("weather-fog", "status", S(CLOUD_M, L(4, 18, 20, 18), L(8, 21, 16, 21)))
add("weather-windy", "status", S("M3 9h11a3 3 0 1 0-3-3", "M3 13h15a3 3 0 1 1-3 3", "M3 17h6a2.500 2.500 0 1 1-2.500 2.500"))
add("weather-tornado", "status", S(L(3, 5, 21, 5), L(5, 9, 19, 9), L(8, 13, 16, 13), L(10, 17, 14, 17), L(11.5, 21, 12.5, 21)))

# ================================================================== printing, updates
_PRN = S(P((7, 8), (7, 4), (17, 4), (17, 8)), R(3, 8, 18, 9, 3), P((7, 17), (7, 21), (17, 21), (17, 17)))
add("printer", "devices", _PRN + S(D(17, 12)))
_b, _r = bang(20, 12, 15.5, 19)
add("printer-error", "status", with_badge(_PRN, _b, _r), alias=("printer-warning",))
add("printer-printing", "status", _PRN + S(L(9, 12, 15, 12)))
add("software-update-available", "status", S(C(12, 12, 9), L(12, 7, 12, 15), P((8.5, 11.8), (12, 15.3), (15.5, 11.8))))

# ================================================================== playlist
add("media-playlist-shuffle", "status", S("M3 7h3c2.400 0 3.500 1.200 4.700 3.100l2.600 4.800c1.100 1.900 2.400 3.100 4.700 3.100H21", "M3 17h3c1.500 0 2.600-.5 3.600-1.500", "M14.400 8.500c1-.9 2.100-1.500 3.600-1.500H21", P((18, 4), (21, 7), (18, 10)), P((18, 14), (21, 17), (18, 20))))
_rep = [RP([(4, 11), (4, 7), (20, 7)], 3), RP([(20, 13), (20, 17), (4, 17)], 3), P((17, 4), (20, 7), (17, 10)), P((7, 14), (4, 17), (7, 20))]
add("media-playlist-repeat", "status", S(*_rep))
add("media-playlist-repeat-song", "status", S(*_rep) + S(L(12, 10.5, 12, 14)))
add("media-playlist-consecutive", "status", S(L(3, 12, 17, 12), P((13, 8), (17, 12), (13, 16)), L(21, 7, 21, 17)))
