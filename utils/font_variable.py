"""Detect OpenType variable fonts on disk."""

from __future__ import annotations

import os


def is_variable_font_filepath(filepath: str) -> bool:
    if not filepath:
        return False
    stem = os.path.splitext(os.path.basename(filepath))[0].lower()
    name_markers = (
        "variable",
        "-vf",
        "_vf",
        "[var]",
        " var",
        "varfont",
    )
    if any(marker in stem for marker in name_markers):
        return True
    return _file_has_fvar_table(filepath)


def _file_has_fvar_table(filepath: str) -> bool:
    try:
        abs_path = os.path.abspath(filepath)
        size = os.path.getsize(abs_path)
        if size <= 0:
            return False
        with open(abs_path, "rb") as handle:
            sample = handle.read(min(size, 512 * 1024))
        return b"fvar" in sample
    except OSError:
        return False
