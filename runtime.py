"""Lazy viewport runtime (draw handler + modal) — not started at addon register."""

from __future__ import annotations

_draw_registered = False
_ensure_timer = None


def is_draw_registered() -> bool:
    return _draw_registered


def ensure(context=None):
    """Register the HUD draw handler and start the modal when a text object is active."""
    global _draw_registered

    import bpy

    from .sync import ensure_subscribers
    from .hud.draw import register as register_draw
    from .utils.text_format import get_active_text

    ensure_subscribers()

    ctx = context or bpy.context
    if get_active_text(ctx) is None:
        return False

    from .hud.hit_test import hud_enabled

    if not hud_enabled(ctx):
        return False

    if not _draw_registered:
        register_draw()
        _draw_registered = True

    from .utils.font_loader import prefetch_font_catalog

    prefetch_font_catalog(ctx)

    return ensure_all_windows(ctx)


def request_ensure(context=None):
    """Schedule HUD startup outside restricted contexts (e.g. panel poll)."""
    global _ensure_timer

    import bpy

    from .ops.hud_modal import modal_running, sync_modal_running_state
    from .sync import ensure_subscribers
    from .utils.text_format import get_active_text

    ensure_subscribers()

    ctx = context or bpy.context
    sync_modal_running_state(ctx)

    if get_active_text(ctx) is None:
        return

    from .hud.hit_test import hud_enabled

    if not hud_enabled(ctx):
        return

    if modal_running(ctx) and _draw_registered:
        return

    if _ensure_timer is not None:
        return

    def _deferred():
        global _ensure_timer
        _ensure_timer = None
        ensure(ctx)
        return None

    _ensure_timer = _deferred
    bpy.app.timers.register(_deferred, first_interval=0.0)


def _ensure_modal(context):
    import bpy

    from .ops.hud_modal import modal_running, sync_modal_running_state

    sync_modal_running_state(context)
    if modal_running(context):
        return True

    try:
        bpy.ops.wm.texthelper_hud_ensure_modal()
    except Exception:
        return False

    sync_modal_running_state(context)
    return modal_running(context)


def ensure_all_windows(context=None):
    """Ensure one HUD modal per Blender window that can show the HUD."""
    import bpy

    from .hud.hit_test import hud_enabled
    from .ops.hud_modal import modal_running, sync_modal_running_state
    from .utils.text_format import get_active_text
    from .utils.view3d_context import find_view3d_area_region

    base = context or bpy.context
    started = False
    for window in bpy.context.window_manager.windows:
        area, region = find_view3d_area_region(window)
        if area is None or region is None:
            continue
        override = base.temp_override(
            window=window,
            screen=window.screen,
            area=area,
            region=region,
            space_data=area.spaces.active,
            region_data=region.data,
        )
        with override:
            ctx = bpy.context
            if get_active_text(ctx) is None or not hud_enabled(ctx):
                continue
            sync_modal_running_state(ctx)
            if modal_running(ctx):
                continue
            try:
                bpy.ops.wm.texthelper_hud_modal("INVOKE_DEFAULT")
                started = True
            except Exception:
                pass
    return started


def shutdown():
    """Tear down viewport runtime on addon unregister."""
    global _draw_registered, _ensure_timer

    import bpy

    from .hud.draw import unregister as unregister_draw
    from .hud.font_picker import close_picker as close_font_picker
    from .hud.preset_picker import close_picker as close_preset_picker
    from .hud.weight_picker import close_picker as close_weight_picker
    from .hud.language_picker import close_picker as close_language_picker

    if _ensure_timer is not None:
        try:
            bpy.app.timers.unregister(_ensure_timer)
        except Exception:
            pass
        _ensure_timer = None

    try:
        ctx = bpy.context
        if ctx is None or not hasattr(ctx, "window_manager"):
            ctx = None
    except Exception:
        ctx = None

    close_font_picker(ctx)
    close_weight_picker(ctx)
    close_preset_picker(ctx)
    close_language_picker(ctx)

    if _draw_registered:
        unregister_draw()
        _draw_registered = False
