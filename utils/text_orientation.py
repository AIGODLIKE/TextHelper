"""Horizontal N-panel editing ↔ vertical Blender body (transpose columns)."""

from __future__ import annotations

import bpy

# Legacy column blocks (pre-1.5.56) used double newlines between stacked columns.
COLUMN_SEP = "\n\n"
# Fullwidth space keeps column slots aligned in CJK fonts (never shown in N-panel).
COLUMN_FILL = "\u3000"
_FILL_STRIP = COLUMN_FILL + " \t"


def _column_order(text_data) -> str:
    return getattr(text_data.text_helper, "th_vertical_column_order", "RTL")


def _strip_column_fill(text: str) -> str:
    return text.rstrip(_FILL_STRIP)


def _pad_lines(lines: list[str]) -> list[str]:
    if not lines:
        return []
    max_len = max(len(line) for line in lines)
    return [line + COLUMN_FILL * (max_len - len(line)) for line in lines]


def layout_columns_from_source_lines(lines: list[str], column_order: str) -> list[str]:
    """Typing-order lines → left-to-right column order for Blender body."""
    if column_order == "RTL":
        return list(reversed(lines))
    return list(lines)


def source_lines_from_layout_columns(columns_left_to_right: list[str], column_order: str) -> list[str]:
    """Left-to-right body columns → typing-order lines for the N-panel."""
    if column_order == "RTL":
        return list(reversed(columns_left_to_right))
    return list(columns_left_to_right)


def columns_source_to_body(source: str, column_order: str = "RTL") -> str:
    """Each source line is one vertical column, typed left-to-right.

    N-panel lines stay in typing order. RTL places the first typed line in the
    rightmost viewport column; LTR places it in the leftmost column.
    """
    if not source:
        return ""
    lines = source.split("\n")
    layout_lines = layout_columns_from_source_lines(lines, column_order)

    if len(layout_lines) == 1:
        return "\n".join(layout_lines[0])

    padded = _pad_lines(layout_lines)
    return "\n".join("".join(chars) for chars in zip(*padded))


def body_to_columns_source(body: str, column_order: str = "RTL") -> str:
    """Recover N-panel typing-order lines from transposed Blender body."""
    if not body:
        return ""

    if COLUMN_SEP in body:
        layout_columns = ["".join(block.split("\n")) for block in body.split(COLUMN_SEP)]
        return "\n".join(source_lines_from_layout_columns(layout_columns, column_order))

    rows = body.split("\n")
    if not rows:
        return ""

    if all(len(row) <= 1 for row in rows):
        return "".join(rows)

    max_cols = max(len(row) for row in rows)
    columns_left_to_right = []
    for col_idx in range(max_cols):
        chars = [row[col_idx] for row in rows if col_idx < len(row)]
        columns_left_to_right.append(_strip_column_fill("".join(chars)))

    source_lines = source_lines_from_layout_columns(columns_left_to_right, column_order)
    return "\n".join(source_lines)


def vertical_source_char_count(text_data) -> int:
    """Visible character count for vertical N-panel source (excludes padding)."""
    source = getattr(text_data.text_helper, "th_vertical_source", "") or ""
    return sum(len(_strip_column_fill(line)) for line in source.split("\n"))


def is_vertical(text_data) -> bool:
    return getattr(text_data.text_helper, "th_text_orientation", "HORIZONTAL") == "VERTICAL"


def vertical_first_column(text_data) -> str:
    """First typing-order column (N-panel line 0), for font previews."""
    if not is_vertical(text_data):
        return ""
    source = getattr(text_data.text_helper, "th_vertical_source", "") or ""
    if not source.strip():
        source = body_to_columns_source(text_data.body or "", _column_order(text_data))
    if not source:
        return ""
    return _strip_column_fill(source.split("\n", 1)[0]).strip()


def _horizontal_content(text_data) -> str:
    return getattr(text_data, "body", "") or ""


def _in_edit_font() -> bool:
    from .font_context import is_font_edit_mode

    return is_font_edit_mode(bpy.context)


def _refresh_after_body_change(text_data) -> None:
    from .text_format import _sync_body_format

    _sync_body_format(text_data, allow_reassign=not _in_edit_font())
    text_data.update_tag()


