"""Shared font catalog filtering for HUD, header, and sidebar lists."""

from __future__ import annotations

import bpy

from .font_family import family_key_for_filepath, family_weight_counts, group_catalog_items
from .font_display import display_name_for_catalog_item
from .font_favorites import is_family_favorite
from .font_recent import recent_family_rank_map, recent_generation
from .font_search import catalog_item_passes_name
from .font_glyph import font_has_full_coverage
from .font_preview_text import get_font_coverage_text
from .font_variable import is_variable_font_filepath
from .font_language import catalog_item_passes_language, get_language_filter
from .addon_prefs import get_addon_prefs

_GLYPH_REFINE_CHUNK = 64


def catalog_glyph_filter_point_size(context) -> float:
    prefs = get_addon_prefs(context)
    pref_size = int(getattr(prefs, "font_preview_size", 36))
    return max(14.0, pref_size * 0.45)


def font_catalog_filter_state(context):
    wm = context.window_manager
    state = wm.th_state
    hide_unsupported = bool(getattr(state, "th_font_picker_hide_unsupported", True))
    return {
        "filter_text": (state.font_filter or "").strip().lower(),
        "sort_mode": state.font_sort or "RECENT",
        "lang": get_language_filter(wm),
        "hide_unsupported": hide_unsupported,
        "multi_weight_only": bool(getattr(state, "th_font_picker_multi_weight_only", False)),
        "favorites_only": bool(getattr(state, "th_font_picker_favorites_only", False)),
        "variable_only": bool(getattr(state, "th_font_picker_variable_only", False)),
        "preview": get_font_coverage_text(context) if hide_unsupported else "",
        "point_size": catalog_glyph_filter_point_size(context) if hide_unsupported else 24.0,
    }


def _family_key_for_item(context, item) -> str:
    filepath = getattr(item, "filepath", "") or ""
    return family_key_for_filepath(filepath, context)


def catalog_item_passes_filters(context, item, filters, *, weight_counts=None, skip_glyph=False) -> bool:
    if not catalog_item_passes_name(item, filters["filter_text"]):
        return False
    if not catalog_item_passes_language(item, filters["lang"], filters["point_size"]):
        return False
    filepath = getattr(item, "filepath", "") or ""
    if (
        not skip_glyph
        and filters["hide_unsupported"]
        and not str(filepath).startswith("blend://")
    ):
        preview = filters["preview"]
        if preview and not font_has_full_coverage(item.filepath, preview, filters["point_size"]):
            return False
    filepath = getattr(item, "filepath", "") or ""
    family_key = _family_key_for_item(context, item)
    if filters["multi_weight_only"]:
        counts = weight_counts if weight_counts is not None else {}
        if counts.get(family_key, 0) <= 1:
            return False
    if filters["favorites_only"] and not is_family_favorite(context, filepath):
        return False
    if filters["variable_only"] and not is_variable_font_filepath(filepath):
        return False
    return True


_FILTER_CACHE_KEY = None
_FILTER_CACHE: dict[str, object] = {}
_GLYPH_TIMER_REGISTERED = False
_GLYPH_REFINE = {
    "key": None,
    "groups": [],
    "index": 0,
    "kept": [],
    "preview": "",
    "point_size": 24.0,
    "catalog_len": 0,
}


def glyph_filter_refining() -> bool:
    return bool(_GLYPH_REFINE.get("key"))


def _cancel_glyph_refine(*, unregister_timer=True) -> None:
    global _GLYPH_TIMER_REGISTERED

    if unregister_timer and _GLYPH_TIMER_REGISTERED:
        try:
            bpy.app.timers.unregister(_glyph_refine_step)
        except ValueError:
            pass
    _GLYPH_TIMER_REGISTERED = False
    _GLYPH_REFINE["key"] = None
    _GLYPH_REFINE["groups"] = []
    _GLYPH_REFINE["index"] = 0
    _GLYPH_REFINE["kept"] = []


