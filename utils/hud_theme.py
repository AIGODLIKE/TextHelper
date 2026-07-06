"""Shared HUD accent and draw colors from add-on preferences or Blender UI theme."""

from __future__ import annotations

# sRGB #4772B3
_ACCENT_BLUE = (71 / 255, 114 / 255, 179 / 255)

HUD_ACCENT_PRESETS = {
    "BLUE": _ACCENT_BLUE,
    "ORANGE": (0.96, 0.52, 0.14),
    "PURPLE": (0.62, 0.38, 0.95),
    "PINK": (0.94, 0.32, 0.58),
}

_VALID_ACCENT_PRESETS = frozenset({"SYSTEM", *HUD_ACCENT_PRESETS.keys(), "CUSTOM"})

_DEFAULT_PRESET = "BLUE"
_FALLBACK_PRESET = "BLUE"
_WARN = (0.96, 0.42, 0.30, 1.0)
_TEXT_ON_DARK = (0.92, 0.92, 0.94, 1.0)
_TEXT_ON_LIGHT = (0.10, 0.10, 0.11, 1.0)


def _luminance(rgba):
    r, g, b = rgba[0], rgba[1], rgba[2]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def readable_text_on_bg(bg, preferred, *, min_contrast=0.32):
    """Pick a foreground that stays readable on ``bg`` (handles light/dark themes)."""
    pref = _color_rgba(preferred)
    bg_color = _color_rgba(bg)
    if abs(_luminance(bg_color) - _luminance(pref)) >= min_contrast:
        return pref
    return _TEXT_ON_LIGHT if _luminance(bg_color) > 0.5 else _TEXT_ON_DARK


def _paired_text(bg, normal, active=None):
    normal = readable_text_on_bg(bg, normal)
    if active is None:
        return normal, normal
    return normal, readable_text_on_bg(bg, active)


def theme_text_color(theme, *, highlighted=False, surface="row"):
    """Foreground matched to a themed surface (row, field, chip, btn, panel)."""
    if surface == "field":
        key = "field_text_on_active" if highlighted else "field_text"
    elif surface == "chip":
        key = "chip_text_on_active" if highlighted else "chip_text"
    elif surface == "btn":
        key = "btn_text_on_active" if highlighted else "btn_text"
    elif surface == "panel":
        key = "panel_text"
    else:
        key = "row_text_on_active" if highlighted else "row_text"

    if key in theme:
        return theme[key]
    if highlighted:
        return theme.get("text_on_active", theme["text"])
    return theme.get("muted", theme["text"])


def _color_similar(a, b, *, threshold=0.12):
    left = _color_rgba(a)
    right = _color_rgba(b)
    return (
        max(abs(left[0] - right[0]), abs(left[1] - right[1]), abs(left[2] - right[2]))
        <= threshold
    )


def _blend_opaque(foreground, background, fg_weight=0.75):
    fg = _color_rgba(foreground)
    bg = _color_rgba(background)
    weight = max(0.0, min(1.0, float(fg_weight)))
    inv = 1.0 - weight
    return (
        fg[0] * weight + bg[0] * inv,
        fg[1] * weight + bg[1] * inv,
        fg[2] * weight + bg[2] * inv,
        1.0,
    )


def _selection_on_accent_backdrop(accent):
    accent = _color_rgba(accent)
    if _luminance(accent) > 0.62:
        sel_bg = _blend_opaque((0.0, 0.0, 0.0, 1.0), accent, fg_weight=0.38)
        sel_fg = readable_text_on_bg(sel_bg, _TEXT_ON_DARK)
    else:
        sel_bg = _blend_opaque((1.0, 1.0, 1.0, 1.0), accent, fg_weight=0.90)
        sel_fg = readable_text_on_bg(sel_bg, _TEXT_ON_LIGHT)
    return sel_bg, sel_fg


def text_field_selection_from_foreground(fg):
    """Selection fill/text derived from field foreground (RGB invert + contrast)."""
    fg = _color_rgba(fg)
    sel_bg = (1.0 - fg[0], 1.0 - fg[1], 1.0 - fg[2], 1.0)
    sel_fg = readable_text_on_bg(sel_bg, fg, min_contrast=0.28)
    return sel_bg, sel_fg


