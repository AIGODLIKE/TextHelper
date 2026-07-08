"""Toolbar layout definitions for the viewport HUD."""

from dataclasses import dataclass, field

import blf

from ..i18n import _

SPACING_SLIDER_IDS = frozenset({"font_size", "char_spacing", "word_spacing", "line_height", "shear", "strike_position"})
SPACING_VALUE_INPUT_IDS = frozenset({"font_size", "char_spacing", "word_spacing", "line_height", "shear"})

FONT_DROPDOWN_WIDTH = 156.0
FONT_WEIGHT_DROPDOWN_WIDTH = 72.0
_FONT_DROPDOWN_TEXT_PAD = 8.0
_FONT_DROPDOWN_CHEVRON_PAD = 20.0

_ROW_GAP = 4.0
_STRIKE_PANEL_GAP = 6.0
_STRIKE_PANEL_WIDTH = 132.0

_SLIDER_PAD = 8.0
_SLIDER_ROW_HEIGHT = 44.0
_SLIDER_HEADER_FONT = 12.0
_SLIDER_HEADER_TOP = 12.0
_SLIDER_TRACK_BOTTOM = 11.0

_LAST_RECTS = []
_LAST_RECTS_BY_REGION: dict[int, list] = {}


def _region_key(context) -> int | None:
    region = getattr(context, "region", None)
    if region is None:
        return None
    return region.as_pointer()


def cache_hud_rects(context, rects) -> None:
    """Store HUD rects for the current 3D View WINDOW region."""
    global _LAST_RECTS
    _LAST_RECTS = rects
    key = _region_key(context)
    if key is not None:
        _LAST_RECTS_BY_REGION[key] = rects


def clear_hud_rects_cache(context=None) -> None:
    global _LAST_RECTS
    _LAST_RECTS = []
    if context is None:
        _LAST_RECTS_BY_REGION.clear()
        return
    key = _region_key(context)
    if key is not None:
        _LAST_RECTS_BY_REGION.pop(key, None)


def get_cached_hud_rects(context):
    key = _region_key(context)
    if key is None:
        return []
    return _LAST_RECTS_BY_REGION.get(key, [])


def set_region_hover(context, hover_id: str) -> None:
    key = _region_key(context)
    if key is not None:
        _LAST_HOVER_BY_REGION[key] = hover_id or ""


def get_region_hover(context) -> str:
    key = _region_key(context)
    if key is None:
        return ""
    return _LAST_HOVER_BY_REGION.get(key, "")


def clear_all_region_hovers() -> None:
    _LAST_HOVER_BY_REGION.clear()


def clear_region_hover(context=None) -> None:
    if context is None:
        _LAST_HOVER_BY_REGION.clear()
        return
    key = _region_key(context)
    if key is not None:
        _LAST_HOVER_BY_REGION.pop(key, None)


_LAST_HOVER_BY_REGION: dict[int, str] = {}


@dataclass
class HudItem:
    id: str
    kind: str  # button, toggle, dropdown, separator, spacing_slider, drag
    label: str = ""
    width: float = 32.0
    icon: str = ""
    op: str = ""
    op_kwargs: dict = field(default_factory=dict)
    active_check: str = ""
    title_key: str = ""
    tip_key: str = ""
    reset_mode: str = ""


@dataclass
class HudRect:
    id: str
    x: float
    y: float
    w: float
    h: float
    item: HudItem


