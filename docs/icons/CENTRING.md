# Where things sit in an icon

Every icon family is placed by one rule, `tools/icons/optical.py`:

> Put the **box** of the drawing on the middle of its canvas, then let its **mass** pull a little: a fifth of the way from
> the box to the mass, never more than 1 % of the canvas.

The eye reads a drawing's margins against the edge of the tile first. The rule before (Nov 4, `centre.py`, W = 0.5)
centred the average of box and mass, so a drawing whose mass lay far from its box ended up visibly off: the signal-bars
Settings tile 3.5 % left and 3.1 % up, the Text Editor symbol 2.7 % right, the cloud's arrow 2.7 % right of the cloud, the
bin's can jumping 4.2 % when the papers appeared. 1 % is the pull I chose: small enough to read as centred, large enough
to help a play triangle or a wedge look balanced. That is a judgement; the rest of this page is measured.

## Where the rule is applied

| Family | How | Tool that measures it and writes its table |
|---|---|---|
| 16 app icons (symbol on its tile) | box on the tile, small pull, shift in glyph units | `centre.py` -> `glyph_shifts.json` |
| 55 Settings and category tiles | same; the symbol is sized to 0.52 of the tile | `tiles.py --centre` -> `tile_shifts.json` |
| 64 objects (folders, files, drives ...) | box on the canvas; the bin's two states share one shift | `centre_objects.py` -> `object_shifts.json` |
| emblems on 41 objects (25 pages, 14 folders, 2 drives) | each emblem on its own origin; a folder puts the origin on the middle of its front face, a page on its centre of mass (1.2 % of the canvas below the middle of the page, because the dog-ear takes a corner off the top) | `centre_emblems.py` -> `emblem_shifts.json` |
| 375 kit glyphs (24 grid) | whole-unit shifts only, so strokes stay crisp; a level series (Wi-Fi, battery) moves as one | `kit_centre.py` -> `kit_shifts.json` |
| one-colour cuts of apps and objects | the cut's canvas is centred on the ink by the same rule | `build_apps.symbolic_vb`, `objfmt.fit_viewbox` |

No emblem carries a hand-set offset any more (`emblemshift.apply` refuses one).

## What changed, measured

Pixels come from Chromium; the box is the pixels above half opacity, the mass is the opacity-weighted centroid. Tile, app
and emblem numbers are read at 256 px, the object and one-colour comparisons at 160 px (so about +-0.3 % of resolution),
the kit glyphs at 96 px as `check_glyphs.py` does. "Off" is the larger of the horizontal and vertical offset of the box
from the middle, as a share of the tile or canvas. The "before" is what you have (the Nov 4 delivery), except for the
Settings tiles and the kit glyphs, which are new in this theme: for those it is the first build of this theme.

| Family | Before | After |
|---|---|---|
| Settings tiles (55) | up to 5.1 % off (Storage), mean 1.06 %, 17 beyond 1.25 % | up to 0.98 %, mean 0.37 %, none beyond |
| App icons, symbol on its tile (16) | up to 2.7 % (Text Editor), mean 0.96 %, 6 beyond 1.25 % | up to 0.78 %, mean 0.38 %, none beyond |
| App icons, one-colour cuts (15) | up to 4.4 % (Music), 7 beyond 1.25 % | up to 0.94 %, none beyond |
| Objects, full colour (45) | up to 2.5 % (cloud), mean 0.52 %; every folder 0.9 % high | mean 0.13 %; the cloud 1.25 %, every folder on the middle; the bin pair, see below |
| Objects, one-colour cuts (34) | up to 3.1 %, 14 beyond 1.25 % | up to 1.25 %, none beyond |
| Emblems on pages (10 existed on Nov 4; 25 now) | the symbol sat 7.9 to 11.5 % of the canvas **below** the page's centre of mass, and 3.5 % higher on one page than on another | all 25 within 0.83 % of it |
| Emblems on folders (10 existed on Nov 4; 14 now) | up to 1.8 % low on the front face | all 14 within 0.78 % |
| Kit glyphs (16 of the 375) | 0.76 to 1.24 units off the middle of the grid (the better of box and box-mass mean), mean 0.97 | at most 0.56 unit, mean 0.18 |

Named fixes:

* **Text Editor.** The pencil is 20 units further left and 8 higher (`translate(44 36)` -> `translate(24 28)`): page and
  pencil read as one object, the symbol is 5.7 % of the tile narrower and sits 0.8 % right of the middle (was 2.7 %).
* **Music.** The note moved from 1.8 % left of the middle to 0.6 %. Its small-size cut (16 to 32 px) was drawn 1.2 % left of
  the full cut, so the note hopped sideways between sizes; now 0.3 %.
* **Cloud storage.** The arrow stood 28 units (2.7 %) right of the middle of the cloud; it is on the axis. Its small cut has
  a bolder stem (30 instead of 20 units): a thin stem exactly on the axis of an even-size canvas falls on the edge between two
  pixels at 16 and 32 px and shows as a faint grey line.
