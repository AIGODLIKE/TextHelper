"""Resolve TextHelper addon preferences."""


class _DefaultPrefs:
    show_floating_toolbar = True
    auto_show_floating_toolbar = True
    show_header_toolbar = True
    auto_layout_frame = True
    toolbar_offset = 100.0
    hud_scale = 0.8
    hud_safe_margin = 10.0
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
    multiline_text_max_len = 500
    font_favorite_keys = "[]"
    font_recent_keys = "[]"
    font_display_mode = "FAMILY"
    font_family_group_mode = "AUTO"


def prefs_are_editable(prefs):
    return hasattr(prefs, "bl_rna")


def prefs_bl_idname():
    """The extension package root, used as AddonPreferences.bl_idname."""
    from .. import ADDON_PACKAGE

    return ADDON_PACKAGE


def get_addon_prefs(context):
    if context is None:
        return _DefaultPrefs()

    package = prefs_bl_idname()
    addons = context.preferences.addons
    if package and package in addons:
        prefs = addons[package].preferences
        if prefs is not None and prefs_are_editable(prefs):
            return prefs

    return _DefaultPrefs()
