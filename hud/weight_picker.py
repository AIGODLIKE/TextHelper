"""GPU font weight picker anchored to the HUD toolbar."""

import blf
import bpy
import gpu

from ..i18n import _
from ..utils.addon_prefs import get_addon_prefs
from ..utils.font_loader import is_current_font, queue_font_catalog, resolve_font_filepath
from ..utils.text_format import get_active_text_data
from ..utils.view3d_context import run_active_font_op
from . import layout as layout_mod
from .gpu_primitives import draw_rounded_rect
from .blf_layout import draw_centered_glyph

_UI_FONT = 0
_LAST_LAYOUT = None
_HOVER_APPLY_INDEX = -1


class WeightHit:
    __slots__ = ("kind", "catalog_index", "filepath", "x", "y", "w", "h")

    def __init__(self, kind, x, y, w, h, catalog_index=-1, filepath=""):
        self.kind = kind
        self.catalog_index = catalog_index
        self.filepath = filepath
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
    return bool(state and getattr(state, "th_weight_picker_open", False))


def _ui_scale(context):
    prefs = get_addon_prefs(context)
    return max(context.preferences.system.ui_scale, 0.5) * prefs.hud_scale


def _theme(context):
    from ..utils.hud_theme import build_picker_draw_theme

    return build_picker_draw_theme(context)


def _queue_font_catalog(wm):
    queue_font_catalog(wm)


def variants_for_text(context, text_data):
    if text_data is None or text_data.font is None:
        return ()
    wm = context.window_manager
    path = resolve_font_filepath(text_data.font)
    if not path:
        return (
            _make_regular_variant("", text_data.font.name),
        )
    _queue_font_catalog(wm)
    catalog = getattr(wm.th_state, "font_catalog", None)
    from ..utils.font_family import ensure_weight_variants

    variants = ensure_weight_variants(catalog, path, context)
    if variants:
        return variants
    return (_make_regular_variant(path, text_data.font.name),)


def _make_regular_variant(filepath, display_name):
    import os

    from ..utils.font_family import FontWeightVariant, parse_font_stem

    stem = os.path.splitext(os.path.basename(filepath or ""))[0]
    _family, label, rank = parse_font_stem(stem)
    return FontWeightVariant(
        catalog_index=-1,
        weight_label=label,
        weight_rank=rank,
        filepath=filepath or "",
        display_name=display_name or label,
    )


def _ensure_toolbar_rects(context):
    """Rebuild HUD rects when the picker opens before the next draw pass."""
    if layout_mod.get_hud_item_rect("font_weight", context) is not None:
        return
    text_data = get_active_text_data(context)
    obj = context.active_object
    if text_data is None or context.region is None:
        return
    from ..utils.addon_prefs import get_addon_prefs
    from ..utils.text_bounds import get_toolbar_anchor
    from ..utils.text_format import get_active_text

    if obj is None:
        obj = get_active_text(context)
    if obj is None:
        return
    prefs = get_addon_prefs(context)
    anchor = get_toolbar_anchor(context, obj, prefs.toolbar_offset)
    if anchor is None:
        return
    scale = _ui_scale(context)
    layout = layout_mod.layout_toolbar(anchor[0], anchor[1], scale, text_data, context)
    layout_mod.cache_hud_rects(context, layout["rects"])


def _picker_position(context, panel_w, panel_h, scale):
    _ensure_toolbar_rects(context)
    region = context.region
    margin = 10.0 * scale
    gap = 6.0 * scale
    weight_rect = layout_mod.get_hud_item_rect("font_weight", context)
    if weight_rect is not None:
        px = weight_rect.x
        panel_top = weight_rect.y - gap
        py = panel_top - panel_h
        px = max(margin, min(px, region.width - panel_w - margin))
        py = max(margin, py)
        return px, py
    font_rect = layout_mod.get_hud_item_rect("font", context)
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


def _panel_width(scale, variant_count):
    return min(340.0 * scale, max(220.0 * scale, 200.0 * scale))


def reset_picker_hover_apply():
    global _HOVER_APPLY_INDEX
    _HOVER_APPLY_INDEX = -1


