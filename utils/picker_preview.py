"""Reversible hover previews for font and style pickers.

Picker hover must never become an untracked edit.  A session snapshots every
selected TextCurve, applies lightweight RNA previews, then either restores the
snapshot on cancel or restores it immediately before the real UNDO operator is
executed.
"""

from __future__ import annotations

import bpy

_SESSIONS = {}

_FONT_ATTRS = ("font", "font_bold", "font_italic", "font_bold_italic")
_VALUE_ATTRS = (
    "size",
    "space_character",
    "space_word",
    "space_line",
    "shear",
    "underline_position",
)
_HELPER_ATTRS = (
    "th_preset",
    "th_pre_bold_size",
    "th_strike_enabled",
    "th_underline_enabled",
    "th_strike_position",
)
_FORMAT_ATTRS = ("use_bold", "use_italic", "use_underline")


def _window_session_key(window):
    if window is None:
        return None
    try:
        return ("WINDOW", window.as_pointer())
    except (AttributeError, ReferenceError):
        return None


def _session_key(context):
    window = getattr(context, "window", None)
    key = _window_session_key(window)
    if key is not None:
        return key
    wm = getattr(context, "window_manager", None)
    if wm is not None:
        try:
            return ("WM", wm.as_pointer())
        except (AttributeError, ReferenceError):
            pass
    return ("CONTEXT", id(context))


def _snapshot_text_data(text_data):
    helper = getattr(text_data, "text_helper", None)
    return {
        "text_data": text_data,
        "fonts": {name: getattr(text_data, name, None) for name in _FONT_ATTRS},
        "values": {name: getattr(text_data, name) for name in _VALUE_ATTRS},
        "helper": (
            {name: getattr(helper, name) for name in _HELPER_ATTRS}
            if helper is not None
            else {}
        ),
        "format": [
            tuple(getattr(item, name) for name in _FORMAT_ATTRS)
            for item in text_data.body_format
        ],
    }


def _selected_text_data(context):
    from .text_format import iter_selected_text_data

    result = []
    seen = set()
    for text_data in iter_selected_text_data(context):
        try:
            key = text_data.as_pointer()
        except (AttributeError, ReferenceError):
            key = id(text_data)
        if key in seen:
            continue
        seen.add(key)
        result.append(text_data)
    return result


def _restore_snapshot(snapshot):
    text_data = snapshot["text_data"]
    try:
        for name, value in snapshot["fonts"].items():
            setattr(text_data, name, value)

        helper = getattr(text_data, "text_helper", None)
        if helper is not None:
            for name, value in snapshot["helper"].items():
                setattr(helper, name, value)

        for name, value in snapshot["values"].items():
            setattr(text_data, name, value)

        body_format = text_data.body_format
        for item, values in zip(body_format, snapshot["format"]):
            for name, value in zip(_FORMAT_ATTRS, values):
                setattr(item, name, value)
        text_data.update_tag()
        return True
    except (AttributeError, ReferenceError, RuntimeError):
        return False


def _restore_session(session):
    restored = False
    for snapshot in session["snapshots"]:
        restored = _restore_snapshot(snapshot) or restored
    return restored


def _restore_font_index(session):
    wm = session.get("wm")
    if wm is None or session["font_index"] < 0:
        return
    try:
        from ..props import set_font_catalog_index

        set_font_catalog_index(wm, session["font_index"])
    except (AttributeError, ReferenceError, RuntimeError):
        pass


def begin_preview(context, owner):
    """Start one picker preview transaction for the current window."""
    key = _session_key(context)
    previous = _SESSIONS.pop(key, None)
    if previous is not None:
        _restore_session(previous)

    targets = _selected_text_data(context)
    if not targets:
        return False

    state = getattr(getattr(context, "window_manager", None), "th_state", None)
    font_index = int(getattr(state, "font_index", -1)) if state is not None else -1
    _SESSIONS[key] = {
        "owner": str(owner),
        "snapshots": [_snapshot_text_data(text_data) for text_data in targets],
        "font_index": font_index,
        "wm": getattr(context, "window_manager", None),
    }
    return True


