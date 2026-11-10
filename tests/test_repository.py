"""Unit and integration test suite for the malva-icons repository."""
from __future__ import annotations

import configparser
import hashlib
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/icons"))

import appfmt as A
import apps
import export_png as EP
import glyphkit as K
import glyphs_all  # noqa: F401
import install_theme as IT
import mi_geom as G
import objects as O
import optical as OP
import rsvg_render as RR
import theme_aliases as TA
import theme_model as TM
import tiles as TL
from objfmt import object_svg


class TestMalvaIconsRepository(unittest.TestCase):
    """Comprehensive verification tests for theme structure, geometry, installer, and exporter."""

    def test_01_repository_layout_and_required_files(self):
        required = [
            "README.md",
            "CHANGELOG.md",
            "Makefile",
            ".gitignore",
            "tokens/tokens.toml",
            "crates/malva-tokens/src/balance.rs",
            "assets/icons/Malva/index.theme",
            "assets/icons/Malva/manifest.json",
            "assets/brand/logo/malva-app-icon.svg",
            "preview/apps-showcase.png",
            "preview/objects-showcase.png",
            "preview/settings-tiles.png",
            "preview/symbolic-glyphs.png",
            "packaging/PKGBUILD",
            "packaging/meson.build",
            "packaging/install.sh",
            ".github/workflows/ci.yml",
        ]
        for rel in required:
            self.assertTrue((ROOT / rel).exists(), f"Missing required repository file: {rel}")

    def test_02_balance_dial_tokens_and_corner_exponent(self):
        self.assertAlmostEqual(G.corner_exponent(), 4.0)
        self.assertAlmostEqual(G.N, 4.0)
        tok = G.tokens()
        self.assertIn("brand", tok)
        a, b, m, err = G.corner_fit(4.0)
        self.assertLess(err, 0.006)
        self.assertAlmostEqual(m, 1 - 2 ** (-1 / 4.0), places=10)

    def test_03_oklch_and_ciede2000_color_math(self):
        for hx in ("#A24E8C", "#4E1D42", "#D06BBA", "#FBF3FA", "#9DBB7E"):
            L, C, H = G.hex_to_oklch(hx)
            rt = G.oklch_to_hex(L, C, H)
            de = G.de2000(G.rgb_to_lab(G.hex_to_rgb(hx)), G.rgb_to_lab(G.hex_to_rgb(rt)))
            self.assertLess(de, 0.5)
        self.assertAlmostEqual(G.contrast((0, 0, 0), (255, 255, 255)), 21.0, places=5)

    def test_04_optical_centring_rule_bounds(self):
        # Zero offset when box and mass sit on 0
        self.assertAlmostEqual(OP.shift(0.0, 0.0, 1024.0), 0.0)
        # Pull toward mass is capped at 1% of the canvas (10.24 units on 1024 canvas)
        s = OP.shift(0.0, 200.0, 1024.0)
        self.assertAlmostEqual(abs(s), 10.24, places=5)

    def test_05_shipped_theme_manifest_and_sha256_integrity(self):
        theme_dir = ROOT / "assets/icons/Malva"
        man = json.loads((theme_dir / "manifest.json").read_text())
        self.assertEqual(man["theme"], "Malva")
        self.assertEqual(len(man["icons"]), 613)
        self.assertEqual(len(man["aliases"]), 145)
        for item in man["icons"]:
            p = theme_dir / item["file"]
            self.assertTrue(p.exists(), f"Missing SVG file: {item['file']}")
            raw = p.read_bytes()
            self.assertEqual(len(raw), item["bytes"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), item["sha256"])

    def test_06_index_theme_validity(self):
        theme_dir = ROOT / "assets/icons/Malva"
        cp = configparser.ConfigParser(interpolation=None, strict=False)
        cp.optionxform = str
        cp.read_string((theme_dir / "index.theme").read_text())
        self.assertEqual(cp["Icon Theme"]["Name"], "Malva")
        dirs = [d.strip() for d in cp["Icon Theme"]["Directories"].split(",") if d.strip()]
        self.assertEqual(len(dirs), 16)
        for d in dirs:
            self.assertIn(d, cp)
            self.assertEqual(cp[d]["Type"], "Scalable")
            self.assertTrue((theme_dir / d).is_dir())

    def test_07_svg_hygiene_and_unique_ids(self):
        theme_dir = ROOT / "assets/icons/Malva"
        man = json.loads((theme_dir / "manifest.json").read_text())
        forbidden = {"text", "image", "script", "style", "foreignObject", "use", "a", "filter"}
        all_ids = set()
        for item in man["icons"]:
            svg_text = (theme_dir / item["file"]).read_text()
            root = ET.fromstring(svg_text)
            tags = {el.tag.split("}")[-1] for el in root.iter()}
            self.assertFalse(tags & forbidden, f"Forbidden tag in {item['file']}: {tags & forbidden}")
            for el in root.iter():
                el_id = el.attrib.get("id")
                if el_id:
                    self.assertNotIn(el_id, all_ids, f"Duplicate ID {el_id} in {item['file']}")
                    all_ids.add(el_id)

    def test_08_install_and_uninstall_symlink_and_copy_modes(self):
        theme_dir = ROOT / "assets/icons/Malva"
        with tempfile.TemporaryDirectory(prefix="malva-install-test-") as td:
            dest = Path(td)
            # Symlink install
            res_sym = IT.install(theme_dir, dest, copy=False, cache=False)
            self.assertEqual(res_sym["files"], 613)
            self.assertEqual(res_sym["aliases"], 145)
            alias_path = dest / "Malva/scalable/places/inode-directory.svg"
            self.assertTrue(alias_path.is_symlink())
            self.assertTrue(alias_path.exists())
            self.assertTrue(IT.uninstall(dest))
            self.assertFalse((dest / "Malva").exists())

            # Copy install (for filesystems without symlink support)
            res_cp = IT.install(theme_dir, dest, copy=True, cache=False)
            self.assertEqual(res_cp["files"], 613)
            self.assertEqual(res_cp["aliases"], 145)
            self.assertTrue(alias_path.exists())
            self.assertFalse(alias_path.is_symlink())
            self.assertTrue(IT.uninstall(dest))

    def test_09_export_png_single_and_symbolic_recolour(self):
        theme_dir = ROOT / "assets/icons/Malva"
        with tempfile.TemporaryDirectory(prefix="malva-export-test-") as td:
            out = Path(td)
            files_svg = theme_dir / "scalable/apps/files.svg"
            sym_svg = theme_dir / "symbolic/status/battery-level-50-symbolic.svg"
            done = EP.export_files([files_svg], [32, 64], out, color="#000000", bg=None, backend="auto")
            self.assertEqual(len(done), 2)
            for p in done:
                self.assertTrue(p.exists())
                self.assertGreater(p.stat().st_size, 100)
            done_sym = EP.export_files([sym_svg], [24], out, color="#F3E6F2", bg=None, backend="auto")
            self.assertEqual(len(done_sym), 1)
            self.assertTrue(done_sym[0].exists())

    def test_10_brand_app_format_variants_present(self):
        fmt_dir = ROOT / "assets/icons/malva-app-format"
        expected = [
            "malva-app-icon-plum.svg",
            "malva-app-icon-lilac.svg",
            "malva-app-icon-dusk.svg",
            "malva-app-icon-leaf.svg",
            "malva-app-icon-mono.svg",
            "malva-app-icon-small.svg",
        ]
        for name in expected:
            p = fmt_dir / name
            self.assertTrue(p.exists(), f"Missing app-format variant: {name}")
            ET.fromstring(p.read_text())


if __name__ == "__main__":
    unittest.main()
