import os

import bpy
from bpy.props import StringProperty
from bpy.types import Operator, Menu

from ..i18n import _
from ..utils.operator_poll import ActiveFontDataPollMixin
from ..utils.font_context import ensure_text_font
from ..utils.font_loader import assign_font, default_font_browse_dir
from ..utils.text_format import get_active_text_data
from .font_list import draw_font_picker_popup


def _draw_font_slot(layout, text_data, prop, label):
    split = layout.split(factor=0.34, align=True)
    split.label(text=label)
    split.template_ID(text_data, prop, new="font.new", open="font.open")


class TH_OT_browse_font(ActiveFontDataPollMixin, Operator):
    bl_idname = "font.texthelper_browse_font"
    bl_label = "Browse Font File"
    bl_description = "Load a .ttf/.otf font from disk and assign it to the text"
    bl_options = {"REGISTER", "UNDO"}

    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.ttf;*.otf;*.TTF;*.OTF;*.ttc;*.TTC")

    def invoke(self, context, event):
        text_data = get_active_text_data(context)
        if text_data is None:
            self.report({"WARNING"}, _("Select a text object first"))
            return {"CANCELLED"}

        if not self.filepath:
            start = default_font_browse_dir()
            if start:
                self.filepath = os.path.join(start, "")
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        text_data = get_active_text_data(context)
        if text_data is None:
            return {"CANCELLED"}
        try:
            assign_font(text_data, self.filepath)
        except FileNotFoundError:
            self.report({"ERROR"}, _("Font file not found"))
            return {"CANCELLED"}
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, _("Font loaded: {}").format(bpy.path.display_name(self.filepath)))
        return {"FINISHED"}


class TH_OT_open_font_safe(ActiveFontDataPollMixin, Operator):
    bl_idname = "font.texthelper_open_font_safe"
    bl_label = "Open Font (Blender)"
    bl_description = "Open Blender's font browser when the 3D View context is required"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from ..utils.font_context import font_view3d_override
        from ..utils.text_format import get_active_text

        obj = get_active_text(context)
        text_data = get_active_text_data(context)
        if obj is None or text_data is None:
            return {"CANCELLED"}
        if not ensure_text_font(text_data):
            self.report({"ERROR"}, _("No font data available"))
            return {"CANCELLED"}

        with font_view3d_override(context, obj) as ok:
            if not ok:
                self.report({"ERROR"}, _("Open a 3D Viewport and try again"))
                return {"CANCELLED"}
            if not bpy.ops.font.open.poll():
                self.report({"ERROR"}, _("Font browser cannot open in the current context"))
                return {"CANCELLED"}
            bpy.ops.font.open("INVOKE_DEFAULT")
        return {"FINISHED"}


class TH_OT_unlink_font(ActiveFontDataPollMixin, Operator):
    bl_idname = "font.texthelper_unlink_font"
    bl_label = "Unlink Font"
    bl_description = "Restore the default Bfont when no custom font is linked"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        text_data = get_active_text_data(context)
        if text_data is None:
            return {"CANCELLED"}
        ensure_text_font(text_data)
        return {"FINISHED"}


class TEXTHELPER_MT_font_menu(Menu):
    bl_label = "Font"
    bl_idname = "TEXTHELPER_MT_font_menu"

    def draw(self, context):
        layout = self.layout
        layout.ui_units_x = 16

        text_data = get_active_text_data(context)
        if text_data is None:
            layout.label(text=_("Select a text object first"), icon="INFO")
            return

        col = layout.column(align=False)
        col.operator("font.texthelper_toggle_font_picker", text=_("Open Font Picker"), icon="FONT_DATA")
        draw_font_picker_popup(col, context)

        col.separator()
        col.operator("font.texthelper_browse_font", text=_("Browse other font file…"), icon="FILE_FOLDER")

        col.separator()
        col.label(text=_("Style slots (bold / italic)"))
        _draw_font_slot(col, text_data, "font_bold", _("Bold Font"))
        _draw_font_slot(col, text_data, "font_italic", _("Italic Font"))
        _draw_font_slot(col, text_data, "font_bold_italic", _("Bold Italic Font"))


classes = (
    TH_OT_browse_font,
    TH_OT_open_font_safe,
    TH_OT_unlink_font,
    TEXTHELPER_MT_font_menu,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
