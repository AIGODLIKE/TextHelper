"""Viewport header numeric sliders (mirrors HUD spacing controls)."""

from __future__ import annotations

import bpy

from .text_format import (
    CHAR_SPACING_DISPLAY_MAX,
    CHAR_SPACING_DISPLAY_MIN,
    LINE_HEIGHT_DISPLAY_MIN,
    SIZE_SLIDER_MAX,
    SIZE_SLIDER_MIN,
    SHEAR_SLIDER_MAX,
    SHEAR_SLIDER_MIN,
    apply_spacing_value,
    get_active_text_data,
    iter_selected_text_data,
    spacing_display_char,
    spacing_display_line,
    spacing_display_word,
)
from .text_frame import tag_view3d_redraw
from .undo import push_undo

_HEADER_SLIDER_GUARD = False


def header_slider_updating() -> bool:
    return _HEADER_SLIDER_GUARD


def sync_header_sliders(context) -> None:
    """No-op: header slider props read live from the active text via get()."""
    _ = context


def apply_header_spacing(context, mode: str, value: float, *, undo: bool = True) -> None:
    if header_slider_updating():
        return
    targets = list(iter_selected_text_data(context))
    if not targets:
        return
    if undo:
        push_undo()
    for text_data in targets:
        apply_spacing_value(text_data, mode, value)
    tag_view3d_redraw(context)


def _header_size_get(self):
    text_data = get_active_text_data(bpy.context)
    if text_data is None:
        return 1.0
    return float(text_data.size)


def _header_size_set(self, value):
    apply_header_spacing(bpy.context, "SIZE", float(value))


def _header_char_spacing_get(self):
    text_data = get_active_text_data(bpy.context)
    if text_data is None:
        return 0.0
    return float(spacing_display_char(text_data.space_character))


def _header_char_spacing_set(self, value):
    apply_header_spacing(bpy.context, "CHAR", float(value))


def _header_word_spacing_get(self):
    text_data = get_active_text_data(bpy.context)
    if text_data is None:
        return 0.0
    return float(spacing_display_word(text_data.space_word))


def _header_word_spacing_set(self, value):
    apply_header_spacing(bpy.context, "WORD", float(value))


def _header_line_height_get(self):
    text_data = get_active_text_data(bpy.context)
    if text_data is None:
        return 10.0
    return float(spacing_display_line(text_data))


def _header_line_height_set(self, value):
    apply_header_spacing(bpy.context, "LINE", float(value))


def _header_shear_get(self):
    text_data = get_active_text_data(bpy.context)
    if text_data is None:
        return 0.0
    return float(text_data.shear)


def _header_shear_set(self, value):
    apply_header_spacing(bpy.context, "SHEAR", float(value))


HEADER_SIZE_PROP = {
    "name": "Font Size",
    "description": "Font size for selected text objects",
    "get": _header_size_get,
    "set": _header_size_set,
    "min": SIZE_SLIDER_MIN,
    "soft_min": SIZE_SLIDER_MIN,
    "soft_max": SIZE_SLIDER_MAX,
    "step": 10,
    "precision": 2,
}

HEADER_CHAR_SPACING_PROP = {
    "name": "Char Spacing",
    "description": "Character spacing offset (0 = preset default)",
    "get": _header_char_spacing_get,
    "set": _header_char_spacing_set,
    "min": CHAR_SPACING_DISPLAY_MIN,
    "soft_min": CHAR_SPACING_DISPLAY_MIN,
    "soft_max": CHAR_SPACING_DISPLAY_MAX,
    "step": 1,
    "precision": 0,
}

HEADER_WORD_SPACING_PROP = {
    "name": "Word Spacing",
    "description": "Word spacing offset (0 = preset default)",
    "get": _header_word_spacing_get,
    "set": _header_word_spacing_set,
    "min": CHAR_SPACING_DISPLAY_MIN,
    "soft_min": CHAR_SPACING_DISPLAY_MIN,
    "soft_max": CHAR_SPACING_DISPLAY_MAX,
    "step": 1,
    "precision": 0,
}

HEADER_LINE_HEIGHT_PROP = {
    "name": "Line Height",
    "description": "Line height display value",
    "get": _header_line_height_get,
    "set": _header_line_height_set,
    "min": LINE_HEIGHT_DISPLAY_MIN,
    "soft_min": LINE_HEIGHT_DISPLAY_MIN,
    "soft_max": 400.0,
    "step": 1,
    "precision": 0,
}

HEADER_SHEAR_PROP = {
    "name": "Shear",
    "description": "Text shear for selected text objects",
    "get": _header_shear_get,
    "set": _header_shear_set,
    "min": SHEAR_SLIDER_MIN,
    "soft_min": SHEAR_SLIDER_MIN,
    "soft_max": SHEAR_SLIDER_MAX,
    "step": 10,
    "precision": 2,
}
