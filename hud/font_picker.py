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
from ..utils.font_loader import is_builtin_bfont_catalog, is_current_font, queue_font_catalog
from ..utils.font_catalog_filter import filtered_font_groups, glyph_filter_refining, invalidate_catalog_filter_cache
from ..utils.font_favorites import is_family_favorite
from ..utils.view3d_context import run_active_font_op
from ..utils.font_language import (
    get_language_filter,
    get_language_label,
)
from ..utils.font_preview_draw import draw_blf_preview
from ..utils.font_preview_text import get_font_coverage_text, get_font_preview_text
from ..utils.text_format import get_active_text_data
from . import layout as layout_mod
from .gpu_primitives import draw_refresh_icon, draw_rounded_rect
from .text_field_edit import (
    begin_mouse_select,
    caret_index,
    draw_text_field_selection,
    draw_text_field_text,
    end_mouse_select,
    handle_text_field_key,
    index_from_x,
    reset_text_field_cursor,
    update_mouse_select,
)
from .tooltip import draw_hud_tooltip
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
    from ..utils.hud_theme import build_picker_draw_theme

    return build_picker_draw_theme(context)


def _preview_point_size(context, scale):
    prefs = get_addon_prefs(context)
    pref_size = int(getattr(prefs, "font_preview_size", 36))
    return max(14.0, pref_size * 0.45 * scale)


def _preview_text(context, display_name=""):
    return get_font_preview_text(context, display_name)


def _coverage_text(context, display_name=""):
    return get_font_coverage_text(context, display_name)


def _picker_text_data(context):
    obj = context.active_object
    if obj and obj.type == "FONT":
        return obj.data
    return get_active_text_data(context)


def _font_supports_preview(item, preview, point_size):
    if not preview:
        return True
    if str(getattr(item, "filepath", "") or "").startswith("blend://"):
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
    from ..utils.font_blf import blf_load, resolve_catalog_blf_path

    abs_path = resolve_catalog_blf_path(filepath) or bpy.path.abspath(filepath)
    if not abs_path or not os.path.isfile(abs_path):
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

    font_id = blf_load(filepath)
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
    ctx = context or bpy.context
    if ctx is None:
        return []
    return filtered_font_groups(ctx)


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


def _invoke_refresh_system_fonts(context):
    from ..utils.font_refresh import perform_font_system_refresh
    from ..utils.operator_report import queue_operator_report

    try:
        perform_font_system_refresh(context)
    except Exception:
        return False
    queue_operator_report(context.window_manager, "Font information refreshed")
    return True


def _invoke_apply_system_font(
    context, filepath, catalog_index=-1, *, keep_picker_open=False, undo=True, record_recent=True
):
    from ..utils.text_format import get_active_text

    obj = get_active_text(context)
    result = {"CANCELLED"}

    def _call():
        nonlocal result
        result = bpy.ops.font.texthelper_apply_system_font(
            filepath=filepath,
            catalog_index=catalog_index,
            keep_picker_open=keep_picker_open,
            record_recent=record_recent,
        )

    if not run_active_font_op(context, _call, obj, undo=undo):
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
        undo=False,
        record_recent=False,
    ):
        return False
    _HOVER_APPLY_INDEX = catalog_index
    return True


def focus_search_field(context):
    """Focus the GPU search field and start the caret blink timer."""
    from .slider_input import dismiss_slider_value_edit

    dismiss_slider_value_edit(context, undo=False)
    state = _state(context)
    if state is None:
        return
    wm = context.window_manager
    query = _get_font_filter(wm)
    state.th_font_picker_search_focus = True
    reset_text_field_cursor(state, len(query))
    _start_caret_timer()


def _search_field_font_size(scale):
    return int(11 * scale)


def _search_field_text_x(hit, scale):
    return hit.x + 8.0 * scale


def _search_field_text_y(hit, scale):
    return hit.y + hit.h * 0.5 - 6.0 * scale


def _search_cursor_index_from_mx(context, mx, my, scale):
    layout = _LAST_LAYOUT
    if layout is None:
        return 0
    search_hit = next((h for h in layout.get("hits", []) if h.kind == "search"), None)
    if search_hit is None:
        return 0
    wm = context.window_manager
    query = _get_font_filter(wm)
    font_size = _search_field_font_size(scale)
    text_x = _search_field_text_x(search_hit, scale)
    return index_from_x(_UI_FONT, font_size, query, mx, text_x)


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
    from ..utils.font_recent import commit_recent_from_active_text

    try:
        commit_recent_from_active_text(context)
    except Exception:
        pass
    reset_picker_hover_apply()
    _stop_caret_timer()
    state = _state(context)
    if state is None:
        return
    state.th_font_picker_open = False
    state.th_font_picker_search_focus = False
    reset_text_field_cursor(state, 0)
    state.th_font_picker_scroll_drag = False
    state.th_font_picker_hover = -1
    state.th_font_picker_chip_hover = ""
    state.th_font_picker_chip_press = ""
    state.th_font_picker_pointer_x = -1.0
    state.th_font_picker_pointer_y = -1.0
    try:
        from .language_picker import close_picker as close_language_picker

        close_language_picker(context)
    except Exception:
        pass
    release_blf_cache()


