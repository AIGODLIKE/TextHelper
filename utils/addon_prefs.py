"""Resolve TextHelper addon preferences (legacy add-on + extension IDs)."""

import sys


class _DefaultPrefs:
    show_floating_toolbar = True
    auto_show_floating_toolbar = True
    show_header_toolbar = True
    auto_layout_frame = True
    toolbar_offset = 100.0
    hud_scale = 0.8
    hud_accent_preset = "BLUE"
    hud_accent_custom = (71 / 255, 114 / 255, 179 / 255)
    font_preview_icons = True
    font_preview_on_select = True
    font_preview_sample = "Exploration witnesses courage, open source witnesses glory"
    font_preview_mode = "OBJECT"
    font_preview_size = 36
    font_preview_width = 512
    font_preview_height = 56
    font_preview_ui_scale = 3.5
    n_panel_textbox_lines = 30
    multiline_text_max_len = 20000
    font_favorite_keys = "[]"
    font_recent_keys = "[]"
    font_display_mode = "FAMILY"
    font_family_group_mode = "AUTO"


def prefs_are_editable(prefs):
    return hasattr(prefs, "bl_rna")


def prefs_bl_idname():
    """AddonPreferences.bl_idname must match the loaded package root."""
    try:
        from .. import ADDON_PACKAGE

        if ADDON_PACKAGE:
            return ADDON_PACKAGE
    except ImportError:
        pass

    for name in ("bl_ext.user_default.TextHelper", "TextHelper"):
        if name in sys.modules:
            return name

    parts = __name__.split(".")
    if parts[0] == "bl_ext" and len(parts) >= 3:
        return ".".join(parts[:3])
    return parts[0] if parts else "TextHelper"


def _addon_pref_keys():
    keys = (
        "bl_ext.user_default.TextHelper",
        "bl_ext.system.TextHelper",
        prefs_bl_idname(),
        "TextHelper",
    )
    seen = set()
    ordered = []
    for key in keys:
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    return ordered


def get_addon_prefs(context):
    if context is None:
        return _DefaultPrefs()

    addons = context.preferences.addons
    for key in _addon_pref_keys():
        if key not in addons:
            continue
        prefs = addons[key].preferences
        if prefs is not None and prefs_are_editable(prefs):
            if hasattr(prefs, "font_preview_width"):
                return prefs

    for key in addons.keys():
        if key.endswith("TextHelper") or key.endswith(".TextHelper"):
            prefs = addons[key].preferences
            if prefs is not None and prefs_are_editable(prefs):
                if hasattr(prefs, "font_preview_width"):
                    return prefs

    return _DefaultPrefs()
