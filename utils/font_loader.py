"""Load VectorFont files and enumerate installed system fonts."""

import os
import sys

import bpy

_FONT_EXTENSIONS = {".ttf", ".otf", ".ttc"}
BLEND_FONT_PREFIX = "blend://"
_catalog_scan_done = False
_catalog_timer_registered = False
_catalog_generation = 0


def catalog_generation() -> int:
    return _catalog_generation


def is_blend_catalog_filepath(filepath: str) -> bool:
    return str(filepath or "").startswith(BLEND_FONT_PREFIX)


def blend_font_name_from_catalog_filepath(filepath: str) -> str:
    if not is_blend_catalog_filepath(filepath):
        return ""
    return filepath[len(BLEND_FONT_PREFIX) :]


def blend_catalog_filepath(font_name: str) -> str:
    return f"{BLEND_FONT_PREFIX}{font_name}"


def is_builtin_bfont_name(name: str) -> bool:
    key = (name or "").strip().lower()
    if not key:
        return False
    return key == "bfont" or key.startswith("bfont ")


def get_default_bfont():
    """Return Blender's built-in text font (name varies by version, e.g. Bfont Regular)."""
    for candidate in ("Bfont Regular", "Bfont"):
        font = bpy.data.fonts.get(candidate)
        if font is not None:
            return font
    for font in bpy.data.fonts:
        if is_builtin_bfont_name(font.name):
            return font
    return None


def is_builtin_bfont_catalog(filepath: str) -> bool:
    if not is_blend_catalog_filepath(filepath):
        return False
    return is_builtin_bfont_name(blend_font_name_from_catalog_filepath(filepath))


def get_blend_font_from_catalog(filepath: str):
    name = blend_font_name_from_catalog_filepath(filepath)
    if not name:
        return None
    font = bpy.data.fonts.get(name)
    if font is not None:
        return font
    if is_builtin_bfont_name(name):
        return get_default_bfont()
    return None


def _blender_datafonts_dir():
    """Blender user fonts folder (5.2+: under DATAFILES, not user_resource('FONTS'))."""
    try:
        datafiles = bpy.utils.user_resource("DATAFILES", create=False)
        if datafiles:
            fonts_dir = os.path.join(datafiles, "fonts")
            if os.path.isdir(fonts_dir):
                return fonts_dir
    except Exception:
        pass
    return None