def invalidate_catalog_filter_cache() -> None:
    global _FILTER_CACHE_KEY
    _FILTER_CACHE_KEY = None
    _FILTER_CACHE.clear()
    _cancel_glyph_refine()


def _filter_cache_key(context, catalog) -> tuple:
    from .font_loader import catalog_generation

    filters = font_catalog_filter_state(context)
    return (
        catalog_generation(),
        recent_generation(),
        len(catalog),
        filters["filter_text"],
        filters["sort_mode"],
        filters["lang"],
        filters["hide_unsupported"],
        filters["multi_weight_only"],
        filters["favorites_only"],
        filters["variable_only"],
        filters["preview"],
        int(round(filters["point_size"] * 100)),
    )


def _sort_groups(groups, sort_mode: str, context) -> None:
    if sort_mode == "RECENT":
        ranks = recent_family_rank_map(context) if context is not None else {}

        def _sort_key(group):
            return (ranks.get(group.family_key, 10**9), group.display_name.lower())

    else:
        reverse = sort_mode == "NAME_ZA"

        def _sort_key(group):
            return group.display_name.lower()

        groups.sort(key=_sort_key, reverse=reverse)
        return

    groups.sort(key=_sort_key)


def _store_filter_cache(key, groups, *, glyph_complete: bool) -> None:
    global _FILTER_CACHE_KEY

    header_indices = [group.representative_index for group in groups]
    visible_indices = {index for group in groups for index in (v.catalog_index for v in group.variants)}
    _FILTER_CACHE.clear()
    _FILTER_CACHE.update(
        {
            "groups": groups,
            "header_indices": header_indices,
            "visible_indices": visible_indices,
            "glyph_complete": glyph_complete,
        }
    )
    _FILTER_CACHE_KEY = key


def _group_passes_glyph_filter(catalog, group, preview: str, point_size: float) -> bool:
    rep = catalog[group.representative_index]
    filepath = getattr(rep, "filepath", "") or ""
    if str(filepath).startswith("blend://"):
        return True
    if not preview:
        return True
    return font_has_full_coverage(filepath, preview, point_size)


def _build_filtered_groups(context, *, apply_glyph_filter: bool = True):
    wm = context.window_manager
    catalog = wm.th_state.font_catalog
    filters = font_catalog_filter_state(context)
    weight_counts = family_weight_counts(catalog, context) if filters["multi_weight_only"] else None
    needs_glyph = bool(filters["hide_unsupported"] and filters["preview"])
    skip_item_glyph = needs_glyph and not apply_glyph_filter

    indexed = []
    for index, item in enumerate(catalog):
        if not catalog_item_passes_filters(
            context,
            item,
            filters,
            weight_counts=weight_counts,
            skip_glyph=skip_item_glyph,
        ):
            continue
        indexed.append((index, item))

    groups = group_catalog_items(indexed, context)

    if filters["multi_weight_only"]:
        weight_counts = weight_counts or family_weight_counts(catalog, context)
        groups = [
            group
            for group in groups
            if weight_counts.get(group.family_key, len(group.variants)) > 1
        ]

    if needs_glyph and apply_glyph_filter:
        preview = filters["preview"]
        point_size = filters["point_size"]
        groups = [
            group
            for group in groups
            if _group_passes_glyph_filter(catalog, group, preview, point_size)
        ]

    _sort_groups(groups, filters["sort_mode"], context)
    return groups


