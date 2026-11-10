"""Install the Malva icon theme for the current user or the whole system.

  python3 tools/icons/install_theme.py                  -> ~/.local/share/icons/Malva
  sudo python3 tools/icons/install_theme.py --system    -> /usr/share/icons/Malva
  python3 tools/icons/install_theme.py --dest DIR       -> DIR/Malva
  python3 tools/icons/install_theme.py --uninstall

The shipped tree holds each drawing once. This step adds the other standard names that mean the same picture (the
"aliases" in manifest.json: inode-directory is a folder, a CD, a DVD and a Blu-ray are one disc ...) as relative
symlinks next to the file they serve, or as copies with --copy where symlinks are not allowed. Then it refreshes the
icon cache if gtk-update-icon-cache is installed (the theme works without one).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import theme_model as TM


def is_malva(p: Path) -> bool:
    idx = p / "index.theme"
    return idx.exists() and f"Name={TM.THEME}" in idx.read_text()


def install(src: Path, dest: Path, copy: bool = False, cache: bool = True) -> dict:
    if not (src / "manifest.json").exists():
        raise SystemExit(f"{src} has no manifest.json: build it first (python3 tools/icons/build_theme.py)")
    man = json.loads((src / "manifest.json").read_text())
    target = dest / TM.THEME
    if target.exists():
        if not is_malva(target):
            raise SystemExit(f"{target} exists and is not a {TM.THEME} icon theme; refusing to replace it")
        shutil.rmtree(target)
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, target)
    mode = "copy" if copy else "symlink"
    try:
        n = TM.link_alias_files(man, target, mode)
    except OSError:
        n = TM.link_alias_files(man, target, "copy")
    cached = False
    exe = shutil.which("gtk-update-icon-cache")
    if cache and exe:
        cached = subprocess.run([exe, "-f", "-t", str(target)], capture_output=True).returncode == 0
    return {"installed": str(target), "files": len(man["icons"]), "aliases": n, "cache": cached}


def uninstall(dest: Path) -> bool:
    target = dest / TM.THEME
    if not target.exists():
        return False
    if not is_malva(target):
        raise SystemExit(f"{target} is not a {TM.THEME} icon theme; refusing to delete it")
    shutil.rmtree(target)
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", type=Path, default=TM.OUT, help="the built theme folder (default assets/icons/Malva)")
    where = ap.add_mutually_exclusive_group()
    where.add_argument("--dest", type=Path, help="icons directory to install into")
    where.add_argument("--system", action="store_true", help="install into /usr/share/icons")
    ap.add_argument("--copy", action="store_true", help="aliases as copies instead of symlinks")
    ap.add_argument("--no-cache", action="store_true", help="do not run gtk-update-icon-cache")
    ap.add_argument("--uninstall", action="store_true")
    a = ap.parse_args(argv)
    dest = a.dest or (Path("/usr/share/icons") if a.system else Path.home() / ".local/share/icons")
    if a.uninstall:
        print("removed" if uninstall(dest) else "nothing to remove", dest / TM.THEME)
        return
    r = install(a.source, dest, copy=a.copy, cache=not a.no_cache)
    print(f"installed {r['files']} files and {r['aliases']} alias names -> {r['installed']}"
          + ("; icon cache refreshed" if r["cache"] else "; no icon cache (gtk-update-icon-cache not found or failed: fine)"))
    print(f"select it: gsettings set org.gnome.desktop.interface icon-theme '{TM.THEME}'   (GNOME and Ubuntu)")


if __name__ == "__main__":
    main()
