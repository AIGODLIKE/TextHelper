"""Shared HUD accent colors from add-on preferences."""

from __future__ import annotations

HUD_ACCENT_PRESETS = {
    "GREEN": (0.12, 0.86, 0.42),
    "BLUE": (0.22, 0.58, 0.96),
    "ORANGE": (0.96, 0.52, 0.14),
    "PURPLE": (0.62, 0.38, 0.95),
    "PINK": (0.94, 0.32, 0.58),
    "CYAN": (0.18, 0.78, 0.86),
}


def get_accent_rgba(prefs):
    preset = getattr(prefs, "hud_accent_preset", "GREEN") or "GREEN"
    if preset == "CUSTOM":
        custom = getattr(prefs, "hud_accent_custom", (0.12, 0.86, 0.42))
        return (float(custom[0]), float(custom[1]), float(custom[2]), 1.0)
    rgb = HUD_ACCENT_PRESETS.get(preset, HUD_ACCENT_PRESETS["GREEN"])
    return (rgb[0], rgb[1], rgb[2], 1.0)


def get_accent_active_bg(accent):
    return (
        accent[0] * 0.35 + 0.1,
        accent[1] * 0.35 + 0.1,
        accent[2] * 0.35 + 0.1,
        1.0,
    )


def get_accent_drag_bg(accent):
    return (
        accent[0] * 0.55 + 0.08,
        accent[1] * 0.55 + 0.08,
        accent[2] * 0.55 + 0.08,
        1.0,
    )


def hud_theme(prefs):
    accent = get_accent_rgba(prefs)
    return {
        "accent": accent,
        "row_active": get_accent_active_bg(accent),
        "drag_active": get_accent_drag_bg(accent),
    }
