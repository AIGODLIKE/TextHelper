"""Persist favorite font families in add-on preferences."""

from __future__ import annotations

import json

from .addon_prefs import get_addon_prefs
from .font_family import family_key_for_filepath

_CACHE_RAW = None
_CACHE_KEYS = frozenset()


def get_favorite_keys(context) -> set[str]:
    global _CACHE_RAW, _CACHE_KEYS

    prefs = get_addon_prefs(context)
    raw = getattr(prefs, "font_favorite_keys", "") or "[]"
    if raw == _CACHE_RAW:
        return set(_CACHE_KEYS)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        _CACHE_RAW = raw
        _CACHE_KEYS = frozenset()
        return set()
    if not isinstance(data, list):
        _CACHE_RAW = raw
        _CACHE_KEYS = frozenset()
        return set()
    _CACHE_RAW = raw
    _CACHE_KEYS = frozenset(str(key) for key in data if key)
    return set(_CACHE_KEYS)


def _save_favorite_keys(context, keys: set[str]) -> None:
    global _CACHE_RAW, _CACHE_KEYS

    prefs = get_addon_prefs(context)
    if not hasattr(prefs, "font_favorite_keys"):
        return
    raw = json.dumps(sorted(keys), ensure_ascii=False)
    prefs.font_favorite_keys = raw
    _CACHE_RAW = raw
    _CACHE_KEYS = frozenset(keys)


def is_family_favorite(context, filepath: str) -> bool:
    key = family_key_for_filepath(filepath, context)
    if not key:
        return False
    return key in get_favorite_keys(context)


def toggle_family_favorite(context, filepath: str) -> bool:
    key = family_key_for_filepath(filepath, context)
    if not key:
        return False
    keys = get_favorite_keys(context)
    if key in keys:
        keys.remove(key)
        _save_favorite_keys(context, keys)
        return False
    keys.add(key)
    _save_favorite_keys(context, keys)
    return True
