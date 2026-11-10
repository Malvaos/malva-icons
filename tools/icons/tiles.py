"""Settings-pane and menu-category icons: a symbol from the one-colour glyph kit on an app-format tile.

An app icon (apps.py) is a chunky lilac glyph on a coloured squircle. These are the same squircle, gradient, light and
shadow (appfmt.app_icon_svg), carrying one of the kit's stroke symbols in lilac instead of a bespoke drawing. So a
Settings pane and the symbol the panel shows for it are one shape, and ~60 tiles cost one line each.

  * a tile's colour is its group's colour (Network blue, Personalisation orchid, Privacy green ...): you find a pane
    by colour first and by symbol second, as in macOS System Settings;
  * the symbol is the kit's drawing scaled by 8 local units per grid unit and stroked 2.3 (a little heavier than the
    panel's 2.0: a tile is looked at from further away and the lilac has to stand against a mid-tone);
  * one SVG per tile, for every size.

Run: python3 tools/icons/tiles.py --centre      (measures every symbol and writes tile_shifts.json)
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import glyphs_all                            # noqa: F401  registers the kit
import glyphkit as K
from appfmt import Tile, Glyph, P, Dm, app_icon_svg, UNIT

K_UNIT = 200.0 / 24.0          # local units per grid unit: the kit's 20-unit ink becomes the app glyphs' 166
STROKE = 2.3                   # kit units
TF = f"scale({K_UNIT:.4f}) translate(-12 -12)"
SHIFTS = Path(__file__).with_name("tile_shifts.json")

# ---- group colours. Hues as the app tiles use them (OKLCH degrees); System is the graphite of the Settings app icon.
GROUPS = {
    "network": ("Network and sharing", Tile(h=250)),
    "personal": ("Personalisation", Tile(h=330)),
    "sound": ("Sound and notifications", Tile(h=28)),
    "privacy": ("Privacy and security", Tile(h=150)),
    "hardware": ("Devices and power", Tile(h=64)),
    "accounts": ("Accounts", Tile(h=200)),
    "system": ("System", Tile(h=265, c=0.045, l=0.54, ld=0.30, cd=0.04)),
}


@dataclass(frozen=True)
class Spec:
    id: str                    # icon-theme name (coloured); the one-colour symbol is `<id>-symbolic` where the kit has one
    name: str                  # what a Settings sidebar calls it
    group: str                 # key of GROUPS, or "" for a tile with its own colour
    glyph: str                 # id in the glyph kit, or in EXTRA
    tile: Tile | None = None   # own colour when group == ""


# ---- symbols only the tiles use (not theme names)
EXTRA = {
    "drive": K.S(K.R(3, 8, 18, 8, 3.5), K.D(7.5, 12), K.L(12, 12, 17, 12)),      # a drive drawn on the middle of the grid (it was drawn 2 units low)
    "landscape": K.S("M2 19L9 10L14 16L17 13L22 19Z", K.C(16.5, 6.5, 2.5)),
    "calendar": K.S(K.R(3, 5, 18, 16, 4), K.L(3, 10, 21, 10), K.L(8, 3, 8, 7), K.L(16, 3, 16, 7)) + K.F(K.disc(8, 15, 1.4), K.disc(12, 15, 1.4), K.disc(16, 15, 1.4)),
    "dots": K.F(K.disc(5, 12, 3.1), K.disc(12, 12, 3.1), K.disc(19, 12, 3.1)),
}


def parts_of(glyph: str):
    return EXTRA[glyph] if glyph in EXTRA else K.GLYPHS[glyph].parts


SPECS = [
    # --- Network and sharing
    Spec("preferences-system-network", "Network", "network", "network-workgroup"),
    Spec("preferences-system-wifi", "Wi-Fi", "network", "network-wireless-signal-excellent"),
    Spec("preferences-system-bluetooth", "Bluetooth", "network", "bluetooth-active"),
    Spec("preferences-system-mobile", "Mobile Network", "network", "network-cellular-signal-excellent"),
    Spec("preferences-system-airplane", "Airplane Mode", "network", "airplane-mode"),
    Spec("preferences-system-sharing", "Sharing", "network", "send-to"),
    # --- Personalisation
    Spec("preferences-desktop-appearance", "Appearance", "personal", "preferences-desktop-appearance"),
    Spec("preferences-desktop-wallpaper", "Wallpaper", "personal", "landscape"),
    Spec("preferences-desktop-font", "Fonts", "personal", "font-select"),
    Spec("preferences-desktop-dock", "Dock", "personal", "preferences-desktop-dock"),
    Spec("preferences-system-night-light", "Night Light", "personal", "night-light"),
    # --- Sound and notifications
    Spec("preferences-system-notifications", "Notifications", "sound", "notification"),
    Spec("preferences-desktop-sound", "Sound", "sound", "audio-volume-high"),
    # --- Privacy and security
    Spec("preferences-system-privacy", "Privacy", "privacy", "preferences-system-privacy"),
    Spec("preferences-desktop-screensaver", "Screen Lock", "privacy", "preferences-desktop-screensaver"),
    Spec("preferences-system-authentication", "Fingerprint", "privacy", "auth-fingerprint"),
    Spec("preferences-system-location", "Location", "privacy", "location-services-active"),
    Spec("preferences-system-camera", "Camera", "privacy", "camera-photo"),
    Spec("preferences-system-microphone", "Microphone", "privacy", "audio-input-microphone"),
    Spec("preferences-system-security", "Security", "privacy", "security-high"),
    # --- Devices and power
    Spec("preferences-desktop-display", "Displays", "hardware", "video-display"),
    Spec("preferences-color", "Colour", "hardware", "preferences-color"),
    Spec("preferences-desktop-keyboard", "Keyboard", "hardware", "input-keyboard"),
    Spec("preferences-desktop-keyboard-shortcuts", "Keyboard Shortcuts", "hardware", "preferences-desktop-keyboard-shortcuts"),
    Spec("preferences-desktop-mouse", "Mouse", "hardware", "input-mouse"),
    Spec("preferences-desktop-touchpad", "Touchpad", "hardware", "input-touchpad"),
    Spec("preferences-desktop-tablet", "Drawing Tablet", "hardware", "input-tablet"),
    Spec("preferences-system-printers", "Printers", "hardware", "printer"),
    Spec("preferences-system-removable-media", "Removable Media", "hardware", "media-eject"),
    Spec("preferences-system-power", "Power", "hardware", "battery-level-70"),
    Spec("preferences-system-storage", "Storage", "hardware", "drive"),
    # --- Accounts
    Spec("preferences-system-users", "Users", "accounts", "system-users"),
    Spec("preferences-system-online-accounts", "Online Accounts", "accounts", "weather-overcast"),
    # --- System
    Spec("preferences-system-details", "About", "system", "dialog-information"),
    Spec("preferences-system-time", "Date and Time", "system", "calendar"),
    Spec("preferences-desktop-default-applications", "Default Applications", "system", "starred"),
    Spec("preferences-desktop-locale", "Region and Language", "system", "preferences-desktop-locale"),
    Spec("preferences-desktop-accessibility", "Accessibility", "system", "emoji-body"),
    Spec("preferences-desktop-multitasking", "Multitasking", "system", "preferences-desktop-multitasking"),
    Spec("preferences-desktop-apps", "Applications", "system", "view-grid"),
    Spec("preferences-system-search", "Search", "system", "edit-find"),
    Spec("preferences-system-parental-controls", "Parental Controls", "system", "preferences-system-parental-controls"),
    Spec("preferences-desktop-remote-desktop", "Remote Desktop", "system", "preferences-desktop-remote-desktop"),
    Spec("preferences-other", "Other", "system", "sliders"),
    # --- application-menu categories: each has its own colour
    Spec("applications-internet", "Internet", "", "preferences-desktop-locale", Tile(h=250)),     # the globe: one drawing, two names
    Spec("applications-office", "Office", "", "applications-office", Tile(h=240)),
    Spec("applications-development", "Development", "", "applications-development", Tile(h=330, c=0.035, l=0.31, ld=0.14, cd=0.03)),
    Spec("applications-games", "Games", "", "input-gaming", Tile(h=312)),
    Spec("applications-graphics", "Graphics", "", "applications-graphics", Tile(h=8)),
    Spec("applications-multimedia", "Sound and Video", "", "applications-multimedia", Tile(h=36)),
    Spec("applications-science", "Science", "", "applications-science", Tile(h=184)),
    Spec("applications-engineering", "Engineering", "", "applications-engineering", Tile(h=156)),
    Spec("applications-utilities", "Utilities", "", "applications-utilities", Tile(h=94, c=0.11)),
    Spec("applications-system", "System Tools", "", "preferences-system", Tile(h=265, c=0.045, l=0.54, ld=0.30, cd=0.04)),
    Spec("applications-other", "Other", "", "dots", Tile(h=212)),
]
BY_ID = {s.id: s for s in SPECS}
ORDER = [s.id for s in SPECS]


def tile_of(spec: Spec) -> Tile:
    return GROUPS[spec.group][1] if spec.group else spec.tile


def els_of(glyph: str, stroke: float = STROKE):
    """The kit's drawing as app-format elements: strokes stay strokes, fills stay fills, the kit's dim parts become the
    dim tone (35 % like the panel's, not the app icons' 55 %)."""
    out = []
    for p in K.GLYPHS[glyph].parts if glyph in K.GLYPHS else EXTRA[glyph]:
        assert not p.eo, f"{glyph}: even-odd fills have no app-format equivalent"
        mk = (lambda d, **k: Dm(d, op=K.DIM, **k)) if p.dim else P
        if p.kind == "S":
            out.append(mk(p.d, stroke=stroke, tf=TF))
        elif p.kind == "FS":
            out.append(mk(p.d, rnd=stroke, tf=TF))
        else:
            out.append(mk(p.d, tf=TF))
    return out


def shifts():
    return json.loads(SHIFTS.read_text()) if SHIFTS.exists() else {}


AIM = 0.52            # longest side of the symbol as a share of the tile: the median of the app icons (0.455..0.545)
# A symbol whose silhouette lies almost on another's once both are centred is drawn a little smaller: a half-filled disc is
# heavy for its size anyway, and its ring then no longer falls on the globe's ring (IoU 0.60 -> below 0.55 with a margin).
AIM_BY_ID = {"preferences-desktop-appearance": 0.46, "preferences-desktop-dock": 0.47}
BASE = 1.15           # the app icons' glyph scale


def glyph_of(i: str, measured: bool = True) -> Glyph:
    sp = BY_ID[i]
    gl = Glyph(tile_of(sp), els_of(sp.glyph), sp.name, BASE)
    if measured:
        dx, dy, sc = shifts().get(i, (0.0, 0.0, BASE))
        gl.shift, gl.scale = (dx, dy), sc
    return gl


def tile_svg(i: str, **kw) -> str:
    return app_icon_svg(glyph_of(i), i, BY_ID[i].name, "full", **kw)


def symbol_svg(i: str) -> str:
    """The same symbol with no tile, one colour (what a toolkit recolours): the kit's own file."""
    return K.svg(K.GLYPHS[BY_ID[i].glyph])


