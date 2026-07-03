"""Viewport sync: redraw on text edits and lazy HUD startup on selection."""

import bpy

_MSG_BUS_OWNER = object()


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


def register():
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


def unregister():
    bpy.msgbus.clear_by_owner(_MSG_BUS_OWNER)

    if _load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_load_post)
