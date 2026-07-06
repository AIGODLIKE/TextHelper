"""Per-object HUD toolbar drag offset stored on the Object (not TextCurve undo stack)."""

from __future__ import annotations

_KEY_X = "texthelper_hud_offset_x"
_KEY_Y = "texthelper_hud_offset_y"


def _legacy_offset(text_data) -> tuple[float, float]:
    helper = getattr(text_data, "text_helper", None)
    if helper is None:
        return 0.0, 0.0
    return float(getattr(helper, "th_hud_offset_x", 0.0) or 0.0), float(
        getattr(helper, "th_hud_offset_y", 0.0) or 0.0
    )


def get_hud_offset(obj) -> tuple[float, float]:
    if obj is None or getattr(obj, "type", None) != "FONT":
        return 0.0, 0.0
    if _KEY_X in obj and _KEY_Y in obj:
        return float(obj[_KEY_X]), float(obj[_KEY_Y])
    text_data = obj.data
    ox, oy = _legacy_offset(text_data)
    if ox or oy:
        set_hud_offset(obj, ox, oy)
    return ox, oy


def set_hud_offset(obj, offset_x: float, offset_y: float) -> None:
    if obj is None or getattr(obj, "type", None) != "FONT":
        return
    obj[_KEY_X] = float(offset_x)
    obj[_KEY_Y] = float(offset_y)