def _glyph_refine_step():
    state = _GLYPH_REFINE
    key = state.get("key")
    if not key:
        return None

    context = bpy.context
    wm = context.window_manager if context is not None else None
    catalog = getattr(getattr(wm, "th_state", None), "font_catalog", None)
    if catalog is None or len(catalog) != state.get("catalog_len", -1):
        _cancel_glyph_refine(unregister_timer=False)
        return None

    if _filter_cache_key(context, catalog) != key:
        _cancel_glyph_refine(unregister_timer=False)
        return None

    groups = state["groups"]
    index = int(state["index"])
    end = min(index + _GLYPH_REFINE_CHUNK, len(groups))
    kept = state["kept"]
    preview = state["preview"]
    point_size = state["point_size"]

    for offset in range(index, end):
        group = groups[offset]
        if _group_passes_glyph_filter(catalog, group, preview, point_size):
            kept.append(group)

    state["index"] = end
    partial = list(kept)
    _sort_groups(partial, font_catalog_filter_state(context)["sort_mode"], context)
    _store_filter_cache(key, partial, glyph_complete=False)

    if end < len(groups):
        try:
            from ..hud.draw import tag_redraw

            tag_redraw()
        except Exception:
            pass
        from .font_preview import tag_ui_redraw

        tag_ui_redraw(context, all_windows=True)
        return 0.01

    _sort_groups(kept, font_catalog_filter_state(context)["sort_mode"], context)
    _store_filter_cache(key, kept, glyph_complete=True)
    _cancel_glyph_refine(unregister_timer=False)
    try:
        from ..hud.draw import tag_redraw

        tag_redraw()
    except Exception:
        pass
    from .font_preview import tag_ui_redraw

    tag_ui_redraw(context, all_windows=True)
    return None


def _schedule_glyph_refine(context, key, catalog, filters, groups) -> None:
    global _GLYPH_TIMER_REGISTERED

    _cancel_glyph_refine()
    _GLYPH_REFINE["key"] = key
    _GLYPH_REFINE["groups"] = list(groups)
    _GLYPH_REFINE["index"] = 0
    _GLYPH_REFINE["kept"] = []
    _GLYPH_REFINE["preview"] = filters["preview"]
    _GLYPH_REFINE["point_size"] = filters["point_size"]
    _GLYPH_REFINE["catalog_len"] = len(catalog)
    bpy.app.timers.register(_glyph_refine_step, first_interval=0.01)
    _GLYPH_TIMER_REGISTERED = True


def _ensure_filter_cache(context):
    global _FILTER_CACHE_KEY

    wm = context.window_manager
    catalog = getattr(getattr(wm, "th_state", None), "font_catalog", None)
    if catalog is None:
        invalidate_catalog_filter_cache()
        return None

    key = _filter_cache_key(context, catalog)
    if _FILTER_CACHE_KEY == key and _FILTER_CACHE:
        # The timer owns incremental glyph refinement.  Rebuilding the fast
        # groups from every draw call made a cached picker nearly as expensive
        # as a cold filter while refinement was active.
        return _FILTER_CACHE

    filters = font_catalog_filter_state(context)
    needs_async_glyph = bool(filters["hide_unsupported"] and filters["preview"] and len(catalog) > 0)

    if needs_async_glyph:
        fast_groups = _build_filtered_groups(context, apply_glyph_filter=False)
        _store_filter_cache(key, fast_groups, glyph_complete=False)
        _schedule_glyph_refine(context, key, catalog, filters, fast_groups)
        return _FILTER_CACHE

    groups = _build_filtered_groups(context, apply_glyph_filter=True)
    _store_filter_cache(key, groups, glyph_complete=True)
    return _FILTER_CACHE


def filtered_font_groups(context):
    cache = _ensure_filter_cache(context)
    if not cache:
        return []
    return cache["groups"]


def sorted_catalog_indices(items, sort_mode: str, context=None):
    indices = list(range(len(items)))
    if sort_mode == "RECENT":
        ranks = recent_family_rank_map(context) if context is not None else {}
        indices.sort(
            key=lambda i: (
                ranks.get(_family_key_for_item(context, items[i]), 10**9),
                display_name_for_catalog_item(items[i], context).lower(),
            )
        )
        return indices
    reverse = sort_mode == "NAME_ZA"
    indices.sort(key=lambda i: display_name_for_catalog_item(items[i], context).lower(), reverse=reverse)
    return indices


def visible_catalog_indices(context, catalog):
    cache = _ensure_filter_cache(context)
    if cache:
        return list(cache["header_indices"])
    filters = font_catalog_filter_state(context)
    weight_counts = family_weight_counts(catalog, context) if filters["multi_weight_only"] else None
    indices = sorted_catalog_indices(catalog, filters["sort_mode"], context)
    return [
        index
        for index in indices
        if catalog_item_passes_filters(context, catalog[index], filters, weight_counts=weight_counts)
    ]


