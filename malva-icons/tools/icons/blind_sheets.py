"""Blind identification test for the object icons: can someone who has only the pictures and a list of names tell which
icon is which?  This is a judgement check (a person or a model looks), not a measurement, so it sits beside the
measured suite (check_objects.py) and is not part of it.

    python3 tools/icons/blind_sheets.py make  OUTDIR [--seed N]     writes two numbered, shuffled sheets and their keys
    python3 tools/icons/blind_sheets.py score KEY.json ANSWERS.json  scores one reviewer's answers

make writes, into OUTDIR:
  A_128_dusk.png   the 128 px PNGs on the dusk wallpaper                    (key: keyA.json)
  B_32_dawn.png    the 32 px PNGs (small cut) on dawn, shown at 2x, nearest (key: keyB.json)
  names.txt        the 39 names to choose from: the seven plain avatars are one class, "avatar-N"
The two sheets use different shuffles, so a reviewer cannot carry an answer from one to the other.
Give the reviewer ONE sheet and names.txt. Never the key, and never this file's source or the repository.
Scoring is by class: avatar-2 .. avatar-8 differ only by colour, so any avatar-N answer for any avatar counts.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import objects as O
import objects_review as RV


def cls(name: str) -> str:
    return "avatar-N" if name.startswith("avatar-") else name


def sheet(order, wallpaper, size, cols, cell, zoom=1, pad=20):
    rows = -(-len(order) // cols)
    W, H = cols * cell + 2 * pad, rows * (cell + 26) + 2 * pad
    im = RV.wall(wallpaper, W, H, ox=900, oy=300)
    d = ImageDraw.Draw(im)
    ink = RV.INK_DUSK if wallpaper == "dusk" else RV.INK_DAWN
    for n, i in enumerate(order):
        r, c = divmod(n, cols)
        ic = RV.icon(i, size)
        if zoom != 1:
            ic = ic.resize((size * zoom, size * zoom), Image.NEAREST)
        im.alpha_composite(ic, (pad + c * cell + (cell - ic.width) // 2, pad + r * (cell + 26) + (cell - ic.height) // 2))
        d.text((pad + c * cell + cell // 2, pad + r * (cell + 26) + cell + 4), str(n + 1), font=RV._font(14), fill=ink, anchor="ma")
    return im.convert("RGB")


def make(out: Path, seed: int = 1):
    out.mkdir(parents=True, exist_ok=True)
    for tag, off in (("A", 0), ("B", 1)):
        order = list(O.ORDER)
        random.Random(seed * 2 + off).shuffle(order)
        (out / f"key{tag}.json").write_text(json.dumps({str(n + 1): i for n, i in enumerate(order)}, indent=1))
        if tag == "A":
            sheet(order, "dusk", 128, 8, 160).save(out / "A_128_dusk.png")
        else:
            sheet(order, "dawn", 32, 9, 96, zoom=2).save(out / "B_32_dawn.png")
    names = sorted(i for i in O.ORDER if not i.startswith("avatar-")) + ["avatar-N"]
    (out / "names.txt").write_text("\n".join(names) + "\n")
    print(f"wrote 2 sheets, 2 keys and {len(names)} names to {out}")


def score(key_path: Path, answers_path: Path):
    key, ans = json.loads(key_path.read_text()), json.loads(answers_path.read_text())
    wrong = [(n, key[n], ans.get(n, "")) for n in key if cls(ans.get(n, "")) != cls(key[n])]
    print(f"{len(key) - len(wrong)}/{len(key)} identified")
    for n, truth, said in wrong:
        print(f"  #{n}: it is {truth}, the reviewer said {said or '(nothing)'}")
    return len(wrong)


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == "make":
        make(Path(a[1]), int(a[a.index("--seed") + 1]) if "--seed" in a else 1)
    elif len(a) == 3 and a[0] == "score":
        sys.exit(1 if score(Path(a[1]), Path(a[2])) else 0)
    else:
        print(__doc__)
