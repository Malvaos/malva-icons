# Malva icon theme (SVG only) - interim

`assets/icons/Malva/` is one freedesktop icon theme in which every icon is **one SVG file**. There are no PNGs: one file
serves every size, and `tools/icons/export_png.py` makes a PNG of any size when a program needs one. The theme is still
growing (more app icons and vector avatars are next); this is what exists today.

613 SVG files, 701,188 bytes (275 KB gzipped), plus `index.theme` and `manifest.json`.

| Folder | Files | What |
|---|---|---|
| `scalable/apps` | 16 | the app icons on their tiles (Files, Terminal, Text Editor, Music, Video, Photos, Settings, ...) |
| `scalable/categories` | 55 | Settings-pane and menu-category tiles |
| `scalable/places` | 18 | folders (with their pictures), home, desktop, the bin |
| `scalable/devices` | 8 | drives (internal, encrypted, USB, removable), flash media, optical disc, cloud storage, server |
| `scalable/mimetypes` | 26 | file types: a page with a symbol on it |
| `scalable/status` | 12 | user and avatar discs, the ID card, the user group |
| `symbolic/actions`, `status` | 157, 157 | one-colour glyphs for toolbars, menus and the panel (`currentColor`), 24 grid |
| `symbolic/devices`, `apps`, `mimetypes`, `places`, `categories`, `ui`, `emblems`, `legacy` | 44, 35, 26, 17, 17, 19, 5, 1 | the rest of the one-colour glyphs, and one-colour cuts of apps, objects and tiles |

* **Names.** Files carry the standard freedesktop names where one exists (`folder`, `user-trash-full`,
  `battery-level-50-symbolic` ...). 145 further standard names that mean the same picture
  (`inode-directory` is a folder, a CD, a DVD and a Blu-ray are one disc ...) are listed as `aliases` in `manifest.json` and
  created by the installer as relative symlinks (or copies with `--copy`). `manifest.json` also lists every icon with its
  family, source, label, file size and SHA-256.
* **Install.** `python3 tools/icons/install_theme.py` (for the current user: `~/.local/share/icons/Malva`), `sudo ... --system`
  (`/usr/share/icons/Malva`), `--dest DIR`, `--uninstall`. The theme inherits Adwaita and hicolor.
* **PNGs on demand.** `python3 tools/icons/export_png.py assets/icons/Malva/scalable/apps/files.svg --size 64 128 256 -o out/`;
  a one-colour glyph in the colour you want: `--color "#F3E6F2"`; the whole theme as a classic raster theme: `--theme
  assets/icons/Malva --size 16 24 32 48 64 --color "#2E2230" -o out/ --aliases`. It uses `rsvg-convert`, `resvg` or `inkscape`
  when they are on the PATH, otherwise headless Chromium; I only ran it with Chromium.
* **Rebuild.** `python3 tools/icons/build_theme.py` (needs `crates/malva-tokens` and `assets/brand` of the repository);
  `--small-cuts` also writes the optional heavier 16 to 32 px drawings (`small/`), `--out DIR` builds elsewhere.
* **Checks.** `check_glyphs.py`, `check_apps.py`, `check_objects.py`, `check_tiles.py`, `check_theme.py`, each with
  negative tests (a deliberately broken input must fail). Where things sit in each icon: `CENTRING.md`.

## What the files contain

No filters, scripts, text, images, `<style>` or external references in any of the 613 files. Full-colour icons use gradients
(135 files), masks (96) and clip paths (54); one-colour files draw in `currentColor`. The logo variants of the app-format
Malva icon are in `assets/icons/malva-app-format/` (made from your brand kit's mark; the kit itself is untouched).

## Known limits

* **GTK's symbolic recolouring.** GTK recolours a one-colour icon with a style rule that sets `fill` on every shape. Most of
  the one-colour glyphs are stroke drawings (a 2-unit stroke on the 24 grid), so under that rule their shape changes:
  measured by `check_theme.py`, 325 of 409 glyph files, 6 of 15 app cuts, 16 of 53 object cuts and the one tile cut. Programs
  that draw the SVG as it is (your own UI, Qt, browsers) are not affected. Converting the strokes to filled outlines is the next
  item on the list; until then, do not use the one-colour files of this theme as GNOME or GTK symbolic icons.
* **Text Editor** has no app-specific one-colour file: `text-editor-symbolic` is served by the kit's document glyph.
* **Crispness.** A 24 px glyph has 2 px strokes on whole pixels; at 16 px the strokes are 1.33 px wide, so 16 px is softer
  than 24 px. The optional small cuts draw the app and object icons heavier for 16 to 32 px.
* **Renderers.** Chromium is the only renderer I ran the theme through; other SVG renderers (librsvg, resvg, Qt) were not
  compared.
* **Seven numbered avatar objects** (`avatar-2` to `avatar-8`) have no one-colour cut.
* `assets/app-icons` and `assets/object-icons` from the Nov 4 delivery (PNGs at many sizes) are superseded by this theme and
  nothing in the repository's Rust code refers to them; they can be deleted. The old `build_apps.py` and `build_objects.py`
  only run with `--legacy`.
