"""Safe context for FONT object operations."""

from contextlib import contextmanager

import bpy

from .text_format import get_active_text
from .view3d_context import find_view3d_area_region

# Blender 5.x reports EDIT_TEXT; older builds used EDIT_FONT.
FONT_EDIT_MODE_IDS = frozenset({"EDIT_TEXT", "EDIT_FONT"})


def is_font_edit_mode_value(mode):
    return mode in FONT_EDIT_MODE_IDS


def is_font_edit_mode(context):
    """True when the active text object is being edited in the 3D viewport."""
    if context is None:
        return False
    if is_font_edit_mode_value(getattr(context, "mode", "")):
        return True
    if getattr(context, "edit_text", None) is not None:
        return True
    edit_obj = getattr(context, "edit_object", None)
    if edit_obj is not None and getattr(edit_obj, "type", "") == "FONT":
        return True
    obj = getattr(context, "active_object", None)
    if obj is not None and getattr(obj, "type", "") == "FONT" and getattr(obj, "mode", "") == "EDIT":
        return True
    return False


def ensure_text_font(text_data):
    """TextCurve operators require a linked VectorFont."""
    if text_data is None:
        return False
    if text_data.font is not None:
        return True
    default = bpy.data.fonts.get("Bfont")
    if default is None and bpy.data.fonts:
        default = bpy.data.fonts[0]
    if default is None:
        return False
    text_data.font = default
    return True


@contextmanager
def font_view3d_override(context, obj=None):
    """Yield True when a 3D View override is active for the text object."""
    if obj is None:
        obj = get_active_text(context)
    if obj is None:
        yield False
        return

    obj.select_set(True)
    context.view_layer.objects.active = obj
    area, region = find_view3d_area_region(context.window)
    if area is None:
        yield False
        return

    override = context.temp_override(
        window=context.window,
        screen=context.window.screen,
        area=area,
        region=region,
        space_data=area.spaces.active,
        object=obj,
        active_object=obj,
    )
    with override:
        yield True


def prepare_font_edit_ui(context):
    """Close floating toolbar overlays and sidebar-adjacent pickers during viewport text edit."""
    try:
        from ..hud.font_picker import close_picker as close_font_picker
        from ..hud.preset_picker import close_picker as close_preset_picker
        from ..hud.weight_picker import close_picker as close_weight_picker
        from ..hud.language_picker import close_picker as close_language_picker

        close_font_picker(context)
        close_weight_picker(context)
        close_preset_picker(context)
        close_language_picker(context)
    except Exception:
        pass
    try:
        from ..hud import layout as layout_mod

        layout_mod._LAST_RECTS = []
    except Exception:
        pass
    try:
        from .text_frame import tag_all_areas_redraw

        tag_all_areas_redraw(context)
    except Exception:
        pass


def enter_text_edit_mode(context, obj=None):
    """Enter Blender in-viewport text edit mode (EDIT_FONT)."""
    if obj is None:
        obj = get_active_text(context)
    if obj is None or obj.type != "FONT":
        return False
    if not ensure_text_font(obj.data):
        return False
    if is_font_edit_mode(context) and context.view_layer.objects.active == obj:
        return True

    from .text_orientation import is_vertical, sync_vertical_source_to_body

    prepare_font_edit_ui(context)

    if is_vertical(obj.data):
        sync_vertical_source_to_body(obj.data)

    area, region = find_view3d_area_region(context.window)
    if area is None:
        return False

    obj.select_set(True)
    context.view_layer.objects.active = obj
    override = context.temp_override(
        window=context.window,
        screen=context.window.screen,
        area=area,
        region=region,
        space_data=area.spaces.active,
        object=obj,
        active_object=obj,
        selected_objects=[obj],
    )
    with override:
        if not is_font_edit_mode(context):
            bpy.ops.object.mode_set(mode="EDIT")
    return is_font_edit_mode(context)


def exit_text_edit_mode(context, obj=None):
    """Leave in-viewport text edit mode."""
    if not is_font_edit_mode(context):
        return True
    if obj is None:
        obj = get_active_text(context)
    if obj is not None:
        from .text_orientation import is_vertical, sync_body_to_vertical_source

        if is_vertical(obj.data):
            sync_body_to_vertical_source(obj.data)
    with font_view3d_override(context, obj) as ok:
        if not ok:
            return False
        bpy.ops.object.mode_set(mode="OBJECT")
    return not is_font_edit_mode(context)


@contextmanager
def font_edit_mode(context, obj=None):
    """Enter EDIT_FONT inside a 3D View override; restore mode on exit."""
    if obj is None:
        obj = get_active_text(context)
    if obj is None:
        yield False
        return

    was_edit = is_font_edit_mode(context)
    prev_active = context.view_layer.objects.active

    with font_view3d_override(context, obj) as ok:
        if not ok:
            yield False
            return
        try:
            if not was_edit:
                bpy.ops.object.mode_set(mode="EDIT")
            yield is_font_edit_mode(context)
        finally:
            if not was_edit and is_font_edit_mode(context):
                bpy.ops.object.mode_set(mode="OBJECT")
            if prev_active is not None:
                context.view_layer.objects.active = prev_active


def run_font_operator(context, obj, callback):
    """Run callback() that calls bpy.ops.font.* inside valid override + edit mode."""
    with font_edit_mode(context, obj) as in_edit:
        if not in_edit:
            return False
        callback()
        return True
