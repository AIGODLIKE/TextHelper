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


def draw_line_segments(shader, segments, color):
    if len(segments) < 2:
        return
    batch = batch_for_shader(shader, "LINES", {"pos": segments})
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def draw_refresh_icon(shader, cx, cy, size, color):
    """Circular refresh arrow for HUD icon buttons."""
    radius = max(3.0, size * 0.38)
    start = math.radians(130.0)
    sweep = math.radians(300.0)
    steps = 20
    arc = []
    for i in range(steps + 1):
        ang = start + sweep * (i / steps)
        arc.append((cx + math.cos(ang) * radius, cy + math.sin(ang) * radius))
    segments = []
    for i in range(len(arc) - 1):
        segments.extend((arc[i], arc[i + 1]))
    tip = arc[-1]
    tip_ang = start + sweep
    arm = max(2.5, size * 0.22)
    left = (
        tip[0] + math.cos(tip_ang + math.radians(135.0)) * arm,
        tip[1] + math.sin(tip_ang + math.radians(135.0)) * arm,
    )
    right = (
        tip[0] + math.cos(tip_ang + math.radians(95.0)) * arm,
        tip[1] + math.sin(tip_ang + math.radians(95.0)) * arm,
    )
    segments.extend((tip, left, tip, right))
    draw_line_segments(shader, segments, color)