def _chip_button_bg(theme, *, hovered=False, pressed=False, active=False):
    if pressed:
        return theme.get("field_focus", theme["row_bg"])
    if active:
        return theme["row_active"]
    if hovered:
        return theme["row_hover"]
    return theme.get("chip_bg", theme["row_bg"])


def _draw_icon_button(shader, hit, theme, scale, *, hovered, pressed, icon_draw):
    bg = _chip_button_bg(theme, hovered=hovered, pressed=pressed)
    draw_rounded_rect(shader, hit.x, hit.y, hit.w, hit.h, bg, 5.0 * scale)
    from ..utils.hud_theme import theme_text_color

    icon_color = theme_text_color(theme, highlighted=(hovered or pressed), surface="chip")
    cx = hit.x + hit.w * 0.5
    cy = hit.y + hit.h * 0.5
    icon_draw(shader, cx, cy, min(hit.w, hit.h) * 0.72, icon_color)


def _chip_is_hovered(hit, kind, chip_hover, pointer_x, pointer_y, *, index=-1):
    if hit is None:
        return False
    if kind == "favorite_toggle" and index >= 0:
        if chip_hover == f"favorite_toggle:{index}":
            return True
    elif chip_hover == kind:
        return True
    if pointer_x >= 0.0 and pointer_y >= 0.0 and hit.contains(pointer_x, pointer_y):
        return True
    return False


_FONT_SORT_MODES = ("RECENT", "NAME_AZ", "NAME_ZA")


def _font_sort_short_label(sort_mode: str) -> str:
    if sort_mode == "RECENT":
        return _("Recent")
    if sort_mode == "NAME_ZA":
        return _("Z-A")
    return _("A-Z")


def _cycle_font_sort(state) -> None:
    current = getattr(state, "font_sort", "RECENT") or "RECENT"
    try:
        index = _FONT_SORT_MODES.index(current)
    except ValueError:
        index = 0
    state.font_sort = _FONT_SORT_MODES[(index + 1) % len(_FONT_SORT_MODES)]
    state.th_font_picker_scroll = 0


def _filter_chip_label(kind: str, active: bool) -> str:
    if kind == "filter_toggle":
        return _("Supported") if active else _("All fonts")
    if kind == "multi_weight_toggle":
        return _("Multi-wt") if active else _("Families")
    if kind == "favorites_toggle":
        return _("Favorites only") if active else _("All favorites")
    if kind == "variable_toggle":
        return _("Variable") if active else _("All types")
    return ""


def _chip_tooltip(kind: str, context, state, *, index=-1) -> str:
    if kind == "close":
        return _("Close font picker")
    if kind == "search":
        return _("Filter the system font list")
    if kind == "clear_filters":
        return _("Clear search text and restore sort, script filter, and filter chips to defaults")
    if kind == "refresh_previews":
        return _("Rescan system fonts and rebuild preview thumbnails")
    if kind == "filter_toggle":
        hide = bool(state and getattr(state, "th_font_picker_hide_unsupported", True))
        if hide:
            return _("Only list fonts that contain every non-space character in the preview text")
        return _("Show every font family, including those missing characters from the preview text")
    if kind == "multi_weight_toggle":
        multi = bool(state and getattr(state, "th_font_picker_multi_weight_only", False))
        if multi:
            return _("Only list font families that have more than one weight on disk")
        return _("Show all font families, including single-weight families")
    if kind == "favorites_toggle":
        favorites = bool(state and getattr(state, "th_font_picker_favorites_only", False))
        if favorites:
            return _("Only list font families marked as favorites")
        return _("Show all font families, not just favorites")
    if kind == "variable_toggle":
        variable = bool(state and getattr(state, "th_font_picker_variable_only", False))
        if variable:
            return _("Only list OpenType variable font files")
        return _("Show all font types, including static and variable fonts")
    if kind == "sort_toggle" and state is not None:
        sort_mode = getattr(state, "font_sort", "RECENT") or "RECENT"
        if sort_mode == "RECENT":
            return _("Show recently applied font families first. Click to cycle sort order.")
        if sort_mode == "NAME_ZA":
            return _("Sort fonts by name descending. Click to cycle sort order.")
        return _("Sort fonts by name ascending. Click to cycle sort order.")
    if kind == "language_menu":
        return _("Filter fonts by supported writing system")
    if kind == "favorite_toggle" and index >= 0:
        return _("Add or remove this font family from favorites")
    return ""


_PICKER_CHIP_KINDS = (
    "close",
    "search",
    "filter_toggle",
    "multi_weight_toggle",
    "favorites_toggle",
    "variable_toggle",
    "sort_toggle",
    "language_menu",
    "clear_filters",
)


