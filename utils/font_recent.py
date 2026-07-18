"""Persist recently used font families in add-on preferences."""

from __future__ import annotations

import json
import time

from .addon_prefs import get_addon_prefs
from .font_family import family_key_for_filepath

_MAX_RECENT = 64
_RECENT_GENERATION = 0


def _load_recent_entries(context) -> list[dict]:
    prefs = get_addon_prefs(context)
    raw = getattr(prefs, "font_recent_keys", "") or "[]"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    entries = []
    for item in data:
        if isinstance(item, str) and item:
            entries.append({"key": item, "ts": 0.0})
        elif isinstance(item, dict):
            key = str(item.get("key", "") or "")
            if key:
                entries.append({"key": key, "ts": float(item.get("ts", 0.0) or 0.0)})
    return entries


def _notify_recent_changed(context) -> None:
    """Invalidate every picker view that can be sorted by recent use."""
    from .font_catalog_filter import invalidate_catalog_filter_cache

    invalidate_catalog_filter_cache()
    try:
        from .font_preview import tag_ui_redraw

        tag_ui_redraw(context, all_windows=True)
    except Exception:
        pass
    try:
        from ..hud.draw import tag_redraw

        tag_redraw()
    except Exception:
        pass


def _save_recent_entries(context, entries: list[dict]) -> bool:
    global _RECENT_GENERATION

    prefs = get_addon_prefs(context)
    trimmed = entries[:_MAX_RECENT]
    serialized = json.dumps(trimmed, ensure_ascii=False)
    if (getattr(prefs, "font_recent_keys", "") or "[]") == serialized:
        return False
    prefs.font_recent_keys = serialized
    _RECENT_GENERATION += 1
    _notify_recent_changed(context)
    return True


def recent_generation() -> int:
    """Return a cheap cache key that changes whenever recent ordering changes."""
    return _RECENT_GENERATION


def recent_family_keys(context) -> list[str]:
    return [entry["key"] for entry in _load_recent_entries(context)]


def recent_family_rank_map(context) -> dict[str, int]:
    return {key: index for index, key in enumerate(recent_family_keys(context))}


def touch_recent_family(context, filepath: str) -> None:
    key = family_key_for_filepath(filepath, context)
    if not key:
        return
    current = _load_recent_entries(context)
    if current and current[0]["key"] == key:
        return
    entries = [entry for entry in current if entry["key"] != key]
    now = time.time()
    entries.insert(0, {"key": key, "ts": now})
    _save_recent_entries(context, entries)


def commit_recent_from_active_text(context) -> None:
    """Record the active text object's font as recently used."""
    from .font_loader import resolve_font_filepath
    from .text_format import get_active_text_data

    text_data = get_active_text_data(context)
    if text_data is None or text_data.font is None:
        return
    path = resolve_font_filepath(text_data.font)
    if path:
        touch_recent_family(context, path)


def clear_recent_families(context) -> None:
    _save_recent_entries(context, [])
