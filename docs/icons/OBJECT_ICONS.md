# Object icons: folders, storage, people and files

Drawings: `tools/icons/objects.py`, format: `tools/icons/objfmt.py`, shared pictograms: `tools/icons/emblems.py`.
Assets: `assets/object-icons/`. Sheets: `docs/icons/objects-*.png`.
Checks: `tools/icons/check_objects.py` (last report: `docs/icons/objects-check-report.txt`).

## What I assumed

You asked for "storage, folders, user id logos and etc". I read that as the icons for *things* in a file manager and a
settings app, as opposed to apps: standalone icons that are not set on an app tile, so they have their own format
(below) in the same brand colours. "User id logos" became the user, administrator, guest, group, avatar and ID-card
icons; "etc" became the trash, cloud storage and the common file types. If you meant something else by "user id
logos", the 12 icons in People are the part to change; no other icon's drawing depends on them.

## The set: 45 icons

Each entry is the Malva id, then in brackets the name an icon theme would install it under. 31 icons have such a name
(each one is a name that Adwaita or Humanity ships, and no two icons share one); the other 14 have no standard name and
install under their Malva id.

| Group | Icons |
|---|---|
| Folders and bins (14) | `folder` (folder), `folder-open` (folder-open), `folder-documents` (folder-documents), `folder-downloads` (folder-download), `folder-pictures` (folder-pictures), `folder-music` (folder-music), `folder-videos` (folder-videos), `folder-desktop` (user-desktop), `folder-home` (user-home), `folder-shared` (folder-publicshare), `folder-locked`, `folder-projects`, `trash-empty` (user-trash), `trash-full` (user-trash-full) |
| Storage (8) | `drive-internal` (drive-harddisk), `drive-external` (drive-harddisk-usb), `drive-network` (network-server), `drive-encrypted`, `usb-stick` (drive-removable-media-usb), `sd-card` (media-flash), `optical-disc` (media-optical), `cloud-storage` |
| People (12) | `user` (avatar-default), `user-admin`, `user-guest`, `users` (system-users), `id-card`, `avatar-2` to `avatar-8` |
| Files (11) | `file` (application-x-generic), `file-text` (text-x-generic), `file-document` (x-office-document), `file-pdf` (application-pdf), `file-spreadsheet` (x-office-spreadsheet), `file-presentation` (x-office-presentation), `file-image` (image-x-generic), `file-audio` (audio-x-generic), `file-video` (video-x-generic), `file-archive` (package-x-generic), `file-code` (text-x-script) |

## Files

    assets/object-icons/
      <id>.svg              full colour, 1024 canvas: use at 48 px and above
      small/<id>.svg        a heavier, simpler drawing for 16 to 32 px
      symbolic/<id>.svg     one colour (currentColor), square canvas fitted so the ink fills about 88% of it
      png/<id>-<size>.png   512, 256, 128, 64 from the full drawing; 48, 32, 24, 22, 16 from the small one
      manifest.json         id, name, group, template, emblem, icon-theme name, hue, file names

541 files, 2.95 MB; the largest SVG is 6.3 KB. Every icon has three drawings, not one drawing scaled: the small cut has
thicker lines and fewer details so that it survives 16 px, and the symbolic cut is the same silhouette with the pictures
cut out. SVGs contain no text, no filters and no scripts, and every SVG id starts with its icon's id, so any number of
them can sit in one page.

## The design

