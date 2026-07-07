"""Text object / N-panel multi-line length limits."""

from __future__ import annotations

import bpy

# Blender manual: max 50,000 characters per text object.
BLENDER_TEXT_BODY_MAX_LEN = 50000
DEFAULT_MULTILINE_TEXT_MAX_LEN = 500
MIN_MULTILINE_TEXT_MAX_LEN = 256
MAX_MULTILINE_TEXT_MAX_LEN = BLENDER_TEXT_BODY_MAX_LEN

# Backward-compatible alias for RNA maxlen registration.
TEXT_BODY_MAX_LEN = BLENDER_TEXT_BODY_MAX_LEN


def text_body_max_len(context=None) -> int:
    """User-configured cap (clamped to Blender's hard maximum)."""
    from .addon_prefs import get_addon_prefs

    if context is None:
        try:
            context = bpy.context
        except Exception:
            context = None
    prefs = get_addon_prefs(context)
    try:
        limit = int(getattr(prefs, "multiline_text_max_len", DEFAULT_MULTILINE_TEXT_MAX_LEN))
    except (TypeError, ValueError):
        limit = DEFAULT_MULTILINE_TEXT_MAX_LEN
    return max(MIN_MULTILINE_TEXT_MAX_LEN, min(limit, MAX_MULTILINE_TEXT_MAX_LEN))


def clamp_multiline_text(text: str, *, context=None) -> str:
    """Clamp multi-line panel / body / clipboard text to the configured cap."""
    limit = text_body_max_len(context)
    if not text or len(text) <= limit:
        return text or ""
    return text[:limit]


def clamp_text_body(text: str, *, context=None) -> str:
    return clamp_multiline_text(text, context=context)


def clamp_clipboard_text(text: str, *, context=None) -> str:
    return clamp_multiline_text(text, context=context)


def multiline_char_count(text_data, *, vertical: bool = False) -> int:
    if text_data is None:
        return 0
    if vertical:
        from .text_orientation import vertical_source_char_count

        return vertical_source_char_count(text_data)
    return len(getattr(text_data, "body", "") or "")


def text_was_truncated(original: str, clamped: str) -> bool:
    return bool(original) and len(original) > len(clamped)


def assign_text_body(text_data, body: str, *, context=None) -> str:
    """Assign body with the configured character cap; returns the stored string."""
    incoming = body or ""
    body = clamp_text_body(incoming, context=context)
    if getattr(text_data, "body", "") == body:
        return body
    text_data.body = body
    text_data.update_tag()
    return body


def enforce_multiline_limits(context=None) -> bool:
    """Clamp all selected text objects to the configured character cap."""
    from .text_format import iter_selected_font_objects
    from .text_orientation import is_vertical, sync_vertical_source_to_body

    ctx = context
    if ctx is None:
        try:
            ctx = bpy.context
        except Exception:
            ctx = None

    updated = False
    for obj in iter_selected_font_objects(ctx):
        text_data = obj.data
        if text_data is None:
            continue
        if is_vertical(text_data):
            before_source = getattr(text_data.text_helper, "th_vertical_source", "") or ""
            before_body = text_data.body or ""
            sync_vertical_source_to_body(text_data, context=ctx)
            after_source = getattr(text_data.text_helper, "th_vertical_source", "") or ""
            after_body = text_data.body or ""
            if before_source != after_source or before_body != after_body:
                updated = True
        else:
            body = text_data.body or ""
            clamped = clamp_text_body(body, context=ctx)
            if clamped != body:
                assign_text_body(text_data, clamped, context=ctx)
                updated = True
    return updated


def assign_vertical_source(text_helper, source: str, *, context=None) -> str:
    """Assign vertical N-panel source with the same character cap."""
    incoming = source or ""
    source = clamp_multiline_text(incoming, context=context)
    if getattr(text_helper, "th_vertical_source", "") == source:
        return source
    text_helper.th_vertical_source = source
    return source
