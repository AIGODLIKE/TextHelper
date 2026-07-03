"""Detect vertical-column alignment risks (proportional fonts, halfwidth chars)."""

from __future__ import annotations

import os
import unicodedata

import blf
import bpy

from .font_blf import blf_load, blf_unload
from .text_orientation import COLUMN_FILL, is_vertical

_CJK_PROBE = ("一", "口", "汉")
_LATIN_PROBE = ("M", "i", "W")
_WIDTH_TOL_RATIO = 0.08
_METRICS_CACHE: dict[tuple[str, int], dict] = {}


def _east_asian_width(char: str) -> str:
    return unicodedata.east_asian_width(char)


def is_halfwidth_for_vertical(char: str) -> bool:
    """True for symbols likely narrower than CJK cells in vertical columns."""
    if not char or char in "\n\r\t":
        return False
    if char == COLUMN_FILL:
        return False
    if char.isspace():
        return False
    return _east_asian_width(char) in ("Na", "H", "N")


def find_halfwidth_chars(text: str) -> list[str]:
    """Unique halfwidth/narrow characters in typing order."""
    seen: set[str] = set()
    found: list[str] = []
    for char in text or "":
        if is_halfwidth_for_vertical(char) and char not in seen:
            seen.add(char)
            found.append(char)
    return found


def _glyph_width(font_id: int, char: str, point_size: float) -> float:
    blf.size(font_id, float(point_size))
    width, _height = blf.dimensions(font_id, char)
    return float(width)


def _width_tolerance(reference: float) -> float:
    return max(0.5, reference * _WIDTH_TOL_RATIO)


def analyze_font_metrics(filepath: str, point_size: float = 24.0) -> dict:
    """Measure whether a font behaves monospace enough for vertical columns."""
    abs_path = os.path.normcase(bpy.path.abspath(filepath))
    cache_key = (abs_path, int(round(point_size * 4)))
    if cache_key in _METRICS_CACHE:
        return _METRICS_CACHE[cache_key]

    font_id = blf_load(abs_path)
    if font_id == -1:
        result = {
            "loaded": False,
            "monospace_ok": False,
            "proportional_cjk": True,
            "fill_width_mismatch": True,
            "latin_proportional": True,
        }
        _METRICS_CACHE[cache_key] = result
        return result

    try:
        cjk_widths = [_glyph_width(font_id, char, point_size) for char in _CJK_PROBE]
        fill_width = _glyph_width(font_id, COLUMN_FILL, point_size)
        latin_widths = [_glyph_width(font_id, char, point_size) for char in _LATIN_PROBE]

        median_cjk = sorted(cjk_widths)[len(cjk_widths) // 2]
        tol = _width_tolerance(median_cjk)
        cjk_spread = max(cjk_widths) - min(cjk_widths)
        latin_spread = max(latin_widths) - min(latin_widths)

        proportional_cjk = cjk_spread > tol
        fill_mismatch = abs(fill_width - median_cjk) > tol
        latin_proportional = latin_spread > tol
        monospace_ok = not proportional_cjk and not fill_mismatch

        result = {
            "loaded": True,
            "monospace_ok": monospace_ok,
            "proportional_cjk": proportional_cjk,
            "fill_width_mismatch": fill_mismatch,
            "latin_proportional": latin_proportional,
            "cjk_width": median_cjk,
            "fill_width": fill_width,
        }
    finally:
        blf_unload(abs_path)

    _METRICS_CACHE[cache_key] = result
    return result


def _font_point_size(text_data) -> float:
    size = float(getattr(text_data, "size", 1.0) or 1.0)
    return max(12.0, round(size * 24.0, 2))


def analyze_font_for_vertical(text_data) -> dict | None:
    from .font_loader import disk_font_path

    font = getattr(text_data, "font", None)
    if font is None:
        return None
    path = disk_font_path(font)
    if not path:
        return None
    return analyze_font_metrics(path, _font_point_size(text_data))


def vertical_source_text(text_data) -> str:
    return getattr(text_data.text_helper, "th_vertical_source", "") or ""


def panel_source_text(text_data) -> str:
    """Text shown in the N-panel editor for the active orientation."""
    if is_vertical(text_data):
        return vertical_source_text(text_data)
    return getattr(text_data, "body", "") or ""


def build_vertical_align_report(text_data) -> dict:
    """Summary used by the N-panel to warn about layout risks."""
    vertical = is_vertical(text_data)
    font_report = analyze_font_for_vertical(text_data) if vertical else None
    halfwidth = find_halfwidth_chars(panel_source_text(text_data))

    font_issues: list[str] = []
    if vertical:
        if font_report is None:
            font_issues.append("unknown_font")
        elif not font_report.get("loaded", False):
            font_issues.append("font_load_failed")
        elif not font_report.get("monospace_ok", False):
            if font_report.get("proportional_cjk"):
                font_issues.append("proportional_cjk")
            if font_report.get("fill_width_mismatch"):
                font_issues.append("fill_width_mismatch")
            if font_report.get("latin_proportional"):
                font_issues.append("latin_proportional")

    has_issues = bool(font_issues) or bool(halfwidth)
    return {
        "font_report": font_report,
        "font_issues": font_issues,
        "halfwidth_chars": halfwidth,
        "has_issues": has_issues,
    }


def format_halfwidth_preview(chars: list[str], limit: int = 12) -> str:
    if not chars:
        return ""
    preview = chars[:limit]
    text = " ".join(preview)
    if len(chars) > limit:
        text += " …"
    return text


def should_convert_to_fullwidth(char: str) -> bool:
    if not char or char in "\n\r\t":
        return False
    if char == COLUMN_FILL:
        return False
    if char == " ":
        return True
    return is_halfwidth_for_vertical(char)


def char_to_fullwidth(char: str) -> str:
    if len(char) != 1:
        return char
    code = ord(char)
    if char == " ":
        return COLUMN_FILL
    if 0x21 <= code <= 0x7E:
        return chr(code + 0xFEE0)
    normalized = unicodedata.normalize("NFKC", char)
    if len(normalized) == 1 and normalized != char:
        return normalized
    return char


def convert_text_to_fullwidth(text: str) -> str:
    """Convert halfwidth/narrow characters to fullwidth forms for vertical columns."""
    return "".join(
        char
        if char in "\n\r"
        else char_to_fullwidth(char)
        if should_convert_to_fullwidth(char)
        else char
        for char in (text or "")
    )


def has_convertible_chars(text: str) -> bool:
    return any(should_convert_to_fullwidth(char) for char in (text or ""))


def count_convertible_chars(text: str) -> int:
    return sum(1 for char in (text or "") if should_convert_to_fullwidth(char))


def apply_fullwidth_fix(text_data) -> int:
    """Convert halfwidth chars in the active N-panel source. Returns chars fixed."""
    from .text_orientation import set_vertical_source

    raw = panel_source_text(text_data)
    count = count_convertible_chars(raw)
    if count <= 0:
        return 0

    converted = convert_text_to_fullwidth(raw)
    if is_vertical(text_data):
        set_vertical_source(text_data, converted)
    else:
        text_data.body = converted
        from .ui_textbox import sync_panel_textbox_from_canonical

        sync_panel_textbox_from_canonical(text_data, vertical=False, flip_active=True)
        text_data.update_tag()
    return count


def invalidate_vertical_align_cache():
    _METRICS_CACHE.clear()
