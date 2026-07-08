"""Native text-input popup for the font picker search field.

Blender only activates the OS IME (e.g. Chinese Pinyin) inside its own native
text widgets. A custom GPU-drawn field running inside a modal operator can never
trigger IME composition, so CJK input is impossible there. This operator routes
search typing through a real Blender ``StringProperty`` field shown in a popup,
which has full IME support, and mirrors the text into the picker filter live.
"""

import bpy
from bpy.props import StringProperty
from bpy.types import Operator

from ..i18n import _
from ..utils.operator_poll import TextHelperOperatorMixin


def _apply_query(context, raw):
    from ..hud.font_picker import _sanitize_field_text

    wm = context.window_manager
    state = getattr(wm, "th_state", None)
    if state is None:
        return
    state.font_filter = _sanitize_field_text(raw, max_len=128)
    state.th_font_picker_scroll = 0

    from ..hud.draw import tag_redraw
    from ..utils.text_frame import tag_view3d_redraw

    tag_view3d_redraw(context)
    tag_redraw()


class TH_OT_font_search_input(TextHelperOperatorMixin, Operator):
    bl_idname = "wm.texthelper_font_search_input"
    bl_label = "Search Fonts"
    bl_description = "Type to filter fonts (native field, supports IME / Chinese input)"
    bl_options = {"INTERNAL"}

    def _update(self, context):
        _apply_query(context, self.query)

    query: StringProperty(
        name="Search Fonts",
        description="Filter the system font list",
        options={"SKIP_SAVE", "TEXTEDIT_UPDATE"},
        update=_update,
    )

    def invoke(self, context, event):
        wm = context.window_manager
        state = getattr(wm, "th_state", None)
        self.query = state.font_filter if state is not None else ""
        return wm.invoke_props_dialog(self, width=320)

    def draw(self, context):
        layout = self.layout
        layout.label(text=_("Search fonts (IME supported)"))
        # Auto-focus the field so the user can switch to their IME and type
        # immediately; the candidate window then anchors to this native widget.
        layout.activate_init = True
        layout.prop(self, "query", text="", icon="VIEWZOOM")

    def execute(self, context):
        _apply_query(context, self.query)
        return {"FINISHED"}


def register():
    bpy.utils.register_class(TH_OT_font_search_input)


def unregister():
    bpy.utils.unregister_class(TH_OT_font_search_input)
