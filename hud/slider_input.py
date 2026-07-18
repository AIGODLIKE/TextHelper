"""Manual numeric input for HUD spacing slider value labels."""

import re
import time

import bpy

from .gpu_blf import get_blf

from ..utils.text_format import (
    LINE_HEIGHT_DISPLAY_MIN,
    SIZE_SLIDER_MIN,
    apply_spacing_value,
    iter_selected_text_data,
    spacing_slider_display_value,
)
from .layout import (
    SPACING_VALUE_INPUT_IDS,
    slider_header_font_size,
    slider_header_position_y,
    slider_value_field_contains,
    slider_value_left_x,
)
from .text_field_edit import (
    begin_mouse_select,
    caret_index,
    draw_text_field_text,
    end_mouse_select,
    handle_text_field_key,
    index_from_x,
    reset_text_field_cursor,
    update_mouse_select,
)

_SLIDER_MODES = {
    "font_size": "SIZE",
    "char_spacing": "CHAR",
    "word_spacing": "WORD",
    "line_height": "LINE",
    "shear": "SHEAR",
}

_UI_FONT = 0
_CARET_TIMER = None
_ALLOWED = re.compile(r"^-?\d*\.?\d*$")


def _state(context):
    return getattr(context.window_manager, "th_state", None)


def slider_value_editing(context):
    state = _state(context)
    if state is None:
        return False
    return getattr(state, "th_hud_slider_edit_id", "") in SPACING_VALUE_INPUT_IDS


def clear_slider_value_edit(state):
    if state is None:
        return
    state.th_hud_slider_edit_id = ""
    state.th_hud_slider_edit_text = ""
    reset_text_field_cursor(state, 0)
    _stop_caret_timer()


def focus_slider_value(context, slider_id, text_data):
    state = _state(context)
    if state is None or slider_id not in SPACING_VALUE_INPUT_IDS:
        return False
    state.th_hud_slider_edit_id = slider_id
    display = spacing_slider_display_value(text_data, slider_id)
    state.th_hud_slider_edit_text = display
    reset_text_field_cursor(state, len(display or ""))
    _start_caret_timer()
    return True


def _sanitize_typed(text):
    if not text:
        return ""
    return "".join(ch for ch in text if ch.isdigit() or ch in ".-")


def _typing_text_from_event(event):
    if event.value not in {"PRESS", "REPEAT"}:
        return ""
    if event.ctrl or event.alt or event.oskey:
        return ""
    utf8 = getattr(event, "utf8", None) or getattr(event, "unicode", None) or ""
    if utf8:
        return _sanitize_typed(utf8)
    if event.type in {"MINUS", "NUMPAD_MINUS"}:
        return "-"
    if event.type in {"PERIOD", "NUMPAD_PERIOD"}:
        return "."
    if event.type == "SPACE":
        return ""
    etype = str(getattr(event, "type", ""))
    if len(etype) == 1 and etype.isdigit():
        return _sanitize_typed(etype)
    return ""


def _parse_edit_value(slider_id, text):
    raw = (text or "").strip()
    if not raw or raw in {"-", ".", "-."}:
        return None
    try:
        if slider_id in {"font_size", "shear"}:
            return float(raw)
        return int(float(raw))
    except ValueError:
        return None


def _validate_slider_text(_slider_id, merged):
    return bool(_ALLOWED.fullmatch(merged) or merged in {"-", ".", "-."})


def _slider_text_origin(rect, scale, display, font_id=0):
    blf = get_blf()
    header_size = slider_header_font_size(scale)
    left = slider_value_left_x(rect, scale, header_size, display, font_id)
    top = slider_header_position_y(rect, scale, header_size, display, font_id) + header_size
    blf.size(font_id, int(header_size))
    _, th = blf.dimensions(font_id, display or "0")
    return left, top - th, int(header_size), th


def _cursor_index_at_mx(rect, scale, display, mx, font_id=0):
    left, _bottom, header_size, _th = _slider_text_origin(rect, scale, display, font_id)
    return index_from_x(font_id, header_size, display or "", mx, left)


def dismiss_slider_value_edit(context, *, undo=False):
    """Commit and leave inline slider editing when focus moves elsewhere."""
    if not slider_value_editing(context):
        return False
    commit_slider_value_edit(context, undo=undo)
    return True


