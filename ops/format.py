import bpy
from bpy.types import Operator

from ..i18n import _
from ..utils.operator_poll import ActiveFontDataPollMixin
from ..utils.text_format import (
    get_active_text_data,
    line_height_display_max,
    spacing_display_char,
    spacing_display_line,
    spacing_from_display_char,
    spacing_from_display_line,
    spacing_display_word,
    spacing_from_display_word,
)
from ..utils.text_frame import add_layout_frame, ensure_layout_frame, tag_view3d_redraw


class TH_OT_style_toggle(ActiveFontDataPollMixin, Operator):
    bl_idname = "font.texthelper_style_toggle"
    bl_label = "Toggle Text Style"
    bl_description = "Toggle bold, italic, underline, or strikethrough on selected text"
    bl_options = {"REGISTER", "UNDO"}

    style: bpy.props.EnumProperty(
        items=[
            ("BOLD", "Bold", ""),
            ("ITALIC", "Italic", ""),
            ("UNDERLINE", "Underline", ""),
            ("STRIKE", "Strikethrough", ""),
        ],
    )

    def execute(self, context):
        from ..utils.text_format import apply_format_to_range
        return apply_format_to_range(context, self.style)


class TH_OT_set_align(ActiveFontDataPollMixin, Operator):
    bl_idname = "font.texthelper_set_align"
    bl_label = "Set Text Alignment"
    bl_description = "Set horizontal text alignment (left, center, right, or justify)"
    bl_options = {"REGISTER", "UNDO"}

    align: bpy.props.EnumProperty(
        items=[
            ("LEFT", "Left", ""),
            ("CENTER", "Center", ""),
            ("RIGHT", "Right", ""),
            ("JUSTIFY", "Justify", ""),
        ],
        default="LEFT",
    )

    def execute(self, context):
        text_data = get_active_text_data(context)
        if text_data is None:
            return {"CANCELLED"}
        text_data.align_x = self.align
        text_data.update_tag()
        return {"FINISHED"}


class TH_OT_set_align_y(ActiveFontDataPollMixin, Operator):
    bl_idname = "font.texthelper_set_align_y"
    bl_label = "Set Vertical Alignment"
    bl_description = "Set vertical text alignment within the object bounds"
    bl_options = {"REGISTER", "UNDO"}

    align: bpy.props.EnumProperty(
        items=[
            ("TOP", "Top", ""),
            ("TOP_BASELINE", "Top Baseline", ""),
            ("CENTER", "Center", ""),
            ("BOTTOM_BASELINE", "Bottom Baseline", ""),
            ("BOTTOM", "Bottom", ""),
        ],
        default="TOP_BASELINE",
    )

    def execute(self, context):
        text_data = get_active_text_data(context)
        if text_data is None:
            return {"CANCELLED"}
        text_data.align_y = self.align
        text_data.update_tag()
        return {"FINISHED"}


class TH_OT_adjust_spacing(ActiveFontDataPollMixin, Operator):
    bl_idname = "font.texthelper_adjust_spacing"
    bl_label = "Adjust Spacing"
    bl_description = "Increase or decrease character, word, line, or paragraph spacing"
    bl_options = {"REGISTER", "UNDO"}

    mode: bpy.props.EnumProperty(
        items=[
            ("CHAR", "Character", ""),
            ("WORD", "Word", ""),
            ("LINE", "Line", ""),
            ("PARA", "Paragraph", ""),
        ],
    )
    delta: bpy.props.FloatProperty(default=1.0)

    def execute(self, context):
        text_data = get_active_text_data(context)
        if text_data is None:
            return {"CANCELLED"}
        if self.mode == "CHAR":
            cur = spacing_display_char(text_data.space_character)
            text_data.space_character = spacing_from_display_char(max(-50, min(200, cur + int(self.delta))))
        elif self.mode == "WORD":
            cur = spacing_display_word(text_data.space_word)
            text_data.space_word = spacing_from_display_word(max(-50, min(200, cur + int(self.delta))))
        elif self.mode == "LINE":
            cur = spacing_display_line(text_data)
            text_data.space_line = spacing_from_display_line(
                text_data,
                max(1, min(line_height_display_max(text_data), cur + int(self.delta))),
            )
        else:
            text_data.offset_y = max(0.0, min(10.0, text_data.offset_y + self.delta * 0.1))
        text_data.update_tag()
        return {"FINISHED"}


