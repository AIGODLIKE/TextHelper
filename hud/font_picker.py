"""GPU font picker panel in the 3D viewport."""

import os
import time
from collections import OrderedDict

import blf
import bpy

from ..i18n import _
from ..utils.addon_prefs import get_addon_prefs
from ..utils.font_glyph import (
    font_has_full_coverage,
    glyph_status_for_font_id,
    invalidate_glyph_cache,
    register_blf_unload_hook,
    unregister_blf_unload_hook,
)
from ..utils.font_blf import blf_load, blf_unload, font_path_usable
from ..utils.font_loader import is_current_font, queue_font_catalog
from ..utils.font_family import family_weight_counts, group_catalog_items
from ..utils.view3d_context import run_active_font_op
from ..utils.font_language import (
    catalog_item_passes_language,
    catalog_item_passes_name,
    get_language_filter,
    get_language_label,
)
from ..utils.font_preview_draw import draw_blf_preview
from ..utils.font_preview_text import get_font_preview_text
from ..utils.text_format import get_active_text_data
from . import layout as layout_mod
from .gpu_primitives import draw_rounded_rect
from .blf_layout import draw_centered_glyph

_UI_FONT = 0
_PICKER_BLF_LOADED = OrderedDict()
_PICKER_BLF_MAX = 8
_BLF_HOOKS_REGISTERED = False
_LAST_LAYOUT = None
_WHEEL_ROWS = 3
_HOVER_APPLY_INDEX = -1
_CARET_TIMER = None


class PickerHit:
    __slots__ = ("kind", "index", "x", "y", "w", "h")

    def __init__(self, kind, x, y, w, h, index=-1):
        self.kind = kind
        self.index = index
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def contains(self, mx, my):
        return self.x <= mx <= self.x + self.w and self.y <= my <= self.y + self.h


def _state(context):
    return getattr(context.window_manager, "th_state", None)


def picker_open(context):
    state = _state(context)
    return bool(state and getattr(state, "th_font_picker_open", False))


def _ui_scale(context):
    prefs = get_addon_prefs(context)
    return max(context.preferences.system.ui_scale, 0.5) * prefs.hud_scale


def _theme(context):
    from ..utils.hud_theme import get_accent_active_bg, get_accent_rgba

    prefs = get_addon_prefs(context)
    accent = get_accent_rgba(prefs)
    return {
        "accent": accent,
        "panel_bg": (0.08, 0.08, 0.09, 0.98),
        "header_bg": (0.10, 0.10, 0.11, 1.0),
        "list_bg": (0.11, 0.11, 0.12, 1.0),
        "row_bg": (0.14, 0.14, 0.15, 1.0),
        "row_hover": (0.22, 0.22, 0.24, 1.0),
        "row_active": get_accent_active_bg(accent),
        "field_bg": (0.12, 0.13, 0.14, 1.0),
        "field_focus": (0.18, 0.18, 0.20, 1.0),
        "border": (0.28, 0.28, 0.30, 0.9),
        "scroll_track": (0.16, 0.16, 0.17, 1.0),
        "scroll_thumb": (0.38, 0.38, 0.40, 1.0),
        "text": (0.95, 0.95, 0.96, 1.0),
        "muted": (0.55, 0.55, 0.58, 1.0),
        "warn": (0.96, 0.42, 0.30, 1.0),
    }


def _preview_point_size(context, scale):
    prefs = get_addon_prefs(context)
    pref_size = int(getattr(prefs, "font_preview_size", 36))
    return max(14.0, pref_size * 0.45 * scale)


def _preview_text(context, display_name=""):
    return get_font_preview_text(context, display_name)


def _picker_text_data(context):
    obj = context.active_object
    if obj and obj.type == "FONT":
        return obj.data
    return get_active_text_data(context)


def _font_supports_preview(item, preview, point_size):
    if not preview:
        return True
    return font_has_full_coverage(item.filepath, preview, point_size)


def _release_picker_blf():
    for key in list(_PICKER_BLF_LOADED.keys()):
        try:
            blf_unload(key)
        except Exception:
            pass
    _PICKER_BLF_LOADED.clear()


def _acquire_picker_blf(filepath):
    abs_path = bpy.path.abspath(filepath)
    if not os.path.isfile(abs_path):
        return -1
    if not font_path_usable(abs_path):
        return -1
    key = os.path.normcase(abs_path)
    cached = _PICKER_BLF_LOADED.get(key)
    if cached is not None:
        _PICKER_BLF_LOADED.move_to_end(key)
        return cached

    while len(_PICKER_BLF_LOADED) >= _PICKER_BLF_MAX:
        evict_key, _ = _PICKER_BLF_LOADED.popitem(last=False)
        try:
            blf_unload(evict_key)
        except Exception:
            pass

    font_id = blf_load(abs_path)
    if font_id == -1:
        return -1
    _PICKER_BLF_LOADED[key] = font_id
    return font_id


