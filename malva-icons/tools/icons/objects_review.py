"""Review sheets for the object icons, built from the files that ship (assets/object-icons), so what you look at is
what you get. Output in docs/icons/:

  objects-on-dusk.png, objects-on-dawn.png   all 45 icons at 128 px on the two brand wallpapers
  objects-sizes.png                          every shipped size (64, 48, 32, 24, 22, 16) on both wallpapers
  objects-16px-zoom.png                      the 16 px files magnified 8x (nearest), with the real-size chip beside them
  objects-symbolic-dark.png / -light.png     the one-colour set at 72 px and 16 px
  objects-system.png                         the materials, and the emblem vocabulary shared by folders, pages and the symbolic set
  objects-in-context.png                     a file-manager mock-up: sidebar, grid, accounts (drawn with PIL, not a real UI)

Run: python3 tools/icons/build_objects.py && python3 tools/icons/objects_review.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import mi_geom as g
import objects as O
from mi_render import Renderer, _font

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets/object-icons"
PNG = ASSETS / "png"
DOCS = ROOT / "docs/icons"
GROUP_TITLE = {"folders": "Folders and bins", "storage": "Storage", "people": "People", "files": "Files"}
INK_DUSK, INK_DAWN = (240, 226, 238), (58, 24, 52)


def wall(name, w, h, ox=300, oy=40):
    """A w x h crop of the brand wallpaper at 1:1 (scaled up only when the sheet is taller or wider than the wallpaper)."""
    im = Image.open(ROOT / "assets/brand" / f"malva-{name}-2560x1440.jpg").convert("RGBA")
    k = max(1.0, (h + 2) / im.height, (w + 2) / im.width)
    if k > 1.0:
        im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    ox, oy = min(ox, im.width - w), min(oy, im.height - h)
    return im.crop((ox, oy, ox + w, oy + h))


def icon(i, s):
    """The shipped PNG of this size; for a size that is not shipped (the mock-up uses 96), the 128 px file scaled down."""
    p = PNG / f"{i}-{s}.png"
    if p.exists():
        return Image.open(p).convert("RGBA")
    return Image.open(PNG / f"{i}-128.png").convert("RGBA").resize((s, s), Image.LANCZOS)


def label(d, xy, text, fill, size=12, anchor="la"):
    d.text(xy, text, font=_font(size), fill=fill, anchor=anchor)


# ----------------------------------------------------------------------------------------------- all icons, one wallpaper
def grid(name):
    cols, cw, ch, s = 8, 156, 176, 128
    blocks = [(gname, ids) for gname, ids in O.GROUPS.items()]
    rows = [-(-len(ids) // cols) for _, ids in blocks]
    W = cols * cw + 60
    H = 70 + sum(34 + r * ch for r in rows) + 24
    im = wall(name, W, H)
    d = ImageDraw.Draw(im)
    ink = INK_DUSK if name == "dusk" else INK_DAWN
    label(d, (30, 20), f"Malva object icons on the {name} wallpaper: 45 icons, 128 px PNG as shipped", ink, 18)
    y = 62
    for (gname, ids), r in zip(blocks, rows):
        label(d, (30, y + 6), f"{GROUP_TITLE[gname]}  ({len(ids)})", ink, 15)
        y += 34
        for k, i in enumerate(ids):
            rr, cc = divmod(k, cols)
            x, yy = 30 + cc * cw + (cw - s) // 2, y + rr * ch
            im.alpha_composite(icon(i, s), (x, yy))
            label(d, (30 + cc * cw + cw // 2, yy + s + 8), i, ink, 12, "ma")
        y += r * ch
    return im.convert("RGB")


# ----------------------------------------------------------------------------------------------- every size
SIZES = (64, 48, 32, 24, 22, 16)


def sizes_panel(name, cols=5):
    cw, ch = 282, 96
    ids = O.ORDER
    rows = -(-len(ids) // cols)
    W, H = cols * cw + 40, rows * ch + 56
    im = wall(name, W, H, 500, 120)
    d = ImageDraw.Draw(im)
    ink = INK_DUSK if name == "dusk" else INK_DAWN
    label(d, (20, 16), f"{name}: 64 / 48 / 32 / 24 / 22 / 16 px, PNG as shipped (64 from the full drawing, the rest from the small one)", ink, 13)
    for k, i in enumerate(ids):
        r, c = divmod(k, cols)
        x, y = 20 + c * cw, 44 + r * ch
        label(d, (x, y), i, ink, 11)
        xx = x
        for s in SIZES:
            im.alpha_composite(icon(i, s), (xx, y + 18 + (64 - s)))
            xx += s + 7
    return im


def sizes():
    a, b = sizes_panel("dusk"), sizes_panel("dawn")
    out = Image.new("RGB", (a.width, a.height + b.height))
    out.paste(a.convert("RGB"), (0, 0))
    out.paste(b.convert("RGB"), (0, a.height))
    return out


# ----------------------------------------------------------------------------------------------- 16 px magnified
def zoom16(K=8, per=9):
    cw = 16 * K + 30
    ch = 16 * K + 50
    rows = -(-len(O.ORDER) // per)
    panels = []
    for name in ("dusk", "dawn"):
        W, H = per * cw + 20, rows * ch + 40
        im = wall(name, W, H, 400, 100)
        d = ImageDraw.Draw(im)
        ink = INK_DUSK if name == "dusk" else INK_DAWN
        label(d, (14, 10), f"{name}: the 16 px files at {K}x (nearest neighbour), and at real size beside them", ink, 13)
        for k, i in enumerate(O.ORDER):
            r, c = divmod(k, per)
            x, y = 14 + c * cw, 34 + r * ch
            big = icon(i, 16).resize((16 * K, 16 * K), Image.NEAREST)
            im.alpha_composite(big, (x, y))
            im.alpha_composite(icon(i, 16), (x + 16 * K + 6, y))
            label(d, (x, y + 16 * K + 4), i, ink, 11)
        panels.append(im.convert("RGB"))
    out = Image.new("RGB", (panels[0].width, panels[0].height * 2))
    out.paste(panels[0], (0, 0))
    out.paste(panels[1], (0, panels[0].height))
    return out


# ----------------------------------------------------------------------------------------------- symbolic
def symbolic(R, dark: bool):
    svgs = [(ASSETS / "symbolic" / f"{i}.svg").read_text() for i in O.ORDER]
    col = "#F3E6F2" if dark else "#5A2350"
    a72, a16 = R.render(svgs, 72, color=col), R.render(svgs, 16, color=col)
    per, cw, ch = 9, 118, 112
    rows = -(-len(O.ORDER) // per)
    W, H = per * cw + 24, rows * ch + 50
    bg = (36, 24, 34) if dark else (246, 236, 245)
    im = Image.new("RGBA", (W, H), bg + (255,))
    d = ImageDraw.Draw(im)
    ink = INK_DUSK if dark else INK_DAWN
    label(d, (14, 12), "symbolic (currentColor) set, 72 px and 16 px: one colour, fitted to a square canvas, ink fills 88% of it", ink, 13)
    for k, (i, big, small) in enumerate(zip(O.ORDER, a72, a16)):
        r, c = divmod(k, per)
        x, y = 12 + c * cw, 40 + r * ch
        im.alpha_composite(Image.fromarray(big), (x, y))
        im.alpha_composite(Image.fromarray(small), (x + 80, y + 28))
        label(d, (x, y + 76), i, ink, 11)
    return im.convert("RGB")


# ----------------------------------------------------------------------------------------------- system sheet
SWATCHES = [("orchid  (containers)", [("#D06BBA", "front, lit"), ("#A64C93", "front, shade"), ("#9A4585", "back, lit"), ("#7C3369", "back, shade")]),
            ("plum  (hardware, people)", [("#A24E8C", "the app tiles' own gradient"), ("#6F2B5F", "body, shade"), ("#4E1D42", "disc, shade"), ("#D99FCB", "lid, lit")]),
            ("lilac  (paper)", [("#FBF3FA", "page, lit"), ("#DEC3E0", "page, shade"), ("#CDAACF", "dog-ear"), ("#8C3274", "page edge (the mark's plum)")]),
            ("leaf  (one accent per icon)", [("#B4CF98", "sheet, lit"), ("#8FB06D", "sheet, shade"), ("#4F7A2F", "on lilac"), ("#3A1232", "engraved ink")])]
VOCAB = [("pictures", "folder-pictures", "file-image"), ("music", "folder-music", "file-audio"), ("videos", "folder-videos", "file-video"),
         ("code", "folder-projects", "file-code"), ("documents", "folder-documents", "file-document"), ("locked (also on the encrypted drive)", "folder-locked", "drive-encrypted")]


def system(R):
    W, H = 1400, 980
    im = Image.new("RGBA", (W, H), (30, 20, 29, 255))
    d = ImageDraw.Draw(im)
    hi, dim = (240, 226, 238), (190, 160, 185)
    label(d, (30, 20), "the object-icon system", hi, 20)
    # materials
    label(d, (30, 64), "four materials, all from the brand kit", dim, 14)
    for r, (title, sw) in enumerate(SWATCHES):
        y = 94 + r * 78
        label(d, (30, y), title, hi, 13)
        for k, (hx, role) in enumerate(sw):
            x = 30 + k * 206
            d.rounded_rectangle([x, y + 22, x + 52, y + 62], 8, fill=hx)
            label(d, (x + 60, y + 24), hx, hi, 12)
            label(d, (x + 60, y + 42), role, dim, 10)
    # one vocabulary, three places
    label(d, (30, 424), "one emblem vocabulary: the same drawing is engraved on a folder, printed on a page in its app's hue, and cut out of the one-colour icon", dim, 14)
    svgs = [(ASSETS / "symbolic" / f"{b}.svg").read_text() for _, b, _ in VOCAB]
    sym = R.render(svgs, 96, color="#F3E6F2")
    for r, ((name, a, b), s) in enumerate(zip(VOCAB, sym)):
        x, y = 30 + (r % 3) * 460, 454 + (r // 3) * 250
        label(d, (x, y), name, hi, 13)
        im.alpha_composite(icon(a, 128), (x, y + 20))
        im.alpha_composite(icon(b, 128), (x + 150, y + 20))
        im.alpha_composite(Image.fromarray(s), (x + 300, y + 36))
        label(d, (x, y + 154), a, dim, 10)
        label(d, (x + 150, y + 154), b, dim, 10)
        label(d, (x + 300, y + 154), "symbolic", dim, 10)
    label(d, (30, 958), "rules: Balance-dial corners (exponent 4)  |  no filters, no text  |  three drawings per icon: full, small (16-32 px), symbolic  |  ids prefixed per icon", dim, 12)
    return im.convert("RGB")


# ----------------------------------------------------------------------------------------------- in context
def context():
    W, H = 1480, 900
    im = wall("dusk", W, H, 200, 60)
    d = ImageDraw.Draw(im)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    od.rounded_rectangle([60, 50, W - 60, H - 50], 26, fill=(28, 17, 27, 232))
    od.rounded_rectangle([60, 50, 330, H - 50], 26, fill=(40, 24, 38, 240))
    od.rectangle([300, 50, 330, H - 50], fill=(40, 24, 38, 240))
    im.alpha_composite(ov)
    d = ImageDraw.Draw(im)
    hi, dim, sel = (240, 226, 238), (178, 148, 172), (96, 52, 86, 255)
    # sidebar
    y = 78
    for title, rows in (("Places", [("folder-home", "Home"), ("folder-desktop", "Desktop"), ("folder-documents", "Documents"), ("folder-downloads", "Downloads"),
                                    ("folder-music", "Music"), ("folder-pictures", "Pictures"), ("folder-videos", "Videos"), ("trash-full", "Trash")]),
                        ("Devices", [("drive-internal", "System"), ("drive-external", "Backup"), ("drive-encrypted", "Vault"), ("drive-network", "NAS"),
                                     ("usb-stick", "USB stick"), ("sd-card", "Camera"), ("optical-disc", "Install disc"), ("cloud-storage", "Cloud")])):
        label(d, (88, y), title.upper(), dim, 11)
        y += 22
        for k, (i, t) in enumerate(rows):
            if title == "Places" and t == "Documents":
                d.rounded_rectangle([76, y - 3, 316, y + 27], 8, fill=sel)
            im.alpha_composite(icon(i, 22), (88, y))
            label(d, (122, y + 4), t, hi, 14)
            y += 31
        y += 14
    # header: path, account
    label(d, (360, 76), "Home  /  Documents", hi, 18)
    im.alpha_composite(icon("user", 32), (W - 100 - 34, 68))
    # grid
    items = [("folder-projects", "Projects"), ("folder-shared", "Shared"), ("folder-locked", "Private"), ("folder-open", "Open"), ("folder", "New folder"),
             ("file-pdf", "report.pdf"), ("file-spreadsheet", "budget.xlsx"), ("file-presentation", "pitch.pptx"), ("file-document", "letter.docx"), ("file-text", "notes.txt"),
             ("file-image", "photo.png"), ("file-audio", "song.flac"), ("file-video", "clip.mp4"), ("file-archive", "backup.zip"), ("file-code", "main.rs")]
    per, cw, ch = 5, 168, 150
    for k, (i, t) in enumerate(items):
        r, c = divmod(k, per)
        x, yy = 366 + c * cw, 130 + r * ch
        if t == "photo.png":
            d.rounded_rectangle([x - 10, yy - 6, x + 106, yy + 124], 12, fill=sel)
        im.alpha_composite(icon(i, 96), (x, yy))
        label(d, (x + 48, yy + 100), t, hi, 12, "ma")
    # sizes strip
    label(d, (366, 604), "the same icons at the sizes a list view and a toolbar use", dim, 12)
    xx = 366
    for s in (48, 32, 24, 22, 16):
        for i in ("folder-music", "file-pdf", "drive-internal", "users"):
            im.alpha_composite(icon(i, s), (xx, 626 + (48 - s)))
            xx += s + 8
        xx += 22
    # accounts
    label(d, (366, 706), "accounts", dim, 12)
    xx = 366
    for i in ("user", "user-admin", "user-guest", "users", "avatar-2", "avatar-3", "avatar-4", "avatar-5", "avatar-6", "avatar-7", "avatar-8"):
        im.alpha_composite(icon(i, 64), (xx, 728))
        xx += 74
    im.alpha_composite(icon("id-card", 96), (xx + 20, 722))
    label(d, (W - 80, H - 76), "mock-up drawn with the shipped PNGs; the window itself is not an icon", dim, 11, "ra")
    return im.convert("RGB")


def main():
    DOCS.mkdir(parents=True, exist_ok=True)
    for n in ("dusk", "dawn"):
        grid(n).save(DOCS / f"objects-on-{n}.png", optimize=True)
    sizes().save(DOCS / "objects-sizes.png", optimize=True)
    zoom16().save(DOCS / "objects-16px-zoom.png", optimize=True)
    with Renderer() as R:
        symbolic(R, True).save(DOCS / "objects-symbolic-dark.png", optimize=True)
        symbolic(R, False).save(DOCS / "objects-symbolic-light.png", optimize=True)
        system(R).save(DOCS / "objects-system.png", optimize=True)
    context().save(DOCS / "objects-in-context.png", optimize=True)
    for p in sorted(DOCS.glob("objects-*.png")):
        print(p.name, Image.open(p).size)


if __name__ == "__main__":
    main()
