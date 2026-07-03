"""GPU style preset picker in the 3D viewport."""

import blf
import bpy
import gpu

from ..i18n import _
from ..utils.addon_prefs import get_addon_prefs
from ..utils.text_format import STYLE_PRESETS, get_active_text_data
from ..utils.view3d_context import run_active_font_op
from . import layout as layout_mod
from .gpu_primitives import draw_rounded_rect
from .blf_layout import draw_centered_glyph

_UI_FONT = 0
_LAST_LAYOUT = None
_HOVER_APPLY_PRESET = ""
_PRESET_ORDER = tuple(STYLE_PRESETS.keys())


class PresetHit:
    __slots__ = ("kind", "preset_id", "x", "y", "w", "h")

    def __init__(self, kind, x, y, w, h, preset_id=""):
        self.kind = kind
        self.preset_id = preset_id
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
    return bool(state and getattr(state, "th_preset_picker_open", False))


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
        "row_bg": (0.14, 0.14, 0.15, 1.0),
        "row_hover": (0.22, 0.22, 0.24, 1.0),
        "row_active": get_accent_active_bg(accent),
        "text": (0.95, 0.95, 0.96, 1.0),
        "muted": (0.55, 0.55, 0.58, 1.0),
    }


def _picker_position(context, panel_w, panel_h, scale):
    region = context.region
    margin = 10.0 * scale
    gap = 6.0 * scale
    preset_rect = layout_mod.get_hud_item_rect("preset")
    if preset_rect is not None:
        px = preset_rect.x
        panel_top = preset_rect.y - gap
        py = panel_top - panel_h
        px = max(margin, min(px, region.width - panel_w - margin))
        py = max(margin, py)
        return px, py
    px = max(margin, region.width * 0.5 - panel_w * 0.5)
    py = max(margin, region.height - 56.0 * scale - panel_h)
    return px, py


def _panel_width(scale):
    preset_rect = layout_mod.get_hud_item_rect("preset")
    base = 220.0 * scale
    if preset_rect is not None:
        base = max(base, preset_rect.w * 2.2)
    return min(base, 300.0 * scale)


def reset_picker_hover_apply():
    global _HOVER_APPLY_PRESET
    _HOVER_APPLY_PRESET = ""


def seed_picker_hover_apply(context):
    global _HOVER_APPLY_PRESET
    text_data = get_active_text_data(context)
    if text_data is None:
        _HOVER_APPLY_PRESET = ""
        return
    _HOVER_APPLY_PRESET = getattr(text_data.text_helper, "th_preset", "BODY") or "BODY"


def _hover_apply_enabled(context):
    prefs = get_addon_prefs(context)
    return getattr(prefs, "font_preview_on_select", True)


def _invoke_apply_preset(context, preset_id, *, keep_picker_open=False):
    from ..utils.text_format import get_active_text

    obj = get_active_text(context)
    result = {"CANCELLED"}

    def _call():
        nonlocal result
        result = bpy.ops.font.texthelper_apply_preset(
            preset_id=preset_id,
            keep_picker_open=keep_picker_open,
        )

    if not run_active_font_op(context, _call, obj):
        return False
    return "FINISHED" in result


def _try_hover_apply_preset(context, preset_id):
    global _HOVER_APPLY_PRESET
    if not _hover_apply_enabled(context):
        return False
    if preset_id == _HOVER_APPLY_PRESET:
        return False
    text_data = get_active_text_data(context)
    if text_data is not None and getattr(text_data.text_helper, "th_preset", "BODY") == preset_id:
        _HOVER_APPLY_PRESET = preset_id
        return False
    if not _invoke_apply_preset(context, preset_id, keep_picker_open=True):
        return False
    _HOVER_APPLY_PRESET = preset_id
    return True


def close_picker(context):
    reset_picker_hover_apply()
    state = _state(context)
    if state is None:
        return
    state.th_preset_picker_open = False
    state.th_preset_picker_hover = ""


