import bpy
from bpy.types import Operator

from ..utils.operator_poll import ActiveFontDataPollMixin
from ..utils.text_format import get_active_text_data
from ..utils.text_frame import tag_view3d_redraw
from ..utils.text_orientation import apply_column_order, apply_orientation, insert_column_break, is_vertical, set_vertical_source
from ..utils.vertical_align_check import convert_text_to_fullwidth, has_convertible_chars


class TH_OT_set_text_orientation(ActiveFontDataPollMixin, Operator):
    bl_idname = "font.texthelper_set_text_orientation"
    bl_label = "Set Text Orientation"
    bl_options = {"REGISTER", "UNDO"}

    orientation: bpy.props.EnumProperty(
        items=[
            ("HORIZONTAL", "Horizontal", "Edit text in horizontal rows"),
            ("VERTICAL", "Vertical", "Edit text in vertical columns"),
        ],
    )

    def execute(self, context):
        text_data = get_active_text_data(context)
        if text_data is None:
            return {"CANCELLED"}
        apply_orientation(text_data, self.orientation)
        tag_view3d_redraw(context)
        return {"FINISHED"}


class TH_OT_set_column_order(ActiveFontDataPollMixin, Operator):
    bl_idname = "font.texthelper_set_column_order"
    bl_label = "Set Column Order"
    bl_options = {"REGISTER", "UNDO"}

    order: bpy.props.EnumProperty(
        items=[
            ("RTL", "Right to Left", "First line is rightmost; Enter adds a column to the left"),
            ("LTR", "Left to Right", "First line is leftmost; Enter adds a column to the right"),
        ],
    )

    def execute(self, context):
        text_data = get_active_text_data(context)
        if text_data is None:
            return {"CANCELLED"}
        apply_column_order(text_data, self.order)
        tag_view3d_redraw(context)
        return {"FINISHED"}


class TH_OT_insert_column_break(ActiveFontDataPollMixin, Operator):
    bl_idname = "font.texthelper_insert_column_break"
    bl_label = "Insert Column Break"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        text_data = get_active_text_data(context)
        if text_data is None:
            return {"CANCELLED"}
        if not insert_column_break(text_data):
            return {"CANCELLED"}
        tag_view3d_redraw(context)
        return {"FINISHED"}


class TH_OT_convert_vertical_fullwidth(ActiveFontDataPollMixin, Operator):
    bl_idname = "font.texthelper_convert_vertical_fullwidth"
    bl_label = "Fix Halfwidth Characters"
    bl_description = "Convert halfwidth characters to fullwidth for vertical column alignment"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from ..i18n import _

        text_data = get_active_text_data(context)
        if text_data is None or not is_vertical(text_data):
            return {"CANCELLED"}

        raw = getattr(text_data.text_helper, "th_vertical_source", "") or ""
        if not has_convertible_chars(raw):
            self.report({"INFO"}, _("No halfwidth characters to convert"))
            return {"CANCELLED"}

        converted = convert_text_to_fullwidth(raw)
        set_vertical_source(text_data, converted)
        tag_view3d_redraw(context)
        return {"FINISHED"}


classes = (
    TH_OT_set_text_orientation,
    TH_OT_set_column_order,
    TH_OT_insert_column_break,
    TH_OT_convert_vertical_fullwidth,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
