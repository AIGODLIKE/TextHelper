"""TextCurve formatting helpers."""


STYLE_PRESETS = {
    "BODY": {
        "label": "Body",
        "size": 1.0,
        "use_bold": False,
        "use_italic": False,
        "use_underline": False,
        "space_character": 1.0,
        "space_word": 1.0,
        "space_line": 1.0,
    },
    "HEADING": {
        "label": "Heading",
        "size": 2.0,
        "use_bold": True,
        "use_italic": False,
        "use_underline": False,
        "space_character": 1.0,
        "space_word": 1.0,
        "space_line": 1.1,
    },
    "SUBHEADING": {
        "label": "Subheading",
        "size": 1.5,
        "use_bold": True,
        "use_italic": False,
        "use_underline": False,
        "space_character": 1.0,
        "space_word": 1.0,
        "space_line": 1.05,
    },
    "CAPTION": {
        "label": "Caption",
        "size": 0.75,
        "use_bold": False,
        "use_italic": False,
        "use_underline": False,
        "space_character": 1.0,
        "space_word": 1.0,
        "space_line": 1.0,
    },
}

_STYLE_ATTR = {
    "BOLD": "use_bold",
    "ITALIC": "use_italic",
}

UNDERLINE_POS_OFF = 0.0
UNDERLINE_POS_UNDERLINE = 0.0
UNDERLINE_POS_STRIKE = 0.4
UNDERLINE_POS_MIN = -0.2
UNDERLINE_POS_MAX = 0.8


def iter_selected_font_objects(context):
    """Yield all selected FONT objects."""
    if context is None:
        return
    for obj in getattr(context, "selected_objects", ()):
        if obj.type == "FONT":
            yield obj


def has_selected_font(context):
    return any(True for _ in iter_selected_font_objects(context))


def get_active_text(context):
    if context is None:
        return None
    obj = getattr(context, "active_object", None)
    if obj and obj.type == "FONT" and obj.select_get():
        return obj
    for candidate in iter_selected_font_objects(context):
        return candidate
    return None


def get_active_text_data(context):
    obj = get_active_text(context)
    if obj is None:
        return None
    return obj.data


def iter_selected_text_data(context):
    """Yield TextCurve data for every selected FONT object."""
    for obj in iter_selected_font_objects(context):
        if obj.data is not None:
            yield obj.data


def ensure_edit_font_mode(context):
    from .font_context import font_edit_mode

    obj = get_active_text(context)
    if obj is None:
        return False
    with font_edit_mode(context, obj) as in_edit:
        return in_edit


def _sync_body_format(text_data, *, allow_reassign=True):
    """Ensure body_format length matches body without bpy.ops.font."""
    body = text_data.body
    fmt = text_data.body_format
    if len(fmt) == len(body):
        return True
    if not body:
        return True
    if not allow_reassign:
        return False
    text_data.body = body
    text_data.update_tag()
    return len(text_data.body_format) == len(body)


def _set_format_attr(text_data, attr, value):
    fmt = text_data.body_format
    if not fmt:
        return
    for item in fmt:
        setattr(item, attr, value)


def _text_helper(text_data):
    return getattr(text_data, "text_helper", None)


def is_strike_active(text_data):
    helper = _text_helper(text_data)
    return bool(helper and helper.th_strike_enabled)


def is_underline_active(text_data):
    helper = _text_helper(text_data)
    return bool(helper and helper.th_underline_enabled)


def sync_line_decoration(text_data):
    """Apply logical underline / strikethrough flags to Blender TextCurve RNA."""
    helper = _text_helper(text_data)
    if helper is None:
        return
    if not _sync_body_format(text_data):
        return

    if helper.th_strike_enabled and helper.th_underline_enabled:
        helper.th_underline_enabled = False

    if helper.th_strike_enabled:
        _set_format_attr(text_data, "use_underline", True)
        text_data.underline_position = float(helper.th_strike_position)
    elif helper.th_underline_enabled:
        _set_format_attr(text_data, "use_underline", True)
        text_data.underline_position = UNDERLINE_POS_UNDERLINE
    else:
        _set_format_attr(text_data, "use_underline", False)
        text_data.underline_position = UNDERLINE_POS_OFF
    text_data.update_tag()


