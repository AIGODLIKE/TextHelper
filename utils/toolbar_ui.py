"""Toggle pressed-state helpers shared with the GPU HUD."""

from __future__ import annotations

from ..utils.text_format import is_strike_active, is_underline_active


def _is_active_check(text_data, active_check: str) -> bool:
    if text_data is None or not active_check:
        return False
    attr, val = active_check.split(":", 1)
    cur = text_data
    for part in attr.split("."):
        cur = getattr(cur, part, None)
        if cur is None:
            return False
    return str(cur) == val


def tool_item_pressed(item, text_data) -> bool:
    """Return whether a HUD toggle should draw depressed."""
    if text_data is None or item.kind != "toggle":
        return False
    if item.id == "bold":
        return any(f.use_bold for f in text_data.body_format) if text_data.body_format else False
    if item.id == "italic":
        return any(f.use_italic for f in text_data.body_format) if text_data.body_format else False
    if item.id == "underline":
        return is_underline_active(text_data)
    if item.id == "strike":
        return is_strike_active(text_data)
    return _is_active_check(text_data, item.active_check)