def _picker_position(context, panel_w, panel_h, scale):
    region = context.region
    margin = 10.0 * scale
    gap = 6.0 * scale
    font_rect = layout_mod.get_hud_item_rect("font")
    if font_rect is not None:
        px = font_rect.x
        panel_top = font_rect.y - gap
        py = panel_top - panel_h
        px = max(margin, min(px, region.width - panel_w - margin))
        py = max(margin, py)
        return px, py
    px = max(margin, region.width * 0.5 - panel_w * 0.5)
    py = max(margin, region.height - 56.0 * scale - panel_h)
    return px, py


def _panel_width(scale):
    return min(480.0 * scale, max(360.0 * scale, layout_mod.FONT_DROPDOWN_WIDTH * 2.8 * scale))


def _filtered_items(wm, context=None):
    catalog = getattr(wm.th_state, "font_catalog", None)
    if not catalog:
        return []
    filt = (wm.th_state.font_filter or "").strip().lower()
    sort_mode = wm.th_state.font_sort or "NAME_AZ"
    lang = get_language_filter(wm)
    state = getattr(wm, "th_state", None)
    hide_unsupported = bool(state and getattr(state, "th_font_picker_hide_unsupported", True))
    multi_weight_only = bool(state and getattr(state, "th_font_picker_multi_weight_only", False))
    preview = _preview_text(context) if context is not None else ""
    point_size = _preview_point_size(context, _ui_scale(context)) if context is not None else 24.0
    indexed = []
    try:
        for i, item in enumerate(catalog):
            if not catalog_item_passes_name(item, filt):
                continue
            if not catalog_item_passes_language(item, lang, point_size):
                continue
            item_preview = _preview_text(context, item.display_name) if context is not None else preview
            if hide_unsupported and item_preview and not _font_supports_preview(item, item_preview, point_size):
                continue
            indexed.append((i, item))
    finally:
        _release_picker_blf()
    groups = group_catalog_items(indexed)
    if multi_weight_only:
        counts = family_weight_counts(catalog)
        groups = [group for group in groups if counts.get(group.family_key, 0) > 1]
    reverse = sort_mode == "NAME_ZA"
    groups.sort(key=lambda group: group.display_name.lower(), reverse=reverse)
    return groups


def _group_is_active(text_data, group):
    if text_data is None or text_data.font is None:
        return False
    return any(is_current_font(text_data, variant.filepath) for variant in group.variants)


def _on_external_blf_unload(abs_path):
    key = os.path.normcase(bpy.path.abspath(abs_path))
    if key in _PICKER_BLF_LOADED:
        _PICKER_BLF_LOADED.pop(key, None)


def release_blf_cache():
    global _BLF_HOOKS_REGISTERED
    _release_picker_blf()
    invalidate_glyph_cache()
    if _BLF_HOOKS_REGISTERED:
        unregister_blf_unload_hook(_on_external_blf_unload)
        _BLF_HOOKS_REGISTERED = False


def _ensure_picker_blf_hooks():
    global _BLF_HOOKS_REGISTERED
    if _BLF_HOOKS_REGISTERED:
        return
    register_blf_unload_hook(_on_external_blf_unload)
    _BLF_HOOKS_REGISTERED = True


def reset_picker_hover_apply():
    global _HOVER_APPLY_INDEX
    _HOVER_APPLY_INDEX = -1


def seed_picker_hover_apply(context):
    """Remember the starting font so the first hover does not re-assign it."""
    global _HOVER_APPLY_INDEX
    wm = context.window_manager
    catalog = getattr(wm.th_state, "font_catalog", None)
    text_data = _picker_text_data(context)
    if not catalog or text_data is None:
        _HOVER_APPLY_INDEX = -1
        return
    for i, item in enumerate(catalog):
        if is_current_font(text_data, item.filepath):
            _HOVER_APPLY_INDEX = i
            return
    _HOVER_APPLY_INDEX = -1


def _hover_apply_enabled(context):
    prefs = get_addon_prefs(context)
    return getattr(prefs, "font_preview_on_select", True)


def _invoke_apply_system_font(context, filepath, catalog_index=-1, *, keep_picker_open=False):
    from ..utils.text_format import get_active_text

    obj = get_active_text(context)
    result = {"CANCELLED"}

    def _call():
        nonlocal result
        result = bpy.ops.font.texthelper_apply_system_font(
            filepath=filepath,
            catalog_index=catalog_index,
            keep_picker_open=keep_picker_open,
        )

    if not run_active_font_op(context, _call, obj):
        return False
    return "FINISHED" in result