def commit_slider_value_edit(context, *, undo=False):
    state = _state(context)
    if state is None:
        return False
    slider_id = getattr(state, "th_hud_slider_edit_id", "")
    if slider_id not in SPACING_VALUE_INPUT_IDS:
        return False

    value = _parse_edit_value(slider_id, state.th_hud_slider_edit_text)
    clear_slider_value_edit(state)
    if value is None:
        return True

    if slider_id == "font_size" and value < SIZE_SLIDER_MIN:
        value = SIZE_SLIDER_MIN
    if slider_id == "line_height" and value < LINE_HEIGHT_DISPLAY_MIN:
        value = LINE_HEIGHT_DISPLAY_MIN

    mode = _SLIDER_MODES.get(slider_id, "SIZE")
    if undo:
        from ..utils.undo import push_undo

        push_undo()
    for text_data in iter_selected_text_data(context):
        apply_spacing_value(text_data, mode, value)
    from ..utils.text_frame import tag_view3d_redraw

    tag_view3d_redraw(context)
    return True


def handle_slider_value_key(context, event):
    state = _state(context)
    if state is None or not slider_value_editing(context):
        return False

    slider_id = state.th_hud_slider_edit_id
    allow_decimal = slider_id in {"font_size", "shear"}
    allow_minus = slider_id in {"char_spacing", "word_spacing", "shear"}

    if event.type in {"RET", "NUMPAD_ENTER"} and event.value == "PRESS":
        commit_slider_value_edit(context, undo=True)
        return True

    if event.type == "ESC" and event.value == "PRESS":
        clear_slider_value_edit(state)
        return True

    def _get_text():
        return state.th_hud_slider_edit_text or ""

    def _set_text(value):
        state.th_hud_slider_edit_text = value

    def _validate(merged):
        if not _validate_slider_text(slider_id, merged):
            return False
        if not allow_minus and merged.lstrip("-") != merged:
            return False
        if not allow_decimal and "." in merged:
            return False
        return True

    if handle_text_field_key(
        context,
        event,
        state,
        get_text=_get_text,
        set_text=_set_text,
        sanitize_typed=_sanitize_typed,
        validate_text=_validate,
    ):
        return True

    text = _typing_text_from_event(event)
    if text:
        if text == "-" and not allow_minus:
            return True
        if text == "." and not allow_decimal:
            return True
        current = _get_text()
        cursor = caret_index(state)
        lo, hi = min(int(state.th_text_field_anchor), cursor), max(int(state.th_text_field_anchor), cursor)
        if lo != hi:
            merged = current[:lo] + text + current[hi:]
            cursor = lo + len(text)
        else:
            merged = current[:cursor] + text + current[cursor:]
            cursor = cursor + len(text)
        if _validate(merged):
            _set_text(merged)
            state.th_text_field_cursor = cursor
            state.th_text_field_anchor = cursor
        return True

    return False


def slider_value_blocks_keymap(event):
    if event.type in {
        "LEFTMOUSE",
        "RIGHTMOUSE",
        "MIDDLEMOUSE",
        "MOUSEMOVE",
        "WHEELUPMOUSE",
        "WHEELDOWNMOUSE",
        "INBETWEEN_MOUSEMOVE",
        "ESC",
        "RET",
        "NUMPAD_ENTER",
    }:
        return False
    return event.value in {"PRESS", "REPEAT"}


def try_begin_slider_value_edit(context, rect, text_data, mx, my, scale):
    if rect.item.kind != "spacing_slider" or rect.id not in SPACING_VALUE_INPUT_IDS:
        return False
    state = _state(context)
    if state is None:
        return False
    display = (
        state.th_hud_slider_edit_text
        if slider_value_editing(context) and state.th_hud_slider_edit_id == rect.id
        else rect.item.label
    )
    if not slider_value_field_contains(rect, mx, my, scale, display, _UI_FONT):
        return False
    if slider_value_editing(context) and state.th_hud_slider_edit_id != rect.id:
        commit_slider_value_edit(context, undo=False)
        focus_slider_value(context, rect.id, text_data)
        display = state.th_hud_slider_edit_text
    elif not slider_value_editing(context):
        focus_slider_value(context, rect.id, text_data)
        display = state.th_hud_slider_edit_text
    idx = _cursor_index_at_mx(rect, scale, display, mx)
    begin_mouse_select(state, idx)
    return True