* **Four materials, all from the brand kit.** Orchid is for containers (folders, trash), plum for hardware and people
  (drives, USB stick, SD card, avatars, ID card), lilac for paper and pale objects (pages, the optical disc, the cloud),
  and leaf green is the one accent in an icon (the sheet in a folder, a drive's LED, the arrow on the cloud, the centre
  of a disc). Ink for engraved pictures is `#3A1232`.

  | Material | Hex values |
  |---|---|
  | orchid (containers) | `#D06BBA` `#A64C93` front; `#9A4585` `#7C3369` back |
  | plum (hardware, people) | `#A24E8C` (the app tiles' own gradient) to `#4E1D42`; body `#6F2B5F`; lid `#D99FCB` |
  | lilac (paper) | `#FBF3FA` to `#DEC3E0`; edge `#8C3274` (the mark's plum); dog-ear `#CDAACF` |
  | leaf (accent) | `#B4CF98` to `#8FB06D`; `#4F7A2F` on paper |

* **Corners are the Balance-dial curve** (a superellipse with exponent 4), not circular arcs, so these icons are the same
  family as the app tiles (which use exponent 5). Corner depth is 0.998 to 1.010 of what the curve predicts on 28
  icons; circular corners would measure 1.84.
* **One pictogram vocabulary** (20 pictures in `emblems.py`). The same drawing is engraved on a folder in dark ink,
  printed on a page in its app's tile hue (OKLCH hue angle: text 184, document and PDF 240, spreadsheet 150,
  presentation 28, image 64, audio 36, video 312, archive 94; source code is neutral grey), and cut out of the
  one-colour icon. A Music folder, a music file and the one-colour Music folder therefore show the same note.
* **The people are one disc template.** `user` is the plum default, the seven avatars use hues 8, 36, 64, 128, 184, 240
  and 290 from the same tile gradient family, `user-guest` is a desaturated grey-plum, `user-admin` adds a shield badge,
  `users` shows two figures. The nine plain person icons (`user`, `user-guest`, `avatar-2` to `avatar-8`) share one
  disc outline (IoU 0.9999).
* **Optical centring (revised: see `CENTRING.md`).** The first version moved 29 icons by up to 43 units (4.2% of the
  canvas) so that the box and the centre of mass, half each, sat at the middle; that left the cloud's arrow 2.7% right
  of the cloud and made the bin's can jump 4.2% when the papers appeared. Now the box of every drawing is put on the
  middle, less a pull towards the mass of at most 1% (`optical.py`); only the cloud, the external drive, the SD card
  and the USB stick still need a shift (`object_shifts.json`, measured from rendered pixels by `centre_objects.py`),
  and the bin's two states share one shift so the can stays where it is.
* **The small cut is its own drawing,** with heavier strokes and fewer details (the PDF's lines are 13 units thick in
  the full cut and 26 in the small one). At 16 px its picture carries at least 1.083 times the ink of the full cut's.

## Measured (rendered pixels, Chromium, 69 checks, `check_objects.py`)

| Check | Limit | Result |
|---|---|---|
| nothing past the safe zone (reach, share of the half canvas) | 0.90 | highest 0.883 (`drive-external`) |
| longest side not too small | 0.60 | lowest 0.633 (`usb-stick`) |
| bounding box and centre of mass centred (half each, % of the canvas) | 1.0% | highest 0.56% (`folder-projects`) |
| centre of mass from the middle | 3.0% | highest 2.44% (`cloud-storage`) |
| edge contrast against the dusk wallpaper | 1.6 | lowest 1.72 (`id-card`); the app tiles measure 1.3 to 1.7 |
| edge contrast against the dawn wallpaper | 1.6 | lowest 2.45 (`avatar-6`) |
| corner depth against the Balance-dial curve | 0.92 to 1.08 | 0.998 to 1.010 |
| avatar discs are circles (IoU, width/height) | 0.985 | 0.998 (`users`), 1.000 |
| picture contrast against its surface, median (WCAG 1.4.11 asks 3:1) | 3.0 | lowest 3.28 (`folder-pictures`), 34 icons |
| picture contrast, 10th percentile | 2.5 | lowest 3.11 (`folder-downloads`) |
| picture centred on its surface (horizontal / vertical) | 2.0% / 3.5% | highest 0.39% / 2.93% |
| picture margin to the surface edge | 3.0% | lowest 4.30% (`cloud-storage`) |
| small cut: ink pixels at 32 px / 16 px | 120 / 40 | lowest 181 / 50 (`usb-stick`) |
| small cut: picture pixels at 32 px / 16 px | 20 / 5 | lowest 23 / 6 (`cloud-storage`) |
| small cut's picture heavier than the full cut's at 16 px | 1.04 | lowest 1.083 (`users`) |
| symbolic: ink fills the canvas | 0.84 to 0.92 | 0.873 to 0.882 |
| symbolic: centred | 4.5 | highest 2.99 (`user-admin`) |
| symbolic: ink at 16 px | 40 px | lowest 77 (`drive-encrypted`) |
| symbolic keeps the full icon's outline (IoU of hulls) | 0.85 | lowest 0.907 (`avatar-3`) |
| one silhouette per template (IoU): 11 folders, 11 pages, 3 internal-style drives, 9 plain person discs | 0.995 | 0.9999 / 1.0000 / 0.9999 / 0.9999 |
| template members have one weight (max deviation) | 0.04 | 0.000 |
| every icon within 0.3x to 2.0x of the set's median weight | | 17.2% to 58.1% of the canvas, median 55.3% |
| every pair of icons told apart at 32 px (990 pairs) | outlines differ (IoU <= 0.55), or >= 2% of the shared area differs (dE00 >= 10; >= 4.5 for each colour-blind type) | closest pair `folder-pictures` / `folder-shared`, 4.9% |
| no two icons share an icon-theme name | | 31 names, none shared |
| SVG ids unique across the whole set | | 195 ids |
| the shipped SVGs, PNG sizes and manifest are what the generator makes now; two PNGs per icon match a fresh render | | all |

A check that cannot fail proves nothing, so 48 deliberately broken icons and files are run through the suite, each of
which a named check must reject, and all 48 are rejected: a picture 60 units off centre, a picture at 1.3:1 contrast, a
folder with a different tab, circular corners, an icon 1.15x too big or 0.5x too small, a body as dark as the dusk
wallpaper or as pale as the dawn one, a blue folder, a small cut that is only the full drawing, an elliptical avatar, a
symbolic canvas 40% too big, two pages that differ by one dot, a duplicated icon id, two icons under one icon-theme name,
a manifest record that no longer matches, a manifest missing an icon, a PNG of the wrong size and a PNG that is not a
render of its SVG, among others. The report lists all 48. Not every one of the 69 checks has a broken counterpart of its
own: `small:32px-ink-survives` and `shape:disc-aspect` do not, and the hygiene and template checks are tested on one
variant (the full cut, the folders) and run on all.

Defects the checks found in my own first drawings, all fixed: the PDF, presentation, image, archive and music pictures
were off-centre; the archive overflowed its page in the small cut; the encrypted drive's lock was too tall for the
slab; the code brackets touched the page border; the cloud's arrow was too low in the small cut; the PDF's 16 px picture
had no pixels (its 1 px lines fell between pixel rows); the guest figure had 2.74:1 contrast; and the seven avatar colours
were indistinguishable under colour-blind simulation (dE00 0.31, now 5.2). A last pass fixed the manifest: `file` and
`file-text` both claimed `text-x-generic`, `id-card` was mapped to the "new contact" action, and four icons used names that
neither Adwaita nor Humanity has. The suite now checks that names are unique.

The app-icon suite was re-run after all this work: 240 checks, 0 failed, 26 of 26 broken icons rejected.

## Judged, not measured

* **Style and cohesion.** I looked at the 128 px, 64 to 16 px and 16 px-zoom sheets on both wallpapers
  (`objects-on-dusk.png`, `objects-on-dawn.png`, `objects-sizes.png`, `objects-16px-zoom.png`) and judged that the set
  reads as one family. That is my opinion, and no number backs it up.
* **Do the pictures read as what they are?** A blind test (`tools/icons/blind_sheets.py`, record in
  `docs/icons/objects-blind-test.json`): a reviewer gets a numbered, shuffled sheet and a list of 39 names and says which
  icon each number is. Round 1 on the first drawings scored 43 of 45; the SD card, which had text lines on its label,
  was read as a document, so I redrew it with a plain label and gave the Group's back figure more opacity. Round 2 on
  the final drawings: **45 of 45 at 128 px, and 45 of 45 at 32 px** (shown at 2x), each on a fresh shuffle.
  What that is worth: the reviewer was a small model (Haiku), one pass per sheet, choosing from a closed list that
  it was handed, and the seven avatars count as one class (they differ only by colour). It is a fair sign that the
  metaphors read, not proof that people will find them obvious. The reviewer's own doubts in round 2 (it got these
  right but said so) were `drive-internal` against `drive-external`, `file-text` against `file-document`, `file-pdf`
  against `file-document`, `user-guest` and `user` against a coloured avatar, and `folder-documents`.

