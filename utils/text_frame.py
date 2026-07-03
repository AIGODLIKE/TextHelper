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


def _bounds_from_object(obj):
    bb = obj.bound_box
    xs = [corner[0] for corner in bb]
    ys = [corner[1] for corner in bb]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    width = max(x1 - x0, 1.0)
    height = max(y1 - y0, 0.5)
    return x0, y0, width, height


def normalize_frame_size(obj, tb):
    """Ensure a text box has non-zero size (some ops leave 0×0 frames)."""
    if tb.width > 0.0 and tb.height > 0.0:
        return
    _x0, _y0, width, height = _bounds_from_object(obj)
    if tb.width <= 0.0:
        tb.width = width
    if tb.height <= 0.0:
        tb.height = height


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
    if len(text_data.text_boxes) > count_before:
        _x0, _y0, width, height = _bounds_from_object(obj)
        if tb.width <= 0.0:
            tb.width = width
        if tb.height <= 0.0:
            tb.height = height
    normalize_frame_size(obj, tb)
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
        tb = text_data.text_boxes[0]
        normalize_frame_size(obj, tb)
        text_data.update_tag()
        return tb
    return add_layout_frame(context, obj)
