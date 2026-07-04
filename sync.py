"""Viewport sync: redraw on text edits and lazy HUD startup on selection."""

import bpy

_MSG_BUS_OWNER = object()
_subscribers_active = False


def _on_text_changed():
    context = bpy.context
    if context.window is None:
        return

    from .utils.text_format import get_active_text
    from .utils.text_case import sync_live_text_case

    obj = get_active_text(context)
    if obj is not None:
        sync_live_text_case(obj.data)

    for area in context.window.screen.areas:
        if area.type == "VIEW_3D":
            area.tag_redraw()


def _on_active_object_changed():
    from .runtime import request_ensure

    request_ensure()


@bpy.app.handlers.persistent
def _load_post(_dummy):
    def _deferred():
        from .runtime import request_ensure

        request_ensure()
        return None

    bpy.app.timers.register(_deferred, first_interval=0.1)


def ensure_subscribers():
    """Register msgbus and load_post when Text Helper is first used."""
    global _subscribers_active
    if _subscribers_active:
        return
    _subscribers_active = True

    bpy.msgbus.subscribe_rna(
        key=(bpy.types.TextCurve, "body"),
        owner=_MSG_BUS_OWNER,
        args=(),
        notify=_on_text_changed,
    )
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.LayerObjects, "active"),
        owner=_MSG_BUS_OWNER,
        args=(),
        notify=_on_active_object_changed,
    )

    if _load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_load_post)


def register():
    """Intentionally empty — subscribers attach lazily via ensure_subscribers()."""
    pass


def unregister():
    global _subscribers_active
    if not _subscribers_active:
        return

    bpy.msgbus.clear_by_owner(_MSG_BUS_OWNER)

    if _load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_load_post)

    _subscribers_active = False


def is_subscribers_active():
    return _subscribers_active
