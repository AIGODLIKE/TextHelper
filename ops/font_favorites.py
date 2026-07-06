"""Toggle favorite font families."""

import bpy
from bpy.types import Operator

from ..i18n import _
from ..utils.font_favorites import toggle_family_favorite
from ..utils.font_preview import tag_ui_redraw
from ..utils.operator_poll import WindowManagerPollMixin
from ..utils.text_frame import tag_view3d_redraw
from ..hud.draw import tag_redraw


class TH_OT_toggle_font_favorite(WindowManagerPollMixin, Operator):
    bl_idname = "font.texthelper_toggle_font_favorite"
    bl_label = "Toggle Font Favorite"
    bl_description = "Add or remove this font family from favorites"
    bl_options = {"REGISTER", "UNDO"}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    keep_picker_open: bpy.props.BoolProperty(default=False, options={"HIDDEN"})

    def execute(self, context):
        if not self.filepath:
            return {"CANCELLED"}
        favorited = toggle_family_favorite(context, self.filepath)
        tag_view3d_redraw(context)
        tag_ui_redraw(context)
        tag_redraw()
        if favorited:
            self.report({"INFO"}, _("Added to favorites"))
        else:
            self.report({"INFO"}, _("Removed from favorites"))
        return {"FINISHED"}


classes = (TH_OT_toggle_font_favorite,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