def _try_hover_apply_font(context, catalog_index):
    global _HOVER_APPLY_INDEX
    if not _hover_apply_enabled(context):
        return False
    if catalog_index == _HOVER_APPLY_INDEX:
        return False

    wm = context.window_manager
    catalog = getattr(wm.th_state, "font_catalog", None)
    if not catalog or catalog_index < 0 or catalog_index >= len(catalog):
        return False

    item = catalog[catalog_index]
    text_data = _picker_text_data(context)
    if text_data is not None and is_current_font(text_data, item.filepath):
        _HOVER_APPLY_INDEX = catalog_index
        return False

    if not _invoke_apply_system_font(
        context,
        item.filepath,
        catalog_index,
        keep_picker_open=True,
    ):
        return False
    _HOVER_APPLY_INDEX = catalog_index
    return True


def focus_search_field(context):
    """Focus the GPU search field and start the caret blink timer."""
    state = _state(context)
    if state is None:
        return
    state.th_font_picker_search_focus = True
    _start_caret_timer()


def picker_search_blocks_keymap(event):
    """Return True when a keyboard event should not reach Blender keymaps."""
    if event.type in {
        "LEFTMOUSE",
        "RIGHTMOUSE",
        "MIDDLEMOUSE",
        "MOUSEMOVE",
        "WHEELUPMOUSE",
        "WHEELDOWNMOUSE",
        "INBETWEEN_MOUSEMOVE",
        "TIMER",
        "TIMER_REPORT",
        "NONE",
    }:
        return False
    if getattr(event, "is_mouse_type", False):
        return False
    return event.value in {"PRESS", "REPEAT"}


def close_picker(context):
    reset_picker_hover_apply()
    _stop_caret_timer()
    state = _state(context)
    if state is None:
        return
    state.th_font_picker_open = False
    state.th_font_picker_search_focus = False
    state.th_font_picker_scroll_drag = False
    state.th_font_picker_hover = -1
    try:
        from .language_picker import close_picker as close_language_picker

        close_language_picker(context)
    except Exception:
        pass
    release_blf_cache()


def _scrollbar_geometry(layout):
    if not layout:
        return None
    scale = layout["scale"]
    items = layout["items"]
    visible_rows = layout["visible_rows"]
    list_y = layout["list_y"]
    list_h = layout["list_h"]
    list_top = layout["list_top"]
    track_x = layout["scrollbar_x"]
    track_w = layout["scrollbar_w"]
    track_y = list_y
    total = max(1, len(items))
    thumb_h = max(24.0 * scale, list_h * min(1.0, visible_rows / total))
    max_scroll = layout["max_scroll"]
    scroll = layout["scroll"]
    if max_scroll <= 0:
        thumb_y = list_top - thumb_h
    else:
        travel = max(1.0, list_h - thumb_h)
        thumb_y = list_top - thumb_h - travel * (scroll / max_scroll)
    return {
        "track_x": track_x,
        "track_y": track_y,
        "track_w": track_w,
        "track_h": list_h,
        "thumb_x": track_x,
        "thumb_y": thumb_y,
        "thumb_w": track_w,
        "thumb_h": thumb_h,
        "list_top": list_top,
    }


