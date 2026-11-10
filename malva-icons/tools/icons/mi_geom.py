"""Geometry, colour and measurement helpers for the MalvaOS icon tools (pure Python + numpy).

Everything that must agree with the rest of the system is read from it, not retyped:
  * the corner family (superellipse exponent) comes from the Balance dial in
    crates/malva-tokens/src/balance.rs (CORNER_EXPONENT);
  * brand seeds come from tokens/tokens.toml.
"""
from __future__ import annotations

import math
import re
import tomllib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]


# ------------------------------------------------------------------ tokens
def corner_exponent() -> float:
    p = ROOT / "crates/malva-tokens/src/balance.rs"
    if p.exists():
        src = p.read_text()
        m = re.search(r"pub const CORNER_EXPONENT: f64 = ([0-9.]+);", src)
        if m:
            return float(m.group(1))
    return 4.0


def tokens() -> dict:
    p = ROOT / "tokens/tokens.toml"
    if p.exists():
        return tomllib.loads(p.read_text())
    return {
        "brand": {
            "plum_light": "#A24E8C",
            "plum_dark": "#4E1D42",
            "orchid": "#C763B0",
            "lilac_top": "#FBF3FA",
            "lilac_bot": "#DEC3E0",
            "leaf": "#9DBB7E",
            "leaf_dark": "#4F7A2F",
        }
    }


N = corner_exponent()


# ------------------------------------------------------------------ number formatting
def f(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# ------------------------------------------------------------------ superellipse corners
def _fit_corner(n: float):
    """Fit two cubic Beziers per quarter-corner of the superellipse |1-X|^n + |1-Y|^n = 1 on
    the unit box, tangent to the box edges. Returns (a, b, m, max_error)."""
    m = 1 - 2 ** (-1 / n)
    # true curve samples: points (X, Y) with (1-X)^n + (1-Y)^n = 1, V=(0,1) to H=(1,0)
    # true curve, sampled densely from both parametrisations so no stretch is sparse
    u = np.linspace(0, 1, 6001)
    yx = 1 - (1 - (1 - u) ** n) ** (1 / n)          # Y as a function of X = u
    xy = 1 - (1 - (1 - u) ** n) ** (1 / n)          # X as a function of Y = u (symmetric)
    curve = np.concatenate([np.stack([u, yx], 1), np.stack([xy, u], 1)])
    d = np.array([1, -1]) / math.sqrt(2)
    M = np.array([m, m])
    V = np.array([0.0, 1.0])
    ts = np.linspace(0, 1, 101)[:, None]
    half = curve[(curve[:, 0] <= m + 1e-9) & (curve[:, 1] >= m - 1e-9)]
    half = half[::max(1, len(half) // 500)]

    def err(a, b):
        P = [V, V + np.array([0, -a]), M - b * d, M]
        bz = ((1 - ts) ** 3 * P[0] + 3 * (1 - ts) ** 2 * ts * P[1]
              + 3 * (1 - ts) * ts ** 2 * P[2] + ts ** 3 * P[3])
        d1 = np.sqrt(((half[:, None, :] - bz[None, :, :]) ** 2).sum(2)).min(1).max()
        d2 = np.sqrt(((bz[:, None, :] - half[None, :, :]) ** 2).sum(2)).min(1).max()
        return max(d1, d2)

    best = (1e9, 0.0, 0.0)
    lo_a, hi_a, lo_b, hi_b = 0.05, 0.9, 0.02, 0.6
    for step in (0.02, 0.004, 0.0008):
        for a in np.arange(lo_a, hi_a, step):
            for b in np.arange(lo_b, hi_b, step):
                e = err(a, b)
                if e < best[0]:
                    best = (e, a, b)
        lo_a, hi_a = best[1] - 4 * step, best[1] + 4 * step
        lo_b, hi_b = max(0.001, best[2] - 4 * step), best[2] + 4 * step
    return best[1], best[2], m, best[0]


_CORNER = {}
_CACHE = Path(__file__).with_name("corner_fit_cache.json")


def corner_fit(n: float = N):
    """Fitting takes a few seconds, so results are cached next to this file (deterministic)."""
    import json
    if not _CORNER and _CACHE.exists():
        _CORNER.update({float(k): tuple(v) for k, v in json.loads(_CACHE.read_text()).items()})
    if n not in _CORNER:
        _CORNER[n] = _fit_corner(n)
        _CACHE.write_text(json.dumps({str(k): list(v) for k, v in sorted(_CORNER.items())}))
    return _CORNER[n]


def rr(x: float, y: float, w: float, h: float, r: float, n: float = N) -> str:
    """Rounded rectangle as a path, corners on the Balance-dial superellipse (not circular arcs).
    r is the corner box size: the curve leaves each edge r from the corner."""
    r = max(0.0, min(r, w / 2, h / 2))
    if r < 1e-6:
        return f"M{f(x)} {f(y)}H{f(x + w)}V{f(y + h)}H{f(x)}Z"
    a, b, m, _ = corner_fit(n)
    k = b / math.sqrt(2)
    V = (0.0, 1.0); H = (1.0, 0.0); M = (m, m)
    # normalized segments
    v2m = [V, (0.0, 1 - a), (m - k, m + k), M]
    m2h = [M, (m + k, m - k), (1 - a, 0.0), H]
    h2m = [H, (1 - a, 0.0), (m + k, m - k), M]
    m2v = [M, (m - k, m + k), (0.0, 1 - a), V]

    def mp(pt, corner):
        X, Y = pt
        if corner == "tl":
            return (x + r * X, y + r * Y)
        if corner == "tr":
            return (x + w - r * X, y + r * Y)
        if corner == "br":
            return (x + w - r * X, y + h - r * Y)
        return (x + r * X, y + h - r * Y)  # bl

    def cubic(seg, corner):
        p = [mp(q, corner) for q in seg]
        return "C" + " ".join(f"{f(px)} {f(py)}" for px, py in p[1:])

    d = [f"M{f(x + r)} {f(y)}", f"H{f(x + w - r)}"]
    d += [cubic(h2m, "tr"), cubic(m2v, "tr")]          # top-right: H -> V
    d += [f"V{f(y + h - r)}"]
    d += [cubic(v2m, "br"), cubic(m2h, "br")]          # bottom-right: V -> H
    d += [f"H{f(x + r)}"]
    d += [cubic(h2m, "bl"), cubic(m2v, "bl")]          # bottom-left: H -> V
    d += [f"V{f(y + r)}"]
    d += [cubic(v2m, "tl"), cubic(m2h, "tl")]          # top-left: V -> H
    d += ["Z"]
    return "".join(d)


# ------------------------------------------------------------------ colour
def srgb_to_lin(c):
    c = np.asarray(c, dtype=float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.asarray(c, dtype=float)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.clip(c, 0, None) ** (1 / 2.4) - 0.055)


def hex_to_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb) -> str:
    return "#" + "".join(f"{int(round(max(0, min(255, v)))):02X}" for v in rgb)


def oklab_from_lin(rgb):
    r, g, b = rgb
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = np.cbrt(l), np.cbrt(m), np.cbrt(s)
    return (0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_)


def lin_from_oklab(L, a, b):
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)


def hex_to_oklch(h: str):
    rgb = srgb_to_lin(np.array(hex_to_rgb(h)) / 255)
    L, a, b = oklab_from_lin(rgb)
    return L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


def oklch_to_hex(L: float, C: float, H: float) -> str:
    """Chroma-reduction gamut mapping at constant L and H (same approach as malva-tokens)."""
    def conv(c):
        a, b = c * math.cos(math.radians(H)), c * math.sin(math.radians(H))
        return lin_from_oklab(L, a, b)
    lo, hi = 0.0, C
    rgb = conv(C)
    if all(-1e-4 <= v <= 1 + 1e-4 for v in rgb):
        pass
    else:
        for _ in range(40):
            mid = (lo + hi) / 2
            if all(-1e-4 <= v <= 1 + 1e-4 for v in conv(mid)):
                lo = mid
            else:
                hi = mid
        rgb = conv(lo)
    srgb = lin_to_srgb(np.clip(rgb, 0, 1)) * 255
    return rgb_to_hex(srgb)


def rel_lum(rgb255) -> float:
    r, g, b = srgb_to_lin(np.array(rgb255) / 255)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a255, b255) -> float:
    la, lb = rel_lum(a255), rel_lum(b255)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# CIEDE2000 -----------------------------------------------------------------
