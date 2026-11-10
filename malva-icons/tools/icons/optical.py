"""The one centring rule of the icon tools.

Put the BOX of a drawing on the centre of its canvas, then let its mass pull a little: a fifth of the way from the box
to the mass, never more than 1 % of the canvas.

Why not halfway, as the first version did (box and mass each off by half their distance)? Because the eye reads the
margins against the tile edge first. Measured on the pixels: the signal-bars tile centred halfway sat 3.5 % of the tile
to the left and 3.1 % up, the text-editor glyph of the first app icons 2.7 % to the right, and the trash can jumped 4.2 %
when the bin filled: each looked like a mistake beside its neighbours. A 1 % pull is the most that still reads as
"centred" and still helps a play triangle or a wedge look balanced.

    shift(box_off, mass_off, canvas)  ->  the shift to add on one axis

`box_off` and `mass_off` are the offsets of the box centre and of the centre of mass from the canvas centre, in any
unit; `canvas` is the canvas size in that unit.
"""
from __future__ import annotations

W_MASS = 0.20       # share of the box-to-mass distance that may pull the box off centre
CAP = 0.010         # ... but never by more than this share of the canvas


def pull(box_off: float, mass_off: float, canvas: float, w: float = W_MASS, cap: float = CAP) -> float:
    """How far the box is left from the canvas centre on purpose (signed, towards the side the mass lies on, reversed)."""
    d = w * (mass_off - box_off)
    return max(-cap * canvas, min(cap * canvas, d))


def shift(box_off: float, mass_off: float, canvas: float, w: float = W_MASS, cap: float = CAP) -> float:
    """The shift to add on one axis so the box ends on the centre, less the capped pull of the mass."""
    return -box_off - pull(box_off, mass_off, canvas, w, cap)


def residual(box_off: float, mass_off: float, canvas: float, w: float = W_MASS, cap: float = CAP) -> float:
    """Where the box ends up after `shift`: the most any drawing is allowed to sit off the centre by this rule."""
    return box_off + shift(box_off, mass_off, canvas, w, cap)