class TH_OT_set_spacing_value(ActiveFontDataPollMixin, Operator):
    bl_idname = "font.texthelper_set_spacing_value"
    bl_label = "Set Spacing Value"
    bl_description = "Set font size, spacing, shear, or strikethrough position to an exact value"
    bl_options = {"REGISTER", "UNDO"}

    mode: bpy.props.EnumProperty(
        items=[
            ("SIZE", "Size", ""),
            ("CHAR", "Character", ""),
            ("WORD", "Word", ""),
            ("SHEAR", "Shear", ""),
            ("LINE", "Line", ""),
            ("PARA", "Paragraph", ""),
            ("STRIKE_POS", "Strike Pos", ""),
        ],
    )
    value: bpy.props.FloatProperty(default=0.0)

    def execute(self, context):
        text_data = get_active_text_data(context)
        if text_data is None:
            return {"CANCELLED"}
        if self.mode == "SIZE":
            from ..utils.text_format import SIZE_SLIDER_MAX, SIZE_SLIDER_MIN

            text_data.size = max(SIZE_SLIDER_MIN, min(SIZE_SLIDER_MAX, float(self.value)))
        elif self.mode == "CHAR":
            text_data.space_character = spacing_from_display_char(int(self.value))
        elif self.mode == "WORD":
            text_data.space_word = spacing_from_display_word(int(self.value))
        elif self.mode == "SHEAR":
            from ..utils.text_format import SHEAR_SLIDER_MAX, SHEAR_SLIDER_MIN

            text_data.shear = max(SHEAR_SLIDER_MIN, min(SHEAR_SLIDER_MAX, float(self.value)))
        elif self.mode == "LINE":
            text_data.space_line = spacing_from_display_line(text_data, int(self.value))
        elif self.mode == "STRIKE_POS":
            from ..utils.text_format import apply_strike_position

            apply_strike_position(text_data, self.value)
        else:
            text_data.offset_y = self.value
        text_data.update_tag()
        return {"FINISHED"}


class TH_OT_reset_format_value(ActiveFontDataPollMixin, Operator):
    bl_idname = "font.texthelper_reset_format_value"
    bl_label = "Reset Format Value"
    bl_description = "Reset font size or spacing to the current style preset default"
    bl_options = {"REGISTER", "UNDO"}

    mode: bpy.props.EnumProperty(
        items=[
            ("SIZE", "Size", ""),
            ("CHAR", "Character", ""),
            ("WORD", "Word", ""),
            ("SHEAR", "Shear", ""),
            ("LINE", "Line", ""),
            ("PARA", "Paragraph", ""),
            ("STRIKE_POS", "Strike Pos", ""),
        ],
    )

    def execute(self, context):
        from ..utils.text_format import preset_format_defaults

        text_data = get_active_text_data(context)
        if text_data is None:
            return {"CANCELLED"}
        defaults = preset_format_defaults(text_data)
        if self.mode == "SIZE":
            text_data.size = defaults["size"]
        elif self.mode == "CHAR":
            text_data.space_character = defaults["space_character"]
        elif self.mode == "WORD":
            text_data.space_word = defaults["space_word"]
        elif self.mode == "SHEAR":
            text_data.shear = defaults["shear"]
        elif self.mode == "LINE":
            text_data.space_line = defaults["space_line"]
        elif self.mode == "STRIKE_POS":
            from ..utils.text_format import apply_strike_position, default_strike_position

            apply_strike_position(text_data, default_strike_position(text_data))
        else:
            text_data.offset_y = defaults["offset_y"]
        text_data.update_tag()
        tag_view3d_redraw(context)
        return {"FINISHED"}


class TH_OT_textbox_add(ActiveFontDataPollMixin, Operator):
    bl_idname = "font.texthelper_textbox_add"
    bl_label = "Add Text Frame"
    bl_description = "Add a layout frame for wrapping and truncating text"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        tb = add_layout_frame(context)
        if tb is None:
            self.report({"ERROR"}, _("Could not add layout frame — select a text object with a 3D View open"))
            return {"CANCELLED"}
        tag_view3d_redraw(context)
        return {"FINISHED"}


class TH_OT_overflow_toggle(ActiveFontDataPollMixin, Operator):
    bl_idname = "font.texthelper_overflow_toggle"
    bl_label = "Toggle Text Overflow"
    bl_description = "Toggle text overflow between clip and expand to fit"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        text_data = get_active_text_data(context)
        if text_data is None:
            return {"CANCELLED"}
        next_overflow = "TRUNCATE" if text_data.overflow == "NONE" else "NONE"
        if next_overflow == "NONE" and not text_data.text_boxes:
            ensure_layout_frame(context)
        text_data.overflow = next_overflow
        text_data.update_tag()
        tag_view3d_redraw(context)
        return {"FINISHED"}


classes = (
    TH_OT_style_toggle,
    TH_OT_set_align,
    TH_OT_set_align_y,
    TH_OT_adjust_spacing,
    TH_OT_set_spacing_value,
    TH_OT_reset_format_value,
    TH_OT_textbox_add,
    TH_OT_overflow_toggle,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
