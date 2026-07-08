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


def _add_text_object(context):
    """Create a FONT object at the 3D cursor without bpy.ops.object.text_add()."""
    curve = bpy.data.curves.new(name="Text", type="FONT")
    obj = bpy.data.objects.new("Text", curve)
    context.collection.objects.link(obj)
    obj.location = context.scene.cursor.location.copy()
    for other in context.selected_objects:
        other.select_set(False)
    obj.select_set(True)
    context.view_layer.objects.active = obj
    curve.body = "Text"
    return obj


class TH_OT_text_add(TextHelperOperatorMixin, Operator):
    bl_idname = "font.texthelper_text_add"
    bl_label = "Add Text"
    bl_description = "Add a new text object in the 3D viewport with optional layout frame"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if context.area is None or context.area.type != "VIEW_3D":
            cls.poll_message_set(_("Open a 3D Viewport and try again"))
            return False
        return True

    def execute(self, context):
        obj = _add_text_object(context)
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
    bl_description = "Clear all characters from the active text object"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = get_active_text(context)
        if obj is None:
            return {"CANCELLED"}
        if is_vertical(obj.data):
            clear_vertical_content(obj.data, context=context)
        else:
            obj.data.body = ""
            obj.data.update_tag()
            sync_panel_textbox_from_canonical(obj.data, vertical=False, context=context, flip_active=True)
        return {"FINISHED"}


class TH_OT_paste_body(ActiveFontDataPollMixin, Operator):
    bl_idname = "font.texthelper_paste_body"
    bl_label = "Paste into Text"
    bl_description = "Replace text content with the system clipboard"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from ..utils.text_limits import (
            assign_text_body,
            clamp_clipboard_text,
            text_body_max_len,
            text_was_truncated,
        )

        obj = get_active_text(context)
        if obj is None:
            return {"CANCELLED"}
        clip = context.window_manager.clipboard or ""
        raw = clamp_clipboard_text(clip, context=context)
        if text_was_truncated(clip, raw):
            self.report({"INFO"}, _("Text truncated to {:d} characters (limit)").format(text_body_max_len(context)))
        if is_vertical(obj.data):
            set_vertical_source(obj.data, raw, context=context)
        else:
            assign_text_body(obj.data, raw, context=context)
            sync_panel_textbox_from_canonical(obj.data, vertical=False, context=context, flip_active=True)
        return {"FINISHED"}


class TH_OT_import_txt(ActiveFontDataPollMixin, Operator):
    bl_idname = "font.texthelper_import_txt"
    bl_label = "Import Text File"
    bl_description = "Load text from a .txt file into the active text object"
    bl_options = {"REGISTER", "UNDO"}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        from ..utils.text_limits import (
            assign_text_body,
            clamp_multiline_text,
            text_body_max_len,
            text_was_truncated,
        )

        obj = get_active_text(context)
        if obj is None:
            return {"CANCELLED"}
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                clip = f.read()
            raw = clamp_multiline_text(clip, context=context)
            if text_was_truncated(clip, raw):
                self.report({"INFO"}, _("Text truncated to {:d} characters (limit)").format(text_body_max_len(context)))
            if is_vertical(obj.data):
                set_vertical_source(obj.data, raw, context=context)
            else:
                assign_text_body(obj.data, raw, context=context)
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
        from ..utils.text_format import iter_selected_font_objects

        applied = False
        for obj in iter_selected_font_objects(context):
            apply_text_case(obj.data, self.case)
            applied = True
        if not applied:
            return {"CANCELLED"}
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
