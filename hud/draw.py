"""GPU drawing for the floating text toolbar."""

import blf
import bpy
import gpu

from ..i18n import _
from ..utils.addon_prefs import get_addon_prefs
from ..utils.text_bounds import get_toolbar_anchor
from ..utils.text_format import get_active_text
from ..utils.toolbar_ui import tool_item_pressed as _is_toggle_on
from ..hud.hit_test import hud_enabled
from .gpu_primitives import draw_rounded_rect
from .tooltip import draw_hud_tooltip
from . import layout as layout_mod
from .layout import (
    layout_toolbar,
    slider_header_font_size,
    slider_header_position_y,
    slider_reset_x,
    slider_row_center,
    slider_row_height,
    slider_track_end,
    slider_track_start,
    slider_track_y,
    spacing_slider_t,
)
from .font_picker import draw_font_picker, picker_open as font_picker_open
from .weight_picker import draw_weight_picker, picker_open as weight_picker_open
from .preset_picker import draw_preset_picker, picker_open as preset_picker_open
from .language_picker import draw_language_picker, picker_open as language_picker_open
from .blf_layout import (
    draw_centered_glyph,
    dropdown_text_max_width,
    fit_dropdown_label,
    text_visual_center_y,
    toolbar_baseline_y,
    toolbar_font_size,
)

_DRAW_HANDLE = None
_FONT_ID = 0


def _prefs(context):
    return get_addon_prefs(context)


def _ui_scale(context):
    prefs = _prefs(context)
    return max(context.preferences.system.ui_scale, 0.5) * prefs.hud_scale


def _toolbar_colors(context):
    from ..utils.hud_theme import get_toolbar_draw_colors

    return get_toolbar_draw_colors(context)


def _is_view3d_draw_context(context):
    region = context.region
    region_3d = context.region_data
    space = getattr(context, "space_data", None)
    if region is None or region_3d is None:
        return False
    if space is not None and getattr(space, "type", None) != "VIEW_3D":
        return False
    return True


def _hud_state(context):
    wm = context.window_manager
    return getattr(wm, "th_state", None)


def _draw_lines(shader, segments, color):
    if not segments:
        return
    from gpu_extras.batch import batch_for_shader

    batch = batch_for_shader(shader, "LINES", {"pos": segments})
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def _draw_align_icon(shader, rect, align, color, scale):
    cx = rect.x + rect.w * 0.5
    cy = rect.y + rect.h * 0.5
    gap = 4.5 * scale
    widths = (12.0 * scale, 9.0 * scale, 6.0 * scale)
    segments = []
    for i, lw in enumerate(widths):
        y = cy - gap + i * gap
        if align == "LEFT":
            x0 = cx - 7.0 * scale
            x1 = x0 + lw
        elif align == "RIGHT":
            x1 = cx + 7.0 * scale
            x0 = x1 - lw
        else:
            x0 = cx - lw * 0.5
            x1 = cx + lw * 0.5
        segments.extend([(x0, y), (x1, y)])
    _draw_lines(shader, segments, color)


def _draw_underline_glyph(shader, rect, baseline_y, color, scale):
    cx = rect.x + rect.w * 0.5
    cy = baseline_y - 3.0 * scale
    half = 5.0 * scale
    _draw_lines(shader, [(cx - half, cy), (cx + half, cy)], color)


def _draw_strike_glyph(shader, rect, center_y, color, scale):
    cx = rect.x + rect.w * 0.5
    half = 5.0 * scale
    _draw_lines(shader, [(cx - half, center_y), (cx + half, center_y)], color)


def _draw_drag_grip(shader, rect, color, scale):
    dot_d = 3.2 * scale
    dot_r = dot_d * 0.5
    gap_x = 4.0 * scale
    gap_y = 4.0 * scale
    cols, rows = 2, 3
    grid_w = dot_d + (cols - 1) * gap_x
    grid_h = dot_d + (rows - 1) * gap_y
    x0 = rect.x + (rect.w - grid_w) * 0.5
    y0 = rect.y + (rect.h - grid_h) * 0.5
    for row in range(rows):
        for col in range(cols):
            dot_x = x0 + col * gap_x
            dot_y = y0 + (rows - 1 - row) * gap_y
            draw_rounded_rect(shader, dot_x, dot_y, dot_d, dot_d, color, dot_r)


def _draw_default_case_glyph(shader, rect, color, scale):
    cx = rect.x + rect.w * 0.5
    cy = rect.y + rect.h * 0.5
    half = 5.5 * scale
    _draw_lines(shader, [(cx - half, cy - half), (cx + half, cy + half)], color)


def _draw_chevron(x, baseline_y, scale, color):
    font_size = toolbar_font_size(scale)
    blf.size(_FONT_ID, font_size)
    blf.color(_FONT_ID, *color)
    blf.position(_FONT_ID, x, baseline_y, 0)
    blf.draw(_FONT_ID, "▼")


