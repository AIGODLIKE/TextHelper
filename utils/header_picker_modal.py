"""Window-local hover preview for header font and weight popovers."""

from __future__ import annotations

import bpy
from bpy.types import Operator

from ..utils.addon_prefs import get_addon_prefs
from ..utils.font_catalog_filter import header_visible_font_catalog_indices
from ..utils.font_loader import is_current_font
from ..utils.operator_poll import TextHelperOperatorMixin
from ..utils.picker_context import ViewportCache, viewport_key
from ..utils.text_format import get_active_text_data
from .header_toolbar import weight_variants_for_text

_UI_UNIT_Y = 20.0
_PREVIEW_OWNER = "HEADER_FONT"
_LAYOUTS = ViewportCache()
_ACTIVE_REGIONS = set()


def _ui_unit_y(context) -> float:
    scale = getattr(context.preferences.system, "ui_scale", 1.0)
    return _UI_UNIT_Y * max(scale, 0.5)


def _hover_apply_enabled(context) -> bool:
    prefs = get_addon_prefs(context)
    return getattr(prefs, "font_preview_on_select", True)


def _seed_hover_apply_key(context) -> str:
    text_data = get_active_text_data(context)
    if text_data is None or text_data.font is None:
        return ""
    from ..utils.font_loader import resolve_font_filepath

    path = resolve_font_filepath(text_data.font)
    return f"w:{path}" if path else ""


def mark_header_picker_layout(
    context,
    picker_type: str,
    header_rows: float,
    *,
    row_units: float = 1.15,
):
    """Record one popover layout without leaking it into another window."""
    unit = _ui_unit_y(context)
    _LAYOUTS.set(
        context,
        {
            "picker_type": str(picker_type or ""),
            "list_top": float(header_rows) * unit,
            "row_height": float(row_units) * unit,
        },
    )
    ensure_header_picker_modal(context)


def ensure_header_picker_modal(context):
    key = viewport_key(context)
    if key is None or key in _ACTIVE_REGIONS or _LAYOUTS.get_key(key) is None:
        return
    try:
        bpy.ops.wm.texthelper_header_picker_modal("INVOKE_DEFAULT")
    except Exception:
        pass


def _apply_font_hover(
    context,
    filepath: str,
    catalog_index: int,
    hover_apply_key: str,
) -> tuple[str, bool]:
    if not filepath or not _hover_apply_enabled(context):
        return hover_apply_key, False

    key = f"f:{catalog_index}:{filepath}"
    if key == hover_apply_key:
        return hover_apply_key, False

    text_data = get_active_text_data(context)
    if text_data is not None and is_current_font(text_data, filepath):
        return key, False

    from .picker_preview import preview_font

    if not preview_font(context, _PREVIEW_OWNER, filepath, catalog_index):
        return hover_apply_key, False
    return key, True


def _hover_row_index(event, area, region, layout) -> int:
    if area is None or region is None or layout is None:
        return -1
    mx = event.mouse_x - region.x
    my = event.mouse_y - region.y
    if mx < 0 or my < 0 or mx > region.width or my > region.height:
        return -1

    list_top = float(layout.get("list_top", 0.0) or 0.0)
    row_height = float(layout.get("row_height", 0.0) or 0.0)
    if row_height <= 0.0 or my < list_top:
        return -1
    return int((my - list_top) / row_height)


def _try_hover_apply(context, row: int, layout, hover_apply_key: str) -> str:
    if row < 0 or layout is None:
        return hover_apply_key

    state = context.window_manager.th_state
    picker_type = layout.get("picker_type", "")
    if picker_type == "FONT":
        indices = header_visible_font_catalog_indices(context)
        if row >= len(indices):
            return hover_apply_key
        catalog = state.font_catalog
        catalog_index = indices[row]
        if catalog_index < 0 or catalog_index >= len(catalog):
            return hover_apply_key
        item = catalog[catalog_index]
        return _apply_font_hover(
            context,
            item.filepath,
            catalog_index,
            hover_apply_key,
        )[0]

    if picker_type == "WEIGHT":
        text_data = get_active_text_data(context)
        variants = weight_variants_for_text(context, text_data)
        if row >= len(variants):
            return hover_apply_key
        variant = variants[row]
        return _apply_font_hover(
            context,
            variant.filepath,
            variant.catalog_index,
            hover_apply_key,
        )[0]
    return hover_apply_key


class TH_OT_header_picker_modal(TextHelperOperatorMixin, Operator):
    bl_idname = "wm.texthelper_header_picker_modal"
    bl_label = "Header Font Picker Hover"
    bl_description = "Preview fonts while hovering the header font or weight list"
    bl_options = {"INTERNAL"}

    _window = None
    _region = None
    _area = None
    _key = None
    _layout = None
    _last_row = -1
    _hover_apply_key = ""

    @classmethod
    def poll(cls, context):
        return _LAYOUTS.get(context) is not None

    def invoke(self, context, event):
        key = viewport_key(context)
        layout = _LAYOUTS.get_key(key)
        if key is None or layout is None or key in _ACTIVE_REGIONS:
            return {"CANCELLED"}

        self._window = context.window
        self._region = context.region
        self._area = context.area
        self._key = key
        self._layout = dict(layout)
        self._last_row = -1
        self._hover_apply_key = _seed_hover_apply_key(context)
        _ACTIVE_REGIONS.add(key)

        from .picker_preview import begin_preview

        begin_preview(context, _PREVIEW_OWNER)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def _region_active(self):
        if self._window is None or self._region is None:
            return False
        try:
            region_key = self._region.as_pointer()
            for area in self._window.screen.areas:
                for region in area.regions:
                    if region.as_pointer() == region_key:
                        return True
        except (AttributeError, ReferenceError):
            return False
        return False

    def modal(self, context, event):
        if not self._region_active():
            self._finish(context)
            return {"CANCELLED"}

        if event.type in {"ESC", "RIGHTMOUSE"} and event.value == "PRESS":
            self._finish(context)
            return {"CANCELLED"}

        if event.type == "MOUSEMOVE":
            row = _hover_row_index(event, self._area, self._region, self._layout)
            if row != self._last_row:
                self._last_row = row
                self._hover_apply_key = _try_hover_apply(
                    context,
                    row,
                    self._layout,
                    self._hover_apply_key,
                )

        return {"PASS_THROUGH"}

    def _finish(self, context):
        from .picker_preview import cancel_preview_for_window

        cancel_preview_for_window(self._window, _PREVIEW_OWNER)
        _ACTIVE_REGIONS.discard(self._key)
        _LAYOUTS.pop_key(self._key)
        self._key = None
        self._layout = None
        self._hover_apply_key = ""


classes = (TH_OT_header_picker_modal,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    _ACTIVE_REGIONS.clear()
    _LAYOUTS.clear()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