def seed_picker_hover_apply(context):
    global _HOVER_APPLY_INDEX
    text_data = get_active_text_data(context)
    wm = context.window_manager
    catalog = getattr(wm.th_state, "font_catalog", None)
    if text_data is None or not catalog:
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


def _invoke_apply_weight(
    context, filepath, catalog_index, *, keep_picker_open=False, undo=True, record_recent=True
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


def _try_hover_apply_weight(context, filepath, catalog_index=-1):
    global _HOVER_APPLY_INDEX
    if not _hover_apply_enabled(context) or not filepath:
        return False
    wm = context.window_manager
    if catalog_index < 0:
        catalog = getattr(wm.th_state, "font_catalog", None)
        from ..utils.font_family import catalog_index_for_filepath

        catalog_index = catalog_index_for_filepath(catalog, filepath)
    if catalog_index == _HOVER_APPLY_INDEX:
        return False
    text_data = get_active_text_data(context)
    if text_data is not None and is_current_font(text_data, filepath):
        _HOVER_APPLY_INDEX = catalog_index
        return False
    if not _invoke_apply_weight(
        context, filepath, catalog_index, keep_picker_open=True, undo=False, record_recent=False
    ):
        return False
    _HOVER_APPLY_INDEX = catalog_index
    return True


def close_picker(context):
    reset_picker_hover_apply()
    state = _state(context)
    if state is None:
        return
    state.th_weight_picker_open = False
    state.th_weight_picker_hover = -1


def layout_picker(context):
    global _LAST_LAYOUT
    region = context.region
    if region is None:
        _LAST_LAYOUT = None
        return None

    _ensure_toolbar_rects(context)
    text_data = get_active_text_data(context)
    variants = variants_for_text(context, text_data)
    if not variants:
        _LAST_LAYOUT = None
        return None

    scale = _ui_scale(context)
    panel_w = _panel_width(scale, len(variants))
    pad = 12.0 * scale
    header_h = 36.0 * scale
    row_h = 34.0 * scale
    rows = len(variants)
    panel_h = header_h + row_h * rows + pad
    px, py = _picker_position(context, panel_w, panel_h, scale)
    panel_top = py + panel_h

    hits = [WeightHit("panel", px, py, panel_w, panel_h)]
    hits.append(
        WeightHit(
            "close",
            px + panel_w - pad - 20.0 * scale,
            panel_top - 26.0 * scale,
            18.0 * scale,
            18.0 * scale,
        )
    )

    list_x = px + pad
    list_w = panel_w - pad * 2
    row_hits = []
    row_body_h = row_h - 4.0 * scale
    for i, variant in enumerate(variants):
        ry = py + pad + i * row_h
        hit = WeightHit(
            "row",
            list_x,
            ry,
            list_w,
            row_body_h,
            variant.catalog_index,
            variant.filepath,
        )
        row_hits.append(hit)
        hits.append(hit)

    _LAST_LAYOUT = {
        "scale": scale,
        "px": px,
        "py": py,
        "panel_top": panel_top,
        "panel_w": panel_w,
        "panel_h": panel_h,
        "pad": pad,
        "header_h": header_h,
        "row_h": row_h,
        "list_x": list_x,
        "list_w": list_w,
        "row_hits": row_hits,
        "hits": hits,
        "list_x": list_x,
        "list_w": list_w,
        "row_h": row_h,
        "variants": variants,
    }
    return _LAST_LAYOUT


def hit_test_picker(context, mx, my):
    layout_picker(context)
    hits = _LAST_LAYOUT.get("hits", []) if _LAST_LAYOUT else []
    for hit in reversed(hits):
        if hit.kind != "panel" and hit.contains(mx, my):
            return hit
    for hit in hits:
        if hit.kind == "panel" and hit.contains(mx, my):
            return hit
    return None


def handle_picker_click(context, hit):
    global _HOVER_APPLY_INDEX
    state = _state(context)
    if state is None or hit is None:
        return False

    if hit.kind == "close":
        close_picker(context)
        return True
    if hit.kind == "row":
        wm = context.window_manager
        filepath = hit.filepath or ""
        catalog_index = hit.catalog_index
        if not filepath and catalog_index >= 0:
            catalog = getattr(wm.th_state, "font_catalog", None)
            if catalog and catalog_index < len(catalog):
                filepath = catalog[catalog_index].filepath
        if filepath:
            _invoke_apply_weight(context, filepath, catalog_index, keep_picker_open=False)
            _HOVER_APPLY_INDEX = catalog_index
        close_picker(context)
        return True
    if hit.kind == "panel":
        return True
    return False


def handle_picker_hover(context, mx, my):
    state = _state(context)
    if state is None:
        return False
    hit = hit_test_picker(context, mx, my)
    applied = False
    if hit and hit.kind == "row":
        state.th_weight_picker_hover = hit.catalog_index
        filepath = hit.filepath or ""
        if not filepath and hit.catalog_index >= 0:
            catalog = getattr(context.window_manager.th_state, "font_catalog", None)
            if catalog and hit.catalog_index < len(catalog):
                filepath = catalog[hit.catalog_index].filepath
        if filepath:
            applied = _try_hover_apply_weight(context, filepath, hit.catalog_index)
    else:
        state.th_weight_picker_hover = -1
    return applied


def draw_weight_picker(context):
    if not picker_open(context):
        return
    if context.region is None:
        return

    layout = layout_picker(context)
    if layout is None:
        return

    text_data = get_active_text_data(context)
    state = _state(context)
    scale = layout["scale"]
    px = layout["px"]
    py = layout["py"]
    panel_w = layout["panel_w"]
    panel_h = layout["panel_h"]
    pad = layout["pad"]
    theme = _theme(context)
    from ..utils.hud_theme import theme_text_color
    hover_index = int(getattr(state, "th_weight_picker_hover", -1)) if state else -1

    gpu.state.blend_set("ALPHA")
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")

    panel_top = layout["panel_top"]
    header_y = panel_top - layout["header_h"]

    draw_rounded_rect(shader, px, py, panel_w, panel_h, theme["panel_bg"], 8.0 * scale)
    draw_rounded_rect(shader, px, header_y, panel_w, layout["header_h"], theme["header_bg"], 8.0 * scale)

    list_x = layout.get("list_x", px + pad)
    list_w = layout.get("list_w", panel_w - pad * 2)
    row_h = layout.get("row_h", 34.0 * scale)
    rows = len(layout.get("variants", ()))
    if rows > 0:
        list_y = py + pad
        list_h = row_h * rows
        draw_rounded_rect(shader, list_x, list_y, list_w, list_h, theme["list_bg"], 5.0 * scale)

    blf.size(_UI_FONT, int(12 * scale))
    blf.color(_UI_FONT, *theme["text"])
    blf.position(_UI_FONT, px + pad, panel_top - 16.0 * scale, 0)
    blf.draw(_UI_FONT, _("Font Weight"))

    close_hit = next((h for h in layout["hits"] if h.kind == "close"), None)
    if close_hit:
        draw_centered_glyph(close_hit, _UI_FONT, int(13 * scale), "×", theme["muted"])

    wm = context.window_manager
    variants = layout.get("variants", ())
    for i, hit in enumerate(layout["row_hits"]):
        if i >= len(variants):
            continue
        variant = variants[i]
        filepath = variant.filepath or hit.filepath
        active = is_current_font(text_data, filepath)
        hovered = hit.catalog_index == hover_index
        if active:
            bg = theme["row_active"]
        elif hovered:
            bg = theme["row_hover"]
        else:
            bg = theme["row_bg"]
        draw_rounded_rect(shader, hit.x, hit.y, hit.w, hit.h, bg, 5.0 * scale)

        label = variant.weight_label
        if active:
            label = "✓ " + label
        blf.size(_UI_FONT, int(10 * scale))
        blf.color(_UI_FONT, *theme_text_color(theme, highlighted=(active or hovered)))
        blf.position(_UI_FONT, hit.x + 10.0 * scale, hit.y + hit.h * 0.5 - 5.0 * scale, 0)
        blf.draw(_UI_FONT, label)

    gpu.state.blend_set("NONE")
