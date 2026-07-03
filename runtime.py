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

    from .hud.draw import register as register_draw
    from .utils.text_format import get_active_text

    ctx = context or bpy.context
    if get_active_text(ctx) is None:
        return False

    if not _draw_registered:
        register_draw()
        _draw_registered = True

    return _ensure_modal(ctx)


def request_ensure(context=None):
    """Schedule HUD startup outside restricted contexts (e.g. panel poll)."""
    global _ensure_timer

    import bpy

    from .utils.text_format import get_active_text

    ctx = context or bpy.context
    if get_active_text(ctx) is None:
        return

    if _ensure_timer is not None:
        return

    def _deferred():
        global _ensure_timer
        _ensure_timer = None
        ensure(None)
        return None

    _ensure_timer = _deferred
    bpy.app.timers.register(_deferred, first_interval=0.0)


def _ensure_modal(context):
    import bpy

    from .ops.hud_modal import modal_running

    if modal_running():
        return True

    try:
        bpy.ops.wm.texthelper_hud_ensure_modal()
    except Exception:
        return False

    return modal_running()


def shutdown():
    """Tear down viewport runtime on addon unregister."""
    global _draw_registered, _ensure_timer

    import bpy

    from .hud.draw import unregister as unregister_draw
    from .hud.font_picker import close_picker as close_font_picker
    from .hud.preset_picker import close_picker as close_preset_picker
    from .hud.language_picker import close_picker as close_language_picker

    if _ensure_timer is not None:
        try:
            bpy.app.timers.unregister(_ensure_timer)
        except Exception:
            pass
        _ensure_timer = None

    close_font_picker(bpy.context)
    close_preset_picker(bpy.context)
    close_language_picker(bpy.context)

    if _draw_registered:
        unregister_draw()
        _draw_registered = False
