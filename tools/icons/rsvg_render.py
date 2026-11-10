"""A second SVG renderer for cross-checks: librsvg (the library GNOME and GTK draw SVG icons with), called through ctypes.

Chromium draws every review sheet and every measured check. A drawing that only one engine draws correctly is not a
portable icon, so the theme checks also render with librsvg wherever it is installed (libcairo.so.2 and
librsvg-2.so.2; no Python bindings needed). Where it is not, the checks that need it report NOT RUN, never a pass.

  render(svg_text, size, css=None) -> HxWx4 uint8 array, straight alpha
  GTK_SYMBOLIC_CSS(rgb)            the style rule GTK injects when it recolours a symbolic icon (gtkicontheme.c):
                                   every rect, circle and path gets `fill: <colour> !important`
"""
from __future__ import annotations

import ctypes
import ctypes.util

import numpy as np

_LIBS = {}


class RsvgUnavailable(RuntimeError):
    pass


class _Rect(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double), ("width", ctypes.c_double), ("height", ctypes.c_double)]


def _load():
    if _LIBS:
        return _LIBS
    try:
        cairo = ctypes.CDLL(ctypes.util.find_library("cairo") or "libcairo.so.2")
        rsvg = ctypes.CDLL(ctypes.util.find_library("rsvg-2") or "librsvg-2.so.2")
        gobj = ctypes.CDLL(ctypes.util.find_library("gobject-2.0") or "libgobject-2.0.so.0")
    except OSError as e:                                     # noqa: PERF203
        raise RsvgUnavailable(str(e)) from e
    vp, c_int, c_dbl = ctypes.c_void_p, ctypes.c_int, ctypes.c_double
    cairo.cairo_image_surface_create.restype = vp
    cairo.cairo_image_surface_create.argtypes = [c_int, c_int, c_int]
    cairo.cairo_create.restype = vp
    cairo.cairo_create.argtypes = [vp]
    cairo.cairo_surface_flush.argtypes = [vp]
    cairo.cairo_image_surface_get_data.restype = ctypes.POINTER(ctypes.c_ubyte)
    cairo.cairo_image_surface_get_data.argtypes = [vp]
    cairo.cairo_image_surface_get_stride.restype = c_int
    cairo.cairo_image_surface_get_stride.argtypes = [vp]
    cairo.cairo_destroy.argtypes = [vp]
    cairo.cairo_surface_destroy.argtypes = [vp]
    rsvg.rsvg_handle_new_from_data.restype = vp
    rsvg.rsvg_handle_new_from_data.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.POINTER(vp)]
    rsvg.rsvg_handle_set_stylesheet.restype = c_int
    rsvg.rsvg_handle_set_stylesheet.argtypes = [vp, ctypes.c_char_p, ctypes.c_size_t, ctypes.POINTER(vp)]
    rsvg.rsvg_handle_render_document.restype = c_int
    rsvg.rsvg_handle_render_document.argtypes = [vp, vp, ctypes.POINTER(_Rect), ctypes.POINTER(vp)]
    gobj.g_object_unref.argtypes = [vp]
    _LIBS.update(cairo=cairo, rsvg=rsvg, gobj=gobj)
    return _LIBS


def available() -> bool:
    try:
        _load()
        return True
    except RsvgUnavailable:
        return False


def GTK_SYMBOLIC_CSS(rgb=(190, 190, 190)) -> str:
    return "rect,circle,path {\n  fill: rgb(%d,%d,%d) !important;\n}\n" % tuple(rgb)


def render(svg: str, size: int, css: str | None = None) -> np.ndarray:
    L = _load()
    data = svg.encode()
    err = ctypes.c_void_p()
    h = L["rsvg"].rsvg_handle_new_from_data(data, len(data), ctypes.byref(err))
    if not h:
        raise ValueError("librsvg could not parse the SVG")
    try:
        if css:
            c = css.encode()
            if not L["rsvg"].rsvg_handle_set_stylesheet(h, c, len(c), ctypes.byref(err)):
                raise ValueError("librsvg rejected the style sheet")
        surf = L["cairo"].cairo_image_surface_create(0, size, size)          # CAIRO_FORMAT_ARGB32
        cr = L["cairo"].cairo_create(surf)
        vp = _Rect(0.0, 0.0, float(size), float(size))
        ok = L["rsvg"].rsvg_handle_render_document(h, cr, ctypes.byref(vp), ctypes.byref(err))
        L["cairo"].cairo_surface_flush(surf)
        if not ok:
            raise ValueError("librsvg could not render the SVG")
        stride = L["cairo"].cairo_image_surface_get_stride(surf)
        buf = ctypes.string_at(L["cairo"].cairo_image_surface_get_data(surf), stride * size)
        L["cairo"].cairo_destroy(cr)
        L["cairo"].cairo_surface_destroy(surf)
    finally:
        L["gobj"].g_object_unref(h)
    px = np.frombuffer(buf, np.uint8).reshape(size, stride // 4, 4)[:, :size].astype(np.float64)   # B G R A, premultiplied
    a = px[..., 3:4]
    rgb = np.where(a > 0, px[..., 2::-1] * 255.0 / np.maximum(a, 1), 0)
    return np.concatenate([np.clip(rgb.round(), 0, 255), a], axis=-1).astype(np.uint8)
