"""Multi-field font catalog search with CJK pinyin and kana helpers.

Bundled ``cjk_pinyin_min.json`` is a minified hanzi→pinyin table (generated from
the pypinyin library, MIT) used only for font name search suggestions. It ships
with the add-on and is not fetched at runtime.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path

import bpy

from .font_family import family_key_for_filepath, family_key_from_stem, parse_font_stem
from .font_display import display_name_for_filepath
from .font_name_meta import read_font_search_name_strings
from .font_search_aliases import alias_tokens_for_query, alias_tokens_for_text

_SEARCH_CACHE: dict[str, str] = {}
_PINYIN_DICT: dict[str, str] | None = None
_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|[_\-./]+")
_QUERY_SPLIT = re.compile(r"[\s,;|]+")


def invalidate_font_search_cache() -> None:
    _SEARCH_CACHE.clear()


def _load_pinyin_dict() -> dict[str, str]:
    global _PINYIN_DICT
    if _PINYIN_DICT is not None:
        return _PINYIN_DICT
    path = Path(__file__).resolve().parent / "cjk_pinyin_min.json"
    if not path.is_file():
        _PINYIN_DICT = {}
        return _PINYIN_DICT
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    _PINYIN_DICT = payload if isinstance(payload, dict) else {}
    return _PINYIN_DICT


def _has_cjk(text: str) -> bool:
    for char in text:
        code = ord(char)
        if (
            0x3040 <= code <= 0x30FF
            or 0x3400 <= code <= 0x4DBF
            or 0x4E00 <= code <= 0x9FFF
            or 0xAC00 <= code <= 0xD7AF
        ):
            return True
    return False


def _kana_fold(text: str) -> str:
    chars = []
    for char in text:
        code = ord(char)
        if 0x3041 <= code <= 0x3096:
            chars.append(chr(code + 0x60))
        elif 0x30A1 <= code <= 0x30F6:
            chars.append(chr(code - 0x60))
        else:
            chars.append(char)
    return "".join(chars)


def _split_tokens(text: str) -> list[str]:
    if not text:
        return []
    parts = []
    for piece in _CAMEL_BOUNDARY.split(text):
        piece = piece.strip()
        if piece:
            parts.append(piece)
    return parts


def _pinyin_variants(text: str) -> tuple[str, str]:
    table = _load_pinyin_dict()
    if not table or not text:
        return "", ""
    syllables = []
    for char in text:
        if char in table:
            syllables.append(table[char])
        elif "\u4e00" <= char <= "\u9fff":
            return "", ""
    if not syllables:
        return "", ""
    full = "".join(syllables)
    initials = "".join(word[0] for word in syllables if word)
    return full, initials


def _cache_key(filepath: str) -> str:
    if str(filepath or "").startswith("blend://"):
        return os.path.normcase(filepath or "")
    abs_path = bpy.path.abspath(filepath or "")
    try:
        mtime = os.path.getmtime(abs_path)
    except OSError:
        mtime = 0
    return f"{os.path.normcase(abs_path)}:{mtime}"


def build_catalog_search_blob(item) -> str:
    filepath = getattr(item, "filepath", "") or ""
    key = _cache_key(filepath)
    cached = _SEARCH_CACHE.get(key)
    if cached is not None:
        return cached

    display_name = getattr(item, "display_name", "") or ""
    if str(filepath).startswith("blend://"):
        blend_name = filepath[8:] or display_name
        stem = blend_name
        basename = blend_name
        family_stem, weight_label, _rank = parse_font_stem(blend_name)
        family_key = family_key_from_stem(blend_name)
        parts = [display_name, blend_name, blend_name.replace("_", " ")]
    else:
        basename = os.path.basename(filepath)
        stem, _ext = os.path.splitext(basename)
        family_stem, weight_label, _rank = parse_font_stem(stem)
        family_key = family_key_for_filepath(filepath)
        parts = [
            display_name,
            basename,
            stem,
            family_stem,
            family_key,
            weight_label,
        ]
        parts.extend(read_font_search_name_strings(filepath))
        catalog_display_name = display_name
        for mode in ("FILENAME", "FAMILY", "FULL", "POSTSCRIPT"):
            label = display_name_for_filepath(
                filepath,
                catalog_display_name=catalog_display_name,
                mode=mode,
            )
            if label:
                parts.append(label)
        parts.extend(_split_tokens(stem))
    if family_stem and weight_label:
        family_display = family_stem.replace("_", " ").replace("-", " ").strip()
        parts.extend((family_stem, family_key, weight_label))
        parts.append(f"{family_stem} {weight_label}")
        if family_display:
            parts.append(f"{family_display} {weight_label}")
    for name in list(parts):
        parts.extend(_split_tokens(name))

    joined = " ".join(part for part in parts if part)
    extras = [
        joined,
        _kana_fold(joined),
        unicodedata.normalize("NFKC", joined),
    ]
    extras.extend(alias_tokens_for_text(joined, *parts))
    if _has_cjk(joined):
        full_py, init_py = _pinyin_variants(joined)
        if full_py:
            extras.append(full_py)
        if init_py:
            extras.append(init_py)
        for name in parts:
            if _has_cjk(name):
                full_py, init_py = _pinyin_variants(name)
                if full_py:
                    extras.append(full_py)
                if init_py:
                    extras.append(init_py)

    blob = " ".join(dict.fromkeys(value.lower() for value in extras if value)).strip()
    _SEARCH_CACHE[key] = blob
    return blob


def _query_variants(filter_text: str) -> list[str]:
    base = filter_text.strip().lower()
    if not base:
        return []
    variants = {base, _kana_fold(base).lower(), unicodedata.normalize("NFKC", base).lower()}
    for token in _QUERY_SPLIT.split(base):
        token = token.strip()
        if not token:
            continue
        variants.add(token)
        variants.add(_kana_fold(token).lower())
    for alias in alias_tokens_for_query(filter_text):
        norm = alias.lower()
        variants.add(norm)
        variants.add(_kana_fold(norm).lower())
        variants.add(unicodedata.normalize("NFKC", norm).lower())
    if _has_cjk(base):
        full_py, init_py = _pinyin_variants(base)
        if full_py:
            variants.add(full_py)
        if init_py:
            variants.add(init_py)
    return [variant for variant in variants if variant]


def _query_in_blob(query: str, blob: str) -> bool:
    """Match typeahead prefixes on index tokens; avoid mid-word hits like sour→resource."""
    if not query:
        return False
    query = query.lower().strip()
    if not query:
        return False
    if _has_cjk(query):
        return query in blob

    tokens = [token for token in blob.split() if token]
    if not tokens:
        return False

    parts = [part for part in _QUERY_SPLIT.split(query) if part]
    if not parts:
        return False
    if len(parts) > 1:
        return all(_query_part_in_blob(part, tokens, blob) for part in parts)
    return _query_part_in_blob(parts[0], tokens, blob)


def _query_part_in_blob(part: str, tokens: list[str], blob: str) -> bool:
    if any(token.startswith(part) for token in tokens):
        return True
    if len(part) >= 3 and any(token.endswith(part) for token in tokens):
        return True
    if len(part) >= 4 and f" {part} " in f" {blob} ":
        return True
    return False


def catalog_item_passes_name(item, text_filter: str) -> bool:
    if not text_filter:
        return True
    blob = build_catalog_search_blob(item)
    if not blob:
        return False
    for query in _query_variants(text_filter):
        if _query_in_blob(query, blob):
            return True
    if text_filter.isascii():
        tokens = [token for token in _QUERY_SPLIT.split(text_filter.lower()) if token]
        if tokens and all(_query_in_blob(token, blob) for token in tokens):
            return True
    return False
