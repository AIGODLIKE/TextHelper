"""Screen-space bounds for FONT objects and HUD safe-area clamping."""

from mathutils import Vector
from bpy_extras import view3d_utils

from .addon_prefs import get_addon_prefs
from .hud_offset import get_hud_offset, set_hud_offset
from ..hud.layout import slider_row_height


def _hud_ui_scale(context):
    prefs = get_addon_prefs(context)
    hud_scale = getattr(prefs, "hud_scale", 0.8) if prefs else 0.8
    return max(context.preferences.system.ui_scale, 0.5) * hud_scale


def _region_overlap_window_local(window, reg):
    """Intersection of a sibling region with WINDOW, in WINDOW-local pixels."""
    if window is None or reg is None or reg.width <= 0 or reg.height <= 0:
        return None

    wx0, wy0 = window.x, window.y
    wx1, wy1 = wx0 + window.width, wy0 + window.height
    rx0, ry0 = reg.x, reg.y
    rx1, ry1 = rx0 + reg.width, ry0 + reg.height

    if rx1 <= wx0 or rx0 >= wx1 or ry1 <= wy0 or ry0 >= wy1:
        return None

    return (
        max(0.0, rx0 - wx0),
        max(0.0, ry0 - wy0),
        min(float(window.width), rx1 - wx0),
        min(float(window.height), ry1 - wy0),
    )


def _window_region_insets(context):
    """Insets inside WINDOW from overlapping toolbars, N-panel, headers, and footer."""
    window = context.region
    area = context.area
    if window is None or area is None or window.type != "WINDOW":
        return 0.0, 0.0, 0.0, 0.0

    left = right = bottom = top = 0.0

    for reg in area.regions:
        if reg == window or reg.width <= 0 or reg.height <= 0:
            continue

        overlap = _region_overlap_window_local(window, reg)
        if overlap is None:
            continue

        ox0, oy0, ox1, oy1 = overlap
        edge_epsilon = 1.0

        if reg.type in {"TOOLS", "UI"}:
            # screen.region_flip can place either region on either side.
            # Infer the occupied edge from its actual WINDOW overlap instead
            # of assuming TOOLS=left and UI=right.
            if ox0 <= edge_epsilon:
                left = max(left, ox1)
            if ox1 >= window.width - edge_epsilon:
                right = max(right, window.width - ox0)
            continue

        if reg.type in {"HEADER", "TOOL_HEADER"}:
            # Headers may likewise be flipped between the top and bottom.
            if oy0 <= edge_epsilon:
                bottom = max(bottom, oy1)
            if oy1 >= window.height - edge_epsilon:
                top = max(top, window.height - oy0)
            continue

        # Bottom timeline strip in the same area — user allows HUD flush to window bottom.
        if reg.type in {"FOOTER", "HUD"}:
            continue

    return left, bottom, right, top


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


def get_hud_safe_bounds(context, scale=None):
    """Safe rectangle inside the 3D View WINDOW region: (x_min, y_min, x_max, y_max)."""
    window = context.region
    if window is None:
        return None

    if scale is None:
        scale = _hud_ui_scale(context)

    prefs = get_addon_prefs(context)
    margin = float(getattr(prefs, "hud_safe_margin", 10.0) or 10.0)

    inset_left, inset_bottom, inset_right, inset_top = _window_region_insets(context)

    x_min = inset_left + margin
    x_max = window.width - inset_right - margin
    y_min = inset_bottom + margin
    y_max = window.height - inset_top - margin

    if x_max <= x_min:
        x_max = x_min + 1.0
    if y_max <= y_min:
        y_max = y_min + 1.0
    return x_min, y_min, x_max, y_max


def clamp_popup_to_hud_safe_bounds(context, x, y, width, height, scale=None):
    """Clamp a HUD popup rectangle to the same safe area as the toolbar."""
    safe = get_hud_safe_bounds(context, scale)
    if safe is None:
        return x, y
    x_min, y_min, x_max, y_max = safe
    max_x = max(x_min, x_max - width)
    max_y = max(y_min, y_max - height)
    return (
        max(x_min, min(float(x), max_x)),
        max(y_min, min(float(y), max_y)),
    )