def layout_picker(context):
    global _LAST_LAYOUT
    wm = context.window_manager
    region = context.region
    if region is None:
        _LAST_LAYOUT = None
        return None

    scale = _ui_scale(context)
    panel_w = _panel_width(scale)
    pad = 12.0 * scale
    header_h = 40.0 * scale
    search_h = 30.0 * scale
    filter_row_h = 28.0 * scale
    filter_row_gap = 4.0 * scale
    filter_h = filter_row_h * 2 + filter_row_gap
    row_h = 52.0 * scale
    footer_h = 22.0 * scale
    scrollbar_w = 8.0 * scale
    visible_rows = 7
    list_h = row_h * visible_rows
    panel_h = header_h + search_h + filter_h + list_h + footer_h + pad * 0.5
    px, py = _picker_position(context, panel_w, panel_h, scale)
    panel_top = py + panel_h

    state = _state(context)
    scroll = max(0, int(getattr(state, "th_font_picker_scroll", 0))) if state else 0

    items = _filtered_items(wm, context)
    max_scroll = max(0, len(items) - visible_rows)
    scroll = min(scroll, max_scroll)

    header_y = panel_top - header_h
    search_y = header_y - search_h
    filter_y = search_y - filter_h
    list_top = filter_y
    list_y = list_top - list_h
    list_x = px + pad
    list_w = panel_w - pad * 2 - scrollbar_w - 4.0 * scale
    scrollbar_x = px + panel_w - pad - scrollbar_w
    chip_inset = 4.0 * scale
    chip_h = filter_row_h - 8.0 * scale
    filter_row1_y = filter_y + chip_inset
    filter_row2_y = filter_y + filter_row_h + filter_row_gap + chip_inset
    hide_chip_w = 118.0 * scale
    multi_chip_w = 132.0 * scale
    chip_gap = 6.0 * scale

    hits = []
    hits.append(PickerHit("panel", px, py, panel_w, panel_h))
    hits.append(
        PickerHit(
            "close",
            px + panel_w - pad - 20.0 * scale,
            panel_top - 26.0 * scale,
            18.0 * scale,
            18.0 * scale,
        )
    )

    hits.append(
        PickerHit("search", list_x, search_y + 4.0 * scale, panel_w - pad * 2, search_h - 8.0 * scale)
    )

    hits.append(
        PickerHit(
            "filter_toggle",
            list_x,
            filter_row1_y,
            hide_chip_w,
            chip_h,
        )
    )
    hits.append(
        PickerHit(
            "multi_weight_toggle",
            list_x + hide_chip_w + chip_gap,
            filter_row1_y,
            multi_chip_w,
            chip_h,
        )
    )
    hits.append(
        PickerHit(
            "language_menu",
            list_x,
            filter_row2_y,
            panel_w - pad * 2,
            chip_h,
        )
    )

    row_hits = []
    for row in range(visible_rows):
        idx = scroll + row
        if idx >= len(items):
            break
        group = items[idx]
        catalog_index = group.representative_index
        ry = list_top - (row + 1) * row_h + 2.0 * scale
        rect = PickerHit("row", list_x, ry, list_w, row_h - 4.0 * scale, catalog_index)
        row_hits.append(rect)
        hits.append(rect)

    sb = _scrollbar_geometry(
        {
            "scale": scale,
            "items": items,
            "visible_rows": visible_rows,
            "list_y": list_y,
            "list_h": list_h,
            "list_top": list_top,
            "scrollbar_x": scrollbar_x,
            "scrollbar_w": scrollbar_w,
            "max_scroll": max_scroll,
            "scroll": scroll,
        }
    )
    if sb and len(items) > visible_rows:
        hits.append(PickerHit("scroll_track", sb["track_x"], sb["track_y"], sb["track_w"], sb["track_h"]))
        hits.append(PickerHit("scroll_thumb", sb["thumb_x"], sb["thumb_y"], sb["thumb_w"], sb["thumb_h"]))

    _LAST_LAYOUT = {
        "scale": scale,
        "px": px,
        "py": py,
        "panel_top": panel_top,
        "panel_w": panel_w,
        "panel_h": panel_h,
        "pad": pad,
        "header_h": header_h,
        "header_y": header_y,
        "search_h": search_h,
        "search_y": search_y,
        "filter_h": filter_h,
        "filter_y": filter_y,
        "filter_row_h": filter_row_h,
        "row_h": row_h,
        "footer_h": footer_h,
        "list_x": list_x,
        "list_y": list_y,
        "list_top": list_top,
        "list_w": list_w,
        "list_h": list_h,
        "scrollbar_x": scrollbar_x,
        "scrollbar_w": scrollbar_w,
        "visible_rows": visible_rows,
        "scroll": scroll,
        "max_scroll": max_scroll,
        "items": items,
        "hits": hits,
        "row_hits": row_hits,
        "scrollbar": sb,
    }
    return _LAST_LAYOUT


def get_last_layout():
    return _LAST_LAYOUT


def get_picker_hits():
    if _LAST_LAYOUT is None:
        return []
    return _LAST_LAYOUT.get("hits", [])


def hit_test_picker(context, mx, my):
    layout_picker(context)
    hits = get_picker_hits()
    for hit in reversed(hits):
        if hit.kind != "panel" and hit.contains(mx, my):
            return hit
    for hit in hits:
        if hit.kind == "panel" and hit.contains(mx, my):
            return hit
    return None