def _hovered_picker_chip(layout, chip_hover, pointer_x, pointer_y):
    refresh_hit = layout.get("refresh_draw")
    if refresh_hit and _chip_is_hovered(
        refresh_hit,
        "refresh_previews",
        chip_hover,
        pointer_x,
        pointer_y,
    ):
        return refresh_hit, "refresh_previews", -1

    for kind in _PICKER_CHIP_KINDS:
        hit = next((h for h in layout["hits"] if h.kind == kind), None)
        if hit and _chip_is_hovered(hit, kind, chip_hover, pointer_x, pointer_y):
            return hit, kind, -1

    if chip_hover.startswith("favorite_toggle:"):
        try:
            fav_index = int(chip_hover.split(":", 1)[1])
        except (IndexError, ValueError):
            fav_index = -1
        if fav_index >= 0:
            fav_hit = next(
                (h for h in layout["hits"] if h.kind == "favorite_toggle" and h.index == fav_index),
                None,
            )
            if fav_hit:
                return fav_hit, "favorite_toggle", fav_index

    if pointer_x >= 0.0 and pointer_y >= 0.0:
        for hit in layout["hits"]:
            if hit.kind == "favorite_toggle" and hit.contains(pointer_x, pointer_y):
                return hit, "favorite_toggle", hit.index

    return None, "", -1


def _fit_footer_label(label: str, max_w: float, font_size: int) -> str:
    if not label:
        return label
    blf.size(_UI_FONT, font_size)
    if max_w <= 0.0:
        return ""
    if blf.dimensions(_UI_FONT, label)[0] <= max_w:
        return label
    ell = "…"
    for count in range(len(label) - 1, 0, -1):
        candidate = label[:count] + ell
        if blf.dimensions(_UI_FONT, candidate)[0] <= max_w:
            return candidate
    return ell


def _fit_chip_label(label: str, max_w: float, scale: float) -> str:
    if not label:
        return label
    blf.size(_UI_FONT, int(9 * scale))
    pad = 14.0 * scale
    avail = max(0.0, max_w - pad)
    if blf.dimensions(_UI_FONT, label)[0] <= avail:
        return label
    ell = "…"
    for count in range(len(label) - 1, 0, -1):
        candidate = label[:count] + ell
        if blf.dimensions(_UI_FONT, candidate)[0] <= avail:
            return candidate
    return ell


def _draw_text_chip(shader, hit, theme, scale, label, *, active=False, hovered=False, pressed=False):
    from ..utils.hud_theme import theme_text_color

    bg = _chip_button_bg(theme, hovered=hovered, pressed=pressed, active=active)
    draw_rounded_rect(shader, hit.x, hit.y, hit.w, hit.h, bg, 5.0 * scale)
    blf.size(_UI_FONT, int(9 * scale))
    blf.color(_UI_FONT, *theme_text_color(theme, highlighted=(active or hovered or pressed), surface="chip"))
    blf.position(_UI_FONT, hit.x + 7.0 * scale, hit.y + hit.h * 0.5 - 5.0 * scale, 0)
    blf.draw(_UI_FONT, _fit_chip_label(label, hit.w, scale))


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
    filter_row_h = 30.0 * scale
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
    content_w = panel_w - pad * 2.0
    scrollbar_x = px + panel_w - pad - scrollbar_w
    chip_inset = 4.0 * scale
    chip_h = filter_row_h - 8.0 * scale
    filter_row1_y = filter_y + chip_inset
    filter_row2_y = filter_y + filter_row_h + filter_row_gap + chip_inset
    refresh_pad = 2.0 * scale
    chip_gap = 5.0 * scale
    filter_chip_count = 4
    icon_btn_w = chip_h
    filter_chip_w = (content_w - chip_gap * (filter_chip_count - 1)) / filter_chip_count
    sort_chip_w = min(72.0 * scale, max(52.0 * scale, content_w * 0.19))
    clear_btn_w = icon_btn_w
    refresh_btn_w = icon_btn_w
    row2_trailing_w = clear_btn_w + refresh_btn_w + chip_gap
    language_w = max(48.0 * scale, content_w - sort_chip_w - row2_trailing_w - chip_gap * 2)
    clear_x = list_x + content_w - clear_btn_w
    refresh_x = clear_x - chip_gap - refresh_btn_w

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
        PickerHit("search", list_x, search_y + 4.0 * scale, content_w, search_h - 8.0 * scale)
    )

    hits.append(
        PickerHit(
            "filter_toggle",
            list_x,
            filter_row1_y,
            filter_chip_w,
            chip_h,
        )
    )
    hits.append(
        PickerHit(
            "multi_weight_toggle",
            list_x + filter_chip_w + chip_gap,
            filter_row1_y,
            filter_chip_w,
            chip_h,
        )
    )
    hits.append(
        PickerHit(
            "favorites_toggle",
            list_x + (filter_chip_w + chip_gap) * 2,
            filter_row1_y,
            filter_chip_w,
            chip_h,
        )
    )
    hits.append(
        PickerHit(
            "variable_toggle",
            list_x + (filter_chip_w + chip_gap) * 3,
            filter_row1_y,
            filter_chip_w,
            chip_h,
        )
    )
    refresh_draw = PickerHit("refresh_draw", refresh_x, filter_row2_y, refresh_btn_w, chip_h)
    hits.append(
        PickerHit(
            "sort_toggle",
            list_x,
            filter_row2_y,
            sort_chip_w,
            chip_h,
        )
    )
    hits.append(
        PickerHit(
            "refresh_previews",
            refresh_x - refresh_pad,
            filter_row2_y - refresh_pad,
            refresh_btn_w + refresh_pad * 2.0,
            chip_h + refresh_pad * 2.0,
        )
    )
    hits.append(
        PickerHit(
            "language_menu",
            list_x + sort_chip_w + chip_gap,
            filter_row2_y,
            language_w,
            chip_h,
        )
    )
    hits.append(
        PickerHit(
            "clear_filters",
            clear_x,
            filter_row2_y,
            clear_btn_w,
            chip_h,
        )
    )

    row_hits = []
    fav_w = 22.0 * scale
    for row in range(visible_rows):
        idx = scroll + row
        if idx >= len(items):
            break
        group = items[idx]
        catalog_index = group.representative_index
        ry = list_top - (row + 1) * row_h + 2.0 * scale
        row_w = list_w - fav_w - 4.0 * scale
        rect = PickerHit("row", list_x, ry, row_w, row_h - 4.0 * scale, catalog_index)
        row_hits.append(rect)
        hits.append(rect)
        hits.append(
            PickerHit(
                "favorite_toggle",
                list_x + row_w + 2.0 * scale,
                ry,
                fav_w,
                row_h - 4.0 * scale,
                catalog_index,
            )
        )

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
        "refresh_draw": refresh_draw,
    }
    return _LAST_LAYOUT


