"""Custom font preview thumbnails (imbuf + blf) with user settings."""

import hashlib
import os

import bpy
import blf
import imbuf

from .addon_prefs import get_addon_prefs
from .font_preview_draw import blf_load_for_preview, draw_blf_preview, trim_text_to_width
from .font_preview_text import get_font_preview_text
from .font_blf import blf_unload, font_path_usable
from .png_clean import strip_png_color_profile, strip_png_dir, write_solid_png

_PREVIEW_COLLECTION = None
_ACTIVE_SETTINGS_HASH = ""
_DEFAULT_SAMPLE = "Exploration witnesses courage, open source witnesses glory"
_FALLBACK_SAMPLE = "Aa"
_PREVIEW_QUEUE = []
_QUEUE_KEYS = set()
_QUEUE_SCHEDULED = False
_REDRAW_SCHEDULED = False
_FAILED_KEYS = set()
_CACHE_CLEANED = False


def _ensure_clean_cache():
    global _CACHE_CLEANED
    if _CACHE_CLEANED:
        return
    strip_png_dir(_cache_dir())
    _CACHE_CLEANED = True


def _addon_cache_root():
    try:
        from .. import ADDON_PACKAGE

        path = bpy.utils.extension_path_user(ADDON_PACKAGE)
        if path:
            return path
    except Exception:
        pass
    for pkg in ("bl_ext.user_default.TextHelper", "TextHelper"):
        try:
            path = bpy.utils.extension_path_user(pkg)
            if path:
                return path
        except Exception:
            continue
    return ""


def _cache_dir():
    base = _addon_cache_root()
    if not base:
        return ""
    cache = os.path.join(base, "font_previews")
    os.makedirs(cache, exist_ok=True)
    return cache


def _settings_token(context):
    prefs = get_addon_prefs(context)
    return "|".join(
        (
            str(getattr(prefs, "font_preview_size", 36)),
            str(getattr(prefs, "font_preview_width", 512)),
            str(getattr(prefs, "font_preview_height", 56)),
            str(getattr(prefs, "font_preview_ui_scale", 3.5)),
            getattr(prefs, "font_preview_mode", "OBJECT"),
            getattr(prefs, "font_preview_sample", _DEFAULT_SAMPLE),
            "dark_v8",
        )
    )


def _settings_hash(context):
    return hashlib.md5(_settings_token(context).encode("utf-8")).hexdigest()[:12]


def _preview_text(context, display_name=""):
    return get_font_preview_text(context, display_name)


def preview_collection():
    global _PREVIEW_COLLECTION
    if _PREVIEW_COLLECTION is None:
        _PREVIEW_COLLECTION = bpy.utils.previews.new()
    return _PREVIEW_COLLECTION


def _preview_key(filepath, settings_hash):
    digest = hashlib.md5(
        (settings_hash + "|" + os.path.normcase(bpy.path.abspath(filepath))).encode("utf-8", errors="surrogateescape")
    ).hexdigest()
    return "thf_" + digest[:24]


def _png_cache_path(key):
    cache = _cache_dir()
    if not cache:
        return ""
    return os.path.join(cache, key + ".png")


def _blank_png_path(width, height, variant="light"):
    cache = _cache_dir()
    if not cache:
        return ""
    return os.path.join(cache, f"_blank_{int(width)}x{int(height)}_{variant}_srgb.png")


def _solid_ibuf(width, height, *, light=True):
    w, h = int(width), int(height)
    variant = "light" if light else "dark"
    blank_path = _blank_png_path(w, h, variant)
    if not blank_path:
        return None
    rgba = (0.97, 0.97, 0.97, 1.0) if light else (0.16, 0.16, 0.17, 1.0)
    if not os.path.isfile(blank_path):
        write_solid_png(blank_path, w, h, rgba)
    else:
        strip_png_color_profile(blank_path)
    try:
        return imbuf.load(blank_path)
    except Exception:
        if write_solid_png(blank_path, w, h, rgba):
            try:
                return imbuf.load(blank_path)
            except Exception:
                return None
        return None

def _write_png(path, ibuf) -> bool:
    if not path:
        return False
    try:
        imbuf.write(ibuf, filepath=path)
    except Exception:
        return False
    if not os.path.isfile(path):
        return False
    strip_png_color_profile(path)
    return os.path.getsize(path) > 64


