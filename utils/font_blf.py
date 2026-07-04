"""Safe BLF font loading with validation and failure caching (less console noise)."""

from __future__ import annotations

import os

import blf
import bpy

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


def mark_font_failed(filepath: str) -> None:
    key = _norm_key(filepath)
    if key:
        _FAILED_PATHS.add(key)


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
    return signature in _TTF_MAGICS


def font_path_usable(filepath: str) -> bool:
    """Fast pre-check before touching BLF / VectorFont loaders."""
    if not font_magic_ok(filepath):
        return False
    return not is_failed_font(filepath)


def blf_load(filepath: str) -> int:
    abs_path = _resolve_disk_path(filepath)
    if not abs_path:
        return -1
    key = os.path.normcase(abs_path)
    if key in _FAILED_PATHS:
        return -1
    if not font_magic_ok(abs_path):
        _FAILED_PATHS.add(key)
        return -1
    # Drop stale BLF handles when font files were replaced on disk while Blender is open.
    try:
        blf.unload(abs_path)
    except Exception:
        pass
    font_id = blf.load(abs_path)
    if font_id == -1:
        _FAILED_PATHS.add(key)
    return font_id


def blf_unload(filepath: str) -> None:
    abs_path = _resolve_disk_path(filepath)
    if not abs_path:
        return
    try:
        blf.unload(abs_path)
    except Exception:
        pass
