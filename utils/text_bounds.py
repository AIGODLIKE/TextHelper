"""Screen-space bounds for FONT objects."""

from mathutils import Vector
from bpy_extras import view3d_utils

from .addon_prefs import get_addon_prefs
from ..hud.layout import slider_row_height


def get_text_screen_bounds(context, obj):
    """Return (x_min, y_min, x_max, y_max) in region pixels, or None."""
    if context.region is None or context.region_data is None:
        return None
    if obj is None or obj.type != "FONT":
        return None

    region = context.region
    region_3d = context.region_data
    coords = []
    for corner in obj.bound_box:
        world = obj.matrix_world @ Vector(corner)
        co = view3d_utils.location_3d_to_region_2d(region, region_3d, world)
        if co is not None:
            coords.append(co)

    if not coords:
        return None

    xs = [c.x for c in coords]
    ys = [c.y for c in coords]
    return min(xs), min(ys), max(xs), max(ys)


def point_in_text_screen_bounds(context, obj, mx, my, padding=6.0):
    """True when a screen point hits the text object's projected bounds."""
    bounds = get_text_screen_bounds(context, obj)
    if bounds is None:
        return False
    x_min, y_min, x_max, y_max = bounds
    return (x_min - padding) <= mx <= (x_max + padding) and (y_min - padding) <= my <= (y_max + padding)


def get_toolbar_anchor(context, obj, offset_px=12.0):
    """HUD anchor fixed near the top-center of the 3D View region."""
    region = context.region
    if region is None:
        return None

    prefs = get_addon_prefs(context)
    hud_scale = getattr(prefs, "hud_scale", 1.0) if prefs else 1.0
    scale = max(context.preferences.system.ui_scale, 0.5) * hud_scale
    bar_h = slider_row_height(scale)
    draw_pad = 4.0 * scale
    top_gap = max(float(offset_px), 14.0 * scale)

    text_data = obj.data if obj is not None else None
    user_ox = getattr(text_data.text_helper, "th_hud_offset_x", 0.0) if text_data else 0.0
    user_oy = getattr(text_data.text_helper, "th_hud_offset_y", 0.0) if text_data else 0.0

    x = region.width * 0.5 + user_ox
    y = region.height - top_gap - bar_h - draw_pad + user_oy
    return x, y
