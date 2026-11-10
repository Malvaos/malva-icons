"""Render SVG strings to pixels with headless Chromium (the same engine users see in a browser)
and compose labelled contact sheets. Rendering is batched: one screenshot per grid.

Supports Playwright (sync_playwright), Selenium WebDriver (headless Chromium), and librsvg fallback.
"""
from __future__ import annotations

import base64
import io
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


def _sized(svg: str, w: int, h: int) -> str:
    return re.sub(r"<svg ", f'<svg width="{w}" height="{h}" ', svg, count=1)


class Renderer:
    def __enter__(self):
        self._mode = None
        if sync_playwright is not None:
            try:
                self.pw = sync_playwright().start()
                self.browser = self.pw.chromium.launch()
                self.page = self.browser.new_page()
                self._mode = "playwright"
                return self
            except Exception:
                pass
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            opts = Options()
            for arg in ("--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
                        "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1"):
                opts.add_argument(arg)
            self.driver = webdriver.Chrome(options=opts)
            self.driver.get("about:blank")
            self._mode = "selenium"
            return self
        except Exception:
            self._mode = "rsvg"
            return self

    def __exit__(self, *a):
        if self._mode == "playwright":
            self.browser.close()
            self.pw.stop()
        elif self._mode == "selenium":
            self.driver.quit()

    def render(self, svgs, size, bg=None, color="#000000", cols=None):
        """size: int or (w, h). Returns a list of HxWx4 uint8 arrays (straight alpha)."""
        w, h = (size, size) if isinstance(size, int) else size
        n = len(svgs)
        if not n:
            return []
        if self._mode == "rsvg":
            import rsvg_render
            import mi_geom as g
            out = []
            for s in svgs:
                im = rsvg_render.render(s.replace("currentColor", color), w)
                if bg is not None:
                    rgb = over(im, g.hex_to_rgb(bg))
                    im = im.copy()
                    im[..., :3] = rgb.round().astype(np.uint8)
                    im[..., 3] = 255
                out.append(im)
            return out

        cols = cols or max(1, min(n, 4096 // w))
        rows = -(-n // cols)
        cells = "".join(
            f'<div style="width:{w}px;height:{h}px;overflow:hidden;color:{color}">{_sized(s, w, h)}</div>'
            for s in svgs)
        bgc = bg or "transparent"
        html = (f"<html><body style='margin:0;background:{bgc}'>"
                f"<div style='display:grid;grid-template-columns:repeat({cols},{w}px);"
                f"background:{bgc}'>{cells}</div></body></html>")
        W, H = cols * w, max(rows * h, 1)
        if self._mode == "playwright":
            self.page.set_viewport_size({"width": W, "height": H})
            self.page.set_content(html)
            png = self.page.screenshot(full_page=False, omit_background=(bg is None),
                                       clip={"x": 0, "y": 0, "width": W, "height": H})
        else:
            self.driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride",
                                        {"width": W, "height": H, "deviceScaleFactor": 1, "mobile": False})
            self.driver.execute_cdp_cmd("Emulation.setDefaultBackgroundColorOverride",
                                        {"color": {"r": 0, "g": 0, "b": 0, "a": 0 if bg is None else 1}})
            self.driver.execute_script("document.open(); document.write(arguments[0]); document.close();", html)
            res = self.driver.execute_cdp_cmd("Page.captureScreenshot", {
                "format": "png",
                "clip": {"x": 0, "y": 0, "width": W, "height": H, "scale": 1},
                "captureBeyondViewport": True,
            })
            png = base64.b64decode(res["data"])
        im = np.array(Image.open(io.BytesIO(png)).convert("RGBA"))
        out = []
        for i in range(n):
            r, c = divmod(i, cols)
            out.append(im[r * h:(r + 1) * h, c * w:(c + 1) * w].copy())
        return out


def over(rgba: np.ndarray, bg_rgb) -> np.ndarray:
    """Composite straight-alpha RGBA over an opaque colour; returns HxWx3 float."""
    a = rgba[..., 3:4].astype(float) / 255
    return rgba[..., :3].astype(float) * a + np.array(bg_rgb, dtype=float) * (1 - a)


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def sheet(items, cols, cell, bg=(24, 20, 23), fg=(235, 230, 233), pad=10, label_h=16,
          title=None, tile_bg=None, font_size=11):
    """items: [(label, HxWx4 array)]. Cells are `cell` px square (array centred)."""
    f = _font(font_size)
    rows = -(-len(items) // cols)
    top = 26 if title else 0
    W = cols * (cell + pad) + pad
    H = top + rows * (cell + label_h + pad) + pad
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    if title:
        d.text((pad, 6), title, fill=fg, font=_font(14))
    for i, (label, arr) in enumerate(items):
        r, c = divmod(i, cols)
        x, y = pad + c * (cell + pad), top + pad + r * (cell + label_h + pad)
        if tile_bg is not None:
            d.rectangle([x, y + label_h, x + cell - 1, y + label_h + cell - 1], fill=tile_bg)
        d.text((x, y), label, fill=fg, font=f)
        base = np.array(im.crop((x, y + label_h, x + cell, y + label_h + cell)))
        h, w = arr.shape[:2]
        ox, oy = (cell - w) // 2, (cell - h) // 2
        a = arr[..., 3:4].astype(float) / 255
        region = base[oy:oy + h, ox:ox + w].astype(float)
        base[oy:oy + h, ox:ox + w] = (arr[..., :3] * a + region * (1 - a)).round().astype(np.uint8)
        im.paste(Image.fromarray(base), (x, y + label_h))
    return im