def build_tool_row_items():
    return [
        HudItem("drag_handle", "drag", "", width=20.0, tip_key="Drag to reposition the toolbar"),
        HudItem(
            "preset",
            "dropdown",
            _("Body"),
            width=76.0,
            op="font.texthelper_toggle_preset_picker",
            tip_key="Open style preset picker",
        ),
        HudItem("font", "dropdown", _("Font"), width=FONT_DROPDOWN_WIDTH, op="font.texthelper_toggle_font_picker", tip_key="Open font picker"),
        HudItem(
            "font_weight",
            "dropdown",
            _("Weight"),
            width=FONT_WEIGHT_DROPDOWN_WIDTH,
            op="font.texthelper_toggle_weight_picker",
            tip_key="Switch font weight",
        ),
        HudItem("sep1", "separator", width=8.0),
        HudItem(
            "bold",
            "toggle",
            "B",
            width=28.0,
            op="font.texthelper_style_toggle",
            op_kwargs={"style": "BOLD"},
            tip_key="Bold",
        ),
        HudItem(
            "italic",
            "toggle",
            "I",
            width=28.0,
            op="font.texthelper_style_toggle",
            op_kwargs={"style": "ITALIC"},
            tip_key="Italic",
        ),
        HudItem(
            "underline",
            "toggle",
            "U",
            width=28.0,
            op="font.texthelper_style_toggle",
            op_kwargs={"style": "UNDERLINE"},
            tip_key="Underline",
        ),
        HudItem(
            "strike",
            "toggle",
            "S",
            width=28.0,
            op="font.texthelper_style_toggle",
            op_kwargs={"style": "STRIKE"},
            tip_key="Strikethrough",
        ),
        HudItem("sep2", "separator", width=8.0),
        HudItem(
            "case_default",
            "toggle",
            "/",
            width=28.0,
            op="font.texthelper_set_text_case",
            op_kwargs={"case": "DEFAULT"},
            active_check="text_helper.th_text_case:DEFAULT",
            tip_key="Default case",
        ),
        HudItem(
            "case_upper",
            "toggle",
            "AA",
            width=28.0,
            op="font.texthelper_set_text_case",
            op_kwargs={"case": "UPPER"},
            active_check="text_helper.th_text_case:UPPER",
            tip_key="Uppercase",
        ),
        HudItem(
            "case_lower",
            "toggle",
            "aa",
            width=28.0,
            op="font.texthelper_set_text_case",
            op_kwargs={"case": "LOWER"},
            active_check="text_helper.th_text_case:LOWER",
            tip_key="Lowercase",
        ),
        HudItem("sep_align", "separator", width=8.0),
        HudItem(
            "align_left",
            "toggle",
            "",
            width=28.0,
            op="font.texthelper_set_align",
            op_kwargs={"align": "LEFT"},
            active_check="align_x:LEFT",
            tip_key="Align left",
        ),
        HudItem(
            "align_center",
            "toggle",
            "",
            width=28.0,
            op="font.texthelper_set_align",
            op_kwargs={"align": "CENTER"},
            active_check="align_x:CENTER",
            tip_key="Align center",
        ),
        HudItem(
            "align_right",
            "toggle",
            "",
            width=28.0,
            op="font.texthelper_set_align",
            op_kwargs={"align": "RIGHT"},
            active_check="align_x:RIGHT",
            tip_key="Align right",
        ),
    ]


def build_slider_row_items():
    return [
        HudItem(
            "font_size",
            "spacing_slider",
            "1",
            width=118.0,
            op="font.texthelper_set_spacing_value",
            op_kwargs={"mode": "SIZE"},
            title_key="Font Size",
            tip_key="Adjust font size (↺ reset · click value to type)",
            reset_mode="SIZE",
        ),
        HudItem(
            "char_spacing",
            "spacing_slider",
            "0",
            width=118.0,
            op="font.texthelper_set_spacing_value",
            op_kwargs={"mode": "CHAR"},
            title_key="Char Spacing",
            tip_key="Adjust character spacing (↺ reset · click value to type)",
            reset_mode="CHAR",
        ),
        HudItem(
            "word_spacing",
            "spacing_slider",
            "0",
            width=118.0,
            op="font.texthelper_set_spacing_value",
            op_kwargs={"mode": "WORD"},
            title_key="Word Spacing",
            tip_key="Adjust word spacing (↺ reset · click value to type)",
            reset_mode="WORD",
        ),
        HudItem(
            "line_height",
            "spacing_slider",
            "10",
            width=118.0,
            op="font.texthelper_set_spacing_value",
            op_kwargs={"mode": "LINE"},
            title_key="Line Height",
            tip_key="Adjust line height (↺ reset · click value to type)",
            reset_mode="LINE",
        ),
        HudItem(
            "shear",
            "spacing_slider",
            "0",
            width=118.0,
            op="font.texthelper_set_spacing_value",
            op_kwargs={"mode": "SHEAR"},
            title_key="Shear",
            tip_key="Adjust text shear (↺ reset · click value to type)",
            reset_mode="SHEAR",
        ),
        HudItem("sep_close", "separator", width=6.0),
        HudItem("close", "button", "×", width=22.0, op="wm.texthelper_hide_hud", tip_key="Hide floating toolbar"),
    ]