def rgb_to_lab(rgb255):
    r, g, b = srgb_to_lin(np.array(rgb255, dtype=float) / 255)
    X = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    Y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    Z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b
    xn, yn, zn = 0.95047, 1.0, 1.08883

    def ff(t):
        return t ** (1 / 3) if t > (6 / 29) ** 3 else t / (3 * (6 / 29) ** 2) + 4 / 29
    fx, fy, fz = ff(X / xn), ff(Y / yn), ff(Z / zn)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def de2000(lab1, lab2) -> float:
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    if C1p * C2p == 0:
        dhp = 0.0
    else:
        dhp = h2p - h1p
        if dhp > 180:
            dhp -= 360
        elif dhp < -180:
            dhp += 360
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp / 2))
    Lbp, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0:
        hbp = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hbp = (h1p + h2p) / 2
    elif h1p + h2p < 360:
        hbp = (h1p + h2p + 360) / 2
    else:
        hbp = (h1p + h2p - 360) / 2
    T = (1 - 0.17 * math.cos(math.radians(hbp - 30)) + 0.24 * math.cos(math.radians(2 * hbp))
         + 0.32 * math.cos(math.radians(3 * hbp + 6)) - 0.20 * math.cos(math.radians(4 * hbp - 63)))
    dth = 30 * math.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lbp - 50) ** 2 / math.sqrt(20 + (Lbp - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cbp, 1 + 0.015 * Cbp * T
    Rt = -math.sin(math.radians(2 * dth)) * Rc
    return math.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2
                     + Rt * (dCp / Sc) * (dHp / Sh))


# colour-vision-deficiency simulation (Machado, Oliveira, Fernandes 2009, severity 1.0)
CVD = {
    "protan": np.array([[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216],
                        [-0.003882, -0.048116, 1.051998]]),
    "deutan": np.array([[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413],
                        [-0.011820, 0.042940, 0.968881]]),
    "tritan": np.array([[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602],
                        [0.004733, 0.691367, 0.303900]]),
}


def simulate(rgb255, kind: str):
    lin = srgb_to_lin(np.array(rgb255, dtype=float) / 255)
    out = np.clip(CVD[kind] @ lin, 0, 1)
    return lin_to_srgb(out) * 255
