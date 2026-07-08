"""Hover preview for header font / weight popovers."""

from __future__ import annotations

import bpy
from bpy.types import Operator

from ..utils.operator_poll import TextHelperOperatorMixin
from ..utils.addon_prefs import get_addon_prefs
from ..utils.font_loader import assign_font, is_current_font
from ..utils.font_catalog_filter import header_visible_font_catalog_indices
from ..utils.text_format import get_active_text_data, iter_selected_text_data
from ..utils.text_frame import tag_view3d_redraw
from .header_toolbar import weight_variants_for_text

_UI_UNIT_Y = 20.0
_HOVER_APPLY_KEY = ""


def _ui_unit_y(context) -> float:
    scale = getattr(context.preferences.system, "ui_scale", 1.0)
    return _UI_UNIT_Y * max(scale, 0.5)


def _hover_apply_enabled(context) -> bool:
    prefs = get_addon_prefs(context)
    return getattr(prefs, "font_preview_on_select", True)


def reset_header_picker_hover_apply():
    global _HOVER_APPLY_KEY
    _HOVER_APPLY_KEY = ""


def seed_header_picker_hover_apply(context):
    global _HOVER_APPLY_KEY
    reset_header_picker_hover_apply()
    text_data = get_active_text_data(context)
    if text_data is None or text_data.font is None:
        return
    from ..utils.font_loader import resolve_font_filepath

    path = resolve_font_filepath(text_data.font)
    if path:
        _HOVER_APPLY_KEY = f"w:{path}"


def mark_header_picker_layout(context, picker_type: str, header_rows: float, *, row_units: float = 1.15):
    wm = context.window_manager
    state = getattr(wm, "th_state", None)
    if state is None:
        return
    unit = _ui_unit_y(context)
    state.th_header_picker_type = picker_type
    state.th_header_picker_list_top = header_rows * unit
    state.th_header_picker_row_height = row_units * unit
    ensure_header_picker_modal(context)


def ensure_header_picker_modal(context):
    wm = context.window_manager
    state = getattr(wm, "th_state", None)
    if state is None or state.th_header_picker_modal:
        return
    try:
        bpy.ops.wm.texthelper_header_picker_modal("INVOKE_DEFAULT")
    except Exception:
        pass


def _apply_font_hover(context, filepath: str, catalog_index: int = -1) -> bool:
    global _HOVER_APPLY_KEY

    if not filepath or not _hover_apply_enabled(context):
        return False

    key = f"f:{catalog_index}:{filepath}"
    if key == _HOVER_APPLY_KEY:
        return False

    text_data = get_active_text_data(context)
    if text_data is not None and is_current_font(text_data, filepath):
        _HOVER_APPLY_KEY = key
        return False

    applied = False
    for target in iter_selected_text_data(context):
        try:
            assign_font(target, filepath)
        except (FileNotFoundError, OSError):
            return False
        applied = True

    if not applied:
        return False

    if catalog_index >= 0:
        from ..props import set_font_catalog_index

        set_font_catalog_index(context.window_manager, catalog_index)

    _HOVER_APPLY_KEY = key
    tag_view3d_redraw(context)
    return True


def _hover_row_index(context, event, area, region) -> int:
    state = context.window_manager.th_state
    if area is None or region is None:
        return -1
    mx = event.mouse_x - region.x
    my = event.mouse_y - region.y
    if mx < 0 or my < 0 or mx > region.width or my > region.height:
        return -1

    list_top = float(getattr(state, "th_header_picker_list_top", 0.0) or 0.0)
    row_height = float(getattr(state, "th_header_picker_row_height", 0.0) or 0.0)
    if row_height <= 0.0 or my < list_top:
        return -1
    return int((my - list_top) / row_height)


def _try_hover_apply(context, event, area, region) -> None:
    state = context.window_manager.th_state
    row = _hover_row_index(context, event, area, region)
    if row < 0:
        return

    picker_type = getattr(state, "th_header_picker_type", "") or ""
    if picker_type == "FONT":
        indices = header_visible_font_catalog_indices(context)
        if row >= len(indices):
            return
        catalog = state.font_catalog
        catalog_index = indices[row]
        if catalog_index < 0 or catalog_index >= len(catalog):
            return
        item = catalog[catalog_index]
        _apply_font_hover(context, item.filepath, catalog_index)
        return

    if picker_type == "WEIGHT":
        text_data = get_active_text_data(context)
        variants = weight_variants_for_text(context, text_data)
        if row >= len(variants):
            return
        variant = variants[row]
        _apply_font_hover(context, variant.filepath, variant.catalog_index)


class TH_OT_header_picker_modal(TextHelperOperatorMixin, Operator):
    bl_idname = "wm.texthelper_header_picker_modal"
    bl_label = "Header Font Picker Hover"
    bl_description = "Preview fonts while hovering the header font or weight list"
    bl_options = {"INTERNAL"}

    _region = None
    _area = None
    _last_row = -1

    @classmethod
    def poll(cls, context):
        return getattr(getattr(context.window_manager, "th_state", None), "th_header_picker_type", "") != ""

    def invoke(self, context, event):
        wm = context.window_manager
        state = wm.th_state
        if state.th_header_picker_modal:
            return {"CANCELLED"}

        self._region = context.region
        self._area = context.area
        self._last_row = -1
        state.th_header_picker_modal = True
        seed_header_picker_hover_apply(context)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def _region_active(self, context):
        if self._region is None:
            return False
        region_key = self._region.as_pointer()
        for area in context.window.screen.areas:
            for region in area.regions:
                if region.as_pointer() == region_key:
                    return True
        return False

    def modal(self, context, event):
        wm = context.window_manager
        state = wm.th_state

        if not self._region_active(context) or not getattr(state, "th_header_picker_type", ""):
            self._finish(state)
            return {"CANCELLED"}

        if event.type in {"ESC", "RIGHTMOUSE"} and event.value == "PRESS":
            self._finish(state)
            return {"CANCELLED"}

        if event.type == "MOUSEMOVE":
            row = _hover_row_index(context, event, self._area, self._region)
            if row != self._last_row:
                self._last_row = row
                if row >= 0:
                    _try_hover_apply(context, event, self._area, self._region)

        return {"PASS_THROUGH"}

    def _finish(self, state):
        state.th_header_picker_modal = False
        state.th_header_picker_type = ""
        reset_header_picker_hover_apply()


classes = (TH_OT_header_picker_modal,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