def system_font_directories():
    """Common system font folders for Windows, macOS, and Linux."""
    dirs = []
    seen = set()

    def _add(path):
        if not path:
            return
        norm = os.path.normcase(os.path.abspath(path))
        if os.path.isdir(path) and norm not in seen:
            seen.add(norm)
            dirs.append(path)

    if sys.platform == "win32":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        _add(os.path.join(windir, "Fonts"))
        _add(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts"))
    elif sys.platform == "darwin":
        _add("/Library/Fonts")
        _add("/System/Library/Fonts")
        home = os.path.expanduser("~")
        _add(os.path.join(home, "Library", "Fonts"))
    else:
        _add("/usr/share/fonts")
        _add("/usr/local/share/fonts")
        home = os.path.expanduser("~")
        _add(os.path.join(home, ".local", "share", "fonts"))
        _add(os.path.join(home, ".fonts"))

    _add(_blender_datafonts_dir())
    try:
        prefs = bpy.context.preferences.filepaths
        if prefs and prefs.font_directory:
            _add(bpy.path.abspath(prefs.font_directory))
    except Exception:
        pass
    return dirs


def default_font_browse_dir():
    """Best starting folder for the font file browser."""
    dirs = system_font_directories()
    return dirs[0] if dirs else ""


def disk_font_path(font):
    """Return an on-disk font path, or "" for Blender built-in / missing fonts."""
    if font is None:
        return ""
    raw = (getattr(font, "filepath", "") or "").strip()
    if not raw or raw.startswith("<"):
        return ""
    abs_path = bpy.path.abspath(raw)
    if not abs_path or abs_path.startswith("<") or not os.path.isfile(abs_path):
        return ""
    return abs_path


def resolve_font_filepath(font):
    """Return a font path for UI lookup even when the file is temporarily missing."""
    path = disk_font_path(font)
    if path:
        return path
    raw = (getattr(font, "filepath", "") or "").strip()
    if not raw or raw.startswith("<"):
        return ""
    abs_path = bpy.path.abspath(raw)
    if not abs_path or abs_path.startswith("<"):
        return ""
    return abs_path


def find_loaded_font(filepath):
    if is_blend_catalog_filepath(filepath):
        return get_blend_font_from_catalog(filepath)
    abs_path = disk_font_path_from_string(filepath)
    if not abs_path:
        return None
    for font in bpy.data.fonts:
        other = disk_font_path(font)
        if other and other == abs_path:
            return font
    return None


def disk_font_path_from_string(filepath):
    raw = (filepath or "").strip()
    if is_blend_catalog_filepath(raw):
        return ""
    if not raw or raw.startswith("<"):
        return ""
    abs_path = bpy.path.abspath(raw)
    if not abs_path or abs_path.startswith("<") or not os.path.isfile(abs_path):
        return ""
    return abs_path


def load_font_file(filepath):
    """Load a .ttf/.otf into bpy.data.fonts, reusing existing data-blocks."""
    from .font_blf import font_path_usable, mark_font_failed

    abs_path = disk_font_path_from_string(filepath)
    if not abs_path:
        raise FileNotFoundError(filepath or "")
    if not font_path_usable(abs_path):
        raise FileNotFoundError(filepath or "")
    existing = find_loaded_font(abs_path)
    if existing is not None:
        return existing
    try:
        return bpy.data.fonts.load(abs_path)
    except Exception:
        mark_font_failed(abs_path)
        raise


_VARIANT_SUFFIXES = {
    "bold": ("-Bold", " Bold", "Bold", "-Bd", "-Heavy", " Heavy"),
    "italic": ("-Italic", " Italic", "Italic", "-It", " It"),
    "bold_italic": (
        "-BoldItalic",
        " Bold Italic",
        "BoldItalic",
        "-Bold-Italic",
        "-Bold Italic",
        "Bold Italic",
    ),
}


def _font_stem_variants(stem):
    stems = {stem}
    for suffix in (
        "-Regular",
        " Regular",
        "Regular",
        "-Normal",
        " Normal",
        "Normal",
        "-Medium",
        " Medium",
        "Medium",
        "-Light",
        " Light",
        "Light",
        "-Roman",
        " Roman",
    ):
        if stem.endswith(suffix):
            stems.add(stem[: -len(suffix)])
    return stems


def find_font_variant(filepath, variant):
    """Return absolute path to a bold/italic sibling font, or None."""
    if not filepath or variant not in _VARIANT_SUFFIXES:
        return None
    directory = os.path.dirname(bpy.path.abspath(filepath))
    basename = os.path.basename(filepath)
    stem, ext = os.path.splitext(basename)
    if not ext:
        ext = ".ttf"
    tried = set()
    for base in _font_stem_variants(stem):
        for suffix in _VARIANT_SUFFIXES[variant]:
            candidate = os.path.join(directory, base + suffix + ext)
            key = os.path.normcase(candidate)
            if key in tried:
                continue
            tried.add(key)
            if os.path.isfile(candidate):
                return candidate
    return None


def sync_font_style_slots(text_data):
    """Fill bold / italic slots from the regular font path when variants exist."""
    filepath = disk_font_path(text_data.font)
    if not filepath:
        return

    regular = find_loaded_font(filepath) or load_font_file(filepath)
    text_data.font = regular

    bold_path = find_font_variant(filepath, "bold")
    italic_path = find_font_variant(filepath, "italic")
    bi_path = find_font_variant(filepath, "bold_italic")

    text_data.font_bold = load_font_file(bold_path) if bold_path else regular
    text_data.font_italic = load_font_file(italic_path) if italic_path else regular
    if bi_path:
        text_data.font_bold_italic = load_font_file(bi_path)
    elif bold_path and italic_path:
        text_data.font_bold_italic = text_data.font_bold
    elif bold_path:
        text_data.font_bold_italic = text_data.font_bold
    elif italic_path:
        text_data.font_bold_italic = text_data.font_italic
    else:
        text_data.font_bold_italic = regular


def has_real_bold_font(text_data):
    font = text_data.font
    bold = text_data.font_bold
    if font is None or bold is None or font == bold:
        return False
    regular_path = disk_font_path(font)
    bold_path = disk_font_path(bold)
    if not regular_path or not bold_path:
        return False
    return os.path.normcase(regular_path) != os.path.normcase(bold_path)


def assign_font(text_data, filepath):
    """Assign regular font and resolve bold/italic companion files when available."""
    if is_blend_catalog_filepath(filepath):
        font = get_blend_font_from_catalog(filepath)
        if font is None:
            raise FileNotFoundError(filepath)
        text_data.font = font
        try:
            from .text_format import reapply_bold_if_active

            reapply_bold_if_active(text_data)
        except Exception:
            pass
        try:
            from .vertical_align_check import invalidate_vertical_align_cache

            invalidate_vertical_align_cache()
        except Exception:
            pass
        text_data.update_tag()
        return font

    font = load_font_file(filepath)
    text_data.font = font
    sync_font_style_slots(text_data)
    try:
        from .text_format import reapply_bold_if_active

        reapply_bold_if_active(text_data)
    except Exception:
        pass
    try:
        from .vertical_align_check import invalidate_vertical_align_cache

        invalidate_vertical_align_cache()
    except Exception:
        pass
    text_data.update_tag()
    return font


def _font_display_name(filename):
    stem = os.path.splitext(filename)[0]
    return stem.replace("_", " ").replace("-", " ")


_FONT_HUD_LABEL_MAX_LEN = 20


def font_hud_label(font, context=None):
    """Font label for HUD/header using add-on font name display preference."""
    if font is None:
        return ""
    from .font_display import display_name_for_filepath

    path = resolve_font_filepath(font)
    name = display_name_for_filepath(path, context) if path else font.name
    if len(name) > _FONT_HUD_LABEL_MAX_LEN:
        return name[:_FONT_HUD_LABEL_MAX_LEN] + "…"
    return name


def iter_system_fonts():
    """Yield sorted dicts: display_name, filepath."""
    from .font_blf import font_magic_ok

    seen = set()
    entries = []
    for directory in system_font_directories():
        try:
            names = os.listdir(directory)
        except OSError:
            continue
        for name in names:
            ext = os.path.splitext(name)[1].lower()
            if ext not in _FONT_EXTENSIONS:
                continue
            filepath = os.path.join(directory, name)
            if not os.path.isfile(filepath):
                continue
            if not font_magic_ok(filepath):
                continue
            key = os.path.normcase(filepath)
            if key in seen:
                continue
            seen.add(key)
            entries.append(
                {
                    "display_name": _font_display_name(name),
                    "filepath": filepath,
                }
            )
    entries.sort(key=lambda item: item["display_name"].lower())
    return entries


def iter_blend_catalog_fonts(seen_disk_paths=None):
    """Yield fonts that live in the .blend (no disk file), plus disk fonts not found by system scan."""
    if seen_disk_paths is None:
        seen_disk_paths = set()
    entries = []
    seen_blend_names = set()
    try:
        fonts = sorted(bpy.data.fonts, key=lambda font: (font.name or "").lower())
    except Exception:
        fonts = ()
    for font in fonts:
        if font is None:
            continue
        disk = disk_font_path(font)
        if disk:
            key = os.path.normcase(disk)
            if key in seen_disk_paths:
                continue
            seen_disk_paths.add(key)
            basename = os.path.basename(disk)
            entries.append(
                {
                    "display_name": _font_display_name(basename) or font.name,
                    "filepath": disk,
                }
            )
            continue
        name = font.name or ""
        if not name or name in seen_blend_names:
            continue
        seen_blend_names.add(name)
        entries.append(
            {
                "display_name": name,
                "filepath": blend_catalog_filepath(name),
            }
        )
    entries.sort(key=lambda item: item["display_name"].lower())
    return entries


def iter_catalog_fonts():
    """System fonts plus blend-embedded / packed fonts from bpy.data.fonts."""
    system = iter_system_fonts()
    seen_disk = {os.path.normcase(entry["filepath"]) for entry in system}
    blend = iter_blend_catalog_fonts(seen_disk)
    return blend + system


def refresh_font_catalog(wm, force=False):
    """Fill WindowManager.th_state.font_catalog from disk."""
    global _catalog_scan_done, _catalog_generation
    if wm is None:
        return 0
    if not force and len(getattr(wm.th_state, "font_catalog", [])) > 0:
        return len(wm.th_state.font_catalog)
    wm.th_state.font_catalog.clear()
    try:
        for entry in iter_catalog_fonts():
            item = wm.th_state.font_catalog.add()
            item.display_name = entry["display_name"]
            item.filepath = entry["filepath"]
    except Exception:
        wm.th_state.font_catalog.clear()
        raise
    finally:
        _catalog_scan_done = True
        _catalog_generation += 1
    try:
        from .font_catalog_filter import invalidate_catalog_filter_cache

        invalidate_catalog_filter_cache()
    except Exception:
        pass
    try:
        from .font_language import invalidate_font_language_cache
        from .font_name_meta import invalidate_font_name_cache
        from .font_search import invalidate_font_search_cache

        invalidate_font_language_cache()
        invalidate_font_name_cache()
        invalidate_font_search_cache()
    except Exception:
        pass
    if wm.th_state.font_index >= len(wm.th_state.font_catalog):
        wm.th_state.font_index = max(0, len(wm.th_state.font_catalog) - 1)
    return len(wm.th_state.font_catalog)


def ensure_font_catalog(wm):
    """Scan fonts once synchronously; use from operators, not draw handlers."""
    global _catalog_scan_done
    if wm is None:
        return
    if len(getattr(wm.th_state, "font_catalog", [])) > 0:
        return
    if _catalog_scan_done:
        return
    try:
        refresh_font_catalog(wm, force=True)
    except Exception:
        _catalog_scan_done = True


def _do_deferred_catalog_load():
    global _catalog_scan_done, _catalog_timer_registered

    _catalog_timer_registered = False
    wm = bpy.context.window_manager
    if wm is None:
        return None
    if len(getattr(wm.th_state, "font_catalog", [])) > 0:
        return None
    if _catalog_scan_done:
        return None
    try:
        refresh_font_catalog(wm, force=True)
    except Exception:
        _catalog_scan_done = True
    try:
        from .font_preview import tag_ui_redraw

        tag_ui_redraw(bpy.context)
    except Exception:
        pass
    return None


def queue_font_catalog(wm):
    """Request an async catalog scan; safe to call from UI draw handlers."""
    global _catalog_timer_registered

    if wm is None:
        return
    if len(getattr(wm.th_state, "font_catalog", [])) > 0:
        return
    if _catalog_scan_done:
        return
    if not _catalog_timer_registered:
        _catalog_timer_registered = True
        bpy.app.timers.register(_do_deferred_catalog_load, first_interval=0.0)


def font_catalog_loading():
    return _catalog_timer_registered


def font_catalog_needs_refresh(wm):
    if wm is None:
        return False
    return _catalog_scan_done and len(getattr(wm.th_state, "font_catalog", [])) == 0


def unregister_font_catalog_queue():
    global _catalog_timer_registered

    if _catalog_timer_registered:
        try:
            bpy.app.timers.unregister(_do_deferred_catalog_load)
        except Exception:
            pass
    _catalog_timer_registered = False


def reset_font_catalog_scan():
    global _catalog_scan_done
    _catalog_scan_done = False


def prefetch_font_catalog(context) -> None:
    """Warm the font catalog in the background when text editing is likely."""
    if context is None:
        return
    wm = context.window_manager
    if wm is None or getattr(wm, "th_state", None) is None:
        return
    queue_font_catalog(wm)


def is_current_font(text_data, filepath):
    if text_data is None or not filepath:
        return False
    if is_blend_catalog_filepath(filepath):
        font = text_data.font
        if font is None:
            return False
        expected = blend_font_name_from_catalog_filepath(filepath)
        if font.name == expected:
            return True
        return is_builtin_bfont_name(expected) and is_builtin_bfont_name(font.name)
    if text_data.font is None:
        return False
    current = disk_font_path(text_data.font)
    other = disk_font_path_from_string(filepath)
    if not current or not other:
        return False
    return os.path.normcase(current) == os.path.normcase(other)
