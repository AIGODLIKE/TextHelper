"""Persist favorite font families in add-on preferences."""

from __future__ import annotations

import json

from .addon_prefs import get_addon_prefs
from .font_family import family_key_for_filepath


def get_favorite_keys(context) -> set[str]:
    prefs = get_addon_prefs(context)
    raw = getattr(prefs, "font_favorite_keys", "") or "[]"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return set()
    if not isinstance(data, list):
        return set()
    return {str(key) for key in data if key}


def _save_favorite_keys(context, keys: set[str]) -> None:
    prefs = get_addon_prefs(context)
    if not hasattr(prefs, "font_favorite_keys"):
        return
    prefs.font_favorite_keys = json.dumps(sorted(keys), ensure_ascii=False)


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
