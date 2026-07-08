from .layout import hit_test, slider_value_from_mouse
from . import layout as layout_mod
from ..utils.addon_prefs import get_addon_prefs
from ..utils.font_context import is_font_edit_mode
from ..utils.text_format import get_active_text
from ..utils.view3d_context import context_view3d_window, override_view3d_window

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


def get_last_rects(context=None):
    if context is None:
        return []
    return layout_mod.get_cached_hud_rects(context)


def get_rects_for_context(context, obj, text_data):
    from ..utils.text_bounds import resolve_hud_layout

    if not hud_enabled(context, text_data):
        return []
    prefs = get_addon_prefs(context)
    if prefs is None:
        return []
    resolved = resolve_hud_layout(context, obj, text_data, toolbar_offset=prefs.toolbar_offset)
    if resolved is None:
        return []
    return resolved["layout"]["rects"]


def get_hud_hit_rects(context, obj, text_data):
    """Rects for modal hit-testing — use the viewport that owns context.region."""
    if not hud_enabled(context, text_data):
        return []
    rects = get_last_rects(context)
    if rects:
        return rects
    if context_view3d_window(context)[0] is not None:
        return get_rects_for_context(context, obj, text_data)
    override = override_view3d_window(context)
    if override is None:
        return []
    with override:
        return get_rects_for_context(context, obj, text_data)
