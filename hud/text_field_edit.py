"""Shared cursor, selection, and keyboard handling for HUD text fields."""

from .gpu_blf import get_blf


def reset_text_field_cursor(state, text_len):
    pos = max(0, int(text_len))
    state.th_text_field_cursor = pos
    state.th_text_field_anchor = pos
    state.th_text_field_selecting = False


def selection_range(state):
    anchor = int(getattr(state, "th_text_field_anchor", 0))
    cursor = int(getattr(state, "th_text_field_cursor", 0))
    return min(anchor, cursor), max(anchor, cursor)


def has_selection(state):
    return int(getattr(state, "th_text_field_anchor", 0)) != int(getattr(state, "th_text_field_cursor", 0))


def caret_index(state):
    return int(getattr(state, "th_text_field_cursor", 0))


def place_cursor(state, index):
    index = max(0, int(index))
    state.th_text_field_cursor = index
    state.th_text_field_anchor = index
    state.th_text_field_selecting = False


def begin_mouse_select(state, index):
    index = max(0, int(index))
    state.th_text_field_cursor = index
    state.th_text_field_anchor = index
    state.th_text_field_selecting = True


def update_mouse_select(state, index):
    state.th_text_field_cursor = max(0, int(index))


def end_mouse_select(state):
    state.th_text_field_selecting = False
    if not has_selection(state):
        place_cursor(state, caret_index(state))


def index_from_x(font_id, font_size, text, click_x, text_x):
    blf = get_blf()
    text = text or ""
    rel_x = float(click_x) - float(text_x)
    if rel_x <= 0.0:
        return 0
    blf.size(font_id, int(font_size))
    full_w, _ = blf.dimensions(font_id, text)
    if rel_x >= full_w:
        return len(text)
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi) // 2
        tw, _ = blf.dimensions(font_id, text[:mid])
        if tw < rel_x:
            lo = mid + 1
        else:
            hi = mid
    if lo > 0:
        prev_w, _ = blf.dimensions(font_id, text[: lo - 1])
        curr_w, _ = blf.dimensions(font_id, text[:lo])
        if abs(rel_x - prev_w) <= abs(rel_x - curr_w):
            return lo - 1
    return lo


def _replace_range(text, lo, hi, insert):
    return text[:lo] + insert + text[hi:]


def _delete_selection(state, get_text, set_text, on_change):
    text = get_text()
    lo, hi = selection_range(state)
    if lo == hi:
        return False
    set_text(text[:lo] + text[hi:])
    place_cursor(state, lo)
    if on_change:
        on_change()
    return True


def select_all(state, text_len):
    state.th_text_field_anchor = 0
    state.th_text_field_cursor = max(0, int(text_len))
    state.th_text_field_selecting = False


