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


def _point_in_region(region, mouse_x, mouse_y):
    """True when a window-space point is inside a Region.

    In Blender both ``Region.x/y`` and ``Area.x/y`` are window-relative
    coordinates (pixels from the window bottom-left). ``Region.x`` already
    includes the owning area offset, so the region rectangle in window space is
    simply ``[region.x, region.x + region.width)``.
    """
    if region is None or region.width <= 0 or region.height <= 0:
        return False
    return (
        region.x <= mouse_x < region.x + region.width
        and region.y <= mouse_y < region.y + region.height
    )


def _point_in_area_region(area, region, mouse_x, mouse_y):
    return _point_in_region(region, mouse_x, mouse_y)


def _point_in_view3d_window_region(area, region, mouse_x, mouse_y):
    """True when a window-space point is inside a VIEW_3D WINDOW region."""
    return _point_in_region(region, mouse_x, mouse_y)


def _area_contains_point(area, mouse_x, mouse_y):
    if area is None:
        return False
    return area.x <= mouse_x < area.x + area.width and area.y <= mouse_y < area.y + area.height


def region_mouse_from_event(event, area, region):
    """Map window-space event coordinates to region-local pixels.

    ``Region.x/y`` are already window-relative, so region-local pixels are just
    ``event.mouse_x - region.x``. ``area`` is accepted for call-site
    compatibility but is intentionally unused.
    """
    if event is None or region is None:
        return None, None
    return event.mouse_x - region.x, event.mouse_y - region.y


def area_region_at_mouse(window, mouse_x, mouse_y):
    """Return the topmost-like (area, region) under window-space mouse coordinates."""
    if window is None:
        return None, None
    for area in reversed(window.screen.areas):
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
    return event.mouse_x - region.x, event.mouse_y - region.y


def context_view3d_window(context):
    """Return (area, region) when context already targets a 3D View WINDOW."""
    area = getattr(context, "area", None)
    region = getattr(context, "region", None)
    if area is None or region is None:
        return None, None
    if area.type != "VIEW_3D" or region.type != "WINDOW":
        return None, None
    return area, region


def view3d_window_region_for_area(area):
    if area is None or area.type != "VIEW_3D":
        return None
    for region in area.regions:
        if region.type == "WINDOW":
            return region
    return None


def iter_view3d_window_regions(window):
    """Yield each 3D View WINDOW region (supports split areas and quad view)."""
    if window is None:
        return
    for area in window.screen.areas:
        if area.type != "VIEW_3D":
            continue
        for region in area.regions:
            if region.type == "WINDOW" and region.width > 0 and region.height > 0:
                yield area, region


def viewport_key(area, region):
    if area is None or region is None:
        return None
    return area.as_pointer(), region.as_pointer()


def viewport_alive(window, area, region):
    """True while the bound 3D View WINDOW still exists on the screen."""
    if window is None or area is None or region is None:
        return False
    target = viewport_key(area, region)
    if target is None:
        return False
    for screen_area in window.screen.areas:
        if screen_area.as_pointer() != target[0]:
            continue
        for screen_region in screen_area.regions:
            if screen_region.as_pointer() == target[1]:
                return True
        return False
    return False


def viewport_owns_pointer(event, area, region, *, window=None):
    """True when the cursor is inside this 3D View WINDOW region."""
    if event is None or area is None or region is None:
        return False
    if window is not None and mouse_in_view3d_ui(window, event.mouse_x, event.mouse_y):
        area_hit, region_hit = area_region_at_mouse(window, event.mouse_x, event.mouse_y)
        if area_hit == area and region_hit is not None and region_hit.type == "UI":
            return False
    return _point_in_view3d_window_region(area, region, event.mouse_x, event.mouse_y)


def view3d_area_at_mouse(window, mouse_x, mouse_y):
    area, region = view3d_window_at_mouse(window, mouse_x, mouse_y)
    return area