def build_items():
    return build_slider_row_items() + build_tool_row_items()


def build_row1_items():
    return build_slider_row_items()


def build_row2_items():
    return build_tool_row_items()


def _visible_row_items(items):
    return [item for item in items if item.kind != "hidden" and item.width > 0]


def _update_item_labels(items, text_data, context=None):
    from ..utils.font_family import short_weight_label, toolbar_weight_label
    from ..utils.font_loader import queue_font_catalog, resolve_font_filepath
    from ..utils.text_format import (
        STYLE_PRESETS,
        format_size_display,
        spacing_display_char,
        spacing_display_word,
        spacing_display_line,
        shear_display,
    )

    for item in items:
        if item.id == "preset" and text_data is not None:
            preset = STYLE_PRESETS.get(text_data.text_helper.th_preset, STYLE_PRESETS["BODY"])
            item.label = _(preset["label"])
        if item.id == "font" and text_data is not None and text_data.font:
            from ..utils.font_loader import font_hud_label

            item.label = font_hud_label(text_data.font, context)
            item.width = FONT_DROPDOWN_WIDTH
        elif item.id == "font":
            item.label = _("Font")
            item.width = FONT_DROPDOWN_WIDTH
        if item.id == "font_weight":
            item.kind = "dropdown"
            label = "Regular"
            if text_data is not None and text_data.font and context is not None:
                wm = context.window_manager
                if wm is not None and getattr(wm, "th_state", None) is not None:
                    from ..utils.font_family import toolbar_weight_label
                    from ..utils.font_loader import queue_font_catalog

                    queue_font_catalog(wm)
                    catalog = wm.th_state.font_catalog
                    path = resolve_font_filepath(text_data.font)
                    if path and len(catalog) > 0:
                        label = toolbar_weight_label(catalog, path)
            item.label = short_weight_label(label)
            item.width = FONT_WEIGHT_DROPDOWN_WIDTH
        if item.id == "font_size" and text_data is not None:
            item.label = format_size_display(text_data.size)
        if item.id == "char_spacing" and text_data is not None:
            item.label = f"{spacing_display_char(text_data.space_character)}"
        if item.id == "word_spacing" and text_data is not None:
            item.label = f"{spacing_display_word(text_data.space_word)}"
        if item.id == "line_height" and text_data is not None:
            item.label = f"{spacing_display_line(text_data)}"
        if item.id == "shear" and text_data is not None:
            item.label = shear_display(text_data.shear)


def slider_row_height(scale):
    return _SLIDER_ROW_HEIGHT * scale


def _layout_items_row(items, anchor_x, y, scale):
    height = slider_row_height(scale)
    gap = 2.0 * scale
    visible = _visible_row_items(items)
    total_w = 0.0
    for i, item in enumerate(visible):
        w = item.width * scale
        total_w += w
        if item.kind != "separator" and i + 1 < len(visible):
            total_w += gap

    x = anchor_x - total_w * 0.5
    rects = []
    for item in visible:
        w = item.width * scale
        if item.kind == "separator":
            sep_h = height - 10 * scale
            sep_y = y + (height - sep_h) * 0.5
            rects.append(HudRect(item.id, x + w * 0.5 - 1, sep_y, 2, sep_h, item))
            x += w
            continue
        rects.append(HudRect(item.id, x, y, w, height, item))
        x += w + gap
    return rects, total_w, height


def row_bounds(rects, pad=4.0):
    items = [rect for rect in rects if rect.item.kind != "separator"]
    if not items:
        return None
    x0 = min(rect.x for rect in items) - pad
    y0 = min(rect.y for rect in items) - pad
    x1 = max(rect.x + rect.w for rect in items) + pad
    y1 = max(rect.y + rect.h for rect in items) + pad
    return x0, y0, x1 - x0, y1 - y0


