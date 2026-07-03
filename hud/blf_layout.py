"""BLF vertical alignment helpers for HUD widgets."""

import blf

_TOOLBAR_REF_GLYPH = "Hg"


def text_bounds(font_id, text):
    box_fn = getattr(blf, "bounding_box", None)
    if box_fn is not None:
        try:
            bounds = box_fn(font_id, text)
            if bounds and len(bounds) >= 4:
                return bounds[0], bounds[1], bounds[2], bounds[3]
        except (TypeError, ValueError):
            pass
    tw, th = blf.dimensions(font_id, text or "A")
    return 0.0, 0.0, tw, th


def glyph_baseline_y(box, font_id, font_size, text="A"):
    """BLF baseline Y so `text` is vertically centered in box (x, y, w, h)."""
    blf.size(font_id, int(font_size))
    mid = box.y + box.h * 0.5
    _, ymin, _, ymax = text_bounds(font_id, text)
    if ymax != ymin:
        return mid - (ymax + ymin) * 0.5

    asc_fn = getattr(blf, "ascender", None)
    desc_fn = getattr(blf, "descender", None)
    if asc_fn is not None and desc_fn is not None:
        asc = asc_fn(font_id)
        desc = desc_fn(font_id)
        if asc != 0.0 or desc != 0.0:
            return mid - (asc + desc) * 0.5

    _, th = blf.dimensions(font_id, text or "A")
    return box.y + (box.h + th) * 0.5 - th * 0.75


def toolbar_baseline_y(box, font_id, font_size):
    """Shared baseline so preset/font/B/I/U/S/AA/aa align across the tool row."""
    return glyph_baseline_y(box, font_id, font_size, _TOOLBAR_REF_GLYPH)


def toolbar_font_size(scale):
    return max(int(round(11.0 * scale)), 9)


def text_visual_center_y(font_id, text, baseline_y):
    _, ymin, _, ymax = text_bounds(font_id, text or "A")
    if ymax != ymin:
        return baseline_y + (ymax + ymin) * 0.5
    _, th = blf.dimensions(font_id, text or "A")
    return baseline_y + th * 0.35


def draw_centered_glyph(box, font_id, font_size, text, color):
    blf.size(font_id, int(font_size))
    blf.color(font_id, *color)
    tw, _ = blf.dimensions(font_id, text)
    baseline_y = glyph_baseline_y(box, font_id, font_size, text)
    blf.position(font_id, box.x + (box.w - tw) * 0.5, baseline_y, 0)
    blf.draw(font_id, text)