def filter_font_catalog_items(ui_list, context, data, propname):
    items = getattr(data, propname)
    cache = _ensure_filter_cache(context)
    if cache:
        header_set = set(cache["header_indices"])
        flt_flags = [
            ui_list.bitflag_filter_item if index in header_set else 0
            for index in range(len(items))
        ]
        return flt_flags, list(cache["header_indices"])

    filters = font_catalog_filter_state(context)
    weight_counts = family_weight_counts(items, context) if filters["multi_weight_only"] else None
    flt_flags = []
    for item in items:
        if catalog_item_passes_filters(context, item, filters, weight_counts=weight_counts):
            flt_flags.append(ui_list.bitflag_filter_item)
        else:
            flt_flags.append(0)
    indices = sorted_catalog_indices(items, filters["sort_mode"], context)
    return flt_flags, indices


def header_family_representative_indices(catalog, visible_indices):
    """Keep one representative row per font family (matches HUD grouping)."""
    if not visible_indices:
        return set()
    indexed = [(index, catalog[index]) for index in visible_indices]
    groups = group_catalog_items(indexed)
    return {group.representative_index for group in groups}


def header_visible_font_catalog_indices(context):
    """Filtered catalog indices for the header font list (one row per family)."""
    wm = context.window_manager
    catalog = wm.th_state.font_catalog
    return visible_catalog_indices(context, catalog)


def dedupe_header_font_filter_items(ui_list, catalog, flt_flags, indices):
    """Hide non-representative family variants in the header font UIList."""
    visible = [index for index, flag in enumerate(flt_flags) if flag & ui_list.bitflag_filter_item]
    representatives = header_family_representative_indices(catalog, visible)
    if not representatives or len(representatives) == len(visible):
        return flt_flags, indices
    new_flags = list(flt_flags)
    for index in visible:
        if index not in representatives:
            new_flags[index] = 0
    return new_flags, indices


def font_filters_differ_from_defaults(context) -> bool:
    wm = context.window_manager
    state = getattr(wm, "th_state", None)
    if state is None:
        return False
    if (state.font_filter or "").strip():
        return True
    if (state.font_sort or "RECENT") != "RECENT":
        return True
    if (state.font_language or "ALL") != "ALL":
        return True
    if not bool(getattr(state, "th_font_picker_hide_unsupported", True)):
        return True
    if bool(getattr(state, "th_font_picker_multi_weight_only", False)):
        return True
    if bool(getattr(state, "th_font_picker_favorites_only", False)):
        return True
    if bool(getattr(state, "th_font_picker_variable_only", False)):
        return True
    return False


def reset_font_catalog_filters(context) -> bool:
    """Restore search text, sort, script filter, and HUD filter chips to defaults."""
    if not font_filters_differ_from_defaults(context):
        return False
    from .font_language import invalidate_font_language_cache

    wm = context.window_manager
    state = getattr(wm, "th_state", None)
    if state is None:
        return False
    state.font_filter = ""
    state.font_sort = "RECENT"
    state.font_language = "ALL"
    state.th_font_picker_hide_unsupported = True
    state.th_font_picker_multi_weight_only = False
    state.th_font_picker_favorites_only = False
    state.th_font_picker_variable_only = False
    state.th_font_picker_scroll = 0
    state.th_font_picker_search_focus = False
    invalidate_font_language_cache()
    invalidate_catalog_filter_cache()
    return True


def report_font_filters_reset(context) -> bool:
    """Queue a status-bar info message after a filter reset attempt."""
    from .operator_report import queue_operator_report

    wm = context.window_manager
    if reset_font_catalog_filters(context):
        queue_operator_report(wm, "Font filters restored to defaults")
        return True
    queue_operator_report(wm, "Font filters already at defaults")
    return False
