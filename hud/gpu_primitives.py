"""GPU helpers for HUD drawing."""

import math

from gpu_extras.batch import batch_for_shader


def rounded_rect_tris(x, y, w, h, radius, segments=5):
    """Return triangle-fan vertices for a rounded rectangle."""
    if w <= 0.0 or h <= 0.0:
        return ()
    radius = max(0.0, min(radius, w * 0.5, h * 0.5))
    if radius <= 0.5:
        return ((x, y), (x + w, y), (x + w, y + h), (x, y + h))

    verts = []
    corners = (
        (x + w - radius, y + h - radius, math.pi * 0.0, math.pi * 0.5),
        (x + radius, y + h - radius, math.pi * 0.5, math.pi),
        (x + radius, y + radius, math.pi, math.pi * 1.5),
        (x + w - radius, y + radius, math.pi * 1.5, math.pi * 2.0),
    )
    for cx, cy, a0, a1 in corners:
        for i in range(segments + 1):
            t = i / segments
            ang = a0 + (a1 - a0) * t
            verts.append((cx + math.cos(ang) * radius, cy + math.sin(ang) * radius))
    return tuple(verts)


def draw_rounded_rect(shader, x, y, w, h, color, radius=6.0):
    verts = rounded_rect_tris(x, y, w, h, radius)
    if not verts:
        return
    batch = batch_for_shader(shader, "TRI_FAN", {"pos": verts})
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)