def preview_active(context, owner=None):
    session = _SESSIONS.get(_session_key(context))
    return bool(session and (owner is None or session["owner"] == owner))


def preview_font(context, owner, filepath, catalog_index=-1):
    """Temporarily assign a font to all targets captured by the picker."""
    if not filepath:
        return False
    key = _session_key(context)
    session = _SESSIONS.get(key)
    if session is None or session["owner"] != owner:
        if not begin_preview(context, owner):
            return False
        session = _SESSIONS.get(key)

    from .font_loader import assign_font

    applied = False
    try:
        for snapshot in session["snapshots"]:
            assign_font(snapshot["text_data"], filepath)
            applied = True
    except (FileNotFoundError, OSError, RuntimeError):
        _restore_session(session)
        return False

    if applied and catalog_index >= 0:
        from ..props import set_font_catalog_index

        set_font_catalog_index(context.window_manager, catalog_index)
    _tag_redraw(context)
    return applied


def preview_preset(context, owner, preset_id):
    """Temporarily apply one style preset to captured TextCurve targets."""
    key = _session_key(context)
    session = _SESSIONS.get(key)
    if session is None or session["owner"] != owner:
        if not begin_preview(context, owner):
            return False
        session = _SESSIONS.get(key)

    from .text_format import apply_preset_to_text_data

    applied = False
    for snapshot in session["snapshots"]:
        try:
            applied = apply_preset_to_text_data(snapshot["text_data"], preset_id) or applied
        except (AttributeError, ReferenceError, RuntimeError):
            _restore_session(session)
            return False
    _tag_redraw(context)
    return applied


def cancel_preview(context, owner=None):
    """Restore and end the current transaction, optionally owner-scoped."""
    key = _session_key(context)
    session = _SESSIONS.get(key)
    if session is None or (owner is not None and session["owner"] != owner):
        return False
    _SESSIONS.pop(key, None)
    restored = _restore_session(session)
    _restore_font_index(session)
    _tag_redraw(context)
    return restored


def cancel_preview_for_window(window, owner=None):
    """Restore a preview using its invoking window, even during context changes."""
    key = _window_session_key(window)
    if key is None:
        return False
    session = _SESSIONS.get(key)
    if session is None or (owner is not None and session["owner"] != owner):
        return False
    _SESSIONS.pop(key, None)
    restored = _restore_session(session)
    _restore_font_index(session)
    _tag_all_view3d_redraw()
    return restored


def prepare_preview_commit(context, owner=None):
    """Restore the baseline before a real UNDO operator commits a selection."""
    return cancel_preview(context, owner=owner)


def cancel_owner_previews(owner):
    """Cancel matching sessions in every Blender window before ownership moves."""
    keys = [
        key
        for key, session in _SESSIONS.items()
        if session.get("owner") == owner
    ]
    restored = False
    for key in keys:
        session = _SESSIONS.pop(key)
        restored = _restore_session(session) or restored
        _restore_font_index(session)
    if restored:
        _tag_all_view3d_redraw()
    return restored


def cancel_all_previews():
    """Best-effort restore for add-on shutdown and script reload."""
    sessions = tuple(_SESSIONS.values())
    _SESSIONS.clear()
    for session in sessions:
        _restore_session(session)
        _restore_font_index(session)
    _tag_all_view3d_redraw()


def _tag_all_view3d_redraw():
    try:
        wm = bpy.context.window_manager
        for window in wm.windows:
            for area in window.screen.areas:
                if area.type == "VIEW_3D":
                    area.tag_redraw()
    except (AttributeError, ReferenceError, RuntimeError):
        pass


def _tag_redraw(context):
    try:
        from .text_frame import tag_view3d_redraw

        tag_view3d_redraw(context)
        from ..hud.draw import tag_redraw

        tag_redraw()
    except (AttributeError, ReferenceError, RuntimeError):
        pass
