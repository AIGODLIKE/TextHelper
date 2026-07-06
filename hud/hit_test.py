from .layout import hit_test, slider_value_from_mouse, layout_toolbar
from . import layout as layout_mod
from ..utils.addon_prefs import get_addon_prefs
from ..utils.font_context import is_font_edit_mode
from ..utils.text_format import get_active_text
from ..utils.view3d_context import view3d_override

__all__ = [
    "hit_test",
    "slider_value_from_mouse",
    "get_last_rects",
    "get_rects_for_context",
    "get_hud_hit_rects",
    "hud_enabled",
    "set_hud_visibility",
]


def hud_enabled(context, text_data=None):
    if is_font_edit_mode(context):
        return False
    prefs = get_addon_prefs(context)
    if prefs is None or not getattr(prefs, "show_floating_toolbar", True):
        return False
    if text_data is None:
        obj = get_active_text(context)
        text_data = obj.data if obj else None
    if text_data is None:
        return False
    helper = text_data.text_helper
    if getattr(prefs, "auto_show_floating_toolbar", True):
        return bool(getattr(helper, "th_hud_visible", True))
    return bool(getattr(helper, "th_hud_user_shown", False))


def set_hud_visibility(text_helper, visible: bool) -> None:
    """Persist floating-toolbar visibility without selection-time RNA side effects."""
    text_helper.th_hud_visible = visible
    text_helper.th_hud_user_shown = visible


def get_last_rects():
    return getattr(layout_mod, "_LAST_RECTS", [])


def get_rects_for_context(context, obj, text_data):
    from ..utils.text_bounds import get_toolbar_anchor

    if not hud_enabled(context, text_data):
        return []
    prefs = get_addon_prefs(context)
    if prefs is None:
        return []
    anchor = get_toolbar_anchor(context, obj, prefs.toolbar_offset)
    if anchor is None:
        return []
    scale = max(context.preferences.system.ui_scale, 0.5) * prefs.hud_scale
    layout = layout_toolbar(anchor[0], anchor[1], scale, text_data, context)
    return layout["rects"]


def get_hud_hit_rects(context, obj, text_data):
    """Rects for modal hit-testing — prefer last draw pass, else compute in 3D View."""
    if not hud_enabled(context, text_data):
        return []
    rects = get_last_rects()
    if rects:
        return rects
    override = view3d_override(context)
    if override is None:
        return []
    with override:
        return get_rects_for_context(context, obj, text_data)