def sync_vertical_source_to_body(text_data, *, context=None) -> None:
    if _in_edit_font():
        return
    from .text_limits import assign_vertical_source, clamp_multiline_text, clamp_text_body, text_body_max_len

    source = clamp_multiline_text(getattr(text_data.text_helper, "th_vertical_source", "") or "", context=context)
    assign_vertical_source(text_data.text_helper, source, context=context)
    if not source and text_data.body:
        source = body_to_columns_source(text_data.body, _column_order(text_data))
        text_data.text_helper.th_vertical_source = source
    body = columns_source_to_body(source, _column_order(text_data))
    truncated = False

    if len(body) > text_body_max_len(context):
        body = clamp_text_body(body, context=context)
        recovered = body_to_columns_source(body, _column_order(text_data))
        global _VERTICAL_SOURCE_GUARD
        _VERTICAL_SOURCE_GUARD = True
        try:
            text_data.text_helper.th_vertical_source = recovered
        finally:
            _VERTICAL_SOURCE_GUARD = False
        truncated = True
    text_data.body = body
    _refresh_after_body_change(text_data)
    if truncated:
        from .ui_textbox import sync_panel_textbox_from_canonical

        sync_panel_textbox_from_canonical(text_data, vertical=True, context=context)


def sync_body_to_vertical_source(text_data, *, context=None) -> None:
    """Recover N-panel columns after in-viewport EDIT_FONT edits."""
    if not is_vertical(text_data):
        return
    from .text_limits import assign_vertical_source, clamp_multiline_text

    source = body_to_columns_source(text_data.body or "", _column_order(text_data))
    source = clamp_multiline_text(source, context=context)
    global _VERTICAL_SOURCE_GUARD
    _VERTICAL_SOURCE_GUARD = True
    try:
        assign_vertical_source(text_data.text_helper, source, context=context)
    finally:
        _VERTICAL_SOURCE_GUARD = False


def apply_orientation(text_data, orientation: str, *, context=None) -> None:
    current = getattr(text_data.text_helper, "th_text_orientation", "HORIZONTAL")
    if orientation == current:
        return

    from .text_limits import clamp_multiline_text

    order = _column_order(text_data)
    if orientation == "VERTICAL":
        if current == "HORIZONTAL":
            text_data.text_helper.th_vertical_source = clamp_multiline_text(
                _horizontal_content(text_data),
                context=context,
            )
        elif not getattr(text_data.text_helper, "th_vertical_source", ""):
            text_data.text_helper.th_vertical_source = clamp_multiline_text(
                body_to_columns_source(text_data.body, order),
                context=context,
            )
        sync_vertical_source_to_body(text_data, context=context)
    else:
        source = getattr(text_data.text_helper, "th_vertical_source", "") or body_to_columns_source(
            text_data.body, order
        )
        text_data.body = clamp_multiline_text(source, context=context)
        _refresh_after_body_change(text_data)

    text_data.text_helper.th_text_orientation = orientation


def apply_column_order(text_data, new_order: str, *, context=None) -> None:
    """Flip viewport column direction without reordering N-panel lines."""
    if new_order == _column_order(text_data):
        return
    text_data.text_helper.th_vertical_column_order = new_order
    if not is_vertical(text_data):
        return
    sync_vertical_source_to_body(text_data, context=context)


def insert_column_break(text_data, *, context=None) -> bool:
    if not is_vertical(text_data):
        return False
    text = getattr(text_data.text_helper, "th_vertical_source", "") or ""
    if text and not text.endswith("\n"):
        text_data.text_helper.th_vertical_source = text + "\n"
        sync_vertical_source_to_body(text_data, context=context)
        return True
    return False


_VERTICAL_SOURCE_GUARD = False


def set_vertical_source(text_data, raw: str, *, context=None) -> None:
    from .text_limits import assign_vertical_source, clamp_multiline_text

    global _VERTICAL_SOURCE_GUARD
    _VERTICAL_SOURCE_GUARD = True
    try:
        assign_vertical_source(text_data.text_helper, clamp_multiline_text(raw, context=context), context=context)
        from .text_case import sync_live_text_case

        sync_live_text_case(text_data)
        sync_vertical_source_to_body(text_data, context=context)
    finally:
        _VERTICAL_SOURCE_GUARD = False
    from .ui_textbox import sync_panel_textbox_from_canonical

    sync_panel_textbox_from_canonical(text_data, vertical=True, context=context)


def clear_vertical_content(text_data, *, context=None) -> None:
    global _VERTICAL_SOURCE_GUARD
    _VERTICAL_SOURCE_GUARD = True
    try:
        text_data.text_helper.th_vertical_source = ""
        text_data.body = ""
    finally:
        _VERTICAL_SOURCE_GUARD = False
    from .ui_textbox import sync_panel_textbox_from_canonical

    sync_panel_textbox_from_canonical(text_data, vertical=True, flip_active=True, context=context)
    _refresh_after_body_change(text_data)


def normalize_incoming_text(text_data, raw: str, *, context=None) -> str:
    if is_vertical(text_data):
        set_vertical_source(text_data, raw, context=context)
        return text_data.body
    return raw
