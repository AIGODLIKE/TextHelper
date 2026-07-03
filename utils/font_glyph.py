"""Detect missing glyphs in font files via blf.NO_FALLBACK."""

import os

import blf
import bpy

_COVERAGE_CACHE = {}
_UNLOAD_HOOKS = []


def register_blf_unload_hook(callback):
    if callback not in _UNLOAD_HOOKS:
        _UNLOAD_HOOKS.append(callback)


def unregister_blf_unload_hook(callback):
    try:
        _UNLOAD_HOOKS.remove(callback)
    except ValueError:
        pass


def _notify_blf_unload(abs_path):
    for hook in list(_UNLOAD_HOOKS):
        try:
            hook(abs_path)
        except Exception:
            pass


def _has_glyph_api(font_id, char):
    has_glyph = getattr(blf, "has_glyph", None)
    if not callable(has_glyph):
        return None
    try:
        return bool(has_glyph(font_id, ord(char)))
    except Exception:
        return None


def _char_missing_glyph(font_id, char, point_size):
    if not char or char.isspace():
        return False

    api_result = _has_glyph_api(font_id, char)
    if api_result is not None:
        return not api_result

    blf.size(font_id, float(point_size))
    blf.enable(font_id, blf.NO_FALLBACK)
    w_nf, h_nf = blf.dimensions(font_id, char)
    if w_nf <= 0.01 or h_nf <= 0.01:
        blf.disable(font_id, blf.NO_FALLBACK)
        return True

    # Fonts often return a non-zero .notdef box for missing codepoints.
    # If enabling the fallback stack changes metrics, the glyph was substituted.
    blf.disable(font_id, blf.NO_FALLBACK)
    w_fb, h_fb = blf.dimensions(font_id, char)
    blf.enable(font_id, blf.NO_FALLBACK)

    dw = abs(w_fb - w_nf)
    dh = abs(h_fb - h_nf)
    tol = max(0.5, float(point_size) * 0.03)
    return dw > tol or dh > tol


def char_renders_without_fallback(font_id, char, point_size):
    """True when blf can draw something for char with NO_FALLBACK (incl. .notdef)."""
    if not char or char.isspace():
        return True
    if font_id == -1:
        return False
    blf.size(font_id, float(point_size))
    blf.enable(font_id, blf.NO_FALLBACK)
    try:
        w, h = blf.dimensions(font_id, char)
    finally:
        blf.disable(font_id, blf.NO_FALLBACK)
    return w > 0.01 and h > 0.01


def glyph_status_for_font_id(font_id, text, point_size):
    """Return list[bool] per character — True means glyph is present."""
    if font_id == -1 or not text:
        return [False] * len(text)

    result = []
    for char in text:
        if not char or char.isspace():
            result.append(True)
            continue
        result.append(not _char_missing_glyph(font_id, char, point_size))
    return result


def font_glyph_status(filepath, text, point_size=24, font_id=None):
    abs_path = os.path.normcase(bpy.path.abspath(filepath))
    cache_key = (abs_path, text, int(round(point_size * 2)), 2)
    if cache_key in _COVERAGE_CACHE:
        return _COVERAGE_CACHE[cache_key]

    loaded_here = False
    if font_id is None or font_id == -1:
        font_id = blf.load(abs_path)
        loaded_here = font_id != -1

    if font_id == -1:
        result = [False] * len(text)
    else:
        try:
            result = glyph_status_for_font_id(font_id, text, point_size)
        finally:
            if loaded_here:
                try:
                    blf.unload(abs_path)
                    _notify_blf_unload(abs_path)
                except Exception:
                    pass

    _COVERAGE_CACHE[cache_key] = result
    return result


def font_missing_count(filepath, text, point_size=24):
    status = font_glyph_status(filepath, text, point_size)
    return sum(1 for ok in status if not ok)


def font_has_full_coverage(filepath, text, point_size=24, font_id=None):
    if not text:
        return True
    if font_id is not None and font_id != -1:
        status = glyph_status_for_font_id(font_id, text, point_size)
    else:
        status = font_glyph_status(filepath, text, point_size)
    for i, char in enumerate(text):
        if char.isspace():
            continue
        if i >= len(status) or not status[i]:
            return False
    return True


def invalidate_glyph_cache():
    _COVERAGE_CACHE.clear()