def get_last_layout():
    return _LAST_LAYOUT


def get_picker_hits():
    if _LAST_LAYOUT is None:
        return []
    return _LAST_LAYOUT.get("hits", [])


_CHIP_HIT_KINDS = frozenset(
    {
        "close",
        "search",
        "clear_filters",
        "filter_toggle",
        "multi_weight_toggle",
        "favorites_toggle",
        "variable_toggle",
        "sort_toggle",
        "favorite_toggle",
        "refresh_previews",
        "language_menu",
        "scroll_thumb",
        "scroll_track",
    }
)


def hit_test_picker(context, mx, my):
    layout_picker(context)
    hits = get_picker_hits()
    for hit in reversed(hits):
        if hit.kind in _CHIP_HIT_KINDS and hit.contains(mx, my):
            return hit
    for hit in reversed(hits):
        if hit.kind == "row" and hit.contains(mx, my):
            return hit
    for hit in reversed(hits):
        if hit.kind != "panel" and hit.contains(mx, my):
            return hit
    for hit in hits:
        if hit.kind == "panel" and hit.contains(mx, my):
            return hit
    return None


def _draw_search_field(shader, hit, scale, theme, text, placeholder, focused, accent, state=None, *, hovered=False):
    """Search input styled like filter chips."""
    from ..utils.hud_theme import theme_text_color

    bg = _chip_button_bg(theme, hovered=hovered or focused, pressed=False, active=focused)
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
    highlighted = focused or hovered
    fg = theme_text_color(theme, highlighted=highlighted, surface="chip")
    if not display and not highlighted:
        muted = theme.get("row_text", theme.get("muted", theme["text"]))
        fg = muted
    text_y = hit.y + hit.h * 0.5 - 6.0 * scale
    text_x = hit.x + 8.0 * scale
    if focused and state is not None:
        from ..utils.hud_theme import text_field_selection_colors

        sel_bg, sel_fg = text_field_selection_colors(theme, backdrop=bg)
        draw_text_field_text(
            _UI_FONT,
            font_size,
            display,
            text_x,
            text_y,
            state,
            fg=fg,
            sel_bg=sel_bg,
            sel_fg=sel_fg,
            shader=shader,
            scale=scale,
        )
    else:
        blf.color(_UI_FONT, *fg)
        blf.position(_UI_FONT, text_x, text_y, 0)
        blf.draw(_UI_FONT, label)

    if focused and int(time.time() / 0.5) % 2 == 0:
        caret_at = caret_index(state) if state is not None else len(display)
        prefix = display[:caret_at]
        tw, _th = blf.dimensions(_UI_FONT, prefix) if prefix else (0.0, 0.0)
        caret_x = text_x + tw
        caret_h = 12.0 * scale
        draw_rounded_rect(
            shader,
            caret_x,
            hit.y + (hit.h - caret_h) * 0.5,
            max(1.0 * scale, 1.5 * scale),
            caret_h,
            fg,
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


def _draw_preview_line(font_id, text, x, y, max_w, size, theme, glyph_status=None, *, highlighted=False, filepath=""):
    from ..utils.hud_theme import theme_text_color

    if is_builtin_bfont_catalog(filepath):
        msg = _("Built-in font preview not supported yet")
        blf.size(_UI_FONT, max(8, int(size * 0.72)))
        blf.color(_UI_FONT, *theme.get("muted", theme.get("row_text", theme["text"])))
        blf.position(_UI_FONT, x, y, 0)
        blf.draw(_UI_FONT, msg)
        return
    if not text:
        return
    if font_id == -1:
        return
    draw_blf_preview(
        font_id,
        text,
        x,
        y,
        max_w,
        size,
        theme_text_color(theme, highlighted=highlighted, surface="row"),
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
    catalog = getattr(getattr(wm, "th_state", None), "font_catalog", None)
    if not catalog:
        from ..utils.font_loader import font_catalog_loading

        scale = _ui_scale(context)
        theme = _theme(context)
        import gpu

        gpu.state.blend_set("ALPHA")
        shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        panel_w = _panel_width(scale)
        pad = 12.0 * scale
        header_h = 40.0 * scale
        search_h = 30.0 * scale
        filter_h = 64.0 * scale
        footer_h = 22.0 * scale
        panel_h = header_h + search_h + filter_h + footer_h + pad * 0.5
        px, py = _picker_position(context, panel_w, panel_h, scale)
        draw_rounded_rect(shader, px, py, panel_w, panel_h, theme["panel_bg"], 8.0 * scale)
        blf.size(_UI_FONT, int(11 * scale))
        blf.color(_UI_FONT, *theme.get("muted", theme["text"]))
        msg = _("Loading fonts…") if font_catalog_loading() else _("Click refresh to load system fonts")
        blf.position(_UI_FONT, px + pad, py + panel_h * 0.5 - 6.0 * scale, 0)
        blf.draw(_UI_FONT, msg)
        gpu.state.blend_set("NONE")
        return

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
    pointer_x = float(getattr(state, "th_font_picker_pointer_x", -1.0)) if state else -1.0
    pointer_y = float(getattr(state, "th_font_picker_pointer_y", -1.0)) if state else -1.0
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

    blf.size(_UI_FONT, int(12 * scale))
    blf.color(_UI_FONT, *theme["text"])
    blf.position(_UI_FONT, px + pad, panel_top - 16.0 * scale, 0)
    blf.draw(_UI_FONT, _("Fonts"))

    preview_label = preview if len(preview) <= 28 else preview[:25] + "…"
    blf.size(_UI_FONT, int(9 * scale))
    blf.color(_UI_FONT, *theme.get("row_text", theme.get("muted", theme["text"])))
    blf.position(_UI_FONT, px + pad, header_y + 6.0 * scale, 0)
    blf.draw(_UI_FONT, _("Preview: {}").format(preview_label))

    chip_hover = getattr(state, "th_font_picker_chip_hover", "") if state else ""
    chip_press = getattr(state, "th_font_picker_chip_press", "") if state else ""

    close_hit = next((h for h in layout["hits"] if h.kind == "close"), None)
    if close_hit:
        from ..utils.hud_theme import theme_text_color

        close_hovered = _chip_is_hovered(close_hit, "close", chip_hover, pointer_x, pointer_y)
        if close_hovered:
            draw_rounded_rect(shader, close_hit.x, close_hit.y, close_hit.w, close_hit.h, theme["row_hover"], 4.0 * scale)
        draw_centered_glyph(
            close_hit,
            _UI_FONT,
            int(13 * scale),
            "×",
            theme_text_color(theme, highlighted=close_hovered, surface="row"),
        )

    search_hit = next((h for h in layout["hits"] if h.kind == "search"), None)
    if search_hit:
        search_focus = bool(state and getattr(state, "th_font_picker_search_focus", False))
        query = wm.th_state.font_filter or ""
        search_hovered = _chip_is_hovered(search_hit, "search", chip_hover, pointer_x, pointer_y)
        _draw_search_field(
            shader,
            search_hit,
            scale,
            theme,
            query,
            _("Search fonts…"),
            search_focus,
            accent,
            state if search_focus else None,
            hovered=search_hovered,
        )

    filter_hit = next((h for h in layout["hits"] if h.kind == "filter_toggle"), None)
    if filter_hit:
        hide_unsupported = bool(state and getattr(state, "th_font_picker_hide_unsupported", True))
        _draw_text_chip(
            shader,
            filter_hit,
            theme,
            scale,
            _filter_chip_label("filter_toggle", hide_unsupported),
            active=hide_unsupported,
            hovered=_chip_is_hovered(filter_hit, "filter_toggle", chip_hover, pointer_x, pointer_y),
        )

    multi_weight_hit = next((h for h in layout["hits"] if h.kind == "multi_weight_toggle"), None)
    if multi_weight_hit:
        multi_weight_only = bool(state and getattr(state, "th_font_picker_multi_weight_only", False))
        _draw_text_chip(
            shader,
            multi_weight_hit,
            theme,
            scale,
            _filter_chip_label("multi_weight_toggle", multi_weight_only),
            active=multi_weight_only,
            hovered=_chip_is_hovered(multi_weight_hit, "multi_weight_toggle", chip_hover, pointer_x, pointer_y),
        )

    favorites_hit = next((h for h in layout["hits"] if h.kind == "favorites_toggle"), None)
    if favorites_hit:
        favorites_only = bool(state and getattr(state, "th_font_picker_favorites_only", False))
        _draw_text_chip(
            shader,
            favorites_hit,
            theme,
            scale,
            _filter_chip_label("favorites_toggle", favorites_only),
            active=favorites_only,
            hovered=_chip_is_hovered(favorites_hit, "favorites_toggle", chip_hover, pointer_x, pointer_y),
        )

    variable_hit = next((h for h in layout["hits"] if h.kind == "variable_toggle"), None)
    if variable_hit:
        variable_only = bool(state and getattr(state, "th_font_picker_variable_only", False))
        _draw_text_chip(
            shader,
            variable_hit,
            theme,
            scale,
            _filter_chip_label("variable_toggle", variable_only),
            active=variable_only,
            hovered=_chip_is_hovered(variable_hit, "variable_toggle", chip_hover, pointer_x, pointer_y),
        )

    sort_hit = next((h for h in layout["hits"] if h.kind == "sort_toggle"), None)
    if sort_hit and state is not None:
        sort_mode = getattr(state, "font_sort", "RECENT") or "RECENT"
        _draw_text_chip(
            shader,
            sort_hit,
            theme,
            scale,
            _font_sort_short_label(sort_mode),
            active=True,
            hovered=_chip_is_hovered(sort_hit, "sort_toggle", chip_hover, pointer_x, pointer_y),
        )

    language_hit = next((h for h in layout["hits"] if h.kind == "language_menu"), None)
    if language_hit:
        lang_code = get_language_filter(wm)
        lang_active = lang_code != "ALL"
        _draw_text_chip(
            shader,
            language_hit,
            theme,
            scale,
            _(get_language_label(lang_code)),
            active=lang_active,
            hovered=_chip_is_hovered(language_hit, "language_menu", chip_hover, pointer_x, pointer_y),
        )

    refresh_hit = layout.get("refresh_draw")
    if refresh_hit:
        _draw_icon_button(
            shader,
            refresh_hit,
            theme,
            scale,
            hovered=_chip_is_hovered(refresh_hit, "refresh_previews", chip_hover, pointer_x, pointer_y),
            pressed=chip_press == "refresh_previews",
            icon_draw=draw_refresh_icon,
        )

    clear_filters_hit = next((h for h in layout["hits"] if h.kind == "clear_filters"), None)
    if clear_filters_hit:
        from ..utils.font_catalog_filter import font_filters_differ_from_defaults
        from ..utils.hud_theme import theme_text_color

        filters_active = font_filters_differ_from_defaults(context)
        clear_hovered = _chip_is_hovered(clear_filters_hit, "clear_filters", chip_hover, pointer_x, pointer_y)
        clear_pressed = chip_press == "clear_filters"
        clear_bg = _chip_button_bg(
            theme,
            hovered=clear_hovered,
            pressed=clear_pressed,
            active=filters_active,
        )
        draw_rounded_rect(
            shader,
            clear_filters_hit.x,
            clear_filters_hit.y,
            clear_filters_hit.w,
            clear_filters_hit.h,
            clear_bg,
            5.0 * scale,
        )
        draw_centered_glyph(
            clear_filters_hit,
            _UI_FONT,
            int(12 * scale),
            "×",
            theme_text_color(
                theme,
                highlighted=(filters_active or clear_hovered or clear_pressed),
                surface="chip",
            ),
        )

    draw_rounded_rect(
        shader,
        layout["list_x"],
        layout["list_y"],
        layout["list_w"] + layout["scrollbar_w"] + 4.0 * scale,
        layout["list_h"],
        theme["list_bg"],
        6.0 * scale,
    )

    items = layout["items"]
    scroll = layout["scroll"]

    try:
        from ..utils.hud_theme import theme_text_color

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
            row_highlight = active or hovered
            blf.size(_UI_FONT, int(9 * scale))
            blf.color(_UI_FONT, *theme_text_color(theme, highlighted=row_highlight, surface="row"))
            blf.position(_UI_FONT, hit.x + 8.0 * scale, hit.y + hit.h - 14.0 * scale, 0)
            blf.draw(_UI_FONT, name)

            row_preview = _preview_text(context, item.display_name)
            coverage = _coverage_text(context, item.display_name)
            font_id = -1 if is_builtin_bfont_catalog(item.filepath) else _acquire_picker_blf(item.filepath)
            missing = 0
            if coverage and font_id != -1:
                glyph_status = glyph_status_for_font_id(font_id, coverage, preview_size)
                missing = sum(1 for ok in glyph_status if not ok)
            _draw_preview_line(
                font_id,
                row_preview,
                hit.x + 8.0 * scale,
                hit.y + 6.0 * scale,
                hit.w - 16.0 * scale,
                preview_size,
                theme,
                highlighted=row_highlight,
                filepath=item.filepath,
            )
            if missing > 0:
                warn = _("Missing {:d}").format(missing)
                blf.size(_UI_FONT, int(8 * scale))
                blf.color(_UI_FONT, *theme["warn"])
                tw, _th = blf.dimensions(_UI_FONT, warn)
                blf.position(_UI_FONT, hit.x + hit.w - tw - 6.0 * scale, hit.y + hit.h - 13.0 * scale, 0)
                blf.draw(_UI_FONT, warn)
            fav_hit = next(
                (
                    h
                    for h in layout["hits"]
                    if h.kind == "favorite_toggle" and h.index == group.representative_index
                ),
                None,
            )
            if fav_hit is not None:
                favorited = is_family_favorite(context, item.filepath)
                fav_hovered = _chip_is_hovered(
                    fav_hit,
                    "favorite_toggle",
                    chip_hover,
                    pointer_x,
                    pointer_y,
                    index=group.representative_index,
                )
                if favorited:
                    fav_bg = theme["row_active"]
                elif fav_hovered:
                    fav_bg = theme["row_hover"]
                else:
                    fav_bg = theme.get("chip_bg", theme["field_bg"])
                draw_rounded_rect(shader, fav_hit.x, fav_hit.y, fav_hit.w, fav_hit.h, fav_bg, 4.0 * scale)
                fav_highlight = favorited or fav_hovered
                glyph_color = theme_text_color(theme, highlighted=fav_highlight, surface="row")
                draw_centered_glyph(
                    fav_hit,
                    _UI_FONT,
                    int(10 * scale),
                    "★" if favorited else "☆",
                    glyph_color,
                )
    finally:
        _release_picker_blf()

    sb = layout.get("scrollbar")
    if sb and len(items) > layout["visible_rows"]:
        scroll_hover = state and getattr(state, "th_font_picker_scroll_drag", False)
        if not scroll_hover and pointer_x >= 0.0 and pointer_y >= 0.0:
            thumb_x, thumb_y, thumb_w, thumb_h = sb["thumb_x"], sb["thumb_y"], sb["thumb_w"], sb["thumb_h"]
            scroll_hover = (
                thumb_x <= pointer_x <= thumb_x + thumb_w
                and thumb_y <= pointer_y <= thumb_y + thumb_h
            )
        draw_rounded_rect(
            shader,
            sb["track_x"],
            sb["track_y"],
            sb["track_w"],
            sb["track_h"],
            theme["scroll_track"],
            4.0 * scale,
        )
        if scroll_hover:
            thumb_color = theme.get("scroll_thumb_hover", theme["accent"])
        else:
            thumb_color = theme["scroll_thumb"]
        draw_rounded_rect(
            shader,
            sb["thumb_x"],
            sb["thumb_y"],
            sb["thumb_w"],
            sb["thumb_h"],
            thumb_color,
            4.0 * scale,
        )

    footer_y = py + 6.0 * scale
    footer_size = int(8 * scale)
    blf.size(_UI_FONT, footer_size)
    blf.color(_UI_FONT, *theme.get("row_text", theme.get("muted", theme["text"])))
    hide_unsupported = bool(state and getattr(state, "th_font_picker_hide_unsupported", True))
    if hide_unsupported and glyph_filter_refining():
        count_text = _("Filtering unsupported fonts… ({:d} shown)").format(len(items))
    else:
        count_text = _("{:d} families · □ = missing").format(len(items))
    blf.position(_UI_FONT, px + pad, footer_y, 0)
    blf.draw(_UI_FONT, count_text)

    if not items and not (hide_unsupported and glyph_filter_refining()):
        empty_msg = _("No matching fonts. Try turning off filters.")
        count_w, _count_h = blf.dimensions(_UI_FONT, count_text)
        gap = 18.0 * scale
        content_w = panel_w - pad * 2.0
        max_hint_w = max(0.0, content_w - count_w - gap)
        hint_x = px + pad + count_w + gap
        hint = _fit_footer_label(empty_msg, max_hint_w, footer_size)
        if hint:
            blf.position(_UI_FONT, hint_x, footer_y, 0)
            blf.draw(_UI_FONT, hint)

    tip_hit, tip_kind, tip_index = _hovered_picker_chip(layout, chip_hover, pointer_x, pointer_y)
    if tip_hit is not None:
        tip_text = _chip_tooltip(tip_kind, context, state, index=tip_index)
        if tip_text:
            region_w = context.region.width if context.region else 1920
            draw_hud_tooltip(shader, _UI_FONT, tip_hit, tip_text, scale, region_w, accent)

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
        if not getattr(state, "th_font_picker_search_focus", False):
            focus_search_field(context)
        idx = _search_cursor_index_from_mx(context, mx, my, _ui_scale(context))
        begin_mouse_select(state, idx)
        return True
    if hit.kind == "clear_filters":
        from ..utils.font_catalog_filter import report_font_filters_reset

        state.th_font_picker_search_focus = False
        _stop_caret_timer()
        state.th_font_picker_chip_press = "clear_filters"
        report_font_filters_reset(context)
        invalidate_catalog_filter_cache()
        return True
    if hit.kind == "filter_toggle":
        state.th_font_picker_hide_unsupported = not getattr(state, "th_font_picker_hide_unsupported", True)
        state.th_font_picker_scroll = 0
        state.th_font_picker_search_focus = False
        _stop_caret_timer()
        invalidate_catalog_filter_cache()
        return True
    if hit.kind == "multi_weight_toggle":
        state.th_font_picker_multi_weight_only = not getattr(state, "th_font_picker_multi_weight_only", False)
        state.th_font_picker_scroll = 0
        state.th_font_picker_search_focus = False
        _stop_caret_timer()
        return True
    if hit.kind == "favorites_toggle":
        state.th_font_picker_favorites_only = not getattr(state, "th_font_picker_favorites_only", False)
        state.th_font_picker_scroll = 0
        state.th_font_picker_search_focus = False
        _stop_caret_timer()
        return True
    if hit.kind == "variable_toggle":
        state.th_font_picker_variable_only = not getattr(state, "th_font_picker_variable_only", False)
        state.th_font_picker_scroll = 0
        state.th_font_picker_search_focus = False
        _stop_caret_timer()
        return True
    if hit.kind == "favorite_toggle" and hit.index >= 0:
        wm = context.window_manager
        if hit.index < len(wm.th_state.font_catalog):
            item = wm.th_state.font_catalog[hit.index]
            from ..utils.font_favorites import toggle_family_favorite

            toggle_family_favorite(context, item.filepath)
        return True
    if hit.kind == "refresh_previews":
        state.th_font_picker_search_focus = False
        _stop_caret_timer()
        state.th_font_picker_chip_press = "refresh_previews"
        _invoke_refresh_system_fonts(context)
        return True
    if hit.kind == "sort_toggle":
        _cycle_font_sort(state)
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
            _invoke_apply_system_font(
                context, item.filepath, hit.index, keep_picker_open=False, record_recent=False
            )
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
    changed = False
    if getattr(state, "th_font_picker_chip_press", ""):
        state.th_font_picker_chip_press = ""
        changed = True
    if getattr(state, "th_font_picker_scroll_drag", False):
        state.th_font_picker_scroll_drag = False
        changed = True
    if getattr(state, "th_text_field_selecting", False):
        end_mouse_select(state)
        changed = True
    return changed


def handle_search_field_mouse_move(context, mx, my):
    state = _state(context)
    if state is None or not getattr(state, "th_font_picker_search_focus", False):
        return False
    if not getattr(state, "th_text_field_selecting", False):
        return False
    idx = _search_cursor_index_from_mx(context, mx, my, _ui_scale(context))
    update_mouse_select(state, idx)
    return True


def handle_picker_hover(context, mx, my):
    state = _state(context)
    if state is None:
        return False
    state.th_font_picker_pointer_x = float(mx)
    state.th_font_picker_pointer_y = float(my)
    hit = hit_test_picker(context, mx, my)
    applied = False
    chip_kind = ""
    if hit and hit.kind == "favorite_toggle" and hit.index >= 0:
        chip_kind = f"favorite_toggle:{hit.index}"
    elif hit and hit.kind in _CHIP_HIT_KINDS:
        chip_kind = hit.kind
    state.th_font_picker_chip_hover = chip_kind
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
    utf8 = getattr(event, "utf8", None) or getattr(event, "unicode", None) or ""
    if utf8:
        return _sanitize_field_text(utf8)
    if event.type == "SPACE":
        return " "
    etype = str(getattr(event, "type", ""))
    if len(etype) == 1 and etype.isalpha():
        return _sanitize_field_text(etype.upper() if event.shift else etype.lower())
    return ""


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
        reset_text_field_cursor(state, 0)
        _stop_caret_timer()
        return True

    if event.type == "ESC" and event.value == "PRESS":
        state.th_font_picker_search_focus = False
        reset_text_field_cursor(state, 0)
        _stop_caret_timer()
        return True

    def _get_text():
        return _get_font_filter(wm)

    def _set_text(value):
        _set_font_filter(wm, value, max_len=max_len)

    if handle_text_field_key(
        context,
        event,
        state,
        get_text=_get_text,
        set_text=_set_text,
        on_change=lambda: _on_field_changed(state),
        sanitize_typed=lambda text: _sanitize_field_text(text, max_len=max_len),
        max_len=max_len,
    ):
        return True

    text = _typing_text_from_event(event)
    if text:
        current = _get_text()
        cursor = caret_index(state)
        lo, hi = min(int(state.th_text_field_anchor), cursor), max(int(state.th_text_field_anchor), cursor)
        if lo != hi:
            merged = current[:lo] + text + current[hi:]
            cursor = lo + len(text)
        else:
            merged = current[:cursor] + text + current[cursor:]
            cursor = cursor + len(text)
        if max_len > 0:
            merged = merged[:max_len]
            cursor = min(cursor, len(merged))
        _set_text(merged)
        state.th_text_field_cursor = cursor
        state.th_text_field_anchor = cursor
        _on_field_changed(state)
        return True

    return False


def picker_blocks_event(context, mx, my):
    if not picker_open(context):
        return False
    hit = hit_test_picker(context, mx, my)
    return hit is not None and hit.kind == "panel"