def text_field_selection_for_editing(fg, theme, *, backdrop=None):
    """Selection colors for HUD inline numeric fields (sliders)."""
    fg = _color_rgba(fg)
    backdrop = _color_rgba(backdrop or theme.get("field_bg", theme.get("chip_bg")))
    accent = _color_rgba(theme["accent"])
    sel_bg = (1.0 - fg[0], 1.0 - fg[1], 1.0 - fg[2], 1.0)
    invert_hidden = (
        _color_similar(sel_bg, backdrop, threshold=0.14)
        or abs(_luminance(sel_bg) - _luminance(backdrop)) < 0.10
    )
    light_on_dark = _luminance(fg) > 0.55 and _luminance(backdrop) < 0.35
    if invert_hidden or light_on_dark:
        sel_bg = _blend_opaque(accent, backdrop, fg_weight=0.82)
    sel_fg = readable_text_on_bg(sel_bg, fg, min_contrast=0.28)
    return sel_bg, sel_fg


def text_field_selection_colors(theme, *, backdrop=None):
    """Background/foreground for HUD text-field selection highlights."""
    backdrop = _color_rgba(
        backdrop or theme.get("field_bg", theme.get("chip_bg", theme.get("panel_bg")))
    )
    field_bg = _color_rgba(theme.get("field_bg", backdrop))
    accent = _color_rgba(theme["accent"])

    theme_sel_bg = theme.get("selection_bg")
    theme_sel_fg = theme.get("selection_text")
    if theme_sel_bg is not None and theme_sel_fg is not None and _color_similar(backdrop, field_bg):
        return _color_rgba(theme_sel_bg), _color_rgba(theme_sel_fg)

    if _color_similar(backdrop, accent, threshold=0.15):
        return _selection_on_accent_backdrop(accent)

    sel_bg = _blend_opaque(accent, backdrop, fg_weight=0.78)
    preferred = theme.get("field_text", theme.get("text", _TEXT_ON_DARK))
    sel_fg = readable_text_on_bg(sel_bg, preferred)
    return sel_bg, sel_fg


def _color_rgba(value, *, default=(0.0, 0.0, 0.0, 1.0)):
    try:
        if value is None:
            return default
        if len(value) >= 4:
            return (float(value[0]), float(value[1]), float(value[2]), float(value[3]))
        return (float(value[0]), float(value[1]), float(value[2]), 1.0)
    except (TypeError, IndexError, ValueError):
        return default


def _read_blender_ui(context):
    if context is None:
        return None
    try:
        themes = context.preferences.themes
        if not themes:
            return None
        return themes[0].user_interface
    except (AttributeError, IndexError, TypeError):
        return None


def hud_accent_preset(prefs) -> str:
    preset = getattr(prefs, "hud_accent_preset", _DEFAULT_PRESET) or _DEFAULT_PRESET
    if preset not in _VALID_ACCENT_PRESETS:
        return _FALLBACK_PRESET
    return preset


def uses_system_theme(prefs) -> bool:
    return hud_accent_preset(prefs) == "SYSTEM"


def _system_accent_from_ui(ui):
    for name in ("wcol_tool", "wcol_toggle", "wcol_toolbar_item"):
        widget = getattr(ui, name, None)
        if widget is not None:
            return _color_rgba(widget.inner_sel)
    return None


def _preset_accent_rgb(preset: str):
    if preset == "CUSTOM":
        return None
    return HUD_ACCENT_PRESETS.get(preset, _ACCENT_BLUE)


def get_accent_rgba(context, prefs):
    preset = hud_accent_preset(prefs)
    if preset == "SYSTEM":
        ui = _read_blender_ui(context)
        if ui is not None:
            accent = _system_accent_from_ui(ui)
            if accent is not None:
                return accent
        preset = _FALLBACK_PRESET

    if preset == "CUSTOM":
        custom = getattr(prefs, "hud_accent_custom", _ACCENT_BLUE)
        return (float(custom[0]), float(custom[1]), float(custom[2]), 1.0)

    rgb = _preset_accent_rgb(preset) or _ACCENT_BLUE
    return (rgb[0], rgb[1], rgb[2], 1.0)


