import bpy
from bpy.types import Operator, Menu

from ..i18n import _
from ..hud.draw import tag_redraw
from ..utils.operator_poll import ActiveFontDataPollMixin
from ..utils.text_format import STYLE_PRESETS, apply_preset, get_active_text_data


class TEXTHELPER_MT_style_preset(Menu):
    bl_label = "Text Style Preset"
    bl_idname = "TEXTHELPER_MT_style_preset"

    def draw(self, context):
        layout = self.layout
        text_data = get_active_text_data(context)
        for key, preset in STYLE_PRESETS.items():
            label = _(preset["label"])
            if text_data and text_data.text_helper.th_preset == key:
                label = f"✓ {label}"
            op = layout.operator("font.texthelper_apply_preset", text=label)
            op.preset_id = key


class TH_OT_apply_preset(ActiveFontDataPollMixin, Operator):
    bl_idname = "font.texthelper_apply_preset"
    bl_label = "Apply Text Preset"
    bl_description = "Apply a typography preset to font size, spacing, and alignment"
    bl_options = {"REGISTER", "UNDO"}

    preset_id: bpy.props.StringProperty(default="BODY")
    keep_picker_open: bpy.props.BoolProperty(default=False, options={"HIDDEN"})

    def execute(self, context):
        text_data = get_active_text_data(context)
        if text_data is None:
            return {"CANCELLED"}
        state = getattr(context.window_manager, "th_state", None)
        if state is not None:
            state.th_hud_open_menu = ""
            if not self.keep_picker_open and getattr(state, "th_preset_picker_open", False):
                from ..hud.preset_picker import close_picker

                close_picker(context)
        result = apply_preset(context, self.preset_id)
        if "FINISHED" in result:
            text_data.text_helper.th_preset = self.preset_id
        if self.keep_picker_open and "FINISHED" in result:
            from ..utils.text_frame import tag_view3d_redraw
            from ..hud.draw import tag_redraw

            tag_view3d_redraw(context)
            tag_redraw()
        return result


class TH_OT_toggle_preset_picker(ActiveFontDataPollMixin, Operator):
    bl_idname = "font.texthelper_toggle_preset_picker"
    bl_label = "Style Preset Picker"
    bl_description = "Open or close the viewport GPU style preset picker"
    bl_options = {"REGISTER"}

    def execute(self, context):
        if get_active_text_data(context) is None:
            self.report({"WARNING"}, _("Select a text object first"))
            return {"CANCELLED"}

        wm = context.window_manager
        state = getattr(wm, "th_state", None)
        if state is None:
            return {"CANCELLED"}

        opening = not getattr(state, "th_preset_picker_open", False)

        if not opening:
            from ..hud.preset_picker import close_picker

            close_picker(context)
            tag_redraw()
            return {"FINISHED"}

        from ..hud.font_picker import close_picker as close_font_picker
        from ..hud.preset_picker import close_picker, seed_picker_hover_apply
        from ..ops.hud_modal import _dismiss_popup_menus

        close_font_picker(context)
        from ..hud.weight_picker import close_picker as close_weight_picker

        close_weight_picker(context)
        state.th_hud_open_menu = ""
        _dismiss_popup_menus(context)
        state.th_preset_picker_open = True
        seed_picker_hover_apply(context)
        bpy.ops.wm.texthelper_hud_ensure_modal()
        tag_redraw()
        return {"FINISHED"}


classes = (
    TEXTHELPER_MT_style_preset,
    TH_OT_apply_preset,
    TH_OT_toggle_preset_picker,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
