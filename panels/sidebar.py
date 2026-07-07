import bpy
from bpy.types import Panel

from ..i18n import _
from ..utils.font_context import is_font_edit_mode
from ..utils.ui_textbox import draw_multiline_field
from ..utils.text_format import get_active_text
from ..utils.header_toolbar import floating_toolbar_pressed
from ..utils.text_orientation import is_vertical
from ..utils.vertical_align_check import (
    build_vertical_align_report,
    format_halfwidth_preview,
    has_convertible_chars,
    panel_source_text,
)

_BUTTON_ROW_SCALE_Y = 1.5
_PERF_HINT_CHAR_THRESHOLD = 200


def _draw_panel_header(layout, context, text_data=None):
    row = layout.row(align=True)
    row.scale_x = 0.92
    row.scale_y = 0.92
    row.operator(
        "wm.texthelper_toggle_toolbar",
        text="",
        icon="OVERLAY",
        depress=floating_toolbar_pressed(context, text_data),
    )
    row.operator(
        "font.texthelper_open_addon_preferences",
        text="",
        icon="PREFERENCES",
    )


def _char_count_text(chars, max_chars, words):
    return _("{:d} / {:d} chars · {:d} words").format(chars, max_chars, words)


def _text_stats(text_data, *, vertical, context=None):
    from ..utils.text_limits import multiline_char_count, text_body_max_len

    chars = multiline_char_count(text_data, vertical=vertical)
    max_chars = text_body_max_len(context)
    if vertical:
        source = getattr(text_data.text_helper, "th_vertical_source", "") or ""
        words = sum(1 for line in source.split("\n") if line.strip())
    else:
        words = len(text_data.body.split()) if text_data.body else 0
    return chars, max_chars, words


def _button_row(parent):
    row = parent.row(align=True)
    row.scale_y = _BUTTON_ROW_SCALE_Y
    return row


def _draw_orientation_row(layout, text_data):
    row = _button_row(layout)
    orientation = getattr(text_data.text_helper, "th_text_orientation", "HORIZONTAL")
    row.operator(
        "font.texthelper_set_text_orientation",
        text=_("Horizontal"),
        icon="ALIGN_LEFT",
        depress=orientation == "HORIZONTAL",
    ).orientation = "HORIZONTAL"
    row.operator(
        "font.texthelper_set_text_orientation",
        text=_("Vertical"),
        icon="SORT_ASC",
        depress=orientation == "VERTICAL",
    ).orientation = "VERTICAL"


def _draw_column_order_row(col, text_data):
    order = getattr(text_data.text_helper, "th_vertical_column_order", "RTL")
    row = _button_row(col)
    row.operator(
        "font.texthelper_set_column_order",
        text=_("Right to Left"),
        icon="BACK",
        depress=order == "RTL",
    ).order = "RTL"
    row.operator(
        "font.texthelper_set_column_order",
        text=_("Left to Right"),
        icon="FORWARD",
        depress=order == "LTR",
    ).order = "LTR"


def _draw_actions_row(col):
    row = _button_row(col)
    row.operator("font.texthelper_paste_body", text=_("Paste"), icon="PASTEDOWN")
    row.operator("font.texthelper_clear_body", text=_("Clear"), icon="TRASH")


def _draw_align_warnings(col, text_data, *, vertical):
    report = build_vertical_align_report(text_data)
    if not report["has_issues"]:
        return

    warn = col.column(align=True)
    warn.scale_y = 0.92

    if vertical:
        font_issues = report["font_issues"]
        if any(
            key in font_issues
            for key in ("proportional_cjk", "fill_width_mismatch", "latin_proportional")
        ):
            warn.label(text=_("Non-monospaced font — columns may misalign"), icon="ERROR")

    halfwidth = report["halfwidth_chars"]
    source = panel_source_text(text_data)
    if halfwidth:
        preview = format_halfwidth_preview(halfwidth)
        warn.label(text=_("Halfwidth characters: {}").format(preview), icon="WARNING_LARGE")
        if has_convertible_chars(source):
            fix_row = _button_row(warn)
            fix_row.operator(
                "font.texthelper_convert_vertical_fullwidth",
                text=_("Fix"),
                icon="SHADERFX",
            )


def _draw_footer(col, *, chars, max_chars, words):
    row = col.row(align=True)
    row.scale_y = 0.88
    row.label(text=_char_count_text(chars, max_chars, words))


def _draw_panel_status_hints(layout, *, chars, max_chars):
    if chars >= max_chars:
        message = _("Reached the configured character limit ({:d} characters).").format(max_chars)
    elif chars > _PERF_HINT_CHAR_THRESHOLD:
        message = _("Too many characters ({:d}) — performance may be reduced.").format(chars)
    else:
        return

    col = layout.column(align=True)
    col.scale_y = 0.9
    box = col.box()
    row = box.row()
    row.alert = True
    row.label(text=message, icon="ERROR")


def _draw_content_box(layout, context, text_data):
    vertical = is_vertical(text_data)
    chars, max_chars, words = _text_stats(text_data, vertical=vertical, context=context)

    plate = layout.box()
    col = plate.column(align=True)
    _draw_orientation_row(col, text_data)

    vertical = is_vertical(text_data)

    if vertical:
        draw_multiline_field(
            col,
            text_data.text_helper,
            "th_vertical_source",
            context=context,
            vertical=True,
        )
    else:
        draw_multiline_field(
            col,
            text_data,
            "body",
            context=context,
            placeholder=_("Type or paste multi-line text…"),
            vertical=False,
        )

    if vertical:
        _draw_column_order_row(col, text_data)

    _draw_actions_row(col)
    _draw_align_warnings(col, text_data, vertical=vertical)
    _draw_footer(col, chars=chars, max_chars=max_chars, words=words)

    return chars, max_chars


class VIEW3D_PT_text_helper(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Text Helper"
    bl_label = "Text Helper"
    bl_translation_context = "*"

    @classmethod
    def poll(cls, context):
        if get_active_text(context) is None:
            return False
        from ..sync import ensure_subscribers

        ensure_subscribers()
        return True

    def draw_header(self, context):
        _draw_panel_header(self.layout, context, context.active_object.data)

    def draw(self, context):
        if is_font_edit_mode(context):
            layout = self.layout
            layout.label(text=_("Editing in viewport"), icon="INFO")
            layout.label(text=_("Double-click empty space to exit edit mode"))
            return
        text_data = context.active_object.data
        chars, max_chars = _draw_content_box(self.layout, context, text_data)
        _draw_panel_status_hints(self.layout, chars=chars, max_chars=max_chars)


class VIEW3D_PT_text_helper_empty(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Text Helper"
    bl_label = "Text Helper"
    bl_translation_context = "*"

    @classmethod
    def poll(cls, context):
        from ..sync import ensure_subscribers

        ensure_subscribers()
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
