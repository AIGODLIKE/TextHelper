"""TextCurve layout frame (text_boxes) helpers."""

import bpy

from .font_context import font_edit_mode, ensure_text_font
from .text_format import get_active_text


def tag_view3d_redraw(context=None):
    wm = bpy.context.window_manager if context is None else context.window_manager
    for window in wm.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def tag_all_areas_redraw(context=None):
    wm = bpy.context.window_manager if context is None else context.window_manager
    for window in wm.windows:
        for area in window.screen.areas:
            area.tag_redraw()


def _reset_textbox_defaults(tb):
    """Default layout frame: zero size and zero offset (Blender Text Boxes panel)."""
    tb.width = 0.0
    tb.height = 0.0
    tb.x = 0.0
    tb.y = 0.0


def _run_textbox_add(context, obj):
    """Call bpy.ops.font.textbox_add with edit mode + 3D View context."""
    with font_edit_mode(context, obj) as in_edit:
        if not in_edit:
            return False
        if not bpy.ops.font.textbox_add.poll():
            return False
        return "FINISHED" in bpy.ops.font.textbox_add()


def add_layout_frame(context, obj=None):
    """Add a layout frame using Blender's font.textbox_add operator."""
    if obj is None:
        obj = get_active_text(context)
    if obj is None or obj.type != "FONT":
        return None
    if not ensure_text_font(obj.data):
        return None

    text_data = obj.data
    count_before = len(text_data.text_boxes)

    try:
        ok = _run_textbox_add(context, obj)
    except Exception:
        ok = False

    if not ok and len(text_data.text_boxes) <= count_before:
        return None

    if not text_data.text_boxes:
        return None

    tb = text_data.text_boxes[-1]
    _reset_textbox_defaults(tb)
    text_data.update_tag()
    obj.update_tag()
    return tb


def ensure_layout_frame(context, obj=None):
    """Return the first layout frame, creating one if missing."""
    if obj is None:
        obj = get_active_text(context)
    if obj is None or obj.type != "FONT":
        return None

    text_data = obj.data
    if text_data.text_boxes:
        return text_data.text_boxes[0]
    return add_layout_frame(context, obj)
