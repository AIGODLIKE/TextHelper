import bpy
from bpy.types import Panel

from ..i18n import _
from ..utils.font_context import is_font_edit_mode
from ..utils.ui_textbox import draw_multiline_field
from ..utils.addon_prefs import get_addon_prefs
from ..utils.text_format import get_active_text
from ..utils.text_orientation import is_vertical, vertical_source_char_count
from ..utils.vertical_align_check import build_vertical_align_report, format_halfwidth_preview, has_convertible_chars


def _floating_toolbar_pressed(context, text_data=None):
    prefs = get_addon_prefs(context)
    if not getattr(prefs, "show_floating_toolbar", True):
        return False
    if text_data is not None:
        return getattr(text_data.text_helper, "th_hud_visible", True)
    return True


def _draw_panel_header(layout, context, text_data=None):
    layout.operator(
        "wm.texthelper_toggle_toolbar",
        text="",
        icon="OVERLAY",
        depress=_floating_toolbar_pressed(context, text_data),
    )
    layout.operator(
        "font.texthelper_open_addon_preferences",
        text="",
        icon="PREFERENCES",
    )


def _draw_vertical_align_warnings(layout, text_data):
    report = build_vertical_align_report(text_data)
    if not report["has_issues"]:
        return

    font_issues = report["font_issues"]
    if any(
        key in font_issues
        for key in ("proportional_cjk", "fill_width_mismatch", "latin_proportional")
    ):
        layout.label(text=_("Non-monospaced font — columns may misalign"), icon="ERROR")

    halfwidth = report["halfwidth_chars"]
    source = getattr(text_data.text_helper, "th_vertical_source", "") or ""
    if halfwidth:
        preview = format_halfwidth_preview(halfwidth)
        row = layout.row(align=True)
        if has_convertible_chars(source):
            fix_col = row.column(align=True)
            fix_col.ui_units_x = 2.0
            fix_col.ui_units_y = 2.0
            fix_col.operator(
                "font.texthelper_convert_vertical_fullwidth",
                text="",
                icon="MODIFIER",
            )
        row.label(text=_("Halfwidth characters: {}").format(preview))


def _draw_direction_row(layout, text_data):
    row = layout.row(align=True)
    orientation = getattr(text_data.text_helper, "th_text_orientation", "HORIZONTAL")
    row.operator(
        "font.texthelper_set_text_orientation",
        text=_("Horizontal"),
        depress=orientation == "HORIZONTAL",
    ).orientation = "HORIZONTAL"
    row.operator(
        "font.texthelper_set_text_orientation",
        text=_("Vertical"),
        depress=orientation == "VERTICAL",
    ).orientation = "VERTICAL"

    if orientation != "VERTICAL":
        return

    order = getattr(text_data.text_helper, "th_vertical_column_order", "RTL")
    row = layout.row(align=True)
    row.operator(
        "font.texthelper_set_column_order",
        text=_("Right to Left"),
        depress=order == "RTL",
    ).order = "RTL"
    row.operator(
        "font.texthelper_set_column_order",
        text=_("Left to Right"),
        depress=order == "LTR",
    ).order = "LTR"


def _draw_content_box(layout, context, text_data):
    col = layout.column(align=True)
    _draw_direction_row(col, text_data)

    vertical = is_vertical(text_data)

    if vertical:
        draw_multiline_field(col, text_data.text_helper, "th_vertical_source", context=context, vertical=True)
        _draw_vertical_align_warnings(col, text_data)
    else:
        draw_multiline_field(
            col,
            text_data,
            "body",
            context=context,
            placeholder=_("Type or paste multi-line text…"),
            vertical=False,
        )

    row = col.row(align=True)
    row.operator("font.texthelper_paste_body", text=_("Paste"), icon="PASTEDOWN")
    row.operator("font.texthelper_clear_body", text=_("Clear"), icon="X")

    if vertical:
        chars = vertical_source_char_count(text_data)
        source = getattr(text_data.text_helper, "th_vertical_source", "") or ""
        words = sum(1 for line in source.split("\n") if line.strip())
    else:
        chars = len(text_data.body)
        words = len(text_data.body.split()) if text_data.body else 0
    col.label(text=_("{:d} chars · {:d} words").format(chars, words))


class VIEW3D_PT_text_helper(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Text Helper"
    bl_label = "Text Helper"

    @classmethod
    def poll(cls, context):
        if get_active_text(context) is None:
            return False
        from ..runtime import request_ensure

        request_ensure()
        return True

    def draw_header(self, context):
        _draw_panel_header(self.layout, context, context.active_object.data)

    def draw(self, context):
        if is_font_edit_mode(context):
            layout = self.layout
            layout.label(text=_("Editing in viewport"), icon="INFO")
            layout.label(text=_("Double-click empty space to exit edit mode"))
            return
        _draw_content_box(self.layout, context, context.active_object.data)


class VIEW3D_PT_text_helper_empty(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Text Helper"
    bl_label = "Text Helper"

    @classmethod
    def poll(cls, context):
        return get_active_text(context) is None

    def draw_header(self, context):
        _draw_panel_header(self.layout, context)

    def draw(self, context):
        layout = self.layout
        layout.label(text=_("Select a text object to edit."))
        layout.operator("font.texthelper_text_add", text=_("Add Text"), icon="OUTLINER_OB_FONT")


classes = (
    VIEW3D_PT_text_helper,
    VIEW3D_PT_text_helper_empty,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
