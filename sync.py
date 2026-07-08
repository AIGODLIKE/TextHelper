"""Viewport sync: redraw on text edits and lazy HUD startup on selection."""

import bpy

_MSG_BUS_OWNER = object()
_subscribers_active = False
_history_handlers_active = False


def refresh_text_objects_after_history(context=None):
    """Re-sync Font curves and redraw after undo/redo."""
    from .utils.text_format import (
        iter_selected_font_objects,
        reapply_bold_if_active,
        sync_line_decoration,
    )
    from .utils.text_frame import tag_view3d_redraw

    ctx = context or bpy.context
    if ctx.window is None:
        return False

    updated = False
    for obj in iter_selected_font_objects(ctx):
        text_data = obj.data
        sync_line_decoration(text_data)
        reapply_bold_if_active(text_data)
        text_data.update_tag()
        obj.update_tag()
        updated = True

    if updated:
        tag_view3d_redraw(ctx)
        try:
            from .hud.draw import tag_redraw

            tag_redraw()
        except Exception:
            pass
    return updated


def _on_text_changed():
    context = bpy.context
    if context.window is None:
        return

    from .utils.text_format import get_active_text
    from .utils.text_case import sync_live_text_case

    obj = get_active_text(context)
    if obj is not None:
        from .utils.text_orientation import is_vertical, sync_body_to_vertical_source, sync_vertical_source_to_body

        if is_vertical(obj.data):
            sync_body_to_vertical_source(obj.data, context=context)
            sync_vertical_source_to_body(obj.data, context=context)
        else:
            from .utils.text_limits import assign_text_body, clamp_multiline_text

            body = obj.data.body or ""
            clamped = clamp_multiline_text(body, context=context)
            if clamped != body:
                assign_text_body(obj.data, clamped, context=context)
        sync_live_text_case(obj.data)

    for area in context.window.screen.areas:
        if area.type == "VIEW_3D":
            area.tag_redraw()


def _on_active_object_changed():
    from .runtime import request_ensure
    from .utils.font_loader import prefetch_font_catalog
    from .utils.text_format import get_active_text

    context = bpy.context
    obj = get_active_text(context)
    if obj is None:
        from .ops.hud_modal import sync_modal_running_state

        sync_modal_running_state(context)
        return

    if obj.type == "FONT":
        prefetch_font_catalog(context)

    request_ensure(context)


@bpy.app.handlers.persistent
def _undo_redo_post(_scene):
    refresh_text_objects_after_history()


@bpy.app.handlers.persistent
def _load_post(_dummy):
    def _deferred():
        from .runtime import request_ensure
        from .utils.font_loader import prefetch_font_catalog, reset_font_catalog_scan

        wm = bpy.context.window_manager
        if wm is not None and getattr(wm, "th_state", None) is not None:
            if len(wm.th_state.font_catalog) == 0:
                reset_font_catalog_scan()
        prefetch_font_catalog(bpy.context)
        request_ensure()
        return None

    bpy.app.timers.register(_deferred, first_interval=0.1)


def _register_history_handlers():
    global _history_handlers_active
    if _history_handlers_active:
        return
    for handler, bucket in (
        (_undo_redo_post, bpy.app.handlers.undo_post),
        (_undo_redo_post, bpy.app.handlers.redo_post),
    ):
        if handler not in bucket:
            bucket.append(handler)
    _history_handlers_active = True


def _unregister_history_handlers():
    global _history_handlers_active
    if not _history_handlers_active:
        return
    for handler, bucket in (
        (_undo_redo_post, bpy.app.handlers.undo_post),
        (_undo_redo_post, bpy.app.handlers.redo_post),
    ):
        if handler in bucket:
            bucket.remove(handler)
    _history_handlers_active = False


def ensure_subscribers():
    """Register msgbus, undo/redo, and load_post when Text Helper is first used."""
    global _subscribers_active
    if _subscribers_active:
        return
    _subscribers_active = True

    _register_history_handlers()

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

    def _bootstrap_hud():
        _on_active_object_changed()
        return None

    bpy.app.timers.register(_bootstrap_hud, first_interval=0.0)


def register():
    """Msgbus and undo/redo handlers attach lazily via ensure_subscribers()."""
    return


def unregister():
    global _subscribers_active

    if _subscribers_active:
        _unregister_history_handlers()

    if not _subscribers_active:
        return

    bpy.msgbus.clear_by_owner(_MSG_BUS_OWNER)

    if _load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_load_post)

    _subscribers_active = False


def is_subscribers_active():
    return _subscribers_active