def get_accent_active_bg(accent):
    """Toggle / active chip backgrounds use the accent color directly."""
    return (accent[0], accent[1], accent[2], accent[3] if len(accent) > 3 else 1.0)


def get_accent_drag_bg(accent):
    return (
        accent[0] * 0.55 + 0.08,
        accent[1] * 0.55 + 0.08,
        accent[2] * 0.55 + 0.08,
        1.0,
    )


def _attach_common_text_keys(theme, *, panel_bg, row_bg, field_bg, chip_bg, btn_bg, active_bg):
    panel_text, _ = _paired_text(panel_bg, theme.get("text", _TEXT_ON_DARK))
    row_text, row_text_on_active = _paired_text(
        row_bg,
        _color_rgba(theme.get("muted", theme["text"])),
        theme.get("text_on_active", theme["text"]),
    )
    _, row_text_on_active = _paired_text(active_bg, row_text_on_active)
    field_text, field_text_on_active = _paired_text(
        field_bg,
        theme.get("field_text", theme["text"]),
        theme.get("text_on_active", theme["text"]),
    )
    chip_text, chip_text_on_active = _paired_text(
        chip_bg,
        row_text,
        theme.get("text_on_active", theme["text"]),
    )
    _, chip_text_on_active = _paired_text(active_bg, chip_text_on_active)
    btn_text, btn_text_on_active = _paired_text(
        btn_bg,
        theme.get("btn_text", theme["text"]),
        theme.get("text_on_active", theme["text"]),
    )
    _, btn_text_on_active = _paired_text(active_bg, btn_text_on_active)

    theme.update(
        {
            "panel_text": panel_text,
            "row_text": row_text,
            "row_text_on_active": row_text_on_active,
            "field_text": field_text,
            "field_text_on_active": field_text_on_active,
            "field_muted": readable_text_on_bg(field_bg, row_text),
            "chip_text": chip_text,
            "chip_text_on_active": chip_text_on_active,
            "btn_text": btn_text,
            "btn_text_on_active": btn_text_on_active,
        }
    )
    return theme


def scroll_colors_for_backdrop(backdrop, ui=None, *, frame_bg=None):
    """Scrollbar track/thumb derived from the list/panel backdrop (light or dark UI)."""
    backdrop = _color_rgba(backdrop)
    frame = _color_rgba(frame_bg if frame_bg is not None else backdrop)

    if ui is not None:
        scroll = ui.wcol_scroll
        theme_track = _color_rgba(scroll.inner)
        theme_thumb = _color_rgba(scroll.item)
        frame_light = _luminance(frame) > 0.5
        theme_light = _luminance(theme_track) > 0.5
        if (
            frame_light == theme_light
            and abs(_luminance(frame) - _luminance(theme_track)) >= 0.06
            and abs(_luminance(theme_track) - _luminance(theme_thumb)) >= 0.08
        ):
            return theme_track, theme_thumb

    if _luminance(frame) > 0.5:
        track = (
            frame[0] * 0.94 + backdrop[0] * 0.06,
            frame[1] * 0.94 + backdrop[1] * 0.06,
            frame[2] * 0.95 + backdrop[2] * 0.05,
            1.0,
        )
        thumb = (
            min(1.0, track[0] * 0.55 + 0.22),
            min(1.0, track[1] * 0.55 + 0.22),
            min(1.0, track[2] * 0.55 + 0.24),
            1.0,
        )
    else:
        track = (
            min(1.0, frame[0] + 0.05),
            min(1.0, frame[1] + 0.05),
            min(1.0, frame[2] + 0.05),
            1.0,
        )
        thumb = (
            min(1.0, track[0] + 0.16),
            min(1.0, track[1] + 0.16),
            min(1.0, track[2] + 0.16),
            1.0,
        )
    return track, thumb


