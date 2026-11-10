# Changelog

## 0.2.0 — 2026-11-09

### Added
* Unified pure-SVG freedesktop icon theme in `assets/icons/Malva/` (`index.theme`, `manifest.json`, and 613 SVG files across 16 directories).
* 55 Settings-pane and category tiles (`scalable/categories/`) across 7 OKLCH hue groups (`tools/icons/tiles.py`, `check_tiles.py`).
* 375 symbolic 24-grid toolbar, status, device, and UI glyphs (`tools/icons/glyphs_*.py`, `check_glyphs.py`) plus 34 mirrored `-rtl` variants.
* 145 standard freedesktop alias mappings (`tools/icons/theme_aliases.py`, `glyphs_alias.py`) materialised on install via `tools/icons/install_theme.py`.
* On-demand PNG rasteriser (`tools/icons/export_png.py`) supporting single icons, custom `currentColor` symbolic rendering, and full raster theme export.
* Whole-theme verification suite (`tools/icons/check_theme.py`) with 31 negative tests, GTK3 icon lookup verification, and `librsvg` vs. Chromium cross-engine checks.

### Changed
* Replaced midpoint box-mass centring (`W = 0.5`) with bounded optical centring (`tools/icons/optical.py`): bounding box centred on the canvas with at most a 1 % pull toward the opacity-weighted centre of mass (`docs/icons/CENTRING.md`).
* Re-aligned Text Editor pencil (`translate(24 28)`), Music note, Cloud storage arrow, and shared empty/full Trash bin anchor.
* Expanded object icons from 45 to 64 icons (25 file-type pages, 14 folders, 8 storage devices, 12 people/avatars, plus bins and cloud storage).

## 0.1.0 — 2026-11-04

### Added
* Initial 16 Malva OS system app icons (`tools/icons/apps.py`, `appfmt.py`, `check_apps.py`) and 6 `malva-app-format` brand mark variants.
* Initial 45 Malva OS object icons (`tools/icons/objects.py`, `objfmt.py`, `emblems.py`, `check_objects.py`) using Balance-dial superellipse (`n = 4.0`) corners and four brand materials (`orchid`, `plum`, `lilac`, `leaf`).