def default_toolbar_anchor(context, offset_px=12.0, scale=None):
    """Top-center anchor without per-object drag offset."""
    region = context.region
    if region is None:
        return None

    if scale is None:
        scale = _hud_ui_scale(context)

    bar_h = slider_row_height(scale)
    draw_pad = 4.0 * scale
    top_gap = max(float(offset_px), 14.0 * scale)
    x = region.width * 0.5
    y = region.height - top_gap - bar_h - draw_pad
    return x, y


def get_toolbar_anchor(context, obj, offset_px=12.0):
    """HUD anchor fixed near the top-center of the 3D View region."""
    region = context.region
    if region is None:
        return None

    scale = _hud_ui_scale(context)
    default = default_toolbar_anchor(context, offset_px, scale)
    if default is None:
        return None

    user_ox, user_oy = get_hud_offset(obj)
    return default[0] + user_ox, default[1] + user_oy


def hud_offset_from_anchor(context, anchor_x, anchor_y, offset_px=12.0, scale=None):
    default = default_toolbar_anchor(context, offset_px, scale)
    if default is None:
        return 0.0, 0.0
    return float(anchor_x) - default[0], float(anchor_y) - default[1]


def clamp_anchor_for_layout(anchor_x, anchor_y, layout, safe):
    from ..hud.layout import row_bounds

    if safe is None:
        return anchor_x, anchor_y

    bounds = row_bounds(layout.get("rects") or [], pad=2.0)
    if bounds is None:
        return anchor_x, anchor_y

    bx, by, bw, bh = bounds
    x_min, y_min, x_max, y_max = safe
    dx = dy = 0.0
    if bx < x_min:
        dx = x_min - bx
    elif bx + bw > x_max:
        dx = x_max - (bx + bw)
    if by < y_min:
        dy = y_min - by
    elif by + bh > y_max:
        dy = y_max - (by + bh)
    return anchor_x + dx, anchor_y + dy


def resolve_hud_layout(context, obj, text_data, *, toolbar_offset=None):
    """Layout toolbar rects with anchor clamped inside the viewport safe area."""
    from ..hud.layout import layout_toolbar

    if context.region is None or text_data is None:
        return None

    prefs = get_addon_prefs(context)
    if prefs is None:
        return None

    if toolbar_offset is None:
        toolbar_offset = prefs.toolbar_offset

    scale = _hud_ui_scale(context)
    anchor = get_toolbar_anchor(context, obj, toolbar_offset)
    if anchor is None:
        return None

    layout = layout_toolbar(anchor[0], anchor[1], scale, text_data, context)
    safe = get_hud_safe_bounds(context, scale)
    ax, ay = clamp_anchor_for_layout(anchor[0], anchor[1], layout, safe)
    if abs(ax - anchor[0]) > 1e-6 or abs(ay - anchor[1]) > 1e-6:
        anchor = (ax, ay)
        layout = layout_toolbar(ax, ay, scale, text_data, context)

    return {"anchor": anchor, "layout": layout, "scale": scale}


def clamp_hud_drag_offset(context, obj, text_data, offset_x, offset_y, *, toolbar_offset=None):
    """Apply a drag offset and clamp it so the full HUD stays inside the safe area."""
    set_hud_offset(obj, offset_x, offset_y)
    resolved = resolve_hud_layout(context, obj, text_data, toolbar_offset=toolbar_offset)
    if resolved is None:
        return offset_x, offset_y

    prefs = get_addon_prefs(context)
    top_offset = toolbar_offset if toolbar_offset is not None else prefs.toolbar_offset
    ox, oy = hud_offset_from_anchor(
        context,
        resolved["anchor"][0],
        resolved["anchor"][1],
        top_offset,
        resolved["scale"],
    )
    set_hud_offset(obj, ox, oy)
    return ox, oy