def handle_text_field_key(
    context,
    event,
    state,
    *,
    get_text,
    set_text,
    on_change=None,
    sanitize_typed=None,
    validate_text=None,
    max_len=0,
):
    """Handle keyboard input for a single-line text field. Returns True if consumed."""
    if event.value not in {"PRESS", "REPEAT"}:
        return False

    text = get_text()
    text_len = len(text)
    cursor = caret_index(state)
    anchor = int(getattr(state, "th_text_field_anchor", 0))
    extend = bool(event.shift)

    def _clamp_index(index):
        return max(0, min(int(index), len(get_text())))

    def _move_cursor(new_cursor, *, keep_anchor=False):
        new_cursor = _clamp_index(new_cursor)
        if keep_anchor:
            state.th_text_field_cursor = new_cursor
        else:
            place_cursor(state, new_cursor)

    def _insert_at_cursor(raw):
        nonlocal text, cursor
        text = get_text()
        cursor = caret_index(state)
        if has_selection(state):
            lo, hi = selection_range(state)
            text = text[:lo] + text[hi:]
            cursor = lo
        cleaned = sanitize_typed(raw) if sanitize_typed else raw
        if not cleaned:
            return False
        merged = text[:cursor] + cleaned + text[cursor:]
        if max_len > 0 and len(merged) > max_len:
            merged = merged[:max_len]
        if validate_text and not validate_text(merged):
            return False
        set_text(merged)
        place_cursor(state, min(cursor + len(cleaned), len(merged)))
        if on_change:
            on_change()
        return True

    if event.type == "A" and event.value == "PRESS" and (event.ctrl or event.oskey) and not event.alt:
        select_all(state, text_len)
        return True

    if event.type == "C" and event.value == "PRESS" and (event.ctrl or event.oskey) and not event.alt:
        if has_selection(state):
            lo, hi = selection_range(state)
            context.window_manager.clipboard = get_text()[lo:hi]
        return True

    if event.type == "X" and event.value == "PRESS" and (event.ctrl or event.oskey) and not event.alt:
        if has_selection(state):
            lo, hi = selection_range(state)
            context.window_manager.clipboard = get_text()[lo:hi]
            _delete_selection(state, get_text, set_text, on_change)
        return True

    if event.type == "V" and event.value == "PRESS" and (event.ctrl or event.oskey) and not event.alt:
        clip = getattr(context.window_manager, "clipboard", "") or ""
        if clip:
            clip = clip.replace("\r\n", "\n").replace("\r", "\n").split("\n", 1)[0]
            if sanitize_typed:
                clip = sanitize_typed(clip)
            if clip:
                if has_selection(state):
                    lo, hi = selection_range(state)
                    text = get_text()
                    merged = text[:lo] + clip + text[hi:]
                    cursor = lo + len(clip)
                else:
                    text = get_text()
                    cursor = caret_index(state)
                    merged = text[:cursor] + clip + text[cursor:]
                    cursor = cursor + len(clip)
                if max_len > 0 and len(merged) > max_len:
                    merged = merged[:max_len]
                    cursor = min(cursor, len(merged))
                if validate_text and not validate_text(merged):
                    return True
                set_text(merged)
                place_cursor(state, cursor)
                if on_change:
                    on_change()
        return True

    if event.type in {"BACK_SPACE", "DEL"} and event.value in {"PRESS", "REPEAT"}:
        if _delete_selection(state, get_text, set_text, on_change):
            return True
        text = get_text()
        cursor = caret_index(state)
        if event.type == "BACK_SPACE" and cursor > 0:
            set_text(text[: cursor - 1] + text[cursor:])
            place_cursor(state, cursor - 1)
            if on_change:
                on_change()
        elif event.type == "DEL" and cursor < len(text):
            set_text(text[:cursor] + text[cursor + 1 :])
            place_cursor(state, cursor)
            if on_change:
                on_change()
        return True

    if event.type == "LEFT_ARROW":
        _move_cursor(cursor - 1, keep_anchor=extend)
        return True
    if event.type == "RIGHT_ARROW":
        _move_cursor(cursor + 1, keep_anchor=extend)
        return True
    if event.type == "HOME":
        _move_cursor(0, keep_anchor=extend)
        return True
    if event.type == "END":
        _move_cursor(len(get_text()), keep_anchor=extend)
        return True

    return False


def draw_text_field_selection(shader, font_id, font_size, text, text_x, text_y, text_h, state, color, scale):
    blf = get_blf()
    if not has_selection(state):
        return
    lo, hi = selection_range(state)
    text = text or ""
    if lo >= hi:
        return
    blf.size(font_id, int(font_size))
    prefix_w, _ = blf.dimensions(font_id, text[:lo]) if lo else (0.0, 0.0)
    sel_w, _ = blf.dimensions(font_id, text[lo:hi])
    from .gpu_primitives import draw_rounded_rect

    pad_y = 1.0 * scale
    draw_rounded_rect(
        shader,
        text_x + prefix_w,
        text_y - pad_y,
        max(sel_w, 1.0 * scale),
        text_h + pad_y * 2.0,
        color,
        1.0 * scale,
    )


def draw_text_field_text(
    font_id,
    font_size,
    text,
    text_x,
    text_y,
    state,
    *,
    fg,
    sel_bg,
    sel_fg,
    shader=None,
    scale=1.0,
):
    """Draw single-line field text; selected range uses contrasting colors."""
    blf = get_blf()
    text = text or ""
    blf.size(font_id, int(font_size))
    _, text_h = blf.dimensions(font_id, text or " ")

    if state is not None and has_selection(state):
        lo, hi = selection_range(state)
        if lo < hi and shader is not None:
            draw_text_field_selection(shader, font_id, font_size, text, text_x, text_y, text_h, state, sel_bg, scale)
            if lo > 0:
                blf.color(font_id, *fg)
                blf.position(font_id, text_x, text_y, 0)
                blf.draw(font_id, text[:lo])
            blf.color(font_id, *sel_fg)
            prefix_w, _ = blf.dimensions(font_id, text[:lo]) if lo else (0.0, 0.0)
            blf.position(font_id, text_x + prefix_w, text_y, 0)
            blf.draw(font_id, text[lo:hi])
            if hi < len(text):
                blf.color(font_id, *fg)
                end_w, _ = blf.dimensions(font_id, text[:hi])
                blf.position(font_id, text_x + end_w, text_y, 0)
                blf.draw(font_id, text[hi:])
            return

    blf.color(font_id, *fg)
    blf.position(font_id, text_x, text_y, 0)
    blf.draw(font_id, text)
