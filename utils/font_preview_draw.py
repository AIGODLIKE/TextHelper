"""Draw font preview strings the same way TextCurve sees them (no fallback mixing)."""

import blf

from .font_blf import blf_load, blf_no_fallback_flag
from .font_glyph import char_renders_without_fallback


def blf_load_for_preview(filepath):
    """Load a font for blf preview (validated; skips known-bad files)."""
    return blf_load(filepath)


def char_has_glyph(font_id, char, point_size):
    return char_renders_without_fallback(font_id, char, point_size)


def trim_text_to_width(font_id, text, max_w, point_size):
    if not text or max_w <= 0.0:
        return ""
    point_size = float(point_size)
    no_fallback = blf_no_fallback_flag()
    blf.size(font_id, point_size)
    blf.enable(font_id, no_fallback)
    try:
        drawn = text
        while len(drawn) > 1 and blf.dimensions(font_id, drawn)[0] > max_w:
            drawn = drawn[:-1]
        return drawn
    finally:
        blf.disable(font_id, no_fallback)


def draw_blf_preview(
    font_id,
    text,
    x,
    y,
    max_w,
    size,
    color,
    *,
    ui_font=0,
    warn_color=(0.96, 0.42, 0.30, 1.0),
    bind_imbuf=None,
):
    """Render preview one glyph at a time with NO_FALLBACK (matches TextCurve)."""
    if font_id == -1 or not text:
        return

    point_size = float(size)
    drawn = trim_text_to_width(font_id, text, max_w, point_size)
    if not drawn:
        return

    cx = float(x)
    box_size = max(8, int(point_size * 0.82))

    def _draw(font_handle, draw_text):
        if bind_imbuf is not None:
            with blf.bind_imbuf(font_handle, bind_imbuf):
                blf.draw(font_handle, draw_text)
        else:
            blf.draw(font_handle, draw_text)

    for ch in drawn:
        if cx > x + max_w:
            break
        if ch.isspace():
            blf.size(ui_font, int(point_size))
            blf.color(ui_font, *color)
            blf.position(ui_font, cx, y, 0)
            _draw(ui_font, ch)
            cx += blf.dimensions(ui_font, ch)[0]
            continue

        if not char_has_glyph(font_id, ch, point_size):
            blf.size(ui_font, box_size)
            blf.color(ui_font, *warn_color)
            blf.position(ui_font, cx, y, 0)
            _draw(ui_font, "□")
            cx += blf.dimensions(ui_font, "□")[0] + 1.0
            continue

        no_fallback = blf_no_fallback_flag()
        blf.size(font_id, int(point_size))
        blf.enable(font_id, no_fallback)
        blf.color(font_id, *color)
        blf.position(font_id, cx, y, 0)
        try:
            _draw(font_id, ch)
            cw, _ = blf.dimensions(font_id, ch)
        finally:
            blf.disable(font_id, no_fallback)
        cx += cw