def layout_toolbar(anchor_x, anchor_y, scale, text_data, context=None):
    """Compute screen rects for a two-row HUD (sliders on top, tools below)."""
    slider_items = build_slider_row_items()
    tool_items = build_tool_row_items()
    _update_item_labels(slider_items + tool_items, text_data, context)

    row_gap = _ROW_GAP * scale
    row1_rects, row1_w, row_h = _layout_items_row(slider_items, anchor_x, anchor_y, scale)
    row2_y = anchor_y - row_h - row_gap
    row2_rects, row2_w, _row2_h = _layout_items_row(tool_items, anchor_x, row2_y, scale)

    strike_rects = layout_strike_panel(anchor_x, row2_y, row_h, scale, text_data, row2_rects)
    all_rects = row1_rects + row2_rects + strike_rects
    total_w = max(row1_w, row2_w)
    total_h = row_h * 2 + row_gap
    if strike_rects:
        total_h += _STRIKE_PANEL_GAP * scale + row_h

    return {
        "rects": all_rects,
        "row1_rects": row1_rects,
        "row2_rects": row2_rects,
        "strike_rects": strike_rects,
        "total_w": total_w,
        "row_h": row_h,
        "row_gap": row_gap,
        "total_h": total_h,
    }


def layout_strike_panel(_anchor_x, _tool_row_y, _row_h, scale, text_data, tool_rects):
    """Strikethrough position slider below the S button, like the style preset picker."""
    from ..utils.text_format import is_strike_active, strike_position_display

    if text_data is None or not is_strike_active(text_data):
        return []

    strike_rect = next((rect for rect in tool_rects if rect.id == "strike"), None)
    if strike_rect is None:
        return []

    panel_w = _STRIKE_PANEL_WIDTH * scale
    panel_h = slider_row_height(scale)
    gap = _STRIKE_PANEL_GAP * scale
    x = strike_rect.x + strike_rect.w * 0.5 - panel_w * 0.5
    y = strike_rect.y - gap - panel_h

    pos = float(text_data.text_helper.th_strike_position)
    item = HudItem(
        "strike_position",
        "spacing_slider",
        strike_position_display(pos),
        width=_STRIKE_PANEL_WIDTH,
        op="font.texthelper_set_spacing_value",
        op_kwargs={"mode": "STRIKE_POS"},
        title_key="Strike Pos",
        tip_key="Adjust strikethrough line position (↺ resets to default)",
        reset_mode="STRIKE_POS",
    )
    return [HudRect(item.id, x, y, panel_w, panel_h, item)]


def get_hud_item_rect(item_id, context=None):
    rects = get_cached_hud_rects(context) if context is not None else []
    if not rects:
        rects = _LAST_RECTS
    for rect in rects:
        if rect.id == item_id:
            return rect
    return None


def hit_test(rects, mx, my):
    for rect in reversed(rects):
        if rect.x <= mx <= rect.x + rect.w and rect.y <= my <= rect.y + rect.h:
            return rect
    return None


def slider_header_top(rect, scale):
    return rect.y + rect.h - _SLIDER_HEADER_TOP * scale


def slider_header_font_size(scale):
    return int(_SLIDER_HEADER_FONT * scale)


def slider_header_position_y(rect, scale, font_size, text, font_id=0):
    """Return blf Y so the top of `text` sits below slider_header_top."""
    blf.size(font_id, int(font_size))
    _, th = blf.dimensions(font_id, text or "字")
    return slider_header_top(rect, scale) - th


def slider_track_y(rect, scale):
    return rect.y + _SLIDER_TRACK_BOTTOM * scale


def slider_value_right_edge(rect):
    return slider_track_end(rect)


def slider_value_left_x(rect, scale, font_size, value_text, font_id=0):
    """Left X for value text so it is right-aligned to the slider panel edge."""
    blf.size(font_id, int(font_size))
    tw, _ = blf.dimensions(font_id, value_text or "0")
    return slider_value_right_edge(rect) - tw


def slider_track_start(rect, scale=1.0, title="", value=""):
    del title, value
    return rect.x + _SLIDER_PAD * scale


def slider_track_bounds(rect, scale, item):
    del item
    x0 = slider_track_start(rect, scale)
    return x0, slider_track_end(rect)


def slider_track_end(rect):
    return rect.x + rect.w - 20.0


def slider_reset_x(rect):
    return rect.x + rect.w - 18.0


def slider_row_center(rect, scale):
    track_y = slider_track_y(rect, scale)
    return track_y + 1.5 * scale