## Limits I know about

* **Avatars cannot be told apart by colour alone for everyone.** The best eight-colour set I could find (the plum
  default and the seven avatars) has a worst-case dE00 of 5.2 between two of its colours under colour-blind simulation,
  which is why that check's limit is 4.5 and not the 10 used for normal vision. The UI should show a name or initials
  next to an avatar.
* **16 px is tight for small details.** The least ink any picture has at 16 px is 6 pixels (the cloud's arrow; the
  limit is 5), the shield on `user-admin` is a few pixels, and the internal and external drives differ only by a
  small plug and their height. They pass the distinctness check, and they are what the reviewer was least sure of.
* **No pixel-grid hints for this family.** The app icons' PNGs are hinted to the pixel grid; these are plain renders, so
  the 16 and 22 px edges are antialiased across pixels.
* **The icon-theme names were checked against Adwaita and Humanity as installed in my sandbox** (an older Adwaita
  legacy set), not against a current GNOME or KDE release. Check them against the theme release you target.
* **Page pictures keep their app's hue**, so a PDF and a document are both blue and are told apart by the ribbon and
  the picture. The generic `file` is a blank page.
* **Page-picture centring** is measured against the page's centre of mass (the dog-ear takes a corner off the top, so
  that is 1.2% of the canvas below the middle of the page), not against the whole page; folder pictures against the middle of
  the front face. See `CENTRING.md` for the measured positions.
* **Not done:** the UI glyph pack (toolbar and menu icons); the deeper optimisation pass over the 16 app icons that you
  asked for earlier (only its audit was done); and a look by a person other than me.

## Rebuild

Needs Python 3 with numpy, Pillow, scipy, scikit-image and playwright with Chromium (the renderer).

    python3 tools/icons/centre_objects.py        # only after a geometry change: refreshes object_shifts.json
    python3 tools/icons/build_objects.py         # SVGs, PNGs and manifest; a re-run is byte-identical
    python3 tools/icons/check_objects.py --report docs/icons/objects-check-report.txt
    python3 tools/icons/objects_review.py        # the sheets in docs/icons
    python3 tools/icons/blind_sheets.py make DIR # new blind sheets; score a reviewer with: blind_sheets.py score KEY ANSWERS