def apply_strike_state(text_data, enabled):
    helper = _text_helper(text_data)
    if helper is None:
        return
    helper.th_strike_enabled = bool(enabled)
    if enabled:
        helper.th_underline_enabled = False
    if enabled and abs(float(helper.th_strike_position) - UNDERLINE_POS_OFF) < 0.001:
        helper.th_strike_position = UNDERLINE_POS_STRIKE
    sync_line_decoration(text_data)


def apply_underline_state(text_data, enabled):
    helper = _text_helper(text_data)
    if helper is None:
        return
    helper.th_underline_enabled = bool(enabled)
    if enabled:
        helper.th_strike_enabled = False
    sync_line_decoration(text_data)


def strike_position_display(position):
    value = round(float(position), 2)
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text or "0"


def strike_position_slider_t(position):
    span = UNDERLINE_POS_MAX - UNDERLINE_POS_MIN
    if span <= 0.0:
        return 0.0
    return max(0.0, min(1.0, (float(position) - UNDERLINE_POS_MIN) / span))


def strike_position_from_slider_t(t):
    t = max(0.0, min(1.0, float(t)))
    return round(UNDERLINE_POS_MIN + t * (UNDERLINE_POS_MAX - UNDERLINE_POS_MIN), 3)


def default_strike_position(_text_data=None):
    return UNDERLINE_POS_STRIKE


def apply_strike_position(text_data, value):
    helper = _text_helper(text_data)
    if helper is None:
        return
    pos = max(UNDERLINE_POS_MIN, min(UNDERLINE_POS_MAX, float(value)))
    helper.th_strike_position = pos
    if helper.th_strike_enabled:
        text_data.underline_position = pos
        if _sync_body_format(text_data):
            _set_format_attr(text_data, "use_underline", True)
        text_data.update_tag()


def _format_toggle_value(text_data, style, *, toggle=True):
    """Resolve target on/off from the active (reference) text object."""
    if style == "UNDERLINE":
        all_on = is_underline_active(text_data)
        return (not all_on) if toggle else True
    if style == "STRIKE":
        all_on = is_strike_active(text_data)
        return (not all_on) if toggle else True

    attr = _STYLE_ATTR.get(style)
    if attr is None:
        return None

    fmt = text_data.body_format
    if not fmt:
        return False
    all_on = all(getattr(item, attr) for item in fmt)
    return (not all_on) if toggle else True


def _apply_format_style_to_text_data(text_data, style, new_val):
    if style == "UNDERLINE":
        apply_underline_state(text_data, new_val)
        return True
    if style == "STRIKE":
        apply_strike_state(text_data, new_val)
        return True

    attr = _STYLE_ATTR.get(style)
    if attr is None:
        return False

    fmt = text_data.body_format
    if not fmt:
        return True

    _set_format_attr(text_data, attr, new_val)
    if style == "BOLD":
        apply_bold_state(text_data, new_val)
    elif style == "ITALIC":
        text_data.shear = ITALIC_SHEAR if new_val else 0.0
    text_data.update_tag()
    return True


def apply_format_to_range(context, style, *, toggle=True):
    """Apply BOLD / ITALIC / UNDERLINE / STRIKE via RNA (no bpy.ops.font)."""
    from .font_context import ensure_text_font

    targets = list(iter_selected_text_data(context))
    if not targets:
        return {"CANCELLED"}

    reference = get_active_text_data(context) or targets[0]
    if not ensure_text_font(reference):
        return {"CANCELLED"}

    if style in ("UNDERLINE", "STRIKE"):
        if not _sync_body_format(reference):
            return {"CANCELLED"}
        new_val = _format_toggle_value(reference, style, toggle=toggle)
    else:
        attr = _STYLE_ATTR.get(style)
        if attr is None:
            return {"CANCELLED"}
        if not _sync_body_format(reference):
            return {"CANCELLED"}
        new_val = _format_toggle_value(reference, style, toggle=toggle)
        if new_val is None:
            return {"CANCELLED"}

    applied = False
    for text_data in targets:
        if not ensure_text_font(text_data):
            continue
        if style in ("UNDERLINE", "STRIKE") and not _sync_body_format(text_data):
            continue
        if style not in ("UNDERLINE", "STRIKE") and not _sync_body_format(text_data):
            continue
        if _apply_format_style_to_text_data(text_data, style, new_val):
            applied = True

    return {"FINISHED"} if applied else {"CANCELLED"}