def _is_active(item, text_data):
    from ..utils.toolbar_ui import _is_active_check

    return _is_active_check(text_data, item.active_check)


def _title_for_item(item):
    if item.title_key:
        return _(item.title_key)
    return ""


def _tip_for_item(item):
    if item.tip_key:
        return _(item.tip_key)
    return ""


def _dropdown_picker_open(context, item_id):
    if item_id == "preset":
        return preset_picker_open(context)
    if item_id == "font":
        return font_picker_open(context)
    if item_id == "font_weight":
        return weight_picker_open(context)
    return False


def _label_color(colors, *, highlight=False, surface="btn"):
    from ..utils.hud_theme import theme_text_color

    return theme_text_color(colors, highlighted=highlight, surface=surface)


def _draw_spacing_slider(shader, rect, item, text_data, scale, accent, colors, context):
    from .slider_input import draw_slider_value_field

    title = _title_for_item(item)
    pad = 8.0 * scale
    header_size = slider_header_font_size(scale)
    header_y = slider_header_position_y(rect, scale, header_size, title, _FONT_ID)
    label_color = _label_color(colors, surface="panel")
    track_color = colors.get("slider_track", (0.28, 0.28, 0.30, 1.0))

    blf.size(_FONT_ID, header_size)
    blf.color(_FONT_ID, *label_color)
    blf.position(_FONT_ID, rect.x + pad, header_y, 0)
    blf.draw(_FONT_ID, title)

    draw_slider_value_field(shader, rect, item, scale, accent, colors, context, font_id=_FONT_ID)

    track_y = slider_track_y(rect, scale)
    track_h = 3.0 * scale
    row_center = slider_row_center(rect, scale)
    track_x0 = slider_track_start(rect, scale)
    track_x1 = slider_track_end(rect)
    t = spacing_slider_t(text_data, item.id)
    draw_rounded_rect(shader, track_x0, track_y, track_x1 - track_x0, track_h, track_color, 1.5 * scale)
    thumb_x = track_x0 + (track_x1 - track_x0) * t - 3 * scale
    draw_rounded_rect(shader, thumb_x, track_y - 2 * scale, 6 * scale, 7 * scale, accent, 2.0 * scale)

    if item.reset_mode:
        blf.size(_FONT_ID, int(10 * scale))
        blf.color(_FONT_ID, *label_color)
        reset_x = slider_reset_x(rect)
        _, reset_h = blf.dimensions(_FONT_ID, "↺")
        blf.position(_FONT_ID, reset_x, row_center - reset_h * 0.5, 0)
        blf.draw(_FONT_ID, "↺")