def _fit_point_size(font_id, text, width, height, max_size):
    inner_w = max(32.0, width - 28.0)
    inner_h = max(16.0, height - 10.0)
    size = int(max_size)
    while size >= 10:
        drawn = trim_text_to_width(font_id, text, inner_w, size) or text
        blf.size(font_id, float(size))
        blf.enable(font_id, blf.NO_FALLBACK)
        try:
            tw, th = blf.dimensions(font_id, drawn)
        finally:
            blf.disable(font_id, blf.NO_FALLBACK)
        if tw <= inner_w and th <= inner_h:
            return size, tw, th
        size -= 1
    blf.size(font_id, 10.0)
    drawn = trim_text_to_width(font_id, text, inner_w, 10) or text
    blf.enable(font_id, blf.NO_FALLBACK)
    try:
        tw, th = blf.dimensions(font_id, drawn)
    finally:
        blf.disable(font_id, blf.NO_FALLBACK)
    return 10, tw, th


def _draw_preview_chars(ibuf, font_id, text, width, height, point_size, glyph_status):
    fitted_size, _, th = _fit_point_size(font_id, text, width, height, point_size)
    py = max(4.0, (height - th) * 0.5)
    draw_blf_preview(
        font_id,
        text,
        14.0,
        py,
        width - 28.0,
        fitted_size,
        (0.95, 0.95, 0.96, 1.0),
        warn_color=(0.96, 0.42, 0.30, 1.0),
        bind_imbuf=ibuf,
    )


def _render_preview_png(filepath, png_path, sample, width, height, point_size):
    font_id = blf_load_for_preview(filepath)
    if font_id == -1:
        return False
    try:
        ibuf = _solid_ibuf(width, height, light=False)
        if ibuf is None:
            return False
        text = sample or _FALLBACK_SAMPLE
        fitted_size, _, _ = _fit_point_size(font_id, text, width, height, point_size)
        _draw_preview_chars(ibuf, font_id, text, width, height, point_size, None)
        return _write_png(png_path, ibuf)
    except Exception:
        return False
    finally:
        blf_unload(filepath)


def _ensure_settings(context):
    global _ACTIVE_SETTINGS_HASH, _FAILED_KEYS
    current = _settings_hash(context)
    if current != _ACTIVE_SETTINGS_HASH:
        release_font_previews()
        _ACTIVE_SETTINGS_HASH = current
        _FAILED_KEYS.clear()


def _schedule_redraw():
    global _REDRAW_SCHEDULED
    if _REDRAW_SCHEDULED:
        return

    def _run():
        global _REDRAW_SCHEDULED
        _REDRAW_SCHEDULED = False
        tag_ui_redraw(bpy.context)
        return None

    _REDRAW_SCHEDULED = True
    bpy.app.timers.register(_run, first_interval=0.05)


def _load_icon_from_png(coll, key, png_path):
    strip_png_color_profile(png_path)
    if key in coll:
        try:
            del coll[key]
        except Exception:
            pass
    try:
        coll.load(key, png_path, "IMAGE")
    except Exception:
        return 0
    return coll[key].icon_id if key in coll else 0


def _process_queue_step(max_items=3):
    global _PREVIEW_QUEUE
    if not _PREVIEW_QUEUE:
        return None

    context = bpy.context
    if context is None:
        return 0.1

    _ensure_settings(context)
    settings_hash = _ACTIVE_SETTINGS_HASH
    coll = preview_collection()
    prefs = get_addon_prefs(context)
    width = int(getattr(prefs, "font_preview_width", 512))
    height = int(getattr(prefs, "font_preview_height", 56))
    point_size = int(getattr(prefs, "font_preview_size", 36))

    processed = 0
    while _PREVIEW_QUEUE and processed < max_items:
        filepath, display_name = _PREVIEW_QUEUE.pop(0)
        abs_path = bpy.path.abspath(filepath)
        key = _preview_key(abs_path, settings_hash)
        _QUEUE_KEYS.discard(key)

        if key in coll and coll[key].icon_id:
            continue
        if key in _FAILED_KEYS:
            continue

        png_path = _png_cache_path(key)
        if not png_path:
            _FAILED_KEYS.add(key)
            continue

        sample = _preview_text(context, display_name)

        if not os.path.isfile(png_path):
            os.makedirs(os.path.dirname(png_path), exist_ok=True)
            ok = _render_preview_png(abs_path, png_path, sample, width, height, point_size)
            if not ok:
                ok = _render_preview_png(abs_path, png_path, _FALLBACK_SAMPLE, width, height, point_size)
            if not ok:
                _FAILED_KEYS.add(key)
                continue

        icon_id = _load_icon_from_png(coll, key, png_path)
        if not icon_id:
            _schedule_redraw()
        processed += 1

    if _PREVIEW_QUEUE:
        _schedule_redraw()
        return 0.05
    _schedule_redraw()
    return None