_PRESET_HUD_OUTER_BG = (0.08, 0.08, 0.09, 0.94)


def _hud_outer_bg_from_ui(ui):
    bg = _color_rgba(ui.wcol_menu_back.inner, default=_color_rgba(ui.panel_back))
    if bg[3] < 0.85:
        bg = (bg[0], bg[1], bg[2], 0.94)
    return bg


def hud_outer_bg(context):
    """Outermost floating HUD / picker shell background (matches toolbar row backdrop)."""
    from .addon_prefs import get_addon_prefs

    prefs = get_addon_prefs(context)
    if uses_system_theme(prefs):
        ui = _read_blender_ui(context)
        if ui is not None:
            return _hud_outer_bg_from_ui(ui)
    return _PRESET_HUD_OUTER_BG


def _system_draw_theme(ui):
    tool = ui.wcol_tool
    regular = ui.wcol_regular
    text_w = ui.wcol_text
    scroll = ui.wcol_scroll
    accent = _color_rgba(tool.inner_sel)

    outer_bg = _hud_outer_bg_from_ui(ui)
    panel_back = _color_rgba(ui.panel_back)
    if panel_back[3] < 0.95:
        panel_back = (panel_back[0], panel_back[1], panel_back[2], max(panel_back[3], 0.98))

    row_bg = _color_rgba(regular.inner)
    field_bg = _color_rgba(text_w.inner)
    chip_bg = row_bg
    btn_bg = _color_rgba(tool.inner)

    theme = {
        "accent": accent,
        "panel_bg": outer_bg,
        "header_bg": _color_rgba(ui.panel_header),
        "list_bg": _color_rgba(ui.panel_sub_back, default=panel_back),
        "row_bg": row_bg,
        "row_hover": accent,
        "row_active": accent,
        "field_bg": field_bg,
        "field_focus": _color_rgba(text_w.inner_sel),
        "chip_bg": chip_bg,
        "border": _color_rgba(ui.panel_outline),
        "scroll_track": _color_rgba(scroll.inner),
        "scroll_thumb": _color_rgba(scroll.item),
        "slider_track": _color_rgba(scroll.inner),
        "text": _color_rgba(ui.panel_text),
        "text_on_active": _color_rgba(tool.text_sel),
        "muted": _color_rgba(regular.text),
        "field_text": _color_rgba(text_w.text),
        "selection_bg": _color_rgba(text_w.inner_sel),
        "selection_text": _color_rgba(text_w.text_sel),
        "btn_text": _color_rgba(tool.text),
        "warn": _WARN,
    }
    return _attach_common_text_keys(
        theme,
        panel_bg=outer_bg,
        row_bg=row_bg,
        field_bg=field_bg,
        chip_bg=chip_bg,
        btn_bg=btn_bg,
        active_bg=accent,
    )


def _preset_draw_theme(accent):
    active = get_accent_active_bg(accent)
    panel_bg = _PRESET_HUD_OUTER_BG
    row_bg = (0.14, 0.14, 0.15, 1.0)
    field_bg = (0.12, 0.13, 0.14, 1.0)
    chip_bg = row_bg
    btn_bg = (0.16, 0.16, 0.17, 1.0)
    theme = {
        "accent": accent,
        "panel_bg": panel_bg,
        "header_bg": (0.10, 0.10, 0.11, 1.0),
        "list_bg": (0.11, 0.11, 0.12, 1.0),
        "row_bg": row_bg,
        "row_hover": (0.22, 0.22, 0.24, 1.0),
        "row_active": active,
        "field_bg": field_bg,
        "field_focus": (0.18, 0.18, 0.20, 1.0),
        "chip_bg": chip_bg,
        "border": (0.28, 0.28, 0.30, 0.9),
        "scroll_track": (0.16, 0.16, 0.17, 1.0),
        "scroll_thumb": (0.38, 0.38, 0.40, 1.0),
        "slider_track": (0.28, 0.28, 0.30, 1.0),
        "text": (0.95, 0.95, 0.96, 1.0),
        "text_on_active": (0.95, 0.95, 0.96, 1.0),
        "muted": (0.55, 0.55, 0.58, 1.0),
        "selection_bg": _blend_opaque(accent, field_bg, fg_weight=0.78),
        "selection_text": readable_text_on_bg(
            _blend_opaque(accent, field_bg, fg_weight=0.78),
            (0.95, 0.95, 0.96, 1.0),
        ),
        "warn": _WARN,
    }
    return _attach_common_text_keys(
        theme,
        panel_bg=panel_bg,
        row_bg=row_bg,
        field_bg=field_bg,
        chip_bg=chip_bg,
        btn_bg=btn_bg,
        active_bg=active,
    )


