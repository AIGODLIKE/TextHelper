"""Language-based font filtering (OS/2 unicode ranges + glyph probes)."""

from __future__ import annotations

import os
import struct

import bpy

from .font_glyph import font_has_full_coverage
from .font_search import catalog_item_passes_name  # noqa: F401 — re-export

LANGUAGE_FILTER_ITEMS = (
    ("ALL", "All", "All languages"),
    ("EN", "English", "English (Latin script)"),
    ("LATIN", "Latin", "Latin script"),
    ("ZH", "Chinese", "Chinese (Han characters)"),
    ("JA", "Japanese", "Japanese (kana and kanji)"),
    ("KO", "Korean", "Korean (Hangul)"),
    ("ARABIC", "Arabic", "Arabic script"),
    ("GREEK", "Greek", "Greek script"),
    ("HEBREW", "Hebrew", "Hebrew script"),
    ("THAI", "Thai", "Thai script"),
    ("RU", "Russian", "Russian (Cyrillic script)"),
)

_LANG_ALIASES = {
    "CYRILLIC": "RU",
}

_LANG_PROBES = {
    "EN": "AaBbZz",
    "LATIN": "AaBbZz",
    "ZH": "中文测试",
    "JA": "あア漢",
    "KO": "한글",
    "RU": "АБВГабв",
    "ARABIC": "ابجد",
    "GREEK": "ΑΒΓΔ",
    "HEBREW": "אבג",
    "THAI": "ไทย",
}

# OS/2 ulUnicodeRange bit indices used for fast rejection.
_OS2_MIN_BITS = {
    "EN": (0,),
    "LATIN": (0,),
    "ZH": (18,),
    "JA": (18,),
    "KO": (56,),
    "RU": (9,),
    "ARABIC": (13,),
    "GREEK": (7,),
    "HEBREW": (11,),
    "THAI": (16,),
}

_OS2_CACHE: dict[str, tuple[int, int, int, int] | None] = {}
_SUPPORT_CACHE: dict[tuple[str, str, int], bool] = {}


def invalidate_font_language_cache() -> None:
    _OS2_CACHE.clear()
    _SUPPORT_CACHE.clear()


def normalize_language_code(lang: str) -> str:
    if not lang:
        return "ALL"
    return _LANG_ALIASES.get(lang, lang)


def get_language_filter(wm) -> str:
    if wm is None:
        return "ALL"
    state = getattr(wm, "th_state", None)
    if state is None:
        return "ALL"
    return normalize_language_code(state.font_language or "ALL")


def get_language_label(code: str) -> str:
    for lang_code, label, _desc in LANGUAGE_FILTER_ITEMS:
        if lang_code == code:
            return label
    return code


def _norm_font_path(filepath: str) -> str:
    return os.path.normcase(bpy.path.abspath(filepath))


def _read_os2_unicode_ranges(filepath: str) -> tuple[int, int, int, int] | None:
    abs_path = _norm_font_path(filepath)
    if abs_path in _OS2_CACHE:
        return _OS2_CACHE[abs_path]

    result = None
    try:
        with open(abs_path, "rb") as handle:
            data = handle.read()
    except OSError:
        _OS2_CACHE[abs_path] = None
        return None

    if len(data) < 12:
        _OS2_CACHE[abs_path] = None
        return None

    num_tables = struct.unpack_from(">H", data, 4)[0]
    for index in range(num_tables):
        record = 12 + index * 16
        if record + 16 > len(data):
            break
        if data[record : record + 4] != b"OS/2":
            continue
        table_offset, table_length = struct.unpack_from(">II", data, record + 8)
        if table_length < 58 or table_offset + 58 > len(data):
            break
        result = struct.unpack_from(">IIII", data, table_offset + 42)
        break

    _OS2_CACHE[abs_path] = result
    return result


def _range_has_bit(ranges: tuple[int, int, int, int], bit_index: int) -> bool:
    word = bit_index // 32
    bit = bit_index % 32
    if word >= len(ranges):
        return False
    return bool(ranges[word] & (1 << bit))


def _os2_fast_confirms_support(filepath: str, lang: str) -> bool:
    """True only when OS/2 unicode-range bits fully confirm script support."""
    bits = _OS2_MIN_BITS.get(lang)
    if not bits:
        return False
    ranges = _read_os2_unicode_ranges(filepath)
    if ranges is None:
        return False
    return all(_range_has_bit(ranges, bit) for bit in bits)


def font_supports_language(filepath: str, lang: str, point_size: float = 24.0) -> bool:
    lang = normalize_language_code(lang)
    if not lang or lang == "ALL":
        return True
    if str(filepath or "").startswith("blend://"):
        return lang in {"EN", "LATIN"}
    if not filepath:
        return False

    cache_key = (_norm_font_path(filepath), lang, int(round(point_size * 2)))
    cached = _SUPPORT_CACHE.get(cache_key)
    if cached is not None:
        return cached

    if _os2_fast_confirms_support(filepath, lang):
        _SUPPORT_CACHE[cache_key] = True
        return True

    probe = _LANG_PROBES.get(lang)
    if not probe:
        result = True
    else:
        result = font_has_full_coverage(filepath, probe, point_size)

    _SUPPORT_CACHE[cache_key] = result
    return result


def catalog_item_passes_language(item, lang: str, point_size: float = 24.0) -> bool:
    return font_supports_language(getattr(item, "filepath", ""), lang, point_size)