def _schedule_queue():
    global _QUEUE_SCHEDULED
    if _QUEUE_SCHEDULED:
        return
    _QUEUE_SCHEDULED = True

    def _kick():
        global _QUEUE_SCHEDULED
        _QUEUE_SCHEDULED = False
        return _process_queue_step()

    bpy.app.timers.register(_kick, first_interval=0.01)


def init_font_preview_cache():
    """Strip legacy ICC chunks from cached preview PNGs once per session."""
    try:
        _ensure_clean_cache()
    except OSError as exc:
        print(f"Text Helper: font preview cache cleanup failed ({exc})")


def queue_font_preview(context, filepath, display_name=""):
    if not filepath or context is None:
        return
    _ensure_clean_cache()
    abs_path = bpy.path.abspath(filepath)
    if not os.path.isfile(abs_path):
        return
    if not font_path_usable(abs_path):
        return
    prefs = get_addon_prefs(context)
    if not getattr(prefs, "font_preview_icons", True):
        return

    _ensure_settings(context)
    key = _preview_key(abs_path, _ACTIVE_SETTINGS_HASH)
    if key in _FAILED_KEYS:
        return
    coll = preview_collection()
    if key in coll and coll[key].icon_id:
        return
    token = (abs_path, display_name)
    if key in _QUEUE_KEYS:
        return
    _QUEUE_KEYS.add(key)
    _PREVIEW_QUEUE.append(token)
    _schedule_queue()


def get_font_icon(context, filepath, display_name=""):
    """Return icon_value for UILayout, or 0 if preview is not ready yet."""
    _ensure_clean_cache()
    if not filepath or context is None:
        return 0
    abs_path = bpy.path.abspath(filepath)
    if not os.path.isfile(abs_path):
        return 0
    if not font_path_usable(abs_path):
        return 0

    prefs = get_addon_prefs(context)
    if not getattr(prefs, "font_preview_icons", True):
        return 0

    _ensure_settings(context)
    key = _preview_key(abs_path, _ACTIVE_SETTINGS_HASH)
    if key in _FAILED_KEYS:
        return 0

    coll = preview_collection()
    if key in coll:
        icon = coll[key].icon_id
        if icon:
            return icon
        _schedule_redraw()

    png_path = _png_cache_path(key)
    if png_path and os.path.isfile(png_path):
        icon = _load_icon_from_png(coll, key, png_path)
        if icon:
            return icon
        _schedule_redraw()

    queue_font_preview(context, filepath, display_name)
    return 0


def clear_font_preview_cache_files():
    cache = _cache_dir()
    if not cache or not os.path.isdir(cache):
        return
    for name in os.listdir(cache):
        if not name.endswith(".png"):
            continue
        try:
            os.remove(os.path.join(cache, name))
        except OSError:
            pass


def warm_font_preview_queue(context, limit=16):
    """Queue previews for visible catalog rows after settings change."""
    if context is None:
        return
    wm = context.window_manager
    state = getattr(wm, "th_state", None)
    catalog = getattr(state, "font_catalog", None) if state is not None else None
    if not catalog:
        return
    center = max(0, min(int(getattr(state, "font_index", 0)), len(catalog) - 1))
    start = max(0, center - 2)
    end = min(len(catalog), start + limit)
    for i in range(start, end):
        item = catalog[i]
        queue_font_preview(context, item.filepath, item.display_name)


def invalidate_font_previews(clear_files=False):
    global _ACTIVE_SETTINGS_HASH, _PREVIEW_QUEUE, _QUEUE_KEYS, _FAILED_KEYS
    _ACTIVE_SETTINGS_HASH = ""
    _PREVIEW_QUEUE.clear()
    _QUEUE_KEYS.clear()
    _FAILED_KEYS.clear()
    release_font_previews()
    if clear_files:
        clear_font_preview_cache_files()


def invalidate_and_rebuild_font_previews(context, *, clear_files=True):
    invalidate_font_previews(clear_files=clear_files)
    warm_font_preview_queue(context)
    tag_ui_redraw(context)
    try:
        from ..hud.draw import tag_redraw

        tag_redraw()
    except Exception:
        pass


def release_font_previews():
    global _PREVIEW_COLLECTION
    if _PREVIEW_COLLECTION is not None:
        bpy.utils.previews.remove(_PREVIEW_COLLECTION)
        _PREVIEW_COLLECTION = None


def tag_ui_redraw(context):
    if context is None:
        return
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()
