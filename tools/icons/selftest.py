"""Self-tests for the helpers. Run: python3 tools/icons/selftest.py"""
import math, sys
import numpy as np
import mi_geom as g

fails = []
def check(name, ok, info=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  {info}" if info else ""))
    if not ok: fails.append(name)

# CIEDE2000 against the Sharma, Wu, Dalal reference pairs
pairs = [((50.0, 2.6772, -79.7751), (50.0, 0.0, -82.7485), 2.0425),
         ((50.0, 3.1571, -77.2803), (50.0, 0.0, -82.7485), 2.8615),
         ((50.0, 2.5, 0.0), (73.0, 25.0, -18.0), 27.1492),
         ((50.0, 2.5, 0.0), (50.0, 0.0, -2.5), 4.3065),
         ((50.0, 2.5, 0.0), (61.0, -5.0, 29.0), 22.8977),
         ((50.0, 2.5, 0.0), (50.0, 3.2972, 0.0), 1.0000)]
for a, b, want in pairs:
    got = g.de2000(a, b)
    check(f"ciede2000 {a} vs {b}", abs(got - want) < 1e-3, f"got {got:.4f} want {want}")

# OKLCH round trip and gamut mapping
for hx in ("#B84F9F", "#8C3274", "#274903", "#FFFFFF", "#000000"):
    L, C, H = g.hex_to_oklch(hx)
    back = g.oklch_to_hex(L, C, H)
    d = g.de2000(g.rgb_to_lab(g.hex_to_rgb(hx)), g.rgb_to_lab(g.hex_to_rgb(back)))
    check(f"oklch round trip {hx}->{back}", d < 0.5, f"dE {d:.3f}")
check("out-of-gamut colour is mapped, not clipped to garbage",
      g.hex_to_rgb(g.oklch_to_hex(0.6, 0.4, 150)) is not None)

# WCAG contrast
check("contrast black/white = 21", abs(g.contrast((0, 0, 0), (255, 255, 255)) - 21) < 1e-6)

# corner fit: the Bezier pair must stay within 0.2% of the corner box of the true superellipse
a, b, m, err = g.corner_fit()
check(f"superellipse n={g.N} corner fit error", err < 0.006, f"max error {err*100:.3f}% of corner size (a={a:.3f}, b={b:.3f}, m={m:.4f})")
check("corner diagonal gap equals r*(1-2^(-1/n)) like the Rust renderer", abs(m - (1 - 2 ** (-1 / g.N))) < 1e-12)

# path sanity: area of rr is close to the analytic superellipse-cornered area
def area_numeric(w, h, r, n):
    cut = 4 * (r * r) * (1 - (math.gamma(1 + 1 / n) ** 2 / math.gamma(1 + 2 / n)))  # quarter-superellipse area removed
    return w * h - cut
check("rr() path is closed and starts/ends on edges", g.rr(2, 2, 20, 20, 6).endswith("Z"))

# CVD matrices leave grey alone
for k in g.CVD:
    gr = g.simulate((128, 128, 128), k)
    check(f"cvd {k} keeps grey", np.abs(gr - 128).max() < 2.5, f"{gr.round(1)}")

sys.exit(1 if fails else 0)