def _draw_field(shader, hit, scale, theme, text, placeholder, focused, accent, cursor=-1):
    bg = theme["field_bg"]
    radius = 5.0 * scale
    draw_rounded_rect(shader, hit.x, hit.y, hit.w, hit.h, bg, radius)
    if focused:
        ring = 1.0 * scale
        draw_rounded_rect(shader, hit.x, hit.y, hit.w, hit.h, (*accent[:3], 0.12), radius)
        draw_rounded_rect(
            shader,
            hit.x + ring,
            hit.y + ring,
            hit.w - ring * 2,
            hit.h - ring * 2,
            bg,
            max(radius - ring, 1.0 * scale),
        )

    font_size = int(11 * scale)
    display = text if text else ""
    label = display if display else placeholder
    blf.size(_UI_FONT, font_size)
    blf.color(_UI_FONT, *(theme["text"] if display else theme["muted"]))
    text_y = hit.y + hit.h * 0.5 - 6.0 * scale
    text_x = hit.x + 8.0 * scale
    blf.position(_UI_FONT, text_x, text_y, 0)
    blf.draw(_UI_FONT, label)

    if focused and display and int(time.time() / 0.5) % 2 == 0:
        caret_at = len(display) if cursor < 0 else max(0, min(cursor, len(display)))
        prefix = display[:caret_at]
        tw, _th = blf.dimensions(_UI_FONT, prefix)
        caret_x = text_x + tw
        caret_h = 12.0 * scale
        draw_rounded_rect(
            shader,
            caret_x,
            hit.y + (hit.h - caret_h) * 0.5,
            max(1.0 * scale, 1.5 * scale),
            caret_h,
            theme["text"],
            0.5 * scale,
        )
    elif focused and not display and int(time.time() / 0.5) % 2 == 0:
        caret_h = 12.0 * scale
        draw_rounded_rect(
            shader,
            text_x,
            hit.y + (hit.h - caret_h) * 0.5,
            max(1.0 * scale, 1.5 * scale),
            caret_h,
            theme["muted"],
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
            state = _state(ctx)
            if state is None or not picker_open(ctx) or not getattr(state, "th_font_picker_search_focus", False):
                _CARET_TIMER = None
                return None
            _tag_redraw()
            return 0.45
        except Exception:
            _CARET_TIMER = None
            return None

    _CARET_TIMER = _tick
    bpy.app.timers.register(_tick, first_interval=0.45)


def _stop_caret_timer():
    global _CARET_TIMER
    if _CARET_TIMER is None:
        return
    try:
        bpy.app.timers.unregister(_CARET_TIMER)
    except Exception:
        pass
    _CARET_TIMER = None


def _draw_preview_line(font_id, text, x, y, max_w, size, theme, glyph_status=None):
    if font_id == -1 or not text:
        return
    draw_blf_preview(
        font_id,
        text,
        x,
        y,
        max_w,
        size,
        theme["text"],
        ui_font=_UI_FONT,
        warn_color=theme.get("warn", (0.96, 0.42, 0.30, 1.0)),
    )


def _tag_redraw():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def draw_font_picker(context):
    if not picker_open(context):
        return
    _ensure_picker_blf_hooks()
    if context.region is None:
        return

    wm = context.window_manager
    queue_font_catalog(wm)
    layout = layout_picker(context)
    if layout is None:
        return

    scale = layout["scale"]
    px = layout["px"]
    py = layout["py"]
    panel_w = layout["panel_w"]
    panel_h = layout["panel_h"]
    pad = layout["pad"]
    state = _state(context)
    hover_index = int(getattr(state, "th_font_picker_hover", -1)) if state else -1
    text_data = _picker_text_data(context)
    preview = _preview_text(context)
    preview_size = _preview_point_size(context, scale)
    theme = _theme(context)
    accent = theme["accent"]

    import gpu

    gpu.state.blend_set("ALPHA")
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")

    panel_top = layout["panel_top"]
    header_y = layout["header_y"]

    draw_rounded_rect(shader, px, py, panel_w, panel_h, theme["panel_bg"], 8.0 * scale)
    draw_rounded_rect(shader, px, header_y, panel_w, layout["header_h"], theme["header_bg"], 8.0 * scale)

    blf.size(_UI_FONT, int(12 * scale))
    blf.color(_UI_FONT, *theme["text"])
    blf.position(_UI_FONT, px + pad, panel_top - 16.0 * scale, 0)
    blf.draw(_UI_FONT, _("Fonts"))

    preview_label = preview if len(preview) <= 28 else preview[:25] + "…"
    blf.size(_UI_FONT, int(9 * scale))
    blf.color(_UI_FONT, *theme["muted"])
    blf.position(_UI_FONT, px + pad, header_y + 6.0 * scale, 0)
    blf.draw(_UI_FONT, _("Preview: {}").format(preview_label))

    close_hit = next((h for h in layout["hits"] if h.kind == "close"), None)
    if close_hit:
        draw_centered_glyph(close_hit, _UI_FONT, int(13 * scale), "×", theme["muted"])

    search_hit = next((h for h in layout["hits"] if h.kind == "search"), None)
    if search_hit:
        search_focus = bool(state and getattr(state, "th_font_picker_search_focus", False))
        query = wm.th_state.font_filter or ""
        _draw_field(shader, search_hit, scale, theme, query, _("Search fonts…"), search_focus, accent)

    filter_hit = next((h for h in layout["hits"] if h.kind == "filter_toggle"), None)
    if filter_hit:
        hide_unsupported = bool(state and getattr(state, "th_font_picker_hide_unsupported", True))
        chip_bg = theme["row_active"] if hide_unsupported else theme["field_bg"]
        draw_rounded_rect(shader, filter_hit.x, filter_hit.y, filter_hit.w, filter_hit.h, chip_bg, 5.0 * scale)
        chip_label = _("Hide unsupported") if hide_unsupported else _("Show all fonts")
        blf.size(_UI_FONT, int(9 * scale))
        blf.color(_UI_FONT, *(theme["text"] if hide_unsupported else theme["muted"]))
        blf.position(_UI_FONT, filter_hit.x + 8.0 * scale, filter_hit.y + filter_hit.h * 0.5 - 5.0 * scale, 0)
        blf.draw(_UI_FONT, chip_label)

    multi_weight_hit = next((h for h in layout["hits"] if h.kind == "multi_weight_toggle"), None)
    if multi_weight_hit:
        multi_weight_only = bool(state and getattr(state, "th_font_picker_multi_weight_only", False))
        chip_bg = theme["row_active"] if multi_weight_only else theme["field_bg"]
        draw_rounded_rect(shader, multi_weight_hit.x, multi_weight_hit.y, multi_weight_hit.w, multi_weight_hit.h, chip_bg, 5.0 * scale)
        chip_label = _("Multi-weight only") if multi_weight_only else _("All font families")
        blf.size(_UI_FONT, int(9 * scale))
        blf.color(_UI_FONT, *(theme["text"] if multi_weight_only else theme["muted"]))
        blf.position(_UI_FONT, multi_weight_hit.x + 8.0 * scale, multi_weight_hit.y + multi_weight_hit.h * 0.5 - 5.0 * scale, 0)
        blf.draw(_UI_FONT, chip_label)

    language_hit = next((h for h in layout["hits"] if h.kind == "language_menu"), None)
    if language_hit:
        lang_code = get_language_filter(wm)
        lang_active = lang_code != "ALL"
        chip_bg = theme["row_active"] if lang_active else theme["field_bg"]
        draw_rounded_rect(shader, language_hit.x, language_hit.y, language_hit.w, language_hit.h, chip_bg, 5.0 * scale)
        chip_label = _("Language: {}").format(_(get_language_label(lang_code)))
        blf.size(_UI_FONT, int(9 * scale))
        blf.color(_UI_FONT, *(theme["text"] if lang_active else theme["muted"]))
        blf.position(_UI_FONT, language_hit.x + 8.0 * scale, language_hit.y + language_hit.h * 0.5 - 5.0 * scale, 0)
        blf.draw(_UI_FONT, chip_label)

    draw_rounded_rect(
        shader,
        layout["list_x"],
        layout["list_y"],
        layout["list_w"] + layout["scrollbar_w"] + 4.0 * scale,
        layout["list_h"],
        theme["field_bg"],
        6.0 * scale,
    )

    items = layout["items"]
    scroll = layout["scroll"]

    try:
        for row, hit in enumerate(layout["row_hits"]):
            idx = scroll + row
            if idx >= len(items):
                break
            group = items[idx]
            item = wm.th_state.font_catalog[group.representative_index]
            active = _group_is_active(text_data, group)
            hovered = group.representative_index == hover_index
            if active:
                bg = theme["row_active"]
            elif hovered:
                bg = theme["row_hover"]
            else:
                bg = theme["row_bg"]
            draw_rounded_rect(shader, hit.x, hit.y, hit.w, hit.h, bg, 5.0 * scale)

            name = group.display_name
            if active:
                name = "✓ " + name
            if group.variant_count > 1:
                name = f"{name}  · {group.variant_count}"
            if len(name) > 26:
                name = name[:23] + "…"
            blf.size(_UI_FONT, int(9 * scale))
            blf.color(_UI_FONT, *theme["muted"])
            blf.position(_UI_FONT, hit.x + 8.0 * scale, hit.y + hit.h - 14.0 * scale, 0)
            blf.draw(_UI_FONT, name)

            row_preview = _preview_text(context, item.display_name)
            font_id = _acquire_picker_blf(item.filepath)
            missing = 0
            if row_preview and font_id != -1:
                glyph_status = glyph_status_for_font_id(font_id, row_preview, preview_size)
                missing = sum(1 for ok in glyph_status if not ok)
            _draw_preview_line(
                font_id, row_preview, hit.x + 8.0 * scale, hit.y + 6.0 * scale, hit.w - 16.0 * scale, preview_size, theme
            )
            if missing > 0:
                warn = _("Missing {:d}").format(missing)
                blf.size(_UI_FONT, int(8 * scale))
                blf.color(_UI_FONT, *theme["warn"])
                tw, _th = blf.dimensions(_UI_FONT, warn)
                blf.position(_UI_FONT, hit.x + hit.w - tw - 6.0 * scale, hit.y + hit.h - 13.0 * scale, 0)
                blf.draw(_UI_FONT, warn)
    finally:
        _release_picker_blf()

    sb = layout.get("scrollbar")
    if sb and len(items) > layout["visible_rows"]:
        draw_rounded_rect(shader, sb["track_x"], sb["track_y"], sb["track_w"], sb["track_h"], theme["scroll_track"], 4.0 * scale)
        thumb_color = theme["accent"] if state and getattr(state, "th_font_picker_scroll_drag", False) else theme["scroll_thumb"]
        draw_rounded_rect(shader, sb["thumb_x"], sb["thumb_y"], sb["thumb_w"], sb["thumb_h"], thumb_color, 4.0 * scale)

    footer_y = py + 6.0 * scale
    blf.size(_UI_FONT, int(8 * scale))
    blf.color(_UI_FONT, *theme["muted"])
    hide_unsupported = bool(state and getattr(state, "th_font_picker_hide_unsupported", True))
    if hide_unsupported:
        count_text = _("{:d} families · □ = missing").format(len(items))
    else:
        count_text = _("{:d} families · □ = missing").format(len(items))
    blf.position(_UI_FONT, px + pad, footer_y, 0)
    blf.draw(_UI_FONT, count_text)

    gpu.state.blend_set("NONE")


def handle_picker_wheel(context, delta):
    state = _state(context)
    layout = _LAST_LAYOUT
    if state is None or layout is None:
        return False
    scroll = int(state.th_font_picker_scroll)
    if delta > 0:
        scroll = max(0, scroll - _WHEEL_ROWS)
    else:
        scroll = min(layout["max_scroll"], scroll + _WHEEL_ROWS)
    state.th_font_picker_scroll = scroll
    return True


def _scroll_from_thumb_y(layout, thumb_y):
    sb = layout.get("scrollbar")
    if not sb or layout["max_scroll"] <= 0:
        return 0
    list_top = sb.get("list_top", sb["track_y"] + sb["track_h"])
    travel = max(1.0, sb["track_h"] - sb["thumb_h"])
    t = (list_top - sb["thumb_h"] - thumb_y) / travel
    t = max(0.0, min(1.0, t))
    return int(round(t * layout["max_scroll"]))


def handle_picker_click(context, hit, mx=0.0, my=0.0):
    global _HOVER_APPLY_INDEX
    state = _state(context)
    if state is None or hit is None:
        return False

    if hit.kind == "close":
        close_picker(context)
        return True
    if hit.kind == "search":
        focus_search_field(context)
        return True
    if hit.kind == "filter_toggle":
        state.th_font_picker_hide_unsupported = not getattr(state, "th_font_picker_hide_unsupported", True)
        state.th_font_picker_scroll = 0
        state.th_font_picker_search_focus = False
        _stop_caret_timer()
        invalidate_glyph_cache()
        return True
    if hit.kind == "multi_weight_toggle":
        state.th_font_picker_multi_weight_only = not getattr(state, "th_font_picker_multi_weight_only", False)
        state.th_font_picker_scroll = 0
        state.th_font_picker_search_focus = False
        _stop_caret_timer()
        return True
    if hit.kind == "language_menu":
        state.th_font_picker_search_focus = False
        _stop_caret_timer()
        from ..hud.language_picker import open_picker

        open_picker(context)
        return True
    if hit.kind == "scroll_thumb":
        state.th_font_picker_scroll_drag = True
        state.th_font_picker_scroll_drag_y = float(my)
        state.th_font_picker_scroll_drag_base = int(state.th_font_picker_scroll)
        return True
    if hit.kind == "scroll_track":
        handle_picker_scroll_track_click(context, my)
        return True
    if hit.kind == "row" and hit.index >= 0:
        wm = context.window_manager
        if hit.index < len(wm.th_state.font_catalog):
            item = wm.th_state.font_catalog[hit.index]
            _invoke_apply_system_font(context, item.filepath, hit.index, keep_picker_open=False)
            _HOVER_APPLY_INDEX = hit.index
        close_picker(context)
        return True
    if hit.kind == "panel":
        state.th_font_picker_search_focus = False
        _stop_caret_timer()
        return True
    return False


def handle_picker_scroll_track_click(context, my):
    layout = _LAST_LAYOUT
    state = _state(context)
    if layout is None or state is None:
        return False
    sb = layout.get("scrollbar")
    if not sb:
        return False
    thumb_h = sb["thumb_h"]
    target_thumb_y = my - thumb_h * 0.5
    state.th_font_picker_scroll = _scroll_from_thumb_y(layout, target_thumb_y)
    return True


def handle_picker_drag(context, my):
    state = _state(context)
    layout = _LAST_LAYOUT
    if state is None or layout is None or not getattr(state, "th_font_picker_scroll_drag", False):
        return False
    sb = layout.get("scrollbar")
    if not sb:
        return False
    dy = my - state.th_font_picker_scroll_drag_y
    travel = max(1.0, sb["track_h"] - sb["thumb_h"])
    scroll_delta = int(round(-(dy / travel) * layout["max_scroll"]))
    state.th_font_picker_scroll = max(0, min(layout["max_scroll"], state.th_font_picker_scroll_drag_base + scroll_delta))
    return True


def handle_picker_release(context):
    state = _state(context)
    if state is None:
        return False
    if getattr(state, "th_font_picker_scroll_drag", False):
        state.th_font_picker_scroll_drag = False
        return True
    return False


def handle_picker_hover(context, mx, my):
    state = _state(context)
    if state is None:
        return False
    hit = hit_test_picker(context, mx, my)
    applied = False
    if hit and hit.kind == "row":
        state.th_font_picker_hover = hit.index
        applied = _try_hover_apply_font(context, hit.index)
    else:
        state.th_font_picker_hover = -1
    return applied


def _event_text(event):
    text = getattr(event, "utf8", None) or getattr(event, "unicode", None) or ""
    return text


def _sanitize_field_text(text, max_len=0):
    if not text:
        return ""
    cleaned = "".join(ch for ch in text if ch == "\t" or ch == " " or (not ch.isspace() and ord(ch) >= 32))
    cleaned = cleaned.replace("\t", " ")
    if max_len > 0:
        cleaned = cleaned[:max_len]
    return cleaned


def _set_font_filter(wm, text, *, max_len=0):
    state = getattr(wm, "th_state", None)
    if state is not None:
        state.font_filter = _sanitize_field_text(text, max_len=max_len)


def _get_font_filter(wm):
    state = getattr(wm, "th_state", None)
    return state.font_filter if state is not None else ""


def _append_font_filter(wm, addition, *, max_len=0):
    current = _get_font_filter(wm)
    _set_font_filter(wm, current + addition, max_len=max_len)


def _on_field_changed(state):
    state.th_font_picker_scroll = 0


def _typing_text_from_event(event):
    """Extract printable input from TEXTINPUT or KEY events in the 3D viewport."""
    if event.value not in {"PRESS", "REPEAT"}:
        return ""
    if event.ctrl or event.alt or event.oskey:
        return ""
    if event.type == "TEXTINPUT":
        return _sanitize_field_text(_event_text(event))
    if event.type == "SPACE":
        return " "
    text = getattr(event, "unicode", None) or ""
    if not text and len(event.type) == 1 and event.type.isalpha():
        text = event.type.upper() if event.shift else event.type.lower()
    return _sanitize_field_text(text)


def handle_picker_key(context, event):
    state = _state(context)
    if state is None:
        return False

    wm = context.window_manager
    if not getattr(state, "th_font_picker_search_focus", False):
        return False

    max_len = 128

    if event.type in {"RET", "NUMPAD_ENTER"} and event.value == "PRESS":
        state.th_font_picker_search_focus = False
        _stop_caret_timer()
        return True

    if event.type == "ESC" and event.value == "PRESS":
        state.th_font_picker_search_focus = False
        _stop_caret_timer()
        return True

    if event.type == "V" and event.value == "PRESS" and (event.ctrl or event.oskey) and not event.alt:
        clip = getattr(wm, "clipboard", "") or ""
        if clip:
            clip = clip.replace("\r\n", "\n").replace("\r", "\n").split("\n", 1)[0]
            _append_font_filter(wm, clip, max_len=max_len)
            _on_field_changed(state)
        return True

    if event.type in {"BACK_SPACE", "DEL"} and event.value in {"PRESS", "REPEAT"}:
        current = _get_font_filter(wm)
        if current:
            _set_font_filter(wm, current[:-1], max_len=max_len)
            _on_field_changed(state)
        return True

    text = _typing_text_from_event(event)
    if text:
        _append_font_filter(wm, text, max_len=max_len)
        _on_field_changed(state)
        return True

    return False


def picker_blocks_event(context, mx, my):
    if not picker_open(context):
        return False
    hit = hit_test_picker(context, mx, my)
    return hit is not None and hit.kind == "panel"
