"""Safe BLF font loading with validation and failure caching (less console noise)."""

from __future__ import annotations

import hashlib
import os

import blf
import bpy

from .font_loader import (
    blend_font_name_from_catalog_filepath,
    disk_font_path,
    get_blend_font_from_catalog,
    is_blend_catalog_filepath,
    is_builtin_bfont_name,
)

_FAILED_PATHS: set[str] = set()
_KNOWN_BAD_NAMES = frozenset(
    name.lower()
    for name in (
        "mstmc.ttf",
        "mstmc.ttc",
    )
)

_TTF_MAGICS = (
    b"\x00\x01\x00\x00",
    b"OTTO",
    b"ttcf",
    b"true",
    b"typ1",
)
_WOFF_MAGICS = (
    b"wOFF",
    b"wOF2",
)
_FONT_MAGICS = _TTF_MAGICS + _WOFF_MAGICS

# BLF_NO_FALLBACK exists in C for older builds but was only exposed to Python recently.
_BLF_NO_FALLBACK = 524288


def blf_no_fallback_flag() -> int:
    return getattr(blf, "NO_FALLBACK", _BLF_NO_FALLBACK)


def _resolve_disk_path(filepath: str) -> str:
    raw = (filepath or "").strip()
    if not raw or raw.startswith("<"):
        return ""
    abs_path = bpy.path.abspath(raw)
    if not abs_path or abs_path.startswith("<") or not os.path.isfile(abs_path):
        return ""
    return abs_path


def _norm_key(filepath: str) -> str:
    abs_path = _resolve_disk_path(filepath)
    if not abs_path:
        return ""
    return os.path.normcase(abs_path)


def is_failed_font(filepath: str) -> bool:
    key = _norm_key(filepath)
    return bool(key) and key in _FAILED_PATHS


def mark_font_failed(filepath: str) -> bool:
    key = _norm_key(filepath)
    if key:
        _FAILED_PATHS.add(key)
    return bool(key)


def clear_font_failure_cache() -> None:
    _FAILED_PATHS.clear()


def font_magic_ok(filepath: str) -> bool:
    abs_path = _resolve_disk_path(filepath)
    if not abs_path:
        return False
    if os.path.basename(abs_path).lower() in _KNOWN_BAD_NAMES:
        return False
    try:
        with open(abs_path, "rb") as handle:
            signature = handle.read(4)
    except OSError:
        return False
    if len(signature) < 4:
        return False
    if signature in _FONT_MAGICS:
        return True
    return os.path.splitext(abs_path)[1].lower() in {".ttf", ".otf", ".ttc", ".woff", ".woff2"}


def font_path_usable(filepath: str) -> bool:
    """Fast pre-check before touching BLF / VectorFont loaders."""
    if not font_magic_ok(filepath):
        return False
    return not is_failed_font(filepath)


def blf_unload(filepath: str) -> None:
    abs_path = resolve_catalog_blf_path(filepath) or _resolve_disk_path(filepath)
    if not abs_path:
        return
    try:
        blf.unload(abs_path)
    except Exception:
        pass


def _blend_font_cache_dir() -> str:
    from .. import ADDON_PACKAGE

    try:
        base = bpy.utils.extension_path_user(ADDON_PACKAGE)
    except Exception:
        base = ""
    if not base:
        return ""
    cache = os.path.join(base, "blend_font_cache")
    os.makedirs(cache, exist_ok=True)
    return cache


def _materialize_blend_font(font) -> str:
    if font is None:
        return ""
    name = getattr(font, "name", "") or "font"
    if is_builtin_bfont_name(name):
        return ""

    cache = _blend_font_cache_dir()
    if not cache:
        return ""

    digest = hashlib.md5(name.encode("utf-8", errors="surrogateescape")).hexdigest()[:16]
    out_path = os.path.join(cache, f"{digest}.font")
    if os.path.isfile(out_path) and os.path.getsize(out_path) > 64:
        return out_path

    packed = getattr(font, "packed_file", None)
    if packed is not None:
        try:
            packed.unpack(out_path)
        except Exception:
            data = getattr(packed, "data", None)
            if data:
                try:
                    with open(out_path, "wb") as handle:
                        handle.write(data)
                except OSError:
                    return ""
        if os.path.isfile(out_path) and os.path.getsize(out_path) > 64:
            return out_path
    return ""


def resolve_catalog_blf_path(filepath: str) -> str:
    """Return a disk path suitable for blf.load for catalog entries."""
    if not is_blend_catalog_filepath(filepath):
        return _resolve_disk_path(filepath)
    if is_builtin_bfont_name(blend_font_name_from_catalog_filepath(filepath)):
        return ""
    font = get_blend_font_from_catalog(filepath)
    if font is None:
        return ""
    disk = disk_font_path(font)
    if disk:
        return disk
    return _materialize_blend_font(font)


def blf_load(filepath: str) -> int:
    abs_path = resolve_catalog_blf_path(filepath)
    if not abs_path:
        return -1
    key = os.path.normcase(abs_path)
    if key in _FAILED_PATHS:
        return -1
    if not font_magic_ok(abs_path):
        _FAILED_PATHS.add(key)
        return -1
    try:
        blf.unload(abs_path)
    except Exception:
        pass
    font_id = blf.load(abs_path)
    if font_id == -1:
        _FAILED_PATHS.add(key)
    return font_id