def build_hud_draw_theme(context):
    from .addon_prefs import get_addon_prefs

    prefs = get_addon_prefs(context)
    if uses_system_theme(prefs):
        ui = _read_blender_ui(context)
        if ui is not None:
            return _system_draw_theme(ui)
    accent = get_accent_rgba(context, prefs)
    return _preset_draw_theme(accent)


def build_picker_draw_theme(context):
    """Theme for floating picker panels (font / weight / language / preset)."""
    from .addon_prefs import get_addon_prefs

    theme = dict(build_hud_draw_theme(context))
    outer_bg = hud_outer_bg(context)
    theme["panel_bg"] = outer_bg
    theme["header_bg"] = outer_bg
    theme["panel_text"] = readable_text_on_bg(outer_bg, theme["text"])
    theme["list_bg"] = theme.get("chip_bg", theme["row_bg"])

    prefs = get_addon_prefs(context)
    ui = _read_blender_ui(context) if uses_system_theme(prefs) else None
    track, thumb = scroll_colors_for_backdrop(theme["list_bg"], ui, frame_bg=outer_bg)
    theme["scroll_track"] = track
    theme["scroll_thumb"] = thumb
    theme["scroll_thumb_hover"] = theme["accent"]
    return theme


def get_toolbar_draw_colors(context):
    """Floating HUD toolbar row colors."""
    theme = dict(build_hud_draw_theme(context))
    from .addon_prefs import get_addon_prefs

    prefs = get_addon_prefs(context)
    accent = theme["accent"]

    if uses_system_theme(prefs):
        ui = _read_blender_ui(context)
        if ui is not None:
            tool = ui.wcol_tool
            bg = _hud_outer_bg_from_ui(ui)
            btn = _color_rgba(tool.inner)
            theme.update(
                {
                    "accent": accent,
                    "btn_active": accent,
                    "drag_active": accent,
                    "bg": bg,
                    "btn": btn,
                    "btn_hover": accent,
                    "slider_track": theme.get("slider_track", _color_rgba(ui.wcol_scroll.inner)),
                }
            )
            theme["panel_text"] = readable_text_on_bg(bg, theme["text"])
            btn_text, _ = _paired_text(btn, _color_rgba(tool.text))
            _, btn_text_on_active = _paired_text(accent, _color_rgba(tool.text_sel))
            theme["btn_text"] = btn_text
            theme["btn_text_on_active"] = btn_text_on_active
            return theme

    bg = _PRESET_HUD_OUTER_BG
    btn = (0.16, 0.16, 0.17, 1.0)
    theme.update(
        {
            "bg": bg,
            "btn": btn,
            "btn_active": get_accent_active_bg(accent),
            "drag_active": get_accent_drag_bg(accent),
            "btn_hover": (0.22, 0.22, 0.24, 1.0),
            "panel_text": theme["text"],
            "btn_text": theme["text"],
            "btn_text_on_active": theme["text_on_active"],
            "muted": theme.get("muted", (0.55, 0.55, 0.58, 1.0)),
        }
    )
    return theme


def hud_theme(context, prefs):
    accent = get_accent_rgba(context, prefs)
    return {
        "accent": accent,
        "row_active": get_accent_active_bg(accent),
        "drag_active": get_accent_drag_bg(accent),
    }
