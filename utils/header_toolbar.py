"""Native viewport header toolbar (separate from GPU HUD)."""

from __future__ import annotations

from ..i18n import _
from ..utils.text_format import (
    STYLE_PRESETS,
    is_strike_active,
    is_underline_active,
    strike_position_display,
)

_SLIDER_LABEL_UNITS = 1.35
_SLIDER_PROP_UNITS = 4.2


def _truncate_label(text: str, max_len: int = 14) -> str:
    text = text or ""
    if len(text) <= max_len:
        return text
    return text[: max(1, max_len - 1)] + "…"


def header_font_label(text_data, context=None) -> str:
    if text_data is None or not text_data.font:
        return _("Font")
    from ..utils.font_loader import font_hud_label

    return _truncate_label(font_hud_label(text_data.font, context), 12)


def header_weight_label(context, text_data) -> str:
    from ..utils.font_family import short_weight_label, toolbar_weight_label
    from ..utils.font_loader import queue_font_catalog, resolve_font_filepath

    label = _("Regular")
    if text_data is None or not text_data.font or context is None:
        return label
    wm = context.window_manager
    if wm is None or getattr(wm, "th_state", None) is None:
        return label
    queue_font_catalog(wm)
    catalog = wm.th_state.font_catalog
    path = resolve_font_filepath(text_data.font)
    if path and catalog:
        label = toolbar_weight_label(catalog, path)
    return short_weight_label(label, max_len=8)


def header_preset_label(text_data) -> str:
    preset_id = getattr(text_data.text_helper, "th_preset", "BODY") if text_data else "BODY"
    preset = STYLE_PRESETS.get(preset_id, STYLE_PRESETS["BODY"])
    return _truncate_label(_(preset["label"]), 9)


def _style_pressed(text_data, style_id: str) -> bool:
    if text_data is None:
        return False
    if style_id == "bold":
        return any(f.use_bold for f in text_data.body_format) if text_data.body_format else False
    if style_id == "italic":
        return any(f.use_italic for f in text_data.body_format) if text_data.body_format else False
    if style_id == "underline":
        return is_underline_active(text_data)
    if style_id == "strike":
        return is_strike_active(text_data)
    return False


def _case_pressed(text_data, case: str) -> bool:
    if text_data is None:
        return case == "DEFAULT"
    return getattr(text_data.text_helper, "th_text_case", "DEFAULT") == case


def floating_toolbar_pressed(context, text_data=None):
    from ..hud.hit_test import hud_enabled

    return hud_enabled(context, text_data)


def _draw_header_controls(row, context, text_data):
    row.operator(
        "wm.texthelper_toggle_toolbar",
        text="",
        icon="OVERLAY",
        depress=floating_toolbar_pressed(context, text_data),
    )

    row.separator(factor=0.25)

    row.menu("TEXTHELPER_MT_style_preset", text=header_preset_label(text_data))
    row.popover(
        panel="VIEW3D_PT_texthelper_font_popover",
        text=header_font_label(text_data, context),
    )
    row.popover(
        panel="VIEW3D_PT_texthelper_weight_popover",
        text=header_weight_label(context, text_data),
    )

    row.separator(factor=0.25)

    for style, style_id, label in (
        ("BOLD", "bold", "B"),
        ("ITALIC", "italic", "I"),
        ("UNDERLINE", "underline", "U"),
    ):
        op = row.operator(
            "font.texthelper_style_toggle",
            text=label,
            depress=_style_pressed(text_data, style_id),
        )
        op.style = style

    op = row.operator(
        "font.texthelper_style_toggle",
        text="S",
        depress=_style_pressed(text_data, "strike"),
    )
    op.style = "STRIKE"
    if is_strike_active(text_data):
        row.popover(
            panel="VIEW3D_PT_texthelper_strike_popover",
            text=strike_position_display(text_data.text_helper.th_strike_position),
        )

    row.separator(factor=0.25)

    for case, label in (("DEFAULT", "/"), ("UPPER", "AA"), ("LOWER", "aa")):
        op = row.operator(
            "font.texthelper_set_text_case",
            text=label,
            depress=_case_pressed(text_data, case),
        )
        op.case = case

    row.separator(factor=0.25)

    for align, icon in (
        ("LEFT", "ALIGN_LEFT"),
        ("CENTER", "ALIGN_CENTER"),
        ("RIGHT", "ALIGN_RIGHT"),
    ):
        op = row.operator(
            "font.texthelper_set_align",
            text="",
            icon=icon,
            depress=text_data.align_x == align,
        )
        op.align = align


def _draw_header_slider(row, state, prop_name: str, label: str):
    pack = row.row(align=True)
    label_row = pack.row(align=True)
    label_row.ui_units_x = _SLIDER_LABEL_UNITS
    label_row.alignment = "RIGHT"
    label_row.label(text=label)
    prop_row = pack.row(align=True)
    prop_row.ui_units_x = _SLIDER_PROP_UNITS
    prop_row.use_property_split = False
    prop_row.use_property_decorate = False
    prop_row.prop(state, prop_name, text="", slider=True)


def _draw_header_value_sliders(row, context, text_data):
    state = context.window_manager.th_state
    row.use_property_split = False
    row.use_property_decorate = False
    row.alignment = "RIGHT"

    _draw_header_slider(row, state, "th_header_size", _("Sz"))
    _draw_header_slider(row, state, "th_header_char_spacing", _("Ch"))
    _draw_header_slider(row, state, "th_header_word_spacing", _("Wd"))
    _draw_header_slider(row, state, "th_header_line_height", _("Ln"))
    _draw_header_slider(row, state, "th_header_shear", _("Sh"))


def draw_header_toolbar(layout, context, text_data):
    """Draw text formatting controls for VIEW3D_HT_tool_header."""
    row = layout.row(align=True)
    _draw_header_controls(row, context, text_data)
    row.separator_spacer()
    _draw_header_value_sliders(row, context, text_data)


def weight_variants_for_text(context, text_data):
    from ..utils.font_family import ensure_weight_variants
    from ..utils.font_loader import queue_font_catalog, resolve_font_filepath

    if text_data is None or text_data.font is None:
        return ()
    wm = context.window_manager
    path = resolve_font_filepath(text_data.font)
    if not path:
        return ()
    queue_font_catalog(wm)
    catalog = getattr(getattr(wm, "th_state", None), "font_catalog", None)
    return ensure_weight_variants(catalog, path, context)