def handle_slider_value_mouse_move(context, mx, scale):
    state = _state(context)
    if state is None or not slider_value_editing(context) or not getattr(state, "th_text_field_selecting", False):
        return False
    slider_id = state.th_hud_slider_edit_id
    from .hit_test import get_hud_hit_rects

    obj = context.active_object
    if obj is None:
        return False
    rects = get_hud_hit_rects(context, obj, obj.data)
    rect = next((r for r in rects if r.id == slider_id), None)
    if rect is None:
        return False
    display = state.th_hud_slider_edit_text or ""
    idx = _cursor_index_at_mx(rect, scale, display, mx)
    update_mouse_select(state, idx)
    return True


def handle_slider_value_mouse_release(context):
    state = _state(context)
    if state is None or not slider_value_editing(context):
        return False
    if not getattr(state, "th_text_field_selecting", False):
        return False
    end_mouse_select(state)
    return True


def draw_slider_value_field(shader, rect, item, scale, accent, colors, context, font_id=0):
    from ..utils.hud_theme import theme_text_color

    from .gpu_primitives import draw_rounded_rect

    blf = get_blf()
    state = _state(context)
    editing = state is not None and state.th_hud_slider_edit_id == item.id
    header_size = slider_header_font_size(scale)
    label_color = theme_text_color(
        colors,
        highlighted=False,
        surface="field" if editing else "panel",
    )
    display = state.th_hud_slider_edit_text if editing else item.label
    left, bottom, header_size, th = _slider_text_origin(rect, scale, display, font_id)
    right = rect.x + rect.w - 8.0 * scale
    text_y = slider_header_position_y(rect, scale, header_size, display, font_id)

    if editing:
        pad = 3.0 * scale
        field_bg = colors.get("field_bg", colors.get("chip_bg", (0.18, 0.18, 0.20, 1.0)))
        draw_rounded_rect(
            shader,
            left - pad,
            bottom - pad,
            right - left + pad * 2.0,
            th + pad * 2.0,
            field_bg,
            3.0 * scale,
        )
        draw_rounded_rect(
            shader,
            left - pad,
            bottom - pad,
            2.0 * scale,
            th + pad * 2.0,
            (*accent[:3], 0.95),
            2.0 * scale,
        )
        from ..utils.hud_theme import text_field_selection_for_editing

        sel_bg, sel_fg = text_field_selection_for_editing(label_color, colors, backdrop=field_bg)
        draw_text_field_text(
            font_id,
            header_size,
            display,
            left,
            text_y,
            state,
            fg=label_color,
            sel_bg=sel_bg,
            sel_fg=sel_fg,
            shader=shader,
            scale=scale,
        )
    else:
        blf.size(font_id, int(header_size))
        blf.color(font_id, *label_color)
        blf.position(font_id, left, text_y, 0)
        blf.draw(font_id, display or "0")

    if editing and int(time.time() / 0.5) % 2 == 0:
        caret_at = caret_index(state)
        prefix = (display or "")[:caret_at]
        tw, _ = blf.dimensions(font_id, prefix) if prefix else (0.0, 0.0)
        caret_x = left + tw
        caret_h = th + 2.0 * scale
        draw_rounded_rect(
            shader,
            caret_x,
            bottom,
            max(1.0 * scale, 1.5 * scale),
            caret_h,
            label_color,
            0.5 * scale,
        )


def _start_caret_timer():
    global _CARET_TIMER
    if _CARET_TIMER is not None:
        return

    def _tick():
        global _CARET_TIMER
        try:
            ctx = bpy.context
            if not slider_value_editing(ctx):
                _CARET_TIMER = None
                return None
            from .draw import tag_redraw

            tag_redraw()
        except Exception:
            _CARET_TIMER = None
            return None
        return 0.25

    _CARET_TIMER = _tick
    bpy.app.timers.register(_CARET_TIMER, first_interval=0.25)


def _stop_caret_timer():
    global _CARET_TIMER
    if _CARET_TIMER is not None:
        try:
            bpy.app.timers.unregister(_CARET_TIMER)
        except ValueError:
            pass
        _CARET_TIMER = None
