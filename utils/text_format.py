"""TextCurve formatting helpers."""

import bpy

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


def get_active_text(context):
    obj = context.active_object
    if obj and obj.type == "FONT" and obj.select_get():
        return obj
    return None


def get_active_text_data(context):
    obj = get_active_text(context)
    if obj is None:
        return None
    return obj.data


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


def apply_format_to_range(context, style, *, toggle=True):
    """Apply BOLD / ITALIC / UNDERLINE / STRIKE via RNA (no bpy.ops.font)."""
    from .font_context import ensure_text_font

    text_data = get_active_text_data(context)
    if text_data is None:
        return {"CANCELLED"}
    if not ensure_text_font(text_data):
        return {"CANCELLED"}

    if style in ("UNDERLINE", "STRIKE"):
        if not _sync_body_format(text_data):
            return {"CANCELLED"}
        if style == "UNDERLINE":
            all_on = is_underline_active(text_data)
            new_val = (not all_on) if toggle else True
            apply_underline_state(text_data, new_val)
        else:
            all_on = is_strike_active(text_data)
            new_val = (not all_on) if toggle else True
            apply_strike_state(text_data, new_val)
        return {"FINISHED"}

    attr = _STYLE_ATTR.get(style)
    if attr is None:
        return {"CANCELLED"}

    if not _sync_body_format(text_data):
        return {"CANCELLED"}

    fmt = text_data.body_format
    if not fmt:
        return {"FINISHED"}

    all_on = all(getattr(item, attr) for item in fmt)
    new_val = (not all_on) if toggle else True
    _set_format_attr(text_data, attr, new_val)
    if style == "BOLD":
        apply_bold_state(text_data, new_val)
    elif style == "ITALIC":
        text_data.shear = ITALIC_SHEAR if new_val else 0.0
    text_data.update_tag()
    return {"FINISHED"}


def apply_preset(context, preset_id):
    from .font_context import ensure_text_font

    text_data = get_active_text_data(context)
    if text_data is None:
        return {"CANCELLED"}
    if not ensure_text_font(text_data):
        return {"CANCELLED"}

    preset = STYLE_PRESETS.get(preset_id)
    if preset is None:
        return {"CANCELLED"}

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
    text_data.update_tag()
    return {"FINISHED"}


def spacing_display_char(space_character):
    """Map Blender factor to UI offset (0 = default)."""
    return round((space_character - 1.0) * 100.0)


def spacing_from_display_char(display):
    return 1.0 + display / 100.0


def spacing_display_word(space_word):
    """Map Blender word-spacing factor to UI offset (0 = default)."""
    return round((float(space_word) - 1.0) * 100.0)


def spacing_from_display_word(display):
    return max(0.0, min(10.0, 1.0 + display / 100.0))


def spacing_display_line(text_data):
    """Display line height as pixel-like value based on size * space_line."""
    return round(text_data.size * text_data.space_line * 10.0)


LINE_HEIGHT_DISPLAY_MIN = 1
LINE_HEIGHT_SPACE_LINE_MAX = 10.0
SIZE_SLIDER_MIN = 0.25
SIZE_SLIDER_MAX = 4.0
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


def shear_display(shear):
    value = round(float(shear), 2)
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text or "0"


def shear_slider_t(shear):
    span = SHEAR_SLIDER_MAX - SHEAR_SLIDER_MIN
    if span <= 0.0:
        return 0.0
    return max(0.0, min(1.0, (float(shear) - SHEAR_SLIDER_MIN) / span))


def shear_from_slider_t(t):
    t = max(0.0, min(1.0, float(t)))
    return round(SHEAR_SLIDER_MIN + t * (SHEAR_SLIDER_MAX - SHEAR_SLIDER_MIN), 3)


def format_size_display(size):
    value = round(float(size), 2)
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text or "0"


def format_size_slider_t(size):
    span = SIZE_SLIDER_MAX - SIZE_SLIDER_MIN
    if span <= 0.0:
        return 0.0
    return max(0.0, min(1.0, (float(size) - SIZE_SLIDER_MIN) / span))


def format_size_from_slider_t(t):
    t = max(0.0, min(1.0, float(t)))
    value = SIZE_SLIDER_MIN + t * (SIZE_SLIDER_MAX - SIZE_SLIDER_MIN)
    return round(value, 2)


def line_height_display_max(text_data):
    """Maximum display value allowed for the current text size."""
    if text_data is None or text_data.size <= 0.0:
        return 96
    return max(
        LINE_HEIGHT_DISPLAY_MIN + 1,
        round(text_data.size * LINE_HEIGHT_SPACE_LINE_MAX * 10.0),
    )


def spacing_from_display_line(text_data, display):
    if text_data.size <= 0.0:
        return 1.0
    display = max(
        LINE_HEIGHT_DISPLAY_MIN,
        min(line_height_display_max(text_data), int(display)),
    )
    return max(0.0, min(LINE_HEIGHT_SPACE_LINE_MAX, display / (text_data.size * 10.0)))
