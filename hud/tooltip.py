"""Shared HUD tooltip drawing."""

import blf

from .gpu_primitives import draw_rounded_rect


def draw_hud_tooltip(shader, font_id, rect, text, scale, region_w, accent):
    if not text:
        return
    tip_size = int(11 * scale)
    blf.size(font_id, tip_size)
    tw, th = blf.dimensions(font_id, text)
    pad_x = 10.0 * scale
    pad_y = 8.0 * scale
    box_w = tw + pad_x * 2.0
    box_h = th + pad_y * 2.0
    cx = rect.x + rect.w * 0.5
    margin = 4.0 * scale
    tip_x = max(margin, min(region_w - box_w - margin, cx - box_w * 0.5))
    tip_y = rect.y - box_h - 8.0 * scale
    if tip_y < margin:
        tip_y = rect.y + rect.h + 8.0 * scale

    draw_rounded_rect(shader, tip_x, tip_y, box_w, box_h, (0.05, 0.05, 0.06, 0.97), 4.0 * scale)
    draw_rounded_rect(shader, tip_x, tip_y, 2.0 * scale, box_h, (*accent[:3], 0.95), 2.0 * scale)
    blf.color(font_id, 0.95, 0.95, 0.96, 1.0)
    blf.position(font_id, tip_x + pad_x, tip_y + pad_y, 0)
    blf.draw(font_id, text)
