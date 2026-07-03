import bpy
from bpy.types import Operator

from ..i18n import _
from ..utils.addon_prefs import get_addon_prefs
from ..utils.font_context import ensure_text_font, enter_text_edit_mode
from ..utils.operator_poll import ActiveFontDataPollMixin, ActiveFontPollMixin, TextHelperOperatorMixin
from ..utils.text_format import get_active_text
from ..utils.text_frame import ensure_layout_frame, tag_view3d_redraw
from ..utils.text_orientation import clear_vertical_content, is_vertical, set_vertical_source
from ..utils.ui_textbox import sync_panel_textbox_from_canonical


class TH_OT_enter_text_edit(ActiveFontPollMixin, Operator):
    bl_idname = "font.texthelper_enter_text_edit"
    bl_label = "Edit Text"
    bl_description = "Enter in-viewport text editing mode"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = get_active_text(context)
        if obj is None:
            self.report({"WARNING"}, _("Select a text object first"))
            return {"CANCELLED"}
        if not enter_text_edit_mode(context, obj):
            self.report({"ERROR"}, _("Open a 3D Viewport and try again"))
            return {"CANCELLED"}
        return {"FINISHED"}


class TH_OT_text_add(TextHelperOperatorMixin, Operator):
    bl_idname = "font.texthelper_text_add"
    bl_label = "Add Text"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if context.area is None or context.area.type != "VIEW_3D":
            cls.poll_message_set(_("Open a 3D Viewport and try again"))
            return False
        return True

    def execute(self, context):
        bpy.ops.object.text_add()
        obj = context.active_object
        if obj and obj.type == "FONT":
            obj.data.body = "Text"
            obj.name = "Text"
            ensure_text_font(obj.data)
            prefs = get_addon_prefs(context)
            if prefs is None or prefs.auto_layout_frame:
                ensure_layout_frame(context, obj)
            tag_view3d_redraw(context)
            from ..runtime import request_ensure

            request_ensure()
        return {"FINISHED"}


class TH_OT_clear_body(ActiveFontDataPollMixin, Operator):
    bl_idname = "font.texthelper_clear_body"
    bl_label = "Clear Text"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = get_active_text(context)
        if obj is None:
            return {"CANCELLED"}
        if is_vertical(obj.data):
            clear_vertical_content(obj.data)
        else:
            obj.data.body = ""
            obj.data.update_tag()
            sync_panel_textbox_from_canonical(obj.data, vertical=False, context=context, flip_active=True)
        return {"FINISHED"}


class TH_OT_paste_body(ActiveFontDataPollMixin, Operator):
    bl_idname = "font.texthelper_paste_body"
    bl_label = "Paste into Text"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = get_active_text(context)
        if obj is None:
            return {"CANCELLED"}
        raw = context.window_manager.clipboard
        if is_vertical(obj.data):
            set_vertical_source(obj.data, raw)
        else:
            obj.data.body = raw
            obj.data.update_tag()
        return {"FINISHED"}


class TH_OT_import_txt(ActiveFontDataPollMixin, Operator):
    bl_idname = "font.texthelper_import_txt"
    bl_label = "Import Text File"
    bl_options = {"REGISTER", "UNDO"}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        obj = get_active_text(context)
        if obj is None:
            return {"CANCELLED"}
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                raw = f.read()
            if is_vertical(obj.data):
                set_vertical_source(obj.data, raw)
            else:
                obj.data.body = raw
                obj.data.update_tag()
        except OSError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        return {"FINISHED"}


class TH_OT_set_text_case(ActiveFontDataPollMixin, Operator):
    bl_idname = "font.texthelper_set_text_case"
    bl_label = "Set Text Case"
    bl_description = "Transform text to default, uppercase, or lowercase"
    bl_options = {"REGISTER", "UNDO"}

    case: bpy.props.EnumProperty(
        items=(
            ("DEFAULT", "Default", "Original letter casing"),
            ("UPPER", "Uppercase", "All uppercase letters"),
            ("LOWER", "Lowercase", "All lowercase letters"),
        ),
    )

    def execute(self, context):
        from ..hud.draw import tag_redraw
        from ..utils.text_case import apply_text_case

        obj = get_active_text(context)
        if obj is None:
            return {"CANCELLED"}
        apply_text_case(obj.data, self.case)
        tag_view3d_redraw(context)
        tag_redraw()
        return {"FINISHED"}


classes = (
    TH_OT_enter_text_edit,
    TH_OT_text_add,
    TH_OT_clear_body,
    TH_OT_paste_body,
    TH_OT_import_txt,
    TH_OT_set_text_case,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