def view3d_window_at_mouse(window, mouse_x, mouse_y):
    """Return the 3D View WINDOW (area, region) under window-space coordinates."""
    if window is None:
        return None, None
    for area in reversed(window.screen.areas):
        if area.type != "VIEW_3D":
            continue
        for region in area.regions:
            if region.type != "WINDOW" or region.width <= 0 or region.height <= 0:
                continue
            if _point_in_view3d_window_region(area, region, mouse_x, mouse_y):
                return area, region
    return None, None


def hud_region_pointer_coords(event, area, region, modal_area=None, modal_region=None, window=None):
    """Map an event to region-local pixels for HUD hit-testing.

    ``Region.x/y`` are window-relative, so ``event.mouse_x - region.x`` gives
    the correct region-local coordinates for *any* region under the cursor,
    regardless of split/quad layouts or which region the modal was invoked in.
    """
    return region_mouse_from_event(event, area, region)


def hud_pointer_target(event, window=None, context=None, modal_area=None, modal_region=None):
    """Resolve the VIEW_3D WINDOW under the cursor and region-local coordinates."""
    import bpy

    ctx = context or bpy.context
    if window is None:
        window = ctx.window
    if event is None or window is None:
        return None, None, None, None

    if mouse_in_view3d_ui(window, event.mouse_x, event.mouse_y):
        return None, None, None, None

    area, region = view3d_window_at_mouse(window, event.mouse_x, event.mouse_y)
    if area is not None and region is not None:
        mx, my = hud_region_pointer_coords(event, area, region, modal_area, modal_region, window)
        return area, region, mx, my

    area, region = context_view3d_window(ctx)
    if area is None or region is None:
        area, region = find_view3d_area_region(window)
    if area is not None and region is not None:
        mx, my = hud_region_pointer_coords(event, area, region, modal_area, modal_region, window)
        return area, region, mx, my
    return None, None, None, None


def view3d_area_count(window):
    if window is None:
        return 0
    return sum(1 for area in window.screen.areas if area.type == "VIEW_3D")


def event_view3d_window_target(event, window=None, context=None):
    """Resolve HUD pointer to the 3D View WINDOW under the cursor."""
    import bpy

    ctx = context or bpy.context
    if window is None:
        window = ctx.window
    if event is None or window is None:
        return None, None, None, None

    area, region = view3d_window_at_mouse(window, event.mouse_x, event.mouse_y)
    if area is not None and region is not None:
        mx, my = region_mouse_from_event(event, area, region)
        return area, region, mx, my

    area, region = context_view3d_window(ctx)
    if area is not None and region is not None:
        mx, my = region_mouse_from_event(event, area, region)
        return area, region, mx, my
    return None, None, None, None


def override_view3d_window(context, area=None, region=None, obj=None):
    """temp_override for the active or explicit 3D View WINDOW."""
    if area is None or region is None:
        area, region = context_view3d_window(context)
    if area is None or region is None:
        area, region = find_view3d_area_region(context.window)
    if area is None or region is None:
        return None
    kwargs = {
        "window": context.window,
        "screen": context.window.screen,
        "area": area,
        "region": region,
        "space_data": area.spaces.active,
        "region_data": region.data,
    }
    if obj is not None:
        from .text_format import iter_selected_font_objects

        selected = [o for o in iter_selected_font_objects(context)]
        if obj not in selected:
            selected.insert(0, obj)
        kwargs["object"] = obj
        kwargs["active_object"] = obj
        kwargs["selected_objects"] = selected
    return context.temp_override(**kwargs)


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
    override = override_view3d_window(context)
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
        from .text_format import iter_selected_font_objects

        selected = [o for o in iter_selected_font_objects(context)]
        if obj not in selected:
            selected.insert(0, obj)
        kwargs["object"] = obj
        kwargs["active_object"] = obj
        kwargs["selected_objects"] = selected
    return context.temp_override(**kwargs)


def run_active_font_op(context, callback, obj=None, *, undo=False):
    """Run callback inside a 3D View override with the active text object selected."""
    override = active_font_override(context, obj)
    if override is None:
        return False
    with override:
        if undo:
            from .undo import push_undo

            push_undo()
        callback()
    return True
