"""Viewport header / tool-header formatting toolbar."""

import bpy
from bpy.types import Menu, Panel, UIList

from ..i18n import _
from ..utils.addon_prefs import get_addon_prefs
from ..utils.font_loader import is_current_font, queue_font_catalog
from ..utils.font_family import header_font_display_label
from ..utils.text_format import get_active_text, get_active_text_data, is_strike_active
from ..utils.header_toolbar import (
    draw_header_toolbar,
    weight_variants_for_text,
)
from ..utils.header_picker_modal import mark_header_picker_layout
from ..ops.font_list import (
    _draw_font_catalog_status,
    _draw_font_filter_row,
    _draw_font_favorite_toggle,
    _draw_header_font_list_header,
    filter_header_font_catalog_items,
)

_ORIGINAL_DRAW_TOOL_SETTINGS = None


class TEXTHELPER_MT_text_case(Menu):
    bl_label = "Text Case"
    bl_idname = "TEXTHELPER_MT_text_case"
    bl_translation_context = "Operator"

    def draw(self, context):
        layout = self.layout
        text_data = context.active_object.data if context.active_object else None
        current = getattr(text_data.text_helper, "th_text_case", "DEFAULT") if text_data else "DEFAULT"
        for case, label in (
            ("DEFAULT", _("Default")),
            ("UPPER", _("Uppercase")),
            ("LOWER", _("Lowercase")),
        ):
            row_text = f"✓ {label}" if case == current else label
            op = layout.operator("font.texthelper_set_text_case", text=row_text)
            op.case = case


class TEXTHELPER_UL_header_fonts(UIList):
    bl_idname = "TEXTHELPER_UL_header_fonts"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        text_data = get_active_text_data(context)
        active = is_current_font(text_data, item.filepath)
        row = layout.row(align=True)
        _draw_font_favorite_toggle(row, context, item.filepath, keep_picker_open=True, solo_icons=True)
        if active:
            row.label(text="", icon="CHECKMARK")
        label = header_font_display_label(context, data.font_catalog, index, item)
        op = row.operator(
            "font.texthelper_apply_system_font",
            text=label,
            emboss=False,
            depress=active,
        )
        op.filepath = item.filepath
        op.catalog_index = index
        op.keep_picker_open = True

    def filter_items(self, context, data, propname):
        return filter_header_font_catalog_items(self, context, data, propname)


class VIEW3D_PT_texthelper_font_popover(Panel):
    bl_label = "Font"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_ui_units_x = 14
    bl_options = {"INSTANCED"}
    bl_translation_context = "*"

    @classmethod
    def poll(cls, context):
        return get_active_text(context) is not None

    def draw(self, context):
        wm = context.window_manager
        layout = self.layout
        queue_font_catalog(wm)

        _draw_header_font_list_header(layout, context, wm)
        _draw_font_filter_row(layout, wm, context, compact_refresh=True)

        if _draw_font_catalog_status(layout, wm):
            return

        mark_header_picker_layout(context, "FONT", header_rows=4.35)

        layout.template_list(
            "TEXTHELPER_UL_header_fonts",
            "th_font_header",
            wm.th_state,
            "font_catalog",
            wm.th_state,
            "font_index",
            rows=8,
        )
        layout.separator()
        layout.operator("font.texthelper_browse_font", text=_("Browse font file…"), icon="FILE_FOLDER")


class VIEW3D_PT_texthelper_weight_popover(Panel):
    bl_label = "Font Weight"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_ui_units_x = 10
    bl_options = {"INSTANCED"}
    bl_translation_context = "*"

    @classmethod
    def poll(cls, context):
        return get_active_text(context) is not None

    def draw(self, context):
        text_data = get_active_text_data(context)
        layout = self.layout
        variants = weight_variants_for_text(context, text_data)
        if not variants:
            layout.label(text=_("No font weight information available"), icon="INFO")
            return

        mark_header_picker_layout(context, "WEIGHT", header_rows=0.35, row_units=1.05)

        col = layout.column(align=True)
        for variant in variants:
            active = is_current_font(text_data, variant.filepath)
            label = variant.weight_label or variant.display_name
            row_text = f"✓ {label}" if active else label
            op = col.operator(
                "font.texthelper_apply_system_font",
                text=row_text,
                depress=active,
            )
            op.filepath = variant.filepath
            op.catalog_index = variant.catalog_index
            op.keep_picker_open = True


class VIEW3D_PT_texthelper_strike_popover(Panel):
    bl_label = "Strike Pos"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_ui_units_x = 8
    bl_options = {"INSTANCED"}
    bl_translation_context = "*"

    @classmethod
    def poll(cls, context):
        text_data = get_active_text_data(context)
        return text_data is not None and is_strike_active(text_data)

    def draw(self, context):
        text_data = get_active_text_data(context)
        if text_data is None or not is_strike_active(text_data):
            self.layout.label(text=_("Enable strikethrough first"), icon="INFO")
            return

        helper = text_data.text_helper
        col = self.layout.column(align=True)
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(helper, "th_strike_position", slider=True)
        row = col.row(align=True)
        op = row.operator("font.texthelper_reset_format_value", text=_("Reset"))
        op.mode = "STRIKE_POS"


def _header_toolbar_poll(context) -> bool:
    prefs = get_addon_prefs(context)
    if not getattr(prefs, "show_header_toolbar", True):
        return False
    return get_active_text(context) is not None


def _draw_texthelper_tool_header(self, context):
    if not _header_toolbar_poll(context):
        return

    region = context.region
    if region is None or region.type != "TOOL_HEADER":
        return

    from ..utils.font_context import is_font_edit_mode

    obj = get_active_text(context)
    if obj is None:
        return

    layout = self.layout
    layout.separator(type="LINE")

    if is_font_edit_mode(context):
        layout.label(text=_("Text Helper"), icon="FONT_DATA")
        return

    draw_header_toolbar(layout, context, obj.data)


def _draw_tool_settings_with_texthelper(self, context):
    _ORIGINAL_DRAW_TOOL_SETTINGS(self, context)
    _draw_texthelper_tool_header(self, context)


classes = (
    TEXTHELPER_MT_text_case,
    TEXTHELPER_UL_header_fonts,
    VIEW3D_PT_texthelper_font_popover,
    VIEW3D_PT_texthelper_weight_popover,
    VIEW3D_PT_texthelper_strike_popover,
)


def register():
    global _ORIGINAL_DRAW_TOOL_SETTINGS
    from ..utils.header_picker_modal import register as register_header_picker_modal

    register_header_picker_modal()
    for cls in classes:
        bpy.utils.register_class(cls)
    cls = bpy.types.VIEW3D_HT_tool_header
    if _ORIGINAL_DRAW_TOOL_SETTINGS is None:
        _ORIGINAL_DRAW_TOOL_SETTINGS = cls.draw_tool_settings
    cls.draw_tool_settings = _draw_tool_settings_with_texthelper


def unregister():
    global _ORIGINAL_DRAW_TOOL_SETTINGS
    from ..utils.header_picker_modal import unregister as unregister_header_picker_modal

    cls = bpy.types.VIEW3D_HT_tool_header
    if _ORIGINAL_DRAW_TOOL_SETTINGS is not None:
        cls.draw_tool_settings = _ORIGINAL_DRAW_TOOL_SETTINGS
        _ORIGINAL_DRAW_TOOL_SETTINGS = None
    unregister_header_picker_modal()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