def layout_picker(context):
    global _LAST_LAYOUT
    region = context.region
    if region is None:
        _LAST_LAYOUT = None
        return None

    scale = _ui_scale(context)
    panel_w = _panel_width(scale)
    pad = 12.0 * scale
    header_h = 36.0 * scale
    row_h = 36.0 * scale
    rows = len(_PRESET_ORDER)
    panel_h = header_h + row_h * rows + pad * 0.5
    px, py = _picker_position(context, panel_w, panel_h, scale)
    panel_top = py + panel_h

    hits = [PresetHit("panel", px, py, panel_w, panel_h)]
    hits.append(
        PresetHit(
            "close",
            px + panel_w - pad - 20.0 * scale,
            panel_top - 26.0 * scale,
            18.0 * scale,
            18.0 * scale,
        )
    )

    list_x = px + pad
    list_w = panel_w - pad * 2
    list_top = panel_top - header_h
    row_hits = []
    for i, preset_id in enumerate(_PRESET_ORDER):
        ry = list_top - (i + 1) * row_h + 2.0 * scale
        hit = PresetHit("row", list_x, ry, list_w, row_h - 4.0 * scale, preset_id)
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
    state = _state(context)
    if state is None or hit is None:
        return False

    if hit.kind == "close":
        close_picker(context)
        return True
    if hit.kind == "row" and hit.preset_id:
        _invoke_apply_preset(context, hit.preset_id, keep_picker_open=False)
        global _HOVER_APPLY_PRESET
        _HOVER_APPLY_PRESET = hit.preset_id
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
        state.th_preset_picker_hover = hit.preset_id
        applied = _try_hover_apply_preset(context, hit.preset_id)
    else:
        state.th_preset_picker_hover = ""
    return applied


def picker_blocks_event(context, mx, my):
    if not picker_open(context):
        return False
    hit = hit_test_picker(context, mx, my)
    return hit is not None and hit.kind == "panel"


def draw_preset_picker(context):
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
    hover_id = getattr(state, "th_preset_picker_hover", "") if state else ""
    theme = _theme(context)
    accent = theme["accent"]

    gpu.state.blend_set("ALPHA")
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")

    panel_top = layout["panel_top"]
    header_y = panel_top - layout["header_h"]

    draw_rounded_rect(shader, px, py, panel_w, panel_h, theme["panel_bg"], 8.0 * scale)
    draw_rounded_rect(shader, px, header_y, panel_w, layout["header_h"], theme["header_bg"], 8.0 * scale)

    blf.size(_UI_FONT, int(12 * scale))
    blf.color(_UI_FONT, *theme["text"])
    blf.position(_UI_FONT, px + pad, panel_top - 16.0 * scale, 0)
    blf.draw(_UI_FONT, _("Style Preset"))

    close_hit = next((h for h in layout["hits"] if h.kind == "close"), None)
    if close_hit:
        draw_centered_glyph(close_hit, _UI_FONT, int(13 * scale), "×", theme["muted"])

    for hit in layout["row_hits"]:
        preset_id = hit.preset_id
        preset = STYLE_PRESETS.get(preset_id, {})
        active = text_data is not None and getattr(text_data.text_helper, "th_preset", "BODY") == preset_id
        hovered = preset_id == hover_id
        if active:
            bg = theme["row_active"]
        elif hovered:
            bg = theme["row_hover"]
        else:
            bg = theme["row_bg"]
        draw_rounded_rect(shader, hit.x, hit.y, hit.w, hit.h, bg, 5.0 * scale)

        label = _(preset.get("label", preset_id))
        if active:
            label = "✓ " + label
        blf.size(_UI_FONT, int(11 * scale))
        blf.color(_UI_FONT, *theme["text"])
        blf.position(_UI_FONT, hit.x + 10.0 * scale, hit.y + hit.h * 0.5 - 6.0 * scale, 0)
        blf.draw(_UI_FONT, label)

    gpu.state.blend_set("NONE")