def apply_preset_to_text_data(text_data, preset_id):
    preset = STYLE_PRESETS.get(preset_id)
    if preset is None:
        return False

    _clear_faux_bold_size(text_data)
    text_data.size = preset["size"]
    text_data.space_character = preset["space_character"]
    text_data.space_word = preset.get("space_word", 1.0)
    text_data.space_line = preset["space_line"]

    bold = preset.get("use_bold", False)
    italic = preset.get("use_italic", False)
    if text_data.body and _sync_body_format(text_data):
        for item in text_data.body_format:
            item.use_bold = bold
            item.use_italic = italic
            item.use_underline = False

    apply_bold_state(text_data, bold)
    apply_strike_state(text_data, False)
    apply_underline_state(text_data, False)
    text_data.shear = ITALIC_SHEAR if italic else 0.0
    text_data.text_helper.th_preset = preset_id
    text_data.update_tag()
    return True


def apply_preset(context, preset_id):
    from .font_context import ensure_text_font

    targets = list(iter_selected_text_data(context))
    if not targets:
        return {"CANCELLED"}
    if preset_id not in STYLE_PRESETS:
        return {"CANCELLED"}

    applied = False
    for text_data in targets:
        if not ensure_text_font(text_data):
            continue
        if apply_preset_to_text_data(text_data, preset_id):
            applied = True

    return {"FINISHED"} if applied else {"CANCELLED"}


def apply_spacing_value(text_data, mode, value):
    """Set one spacing/size property on a single TextCurve."""
    if mode == "SIZE":
        text_data.size = max(SIZE_SLIDER_MIN, float(value))
    elif mode == "CHAR":
        text_data.space_character = spacing_from_display_char(int(value))
    elif mode == "WORD":
        text_data.space_word = spacing_from_display_word(int(value))
    elif mode == "SHEAR":
        text_data.shear = float(value)
    elif mode == "LINE":
        text_data.space_line = spacing_from_display_line(text_data, int(value))
    elif mode == "STRIKE_POS":
        apply_strike_position(text_data, value)
    else:
        text_data.offset_y = value
    text_data.update_tag()


def reset_format_value(text_data, mode):
    """Reset one spacing/size property to the current preset default."""
    defaults = preset_format_defaults(text_data)
    if mode == "SIZE":
        text_data.size = defaults["size"]
    elif mode == "CHAR":
        text_data.space_character = defaults["space_character"]
    elif mode == "WORD":
        text_data.space_word = defaults["space_word"]
    elif mode == "SHEAR":
        text_data.shear = defaults["shear"]
    elif mode == "LINE":
        text_data.space_line = defaults["space_line"]
    elif mode == "STRIKE_POS":
        apply_strike_position(text_data, default_strike_position(text_data))
    else:
        text_data.offset_y = defaults["offset_y"]
    text_data.update_tag()


def spacing_display_char(space_character):
    """Map Blender factor to UI offset (0 = default)."""
    return round((space_character - 1.0) * 100.0)


def spacing_from_display_char(display):
    return 1.0 + display / 100.0


def spacing_display_word(space_word):
    """Map Blender word-spacing factor to UI offset (0 = default)."""
    return round((float(space_word) - 1.0) * 100.0)


def spacing_from_display_word(display):
    return max(0.0, 1.0 + display / 100.0)


def spacing_display_line(text_data):
    """Display line height as pixel-like value based on size * space_line."""
    return round(text_data.size * text_data.space_line * 10.0)


LINE_HEIGHT_DISPLAY_MIN = 1
LINE_HEIGHT_SPACE_LINE_MAX = 10.0
SIZE_SLIDER_MIN = 0.25
SIZE_SLIDER_MAX = 4.0
CHAR_SPACING_DISPLAY_MIN = -50
CHAR_SPACING_DISPLAY_MAX = 200
SHEAR_SLIDER_MIN = -1.0
SHEAR_SLIDER_MAX = 1.0
ITALIC_SHEAR = 0.4
BOLD_FAUX_SIZE_MULT = 1.12


def _clear_faux_bold_size(text_data):
    pre = float(getattr(text_data.text_helper, "th_pre_bold_size", 0.0) or 0.0)
    if pre > 0.0:
        text_data.size = pre
        text_data.text_helper.th_pre_bold_size = 0.0


