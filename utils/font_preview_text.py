"""Shared preview phrase for font thumbnails and the viewport picker."""

from .addon_prefs import get_addon_prefs
from .text_format import get_active_text_data

DEFAULT_SAMPLE = "Exploration witnesses courage, open source witnesses glory"
MAX_PREVIEW_LEN = 48

_LEGACY_MODES = {
    "BOTH": "OBJECT",
}


def _pref_sample(prefs):
    if prefs is None:
        return DEFAULT_SAMPLE
    return (getattr(prefs, "font_preview_sample", DEFAULT_SAMPLE) or DEFAULT_SAMPLE).strip()


def _inline_sample(context):
    wm = getattr(context, "window_manager", None)
    if wm is None:
        return ""
    state = getattr(wm, "th_state", None)
    if state is None:
        return ""
    return (getattr(state, "font_picker_preview", "") or "").strip()


def _object_sample(context):
    text_data = get_active_text_data(context)
    if text_data is None:
        return ""
    from .text_orientation import is_vertical, vertical_first_column

    if is_vertical(text_data):
        line = vertical_first_column(text_data)
    elif text_data.body:
        body = text_data.body.replace("\r\n", "\n").replace("\r", "\n")
        line = body.split("\n", 1)[0].strip()
    else:
        line = ""
    return (line or "").strip()


def _custom_sample(context, prefs):
    return (_inline_sample(context) or _pref_sample(prefs) or DEFAULT_SAMPLE).strip()


def _preview_mode(prefs):
    mode = getattr(prefs, "font_preview_mode", "OBJECT") if prefs else "OBJECT"
    return _LEGACY_MODES.get(mode, mode)


def get_font_preview_text(context, display_name=""):
    """Resolve preview characters from add-on preferences."""
    if context is None:
        return (DEFAULT_SAMPLE or "Aa")[:MAX_PREVIEW_LEN]

    prefs = get_addon_prefs(context)
    mode = _preview_mode(prefs)
    custom = _custom_sample(context, prefs)[:MAX_PREVIEW_LEN]
    name = (display_name or "").strip()[:MAX_PREVIEW_LEN]

    if mode == "NAME":
        return name or custom or "Aa"

    if mode == "SAMPLE":
        return custom or "Aa"

    object_text = _object_sample(context)[:MAX_PREVIEW_LEN]
    if object_text:
        return object_text
    return custom or "Aa"