def slider_reset_hit(rect, mx, my):
    reset_x0 = slider_reset_x(rect)
    return reset_x0 <= mx <= rect.x + rect.w - 2.0 and rect.y <= my <= rect.y + rect.h


def slider_value_field_contains(rect, mx, my, scale, value_text, font_id=0):
    """Hit-test the editable value label on the right of a spacing slider."""
    if mx < 0.0 or my < 0.0:
        return False
    header_size = slider_header_font_size(scale)
    left = slider_value_left_x(rect, scale, header_size, value_text, font_id)
    right = slider_value_right_edge(rect)
    top = slider_header_top(rect, scale)
    blf.size(font_id, int(header_size))
    _, th = blf.dimensions(font_id, value_text or "0")
    bottom = top - th - 2.0 * scale
    pad = 4.0 * scale
    return (left - pad) <= mx <= (right + pad) and bottom <= my <= (top + pad)


def spacing_slider_t(text_data, item_id):
    from ..utils.text_format import (
        char_spacing_display_bounds,
        format_size_slider_t,
        line_height_display_max,
        spacing_display_line,
        spacing_display_char,
        spacing_display_word,
        LINE_HEIGHT_DISPLAY_MIN,
        shear_slider_t,
        strike_position_slider_t,
        word_spacing_display_bounds,
    )

    if item_id == "font_size":
        return format_size_slider_t(text_data.size if text_data is not None else 1.0)
    if item_id == "char_spacing":
        cur = spacing_display_char(text_data.space_character) if text_data is not None else 0
        lo, hi = char_spacing_display_bounds(cur)
        span = max(1.0, float(hi - lo))
        return max(0.0, min(1.0, (cur - lo) / span))
    if item_id == "word_spacing":
        cur = spacing_display_word(text_data.space_word) if text_data is not None else 0
        lo, hi = word_spacing_display_bounds(cur)
        span = max(1.0, float(hi - lo))
        return max(0.0, min(1.0, (cur - lo) / span))
    if item_id == "line_height":
        dmax = line_height_display_max(text_data)
        dmin = LINE_HEIGHT_DISPLAY_MIN
        span = max(1.0, float(dmax - dmin))
        return max(0.0, min(1.0, (spacing_display_line(text_data) - dmin) / span))
    if item_id == "shear":
        return shear_slider_t(text_data.shear if text_data is not None else 0.0)
    if item_id == "strike_position":
        pos = float(text_data.text_helper.th_strike_position) if text_data is not None else 0.4
        return strike_position_slider_t(pos)
    return 0.0


def slider_value_from_mouse(rect, mx, text_data, item_id, scale=1.0):
    from ..utils.text_format import (
        char_spacing_display_bounds,
        format_size_from_slider_t,
        line_height_display_max,
        LINE_HEIGHT_DISPLAY_MIN,
        shear_from_slider_t,
        spacing_display_char,
        spacing_display_word,
        strike_position_from_slider_t,
        word_spacing_display_bounds,
    )

    item = rect.item
    track_x0, track_x1 = slider_track_bounds(rect, scale, item)
    if track_x1 <= track_x0:
        return 0
    t = (mx - track_x0) / (track_x1 - track_x0)
    t = max(0.0, min(1.0, t))
    if item_id == "font_size":
        current = text_data.size if text_data is not None else 1.0
        return format_size_from_slider_t(t, current)
    if item_id == "char_spacing":
        cur = spacing_display_char(text_data.space_character) if text_data is not None else 0
        lo, hi = char_spacing_display_bounds(cur)
        return int(round(lo + t * (hi - lo)))
    if item_id == "word_spacing":
        cur = spacing_display_word(text_data.space_word) if text_data is not None else 0
        lo, hi = word_spacing_display_bounds(cur)
        return int(round(lo + t * (hi - lo)))
    if item_id == "line_height":
        dmax = line_height_display_max(text_data)
        dmin = LINE_HEIGHT_DISPLAY_MIN
        return int(round(dmin + t * (dmax - dmin)))
    if item_id == "shear":
        current = text_data.shear if text_data is not None else 0.0
        return shear_from_slider_t(t, current)
    if item_id == "strike_position":
        return strike_position_from_slider_t(t)
    return 0