* **Bin.** The empty and full states share one position, so the can stays where it is when the papers appear (it moved 43
  units, 4.2 %, before). The price: each state's own box is off the middle, the empty bin 1.6 % low and the full bin 2.3 %
  high; their mean is 0.4 % high. The check holds them to that (no more than 3 % each, the mean within 1.25 %).
* **Settings tiles.** Centring put the Appearance symbol almost on top of Region and Language (silhouette IoU 0.60) and the
  Dock symbol almost on top of Remote Desktop (0.57). Appearance and Dock are in the plum group, the other two in the slate
  group, and those two groups are only 1.5 dE00 apart to a deuteranope, so the tile check (IoU 0.55, or tile dE00 of 10, or
  4.5 under every colour-blind simulation) failed. The Appearance and Dock symbols are drawn a little smaller (`AIM_BY_ID`:
  0.46 and 0.47 of the tile instead of 0.52); the threshold is unchanged.
* **Kit glyphs.** The 16 are Character Map, Utilities, Headset, Bluetooth disabled, Colour select, Open recent, Go jump, Tablet,
  Remove all, Mail replied, Mail unread, Microphone disabled, Modem, Sort ascending, Sort descending and Few clouds
  (`kit_shifts.json`: one whole unit at most on each axis).

## What did not improve, and what is on purpose

* **Centre of mass.** Box first means the mass can sit further from the middle than before. The largest mass offset of an
  app symbol went from 2.8 % to 3.2 %, of a Settings tile from 5.1 % to 7.9 % (the signal-bars Mobile tile: its mass is low
  and to the right by construction). The checks only use the mass as a guard against a lopsided drawing.
* **The bin pair** is off by design, as above.
* **Page emblems** are within 0.8 % vertically and within 0.8 % horizontally. Horizontally that is slightly more than the
  Nov 4 pages (0.2 %): the rule leaves an emblem up to 1 % off its origin for the pull of its mass, and the limit is 1.2 %.
* **Kit glyphs** are judged by the better of their box and their box-mass mean being within 0.75 unit of the middle (3.1 % of
  the canvas), looser than the 1.25 % of the other families, because a glyph on a 24 grid moves by whole units to stay
  crisp. Glyphs tagged `anchored` (the window-minimise bar rests on the bottom edge) are exempt, and the members of a level
  series must stay within half a unit of the full drawing's box so that they share one anchor. Only the 16 above needed a
  shift.
* **Text Editor has no app-specific one-colour file in the theme.** `text-editor-symbolic` is served by the kit's document
  glyph (the kit wins every `-symbolic` name); that is why the one-colour row above has 15 apps, not 16.

## Checks

`check_glyphs.py`, `check_apps.py`, `check_objects.py`, `check_tiles.py` and `check_theme.py` judge centring the same way.
The box is held to 1.25 % of the middle for the symbol on an app tile, for the Settings tiles and for the objects (full and
small cut), and to 1.5 % for the one-colour cuts and the small cuts of apps; the centre of mass only as a guard (5 % for app
symbols and objects, 6 % for the small cuts of apps and the one-colour cuts of objects, 9 % for tiles, 11 % for the
one-colour cuts of apps). Each check has a negative test that slides an icon
off the middle and must be caught. Last run on the theme in this folder: glyphs 375 / 46 checks / 28 of 28 negative tests,
apps 16 / 258 / 26 of 26, objects 64 / 69 / 46 of 46, tiles 55 / 20 / 14 of 14, theme 613 files / 40 / 31 of 31, none failing.

## Re-running it

After drawing or changing anything, in this order (each writes its table next to the tools):

```
python3 tools/icons/kit_centre.py          # kit glyphs      -> kit_shifts.json
python3 tools/icons/centre.py              # app symbols     -> glyph_shifts.json
python3 tools/icons/tiles.py --centre      # Settings tiles  -> tile_shifts.json
python3 tools/icons/centre_emblems.py      # emblems         -> emblem_shifts.json
python3 tools/icons/centre_objects.py      # objects         -> object_shifts.json
python3 tools/icons/build_theme.py         # rebuild assets/icons/Malva
python3 tools/icons/check_glyphs.py && python3 tools/icons/check_apps.py && python3 tools/icons/check_objects.py \
  && python3 tools/icons/check_tiles.py && python3 tools/icons/check_theme.py
```

The tools find the repository from their own location (`mi_geom.py` reads `crates/malva-tokens/src/balance.rs`, the logo
comes from `assets/brand`), so they must stay in `tools/icons` of the repository.

## Before / after sheets (`docs/icons/centring/`)

Upper cell = before, lower cell = after. Pink cross = the middle, blue box = the ink box, yellow dot = the centre of mass;
the number under each cell is the box centre's offset from the middle in % (x, y).

* `apps-on-tiles-before-after.png`: the six app icons that moved most.
* `settings-tiles-before-after.png`: the twelve Settings tiles that moved most.
* `objects-before-after.png`: the sixteen objects that moved most.
* `file-types-before-after.png`: the file-type symbols; the green line is the page's centre of mass.
* `apps-one-colour-before-after.png`: the one-colour cuts of the apps.
