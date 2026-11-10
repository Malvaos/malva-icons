# Music app icon: what was wrong, what changed, what was measured

Source: `tools/icons/apps.py` (`MUSIC`, `MUSIC_SMALL`, `music_parts`), sheet: `docs/icons/music-review.png`
(regenerate with `python3 tools/icons/music_review.py`). Checks: `tools/icons/check_apps.py`.

## Defects in the first version (found by looking at it enlarged)

* The bottom corner of each stem stuck out of its notehead (a small square foot).
* The beam had a notch where it met the left stem (beam corner radius against a straight stem edge).
* Stems, beam and heads were five separate shapes with no shared rule: head tilt 20 degrees, beam slope
  not tied to the heads, stems placed by eye.
* The glyph sat visibly off the tile centre (the centring offset was 17 local units).
* No leaf accent, unlike the rest of the set.

## The drawing now

* Two identical ellipses tilted -22 degrees; the beam runs parallel to the line through their centres.
* Each stem's right edge lies exactly on its head's right-most tangent and stops inside the head.
* One outline for stems and beam. Convex beam corners have the same true radius (7 units) at both ends,
  although the slanted beam gives them different angles. Every inside corner is filleted: beam/stem r4 and
  stem/head r4 (a filler shape that overlaps the stem and head so no anti-aliasing seam shows).
* A second, leaf-green beam (a sixteenth-note beam). It is the brand accent and is decorative: the icon
  reads without it. It is dropped in the small and symbolic cuts.
* The 32 px and 16 px cut is a separate drawing with heavier stems (19 vs 14), beam (30 vs 24) and heads,
  and no accent. Reason: at 32 px the 14-unit stems are about 1.4 px wide.
* Glyph scale 1.3 (was 1.15 for most icons), measured reach 0.50 of the half tile.

## Measured (all run on pixels, `docs/icons/` + `check_apps.py`)

| Check | Result |
|---|---|
| stem pixels below a head's tangent line (no foot) | 0 |
| beam angle vs line through the heads | -11.31 deg vs -11.31 deg (limit 0.6) |
| silhouette is one connected piece | 1 component |
| head areas | 21279 vs 21289 px (limit 1%) |
| closing the silhouette with a 2-unit disc adds | 4 px (limit 8); broken geometry without fillets: 48 px |
| optical centring | centroid 1.9% of tile off (limit 3.5%) |
| contrast glyph vs tile | min 4.08, median 5.09 (WCAG 3:1 required) |
| leaf accent vs tile | min 2.65 (decorative, floor 2.0) |

Each of the music checks has a negative test (a stem foot, a beam 0.1 slope off, missing fillets) that the
check rejects.

## Judgement, not measured

* That the sixteenth-note beam helps rather than distracts. A separate reviewer called the first version of it a
  stripe that went muddy at 48/64 px; the gap and thickness were enlarged (7 to 10, 10 to 13 units), the
  result was looked at by me only.
* That the terracotta tile suits Music. The reviewer found the sage accent on brick muddy; kept, because the
  accent colour is the brand's and the tile hue plan spaces 13 hues around the wheel.
* Not done: pixel-hinting the 16 px cut by hand, a rim light or glyph shadow (the supplied icon has none that
  renders; see the shadow note in the main design doc), a side-by-side with any platform's music icon.

## Side effects on the other 15 icons (re-checked, all pass)

* Optical centring was then the midpoint between the pixel centroid and the bounding-box centre (`centre.py`, W = 0.5).
  **Revised on Nov 9 (see `CENTRING.md`):** the box is now put on the middle of the tile, less a pull towards the mass
  of at most 1%, which moved the Music glyph from 1.8% left of the middle to 0.6%; its small cut now shares the full
  cut's centre. The "centroid 1.9% off" row in the table above belongs to the old rule.
* The symbolic (currentColor) icons are the small cut in one colour, with optical centring, and a canvas fitted
  per glyph so the longest half-extent fills 88% of it (checks: nothing clipped, 84-92% fill, 16 px ink).
