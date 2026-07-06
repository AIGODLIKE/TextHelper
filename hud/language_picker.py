"""GPU language filter picker (confirm selection, then close)."""

import blf
import bpy
import gpu

from ..i18n import _
from ..utils.font_language import LANGUAGE_FILTER_ITEMS, get_language_filter, invalidate_font_language_cache
from ..utils.text_frame import tag_view3d_redraw
from .font_picker import get_last_layout as get_font_picker_layout
from .gpu_primitives import draw_rounded_rect
from .blf_layout import draw_centered_glyph

_UI_FONT = 0
_LAST_LAYOUT = None
_LANG_ORDER = tuple(code for code, _label, _desc in LANGUAGE_FILTER_ITEMS)


class LanguageHit:
    __slots__ = ("kind", "language", "x", "y", "w", "h")

    def __init__(self, kind, x, y, w, h, language=""):
        self.kind = kind
        self.language = language
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
    return bool(state and getattr(state, "th_language_picker_open", False))


def _ui_scale(context):
    from ..utils.addon_prefs import get_addon_prefs

    prefs = get_addon_prefs(context)
    return max(context.preferences.system.ui_scale, 0.5) * prefs.hud_scale


def _theme(context):
    from ..utils.hud_theme import build_picker_draw_theme

    return build_picker_draw_theme(context)


def _picker_position(context, panel_w, panel_h, scale):
    region = context.region
    margin = 10.0 * scale
    font_layout = get_font_picker_layout()
    if font_layout is not None:
        for hit in reversed(font_layout.get("hits", [])):
            if hit.kind == "language_menu":
                gap = 6.0 * scale
                px = hit.x
                py = hit.y + hit.h + gap
                px = max(margin, min(px, region.width - panel_w - margin))
                if py + panel_h > region.height - margin:
                    py = max(margin, hit.y - panel_h - gap)
                return px, py
    px = max(margin, region.width * 0.5 - panel_w * 0.5)
    py = max(margin, region.height * 0.5 - panel_h * 0.5)
    return px, py


def close_picker(context):
    state = _state(context)
    if state is None:
        return
    state.th_language_picker_open = False
    state.th_language_picker_hover = ""


def open_picker(context):
    from .slider_input import dismiss_slider_value_edit

    dismiss_slider_value_edit(context, undo=False)
    state = _state(context)
    if state is None:
        return
    state.th_language_picker_open = True
    state.th_language_picker_hover = get_language_filter(context.window_manager)


def _apply_language(context, language):
    from ..utils.font_language import normalize_language_code

    wm = context.window_manager
    wm.th_state.font_language = normalize_language_code(language)
    state = _state(context)
    if state is not None:
        state.th_font_picker_scroll = 0
    invalidate_font_language_cache()
    tag_view3d_redraw(context)
    from ..utils.font_preview import tag_ui_redraw
    from .draw import tag_redraw

    tag_ui_redraw(context)
    tag_redraw()
    return True


def layout_picker(context):
    global _LAST_LAYOUT
    region = context.region
    if region is None:
        _LAST_LAYOUT = None
        return None

    scale = _ui_scale(context)
    panel_w = 200.0 * scale
    pad = 12.0 * scale
    header_h = 34.0 * scale
    row_h = 30.0 * scale
    rows = len(_LANG_ORDER)
    panel_h = header_h + row_h * rows + pad * 0.5
    px, py = _picker_position(context, panel_w, panel_h, scale)
    panel_top = py + panel_h

    hits = [LanguageHit("panel", px, py, panel_w, panel_h)]
    hits.append(
        LanguageHit(
            "close",
            px + panel_w - pad - 20.0 * scale,
            panel_top - 24.0 * scale,
            18.0 * scale,
            18.0 * scale,
        )
    )

    list_x = px + pad
    list_w = panel_w - pad * 2
    list_top = panel_top - header_h
    row_hits = []
    for index, language in enumerate(_LANG_ORDER):
        ry = list_top - (index + 1) * row_h + 2.0 * scale
        hit = LanguageHit("row", list_x, ry, list_w, row_h - 4.0 * scale, language)
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
        "row_hits": row_hits,
        "hits": hits,
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


def panel_contains(context, mx, my):
    layout = layout_picker(context)
    if layout is None:
        return False
    px = layout["px"]
    py = layout["py"]
    return px <= mx <= px + layout["panel_w"] and py <= my <= py + layout["panel_h"]


def handle_picker_click(context, hit):
    state = _state(context)
    if state is None or hit is None:
        return False

    if hit.kind == "close":
        close_picker(context)
        return True
    if hit.kind == "row" and hit.language:
        _apply_language(context, hit.language)
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
    if hit and hit.kind == "row":
        state.th_language_picker_hover = hit.language
    else:
        state.th_language_picker_hover = ""
    return False


def draw_language_picker(context):
    layout = layout_picker(context)
    if layout is None:
        return

    wm = context.window_manager
    state = _state(context)
    scale = layout["scale"]
    theme = _theme(context)
    from ..utils.hud_theme import theme_text_color
    current = get_language_filter(wm)
    hover = getattr(state, "th_language_picker_hover", "") if state else ""

    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    gpu.state.blend_set("ALPHA")

    px = layout["px"]
    py = layout["py"]
    panel_w = layout["panel_w"]
    panel_h = layout["panel_h"]
    panel_top = layout["panel_top"]
    header_y = panel_top - layout["header_h"]

    draw_rounded_rect(shader, px, py, panel_w, panel_h, theme["panel_bg"], 8.0 * scale)
    draw_rounded_rect(shader, px, header_y, panel_w, layout["header_h"], theme["header_bg"], 8.0 * scale)

    blf.size(_UI_FONT, int(12 * scale))
    blf.color(_UI_FONT, *theme["text"])
    blf.position(_UI_FONT, px + layout["pad"], panel_top - 16.0 * scale, 0)
    blf.draw(_UI_FONT, _("Language"))

    close_hit = next((h for h in layout["hits"] if h.kind == "close"), None)
    if close_hit:
        draw_centered_glyph(close_hit, _UI_FONT, int(13 * scale), "×", theme["muted"])

    labels = {code: _(label) for code, label, _desc in LANGUAGE_FILTER_ITEMS}
    for hit in layout["row_hits"]:
        active = hit.language == current
        hovered = hit.language == hover
        if active:
            bg = theme["row_active"]
        elif hovered:
            bg = theme["row_hover"]
        else:
            bg = theme["row_bg"]
        draw_rounded_rect(shader, hit.x, hit.y, hit.w, hit.h, bg, 5.0 * scale)
        label = labels.get(hit.language, hit.language)
        if active:
            label = f"✓ {label}"
        blf.size(_UI_FONT, int(10 * scale))
        blf.color(_UI_FONT, *theme_text_color(theme, highlighted=(active or hovered)))
        blf.position(_UI_FONT, hit.x + 8.0 * scale, hit.y + hit.h * 0.5 - 5.0 * scale, 0)
        blf.draw(_UI_FONT, label)

    gpu.state.blend_set("NONE")
