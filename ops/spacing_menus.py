import bpy
from bpy.types import Menu

from ..utils.text_format import get_active_text_data, spacing_display_line


CHAR_SPACING_VALUES = (-50, -25, -10, 0, 10, 25, 50, 100, 150, 200)
LINE_HEIGHT_VALUES = (12, 16, 20, 24, 30, 36, 42, 48, 60, 72, 96)


class TEXTHELPER_MT_char_spacing(Menu):
    bl_label = "Character Spacing"
    bl_idname = "TEXTHELPER_MT_char_spacing"

    def draw(self, context):
        layout = self.layout
        text_data = get_active_text_data(context)
        from ..utils.text_format import spacing_display_char

        current = spacing_display_char(text_data.space_character) if text_data else 0
        for value in CHAR_SPACING_VALUES:
            label = str(value)
            if value == current:
                label = f"✓ {label}"
            op = layout.operator("font.texthelper_set_spacing_value", text=label)
            op.mode = "CHAR"
            op.value = value


class TEXTHELPER_MT_line_height(Menu):
    bl_label = "Line Height"
    bl_idname = "TEXTHELPER_MT_line_height"

    def draw(self, context):
        layout = self.layout
        text_data = get_active_text_data(context)
        current = spacing_display_line(text_data) if text_data else 30
        for value in LINE_HEIGHT_VALUES:
            label = str(value)
            if value == current:
                label = f"✓ {label}"
            op = layout.operator("font.texthelper_set_spacing_value", text=label)
            op.mode = "LINE"
            op.value = value


class TEXTHELPER_MT_word_spacing(Menu):
    bl_label = "Word Spacing"
    bl_idname = "TEXTHELPER_MT_word_spacing"

    def draw(self, context):
        layout = self.layout
        text_data = get_active_text_data(context)
        from ..utils.text_format import spacing_display_word

        current = spacing_display_word(text_data.space_word) if text_data else 0
        for value in CHAR_SPACING_VALUES:
            label = str(value)
            if value == current:
                label = f"✓ {label}"
            op = layout.operator("font.texthelper_set_spacing_value", text=label)
            op.mode = "WORD"
            op.value = value


classes = (
    TEXTHELPER_MT_char_spacing,
    TEXTHELPER_MT_word_spacing,
    TEXTHELPER_MT_line_height,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
