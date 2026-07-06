"""Helpers for Blender 5.2+ UILayout.textbox."""

import bpy

from ..i18n import _
from .addon_prefs import get_addon_prefs

_PANEL_BUF_PROPS = ("th_panel_buf_a", "th_panel_buf_b")

_module_sync_guard = False
_pending_panel_updates = {}
_timer_registered = False


def n_panel_textbox_lines(context=None):
    prefs = get_addon_prefs(context)
    return max(3, min(30, int(getattr(prefs, "n_panel_textbox_lines", 30) or 30)))


def _panel_buf_mode(vertical):
    return "V" if vertical else "H"


def _canonical_panel_text(text_data, vertical):
    if vertical:
        return getattr(text_data.text_helper, "th_vertical_source", "") or ""
    return text_data.body or ""


def _active_panel_buf_prop(text_helper):
    return _PANEL_BUF_PROPS[1 if getattr(text_helper, "th_panel_buf_active", False) else 0]


def _inactive_panel_buf_prop(text_helper):
    return _PANEL_BUF_PROPS[0 if getattr(text_helper, "th_panel_buf_active", False) else 1]


def _apply_panel_buf_to_text(text_data, text_helper, content, *, context=None):
    from .text_limits import assign_text_body, assign_vertical_source, clamp_multiline_text

    content = clamp_multiline_text(content, context=context)
    mode = getattr(text_helper, "th_panel_buf_mode", "")
    if mode == "V":
        assign_vertical_source(text_helper, content, context=context)
        return
    if text_data.body == content:
        return
    assign_text_body(text_data, content, context=context)


def _apply_deferred_panel_update(text_data, updates):
    global _module_sync_guard

    text_helper = text_data.text_helper
    _module_sync_guard = True
    try:
        for key, value in updates.items():
            setattr(text_helper, key, value)
    finally:
        _module_sync_guard = False


def _do_deferred_panel_update():
    global _timer_registered

    pending = dict(_pending_panel_updates)
    _pending_panel_updates.clear()

    for text_data_name, updates in pending.items():
        text_data = bpy.data.curves.get(text_data_name)
        if text_data is None or not hasattr(text_data, "text_helper"):
            continue
        try:
            _apply_deferred_panel_update(text_data, updates)
        except Exception:
            pass

    if _pending_panel_updates:
        return 0.0
    _timer_registered = False
    return None


def _queue_panel_update(text_data, updates):
    global _timer_registered

    key = text_data.name
    existing = _pending_panel_updates.get(key, {})
    existing.update(updates)
    _pending_panel_updates[key] = existing
    if not _timer_registered:
        _timer_registered = True
        bpy.app.timers.register(_do_deferred_panel_update, first_interval=0.0)


def _update_panel_buf(self, context, prop_name):
    global _module_sync_guard

    if _module_sync_guard:
        return
    if _active_panel_buf_prop(self) != prop_name:
        return
    text_data = self.id_data
    if text_data is None:
        return
    content = getattr(self, prop_name, "")
    mode = getattr(self, "th_panel_buf_mode", "")
    from .text_limits import clamp_multiline_text

    clamped = clamp_multiline_text(content, context=context)
    if clamped != content:
        _module_sync_guard = True
        try:
            setattr(self, prop_name, clamped)
        finally:
            _module_sync_guard = False
        content = clamped
    _apply_panel_buf_to_text(text_data, self, content, context=context)


def update_panel_buf_a(self, context):
    _update_panel_buf(self, context, "th_panel_buf_a")


def update_panel_buf_b(self, context):
    _update_panel_buf(self, context, "th_panel_buf_b")


def resolve_panel_textbox(text_data, context, *, vertical=False, visible_lines=None):
    """Pick a buffer property so each line-height pref gets a fresh textbox state."""
    from .text_limits import clamp_multiline_text

    text_helper = text_data.text_helper
    if visible_lines is None:
        lines = n_panel_textbox_lines(context)
    else:
        lines = max(3, int(visible_lines))
    mode = _panel_buf_mode(vertical)
    canonical = clamp_multiline_text(_canonical_panel_text(text_data, vertical), context=context)

    stored_lines = int(getattr(text_helper, "th_panel_buf_lines", 0) or 0)
    stored_mode = getattr(text_helper, "th_panel_buf_mode", "") or ""

    if stored_lines != lines or stored_mode != mode:
        inactive = _inactive_panel_buf_prop(text_helper)
        if not _module_sync_guard:
            _queue_panel_update(
                text_data,
                {
                    inactive: canonical,
                    "th_panel_buf_active": inactive == _PANEL_BUF_PROPS[1],
                    "th_panel_buf_lines": lines,
                    "th_panel_buf_mode": mode,
                },
            )
        return text_helper, inactive

    active = _active_panel_buf_prop(text_helper)
    if getattr(text_helper, active, "") != canonical:
        if not _module_sync_guard:
            _queue_panel_update(text_data, {active: canonical})
    return text_helper, active


def sync_panel_textbox_from_canonical(
    text_data,
    *,
    vertical=False,
    context=None,
    visible_lines=None,
    flip_active=False,
):
    """Push th_vertical_source / body into both panel textbox buffers immediately."""
    from .text_limits import clamp_multiline_text

    text_helper = text_data.text_helper
    canonical = clamp_multiline_text(_canonical_panel_text(text_data, vertical), context=context)
    if visible_lines is None:
        visible_lines = n_panel_textbox_lines(context)
    lines = max(3, int(visible_lines))

    global _module_sync_guard
    _module_sync_guard = True
    try:
        text_helper.th_panel_buf_a = canonical
        text_helper.th_panel_buf_b = canonical
        text_helper.th_panel_buf_lines = lines
        text_helper.th_panel_buf_mode = _panel_buf_mode(vertical)
        if flip_active:
            text_helper.th_panel_buf_active = not getattr(text_helper, "th_panel_buf_active", False)
    finally:
        _module_sync_guard = False


def _draw_layout_textbox(col, data, prop, *, visible_lines, placeholder=""):
    attempts = []
    if placeholder:
        attempts.append({"initial_visible_lines": visible_lines, "placeholder": placeholder})
    attempts.append({"initial_visible_lines": visible_lines})
    if placeholder:
        attempts.append({"placeholder": placeholder})
    attempts.append({})

    for kwargs in attempts:
        try:
            col.textbox(data, prop, **kwargs)
            return True
        except AttributeError:
            break
        except TypeError:
            continue

    col.label(text=_("Multi-line textbox requires Blender 5.2+"), icon="ERROR")
    col.prop(data, prop, text="")
    return False


def draw_multiline_field(layout, data, prop, *, context=None, placeholder="", visible_lines=None, vertical=False):
    """Draw a multi-line textbox when supported, otherwise a single-line fallback."""
    if visible_lines is None:
        visible_lines = n_panel_textbox_lines(context)

    if hasattr(data, "text_helper"):
        text_data = data
    elif hasattr(data, "id_data") and getattr(data, "id_data", None) is not None:
        text_data = data.id_data
    else:
        text_data = None

    if text_data is not None and hasattr(text_data, "text_helper"):
        data, prop = resolve_panel_textbox(
            text_data,
            context,
            vertical=vertical,
            visible_lines=int(visible_lines),
        )

    return _draw_layout_textbox(
        layout,
        data,
        prop,
        visible_lines=int(visible_lines),
        placeholder=placeholder,
    )


def unregister():
    global _timer_registered, _pending_panel_updates

    if _timer_registered:
        try:
            bpy.app.timers.unregister(_do_deferred_panel_update)
        except Exception:
            pass
    _timer_registered = False
    _pending_panel_updates.clear()
