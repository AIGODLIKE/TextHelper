"""Find a usable 3D View area/region for operators and HUD."""

from contextlib import contextmanager


def find_view3d_area_region(window=None):
    if window is None:
        import bpy

        window = bpy.context.window
    if window is None:
        return None, None
    for area in window.screen.areas:
        if area.type != "VIEW_3D":
            continue
        for region in area.regions:
            if region.type == "WINDOW":
                return area, region
    return None, None


def _point_in_area_region(area, region, mouse_x, mouse_y):
    if area is None or region is None or region.width <= 0 or region.height <= 0:
        return False
    left = area.x + region.x
    bottom = area.y + region.y
    right = left + region.width
    top = bottom + region.height
    return left <= mouse_x < right and bottom <= mouse_y < top


def area_region_at_mouse(window, mouse_x, mouse_y):
    """Return the topmost-like (area, region) under window-space mouse coordinates."""
    if window is None:
        return None, None
    for area in window.screen.areas:
        for region in reversed(area.regions):
            if _point_in_area_region(area, region, mouse_x, mouse_y):
                return area, region
    return None, None


def hud_pointer_context(context):
    """True when the event should use 3D View WINDOW region coordinates."""
    area = context.area
    region = context.region
    if area is None or region is None:
        return False
    return area.type == "VIEW_3D" and region.type == "WINDOW"


def mouse_in_view3d_ui(window, mouse_x, mouse_y):
    area, region = area_region_at_mouse(window, mouse_x, mouse_y)
    return area is not None and area.type == "VIEW_3D" and region is not None and region.type == "UI"


def mouse_in_view3d_window(window, mouse_x, mouse_y):
    """True when the cursor is inside the 3D View main WINDOW region."""
    if mouse_in_view3d_ui(window, mouse_x, mouse_y):
        return False
    area, region = find_view3d_area_region(window)
    return _point_in_area_region(area, region, mouse_x, mouse_y)


def view3d_window_mouse(event, window=None):
    """Map an event to 3D View WINDOW region coordinates."""
    if window is None:
        import bpy

        window = bpy.context.window
    area, region = find_view3d_area_region(window)
    if area is None or region is None or event is None:
        return None, None
    mx = event.mouse_x - area.x - region.x
    my = event.mouse_y - area.y - region.y
    return mx, my


def view3d_override(context):
    area, region = find_view3d_area_region(context.window)
    if area is None:
        return None
    return context.temp_override(
        window=context.window,
        screen=context.window.screen,
        area=area,
        region=region,
        space_data=area.spaces.active,
    )


@contextmanager
def view3d_region_context(context):
    """Run code with bpy.context.region set to the 3D View window region."""
    override = view3d_override(context)
    if override is None:
        yield False
        return
    with override:
        yield True


def active_font_override(context, obj=None):
    """temp_override for operators that need the active text object in a 3D View."""
    if obj is None:
        from .text_format import get_active_text

        obj = get_active_text(context)
    area, region = find_view3d_area_region(context.window)
    if area is None:
        return None
    kwargs = {
        "window": context.window,
        "screen": context.window.screen,
        "area": area,
        "region": region,
        "space_data": area.spaces.active,
    }
    if obj is not None:
        kwargs["object"] = obj
        kwargs["active_object"] = obj
    return context.temp_override(**kwargs)


def run_active_font_op(context, callback, obj=None):
    """Run callback inside a 3D View override with the active text object selected."""
    override = active_font_override(context, obj)
    if override is None:
        return False
    with override:
        callback()
    return True