def draw_hud():
    context = bpy.context
    prefs = _prefs(context)
    if not hud_enabled(context):
        layout_mod._LAST_RECTS = []
        return
    if not _is_view3d_draw_context(context):
        return

    from ..ops.hud_modal import modal_running, sync_modal_running_state
    from ..runtime import request_ensure

    sync_modal_running_state(context)
    if not modal_running():
        request_ensure(context)

    obj = get_active_text(context)
    if obj is None:
        layout_mod._LAST_RECTS = []
        return

    text_data = obj.data
    anchor = get_toolbar_anchor(context, obj, prefs.toolbar_offset)
    if anchor is None:
        return

    scale = _ui_scale(context)
    layout = layout_toolbar(anchor[0], anchor[1], scale, text_data, context)
    rects = layout["rects"]
    row1_rects = layout["row1_rects"]
    row2_rects = layout["row2_rects"]
    strike_rects = layout["strike_rects"]
    layout_mod._LAST_RECTS = rects

    gpu.state.blend_set("ALPHA")
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    colors = _toolbar_colors(context)
    accent = colors["accent"]
    btn_active = colors["btn_active"]
    drag_active = colors["drag_active"]
    bg = colors["bg"]
    btn = colors["btn"]
    btn_hover = colors["btn_hover"]
    muted = colors["muted"]
    radius = 8.0 * scale
    btn_radius = 5.0 * scale

    pad = 4.0 * scale
    for row_rects in (row1_rects, row2_rects):
        bounds = layout_mod.row_bounds(row_rects, pad)
        if bounds is None:
            continue
        bx, by, bw, bh = bounds
        draw_rounded_rect(shader, bx, by, bw, bh, bg, radius)

    for strike_rect in strike_rects:
        draw_rounded_rect(
            shader,
            strike_rect.x - pad,
            strike_rect.y - pad,
            strike_rect.w + pad * 2,
            strike_rect.h + pad * 2,
            bg,
            radius,
        )

    state = _hud_state(context)
    hover_id = state.th_hud_hover_id if state else ""
    moving = state.th_hud_moving if state else False

    for rect in rects:
        item = rect.item
        if item.kind == "separator":
            draw_rounded_rect(shader, rect.x, rect.y, rect.w, rect.h, (0.35, 0.35, 0.38, 0.5), 1.0 * scale)
            continue

        is_hover = hover_id == rect.id
        is_on = _is_toggle_on(item, text_data) or _is_active(item, text_data)
        picker_open = item.kind == "dropdown" and _dropdown_picker_open(context, item.id)
        text_highlight = is_on or is_hover or picker_open or (item.kind == "drag" and moving)
        color = btn
        if item.kind == "drag":
            if moving or is_hover:
                color = drag_active
            else:
                color = btn
        elif is_on or picker_open:
            color = btn_active
        elif is_hover:
            color = btn_hover
        draw_rounded_rect(shader, rect.x, rect.y, rect.w, rect.h, color, btn_radius)

        if item.kind == "drag":
            grip_color = _label_color(colors, highlight=text_highlight, surface="btn")
            _draw_drag_grip(shader, rect, grip_color, scale)

        elif item.kind == "dropdown":
            font_size = toolbar_font_size(scale)
            baseline_y = toolbar_baseline_y(rect, _FONT_ID, font_size)
            blf.size(_FONT_ID, font_size)
            blf.color(_FONT_ID, *_label_color(colors, highlight=text_highlight, surface="btn"))
            text_max_w = dropdown_text_max_width(rect.w, scale)
            display_label = fit_dropdown_label(_FONT_ID, item.label, font_size, text_max_w)
            blf.position(_FONT_ID, rect.x + 8 * scale, baseline_y, 0)
            blf.draw(_FONT_ID, display_label)
            chevron_w, _ = blf.dimensions(_FONT_ID, "▼")
            _draw_chevron(
                rect.x + rect.w - 8 * scale - chevron_w,
                baseline_y,
                scale,
                _label_color(colors, highlight=text_highlight, surface="btn"),
            )

        elif item.kind == "toggle":
            icon_color = _label_color(colors, highlight=text_highlight, surface="btn")
            if item.id.startswith("align_"):
                align = item.id.replace("align_", "").upper()
                _draw_align_icon(shader, rect, align, icon_color, scale)
            elif item.id == "case_default":
                _draw_default_case_glyph(shader, rect, icon_color, scale)
            else:
                font_size = toolbar_font_size(scale)
                label = item.label
                baseline_y = toolbar_baseline_y(rect, _FONT_ID, font_size)
                blf.size(_FONT_ID, font_size)
                blf.color(_FONT_ID, *icon_color)
                tw, _ = blf.dimensions(_FONT_ID, label)
                blf.position(
                    _FONT_ID,
                    rect.x + (rect.w - tw) * 0.5,
                    baseline_y,
                    0,
                )
                blf.draw(_FONT_ID, label)
                if item.id == "underline":
                    _draw_underline_glyph(
                        shader,
                        rect,
                        baseline_y,
                        icon_color,
                        scale,
                    )
                elif item.id == "strike":
                    _draw_strike_glyph(
                        shader,
                        rect,
                        text_visual_center_y(_FONT_ID, label, baseline_y),
                        icon_color,
                        scale,
                    )

        elif item.kind == "spacing_slider":
            _draw_spacing_slider(shader, rect, item, text_data, scale, accent, colors, context)

        elif item.kind == "button":
            font_size = max(int(round(13.0 * scale)), 9)
            draw_centered_glyph(
                rect,
                _FONT_ID,
                font_size,
                item.label,
                _label_color(colors, highlight=is_hover, surface="btn"),
            )

    if hover_id:
        hover_rect = next((r for r in rects if r.id == hover_id), None)
        if hover_rect is not None and hover_rect.item.kind != "separator":
            tip = _tip_for_item(hover_rect.item)
            if tip:
                region_w = context.region.width if context.region else 1920
                draw_hud_tooltip(shader, _FONT_ID, hover_rect, tip, scale, region_w, accent)

    gpu.state.blend_set("NONE")

    if font_picker_open(context):
        draw_font_picker(context)
    if weight_picker_open(context):
        draw_weight_picker(context)
    if preset_picker_open(context):
        draw_preset_picker(context)
    if language_picker_open(context):
        draw_language_picker(context)


def tag_redraw():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def register():
    global _DRAW_HANDLE
    if _DRAW_HANDLE is None:
        _DRAW_HANDLE = bpy.types.SpaceView3D.draw_handler_add(draw_hud, (), "WINDOW", "POST_PIXEL")


def unregister():
    global _DRAW_HANDLE
    if _DRAW_HANDLE is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_DRAW_HANDLE, "WINDOW")
        except (ValueError, ReferenceError):
            pass
        _DRAW_HANDLE = None