def apply_bold_state(text_data, enabled):
    """Bold on: real bold font when found, otherwise slightly larger size."""
    from .font_loader import disk_font_path, has_real_bold_font, sync_font_style_slots

    if enabled:
        if disk_font_path(text_data.font):
            sync_font_style_slots(text_data)
            if has_real_bold_font(text_data):
                text_data.text_helper.th_pre_bold_size = 0.0
                return
        pre = float(getattr(text_data.text_helper, "th_pre_bold_size", 0.0) or 0.0)
        if pre <= 0.0:
            text_data.text_helper.th_pre_bold_size = float(text_data.size)
            text_data.size = round(text_data.text_helper.th_pre_bold_size * BOLD_FAUX_SIZE_MULT, 2)
    else:
        _clear_faux_bold_size(text_data)


def reapply_bold_if_active(text_data):
    if not text_data.body_format or not any(item.use_bold for item in text_data.body_format):
        return
    _clear_faux_bold_size(text_data)
    apply_bold_state(text_data, True)


def preset_format_defaults(text_data):
    """Default size/spacing values for the active style preset."""
    preset_id = getattr(text_data.text_helper, "th_preset", "BODY") if text_data is not None else "BODY"
    preset = STYLE_PRESETS.get(preset_id, STYLE_PRESETS["BODY"])
    return {
        "size": preset["size"],
        "space_character": preset["space_character"],
        "space_word": preset.get("space_word", 1.0),
        "space_line": preset["space_line"],
        "offset_y": 0.0,
        "shear": 0.0,
    }


def size_slider_max(current_size):
    return max(SIZE_SLIDER_MAX, float(current_size))


def char_spacing_display_bounds(current_display):
    return CHAR_SPACING_DISPLAY_MIN, max(CHAR_SPACING_DISPLAY_MAX, int(current_display))


def word_spacing_display_bounds(current_display):
    return CHAR_SPACING_DISPLAY_MIN, max(CHAR_SPACING_DISPLAY_MAX, int(current_display))


def shear_slider_bounds(current_shear):
    value = float(current_shear)
    return min(SHEAR_SLIDER_MIN, value), max(SHEAR_SLIDER_MAX, value)


def spacing_slider_display_value(text_data, item_id):
    if text_data is None:
        return "0"
    if item_id == "font_size":
        return format_size_display(text_data.size)
    if item_id == "char_spacing":
        return str(spacing_display_char(text_data.space_character))
    if item_id == "word_spacing":
        return str(spacing_display_word(text_data.space_word))
    if item_id == "line_height":
        return str(spacing_display_line(text_data))
    if item_id == "shear":
        return shear_display(text_data.shear)
    return "0"


def shear_display(shear):
    value = round(float(shear), 2)
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text or "0"


def shear_slider_t(shear):
    lo, hi = shear_slider_bounds(shear)
    span = hi - lo
    if span <= 0.0:
        return 0.0
    return max(0.0, min(1.0, (float(shear) - lo) / span))


def shear_from_slider_t(t, current_shear=0.0):
    lo, hi = shear_slider_bounds(current_shear)
    t = max(0.0, min(1.0, float(t)))
    return round(lo + t * (hi - lo), 3)


def format_size_display(size):
    value = round(float(size), 2)
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text or "0"


def format_size_slider_t(size):
    hi = size_slider_max(size)
    span = hi - SIZE_SLIDER_MIN
    if span <= 0.0:
        return 0.0
    return max(0.0, min(1.0, (float(size) - SIZE_SLIDER_MIN) / span))


def format_size_from_slider_t(t, current_size=1.0):
    hi = size_slider_max(current_size)
    t = max(0.0, min(1.0, float(t)))
    value = SIZE_SLIDER_MIN + t * (hi - SIZE_SLIDER_MIN)
    return round(value, 2)


def line_height_display_max(text_data):
    """Maximum display value for the line-height slider (expands with current value)."""
    if text_data is None or text_data.size <= 0.0:
        return 96
    current = spacing_display_line(text_data)
    default_max = max(
        LINE_HEIGHT_DISPLAY_MIN + 1,
        round(text_data.size * LINE_HEIGHT_SPACE_LINE_MAX * 10.0),
    )
    return max(default_max, current)


def spacing_from_display_line(text_data, display):
    if text_data.size <= 0.0:
        return 1.0
    display = max(LINE_HEIGHT_DISPLAY_MIN, int(display))
    return max(0.0, display / (text_data.size * 10.0))