# ----------------------------------------------------------------------------------------------- centring
def _ink(R, gl, i, S):
    import numpy as np
    a = R.render([app_icon_svg(gl, i, i, tile=False, shadow=False)], S)[0][..., 3].astype(float)
    ys, xs = np.nonzero(a > 127)
    return a, xs, ys


def centre():
    """Two measurements on rendered pixels. Size: the scale at which the symbol's longest side is AIM of the tile
    (clamped to 0.95..1.30 x the apps' scale, 0.88 for the symbols in AIM_BY_ID, so a thin symbol is not blown up and a heavy one is not crushed; a few symbols have their own aim, AIM_BY_ID).
    Position: the box on the middle of the tile, less a capped pull of the mass (optical.py, the rule shared with
    centre.py and centre_objects.py)."""
    import numpy as np
    import optical
    from mi_render import Renderer
    S = 512
    out = {}
    with Renderer() as R:
        for i in ORDER:
            gl = glyph_of(i, measured=False)
            a, xs, ys = _ink(R, gl, i, S)
            longest = max(xs.max() - xs.min() + 1, ys.max() - ys.min() + 1) / S
            sc = round(min(max(BASE * AIM_BY_ID.get(i, AIM) / longest, BASE * (0.88 if i in AIM_BY_ID else 0.95)), BASE * 1.30), 3)
            gl.scale = sc
            a, xs, ys = _ink(R, gl, i, S)
            cx = (a * np.arange(S)[None, :]).sum() / a.sum() + 0.5
            cy = (a * np.arange(S)[:, None]).sum() / a.sum() + 0.5
            bx, by = (xs.min() + xs.max() + 1) / 2, (ys.min() + ys.max() + 1) / 2
            ox = optical.shift(bx - S / 2, cx - S / 2, S)
            oy = optical.shift(by - S / 2, cy - S / 2, S)
            ppu = S / 1024 * UNIT * sc
            sx, sy = round(ox / ppu, 1), round(oy / ppu, 1)
            out[i] = [float(sx), float(sy), sc]
    SHIFTS.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return out


if __name__ == "__main__":
    if "--centre" in sys.argv:
        r = centre()
        print(len(r), "tiles measured; scales", min(v[2] for v in r.values()), "..", max(v[2] for v in r.values()))
    else:
        print(len(SPECS), "tiles in", len(GROUPS), "groups +", sum(1 for s in SPECS if not s.group), "category tiles")
