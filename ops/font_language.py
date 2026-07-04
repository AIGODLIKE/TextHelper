"""Font language filter menu and operator."""

import bpy
from bpy.types import Menu, Operator

from ..i18n import _
from ..utils.addon_prefs import prefs_bl_idname
from ..utils.font_language import LANGUAGE_FILTER_ITEMS, get_language_filter, invalidate_font_language_cache
from ..utils.operator_poll import PreferencesPollMixin, WindowManagerPollMixin
from ..utils.text_frame import tag_view3d_redraw


class TH_OT_set_font_language(WindowManagerPollMixin, Operator):
    bl_idname = "font.texthelper_set_font_language"
    bl_label = "Set Font Language Filter"
    bl_description = "Filter the font list by script or language"
    bl_options = {"INTERNAL"}

    language: bpy.props.EnumProperty(items=LANGUAGE_FILTER_ITEMS)

    def execute(self, context):
        from ..utils.font_language import normalize_language_code

        wm = context.window_manager
        wm.th_state.font_language = normalize_language_code(self.language)
        state = getattr(wm, "th_state", None)
        if state is not None:
            state.th_font_picker_scroll = 0
            if getattr(state, "th_language_picker_open", False):
                from ..hud.language_picker import close_picker

                close_picker(context)
        invalidate_font_language_cache()
        from ..utils.font_preview import tag_ui_redraw
        from ..hud.draw import tag_redraw

        tag_ui_redraw(context)
        tag_view3d_redraw(context)
        tag_redraw()
        return {"FINISHED"}


class TH_OT_open_addon_preferences(PreferencesPollMixin, Operator):
    bl_idname = "font.texthelper_open_addon_preferences"
    bl_label = "Text Helper Preferences"
    bl_description = "Open Text Helper add-on preferences"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        module = prefs_bl_idname()
        for candidate in (module, "bl_ext.user_default.TextHelper", "TextHelper"):
            if candidate in context.preferences.addons:
                module = candidate
                break
        bpy.ops.preferences.addon_show(module=module)
        return {"FINISHED"}


class TEXTHELPER_MT_font_language(Menu):
    bl_idname = "TEXTHELPER_MT_font_language"
    bl_label = "Language"

    def draw(self, context):
        wm = context.window_manager
        current = get_language_filter(wm)
        layout = self.layout
        for code, label, _desc in LANGUAGE_FILTER_ITEMS:
            text = _(label)
            if current == code:
                text = f"✓ {text}"
            op = layout.operator("font.texthelper_set_font_language", text=text)
            op.language = code


classes = (
    TH_OT_set_font_language,
    TH_OT_open_addon_preferences,
    TEXTHELPER_MT_font_language,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
