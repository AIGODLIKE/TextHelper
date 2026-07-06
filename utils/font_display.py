"""Resolve catalog font labels from add-on display preferences."""

from __future__ import annotations

import os

from .addon_prefs import get_addon_prefs
from .font_family import parse_font_stem


def get_font_display_mode(context) -> str:
    prefs = get_addon_prefs(context)
    mode = getattr(prefs, "font_display_mode", "FAMILY") or "FAMILY"
    if mode in {"FILENAME", "FAMILY", "FULL", "POSTSCRIPT"}:
        return mode
    return "FAMILY"


def _filename_display(filepath: str, catalog_display_name: str = "") -> str:
    if catalog_display_name:
        return catalog_display_name
    stem = os.path.splitext(os.path.basename(filepath or ""))[0]
    return stem.replace("_", " ").replace("-", " ")


def _parsed_family_display(filepath: str) -> str:
    stem = os.path.splitext(os.path.basename(filepath or ""))[0]
    family, _weight, _rank = parse_font_stem(stem)
    return family.replace("_", " ").replace("-", " ").strip()


def display_name_for_filepath(
    filepath: str,
    context=None,
    *,
    catalog_display_name: str = "",
    mode: str | None = None,
) -> str:
    if str(filepath or "").startswith("blend://"):
        name = filepath[8:] or catalog_display_name
        return name.replace("_", " ").strip() or name
    if not filepath:
        return catalog_display_name or ""

    if mode is None:
        mode = get_font_display_mode(context)

    if mode == "FILENAME":
        return _filename_display(filepath, catalog_display_name)

    from .font_name_meta import read_font_name_id

    if mode == "FAMILY":
        name = read_font_name_id(filepath, 16) or read_font_name_id(filepath, 1)
        if name:
            return name
        parsed = _parsed_family_display(filepath)
        if parsed:
            return parsed
        return _filename_display(filepath, catalog_display_name)

    if mode == "FULL":
        name = read_font_name_id(filepath, 4)
        if name:
            return name
        return _filename_display(filepath, catalog_display_name)

    if mode == "POSTSCRIPT":
        name = read_font_name_id(filepath, 6)
        if name:
            return name
        return os.path.splitext(os.path.basename(filepath))[0]

    return _filename_display(filepath, catalog_display_name)


def display_name_for_catalog_item(item, context=None, *, mode: str | None = None) -> str:
    filepath = getattr(item, "filepath", "") or ""
    catalog_display_name = getattr(item, "display_name", "") or ""
    return display_name_for_filepath(
        filepath,
        context,
        catalog_display_name=catalog_display_name,
        mode=mode,
    )
