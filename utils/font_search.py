"""Multi-field font catalog search with CJK pinyin and kana helpers.

Bundled ``cjk_pinyin_min.json`` is a minified hanzi→pinyin table used only for
font name search suggestions. It ships with the add-on and is not fetched at runtime.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from time import perf_counter

import bpy

from .font_family import family_key_for_filepath, family_key_from_stem, parse_font_stem
from .font_display import display_name_for_filepath
from .font_name_meta import read_font_search_name_strings
from .font_search_aliases import alias_tokens_for_query, alias_tokens_for_text

@dataclass(frozen=True)
class _SearchIndex:
    blob: str
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class _QueryPlan:
    variants: tuple[str, ...]
    ascii_tokens: tuple[str, ...]


_SEARCH_CACHE: dict[str, _SearchIndex] = {}
_SEARCH_PATH_KEYS: dict[str, str] = {}
_PINYIN_DICT: dict[str, str] | None = None
_WARM_STATE = None
_WARM_TIMER_REGISTERED = False
_WARM_BUDGET_SECONDS = 0.004
_WARM_MAX_ITEMS = 8
_DISK_CACHE_SCHEMA = 1
_DISK_CACHE_LOADED = False
_DISK_CACHE_DIRTY = False
_DISK_CACHE_RECORDS = 0
_DISK_CACHE_FILE_SIZE = 0
_DISK_CACHE_MAX_BYTES = 32 * 1024 * 1024
_DISK_CACHE_MAX_RECORDS = 100_000
_SAVE_TIMER_REGISTERED = False
_CACHE_ROOT_OVERRIDE = None
_LAST_WARM_STATS = {"total": 0, "reused": 0, "built": 0}
_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|[_\-./]+")
_QUERY_SPLIT = re.compile(r"[\s,;|]+")


def invalidate_font_search_cache(*, clear_disk=False) -> None:
    global _DISK_CACHE_LOADED, _DISK_CACHE_DIRTY
    global _DISK_CACHE_RECORDS, _DISK_CACHE_FILE_SIZE

    _cancel_search_warm()
    _cancel_search_cache_save()
    _SEARCH_CACHE.clear()
    _SEARCH_PATH_KEYS.clear()
    _query_variants.cache_clear()
    _query_plan.cache_clear()
    if clear_disk:
        _remove_search_cache_file()
        _DISK_CACHE_LOADED = True
    else:
        _DISK_CACHE_LOADED = False
    _DISK_CACHE_DIRTY = False
    _DISK_CACHE_RECORDS = 0
    _DISK_CACHE_FILE_SIZE = 0


def _search_cache_root(*, create=False) -> Path | None:
    if _CACHE_ROOT_OVERRIDE is not None:
        root = Path(_CACHE_ROOT_OVERRIDE)
    else:
        from .. import ADDON_PACKAGE

        try:
            base = bpy.utils.extension_path_user(ADDON_PACKAGE) or ""
        except Exception:
            base = ""
        if not base:
            return None
        root = Path(base) / "font_search"
    if create:
        try:
            root.mkdir(parents=True, exist_ok=True)
        except OSError:
            return None
    return root


def _search_cache_path(*, create=False) -> Path | None:
    root = _search_cache_root(create=create)
    if root is None:
        return None
    return root / "font_search_index_v1.json"


def _ensure_disk_cache_loaded() -> None:
    global _DISK_CACHE_LOADED, _DISK_CACHE_DIRTY
    global _DISK_CACHE_RECORDS, _DISK_CACHE_FILE_SIZE

    if _DISK_CACHE_LOADED:
        return
    _DISK_CACHE_LOADED = True
    _DISK_CACHE_DIRTY = False
    _DISK_CACHE_RECORDS = 0
    _DISK_CACHE_FILE_SIZE = 0
    path = _search_cache_path()
    if path is None:
        return
    try:
        size = path.stat().st_size
        if size <= 0 or size > _DISK_CACHE_MAX_BYTES:
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return
    if not isinstance(payload, dict) or payload.get("schema") != _DISK_CACHE_SCHEMA:
        return
    records = payload.get("records")
    if not isinstance(records, dict) or len(records) > _DISK_CACHE_MAX_RECORDS:
        return

    loaded = 0
    for key, blob in records.items():
        if (
            not isinstance(key, str)
            or not isinstance(blob, str)
            or not key
            or len(key) > 32_768
            or len(blob) > 262_144
        ):
            continue
        _SEARCH_CACHE.setdefault(
            key,
            _SearchIndex(blob=blob, tokens=tuple(dict.fromkeys(blob.split()))),
        )
        loaded += 1
    _DISK_CACHE_RECORDS = loaded
    _DISK_CACHE_FILE_SIZE = size


def _write_search_cache_now() -> bool:
    global _DISK_CACHE_DIRTY, _DISK_CACHE_RECORDS, _DISK_CACHE_FILE_SIZE

    if not _DISK_CACHE_DIRTY:
        return True
    path = _search_cache_path(create=True)
    if path is None:
        return False
    records = {
        key: index.blob
        for key, index in list(_SEARCH_CACHE.items())[:_DISK_CACHE_MAX_RECORDS]
    }
    payload = {
        "schema": _DISK_CACHE_SCHEMA,
        "records": records,
    }
    temp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(encoded) > _DISK_CACHE_MAX_BYTES:
            return False
        with temp_path.open("wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        _DISK_CACHE_RECORDS = len(records)
        _DISK_CACHE_FILE_SIZE = len(encoded)
        _DISK_CACHE_DIRTY = False
        return True
    except OSError:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def _save_search_cache_step():
    global _SAVE_TIMER_REGISTERED

    _SAVE_TIMER_REGISTERED = False
    _write_search_cache_now()
    return None


def _queue_search_cache_save() -> None:
    global _SAVE_TIMER_REGISTERED

    if _SAVE_TIMER_REGISTERED or not _DISK_CACHE_DIRTY:
        return
    if _search_cache_root() is None:
        return
    bpy.app.timers.register(_save_search_cache_step, first_interval=0.2)
    _SAVE_TIMER_REGISTERED = True


def _cancel_search_cache_save() -> None:
    global _SAVE_TIMER_REGISTERED

    if _SAVE_TIMER_REGISTERED:
        try:
            bpy.app.timers.unregister(_save_search_cache_step)
        except ValueError:
            pass
    _SAVE_TIMER_REGISTERED = False


def _remove_search_cache_file() -> None:
    path = _search_cache_path()
    if path is None:
        return
    for target in (path, path.with_suffix(path.suffix + ".tmp")):
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass


def clear_font_search_disk_cache() -> None:
    """Clear persisted font-name metadata before a user-requested rebuild."""
    invalidate_font_search_cache(clear_disk=True)


def font_search_cache_stats() -> dict[str, object]:
    _ensure_disk_cache_loaded()
    state = _WARM_STATE
    active = {
        "total": int(state.get("total", 0)),
        "reused": int(state.get("reused", 0)),
        "built": int(state.get("built", 0)),
    } if state is not None else dict(_LAST_WARM_STATS)
    path = _search_cache_path()
    return {
        "memory_records": len(_SEARCH_CACHE),
        "persistent_records": _DISK_CACHE_RECORDS,
        "file_size": _DISK_CACHE_FILE_SIZE,
        "dirty": _DISK_CACHE_DIRTY,
        "warming": font_search_warming(),
        "path": str(path) if path is not None else "",
        **active,
    }


def _load_pinyin_dict() -> dict[str, str]:
    global _PINYIN_DICT
    if _PINYIN_DICT is not None:
        return _PINYIN_DICT
    path = Path(__file__).resolve().parent / "cjk_pinyin_min.json"
    if not path.is_file():
        _PINYIN_DICT = {}
        return _PINYIN_DICT
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    _PINYIN_DICT = payload if isinstance(payload, dict) else {}
    return _PINYIN_DICT


def _has_cjk(text: str) -> bool:
    for char in text:
        code = ord(char)
        if (
            0x3040 <= code <= 0x30FF
            or 0x3400 <= code <= 0x4DBF
            or 0x4E00 <= code <= 0x9FFF
            or 0xAC00 <= code <= 0xD7AF
        ):
            return True
    return False


def _kana_fold(text: str) -> str:
    chars = []
    for char in text:
        code = ord(char)
        if 0x3041 <= code <= 0x3096:
            chars.append(chr(code + 0x60))
        elif 0x30A1 <= code <= 0x30F6:
            chars.append(chr(code - 0x60))
        else:
            chars.append(char)
    return "".join(chars)


def _split_tokens(text: str) -> list[str]:
    if not text:
        return []
    parts = []
    for piece in _CAMEL_BOUNDARY.split(text):
        piece = piece.strip()
        if piece:
            parts.append(piece)
    return parts


def _pinyin_variants(text: str) -> tuple[str, str]:
    table = _load_pinyin_dict()
    if not table or not text:
        return "", ""
    syllables = []
    for char in text:
        if char in table:
            syllables.append(table[char])
        elif "\u4e00" <= char <= "\u9fff":
            return "", ""
    if not syllables:
        return "", ""
    full = "".join(syllables)
    initials = "".join(word[0] for word in syllables if word)
    return full, initials


def _cache_key(filepath: str) -> str:
    if str(filepath or "").startswith("blend://"):
        return os.path.normcase(filepath or "")
    abs_path = bpy.path.abspath(filepath or "")
    norm_path = os.path.normcase(abs_path)
    cached = _SEARCH_PATH_KEYS.get(norm_path)
    if cached is not None:
        return cached
    try:
        stat = os.stat(abs_path)
        fingerprint = f"{stat.st_mtime_ns}:{stat.st_size}"
    except OSError:
        fingerprint = "0:0"
    key = f"{norm_path}:{fingerprint}"
    _SEARCH_PATH_KEYS[norm_path] = key
    return key


def _build_catalog_search_index(display_name: str, filepath: str) -> _SearchIndex:
    global _DISK_CACHE_DIRTY

    _ensure_disk_cache_loaded()
    key = _cache_key(filepath)
    cached = _SEARCH_CACHE.get(key)
    if cached is not None:
        return cached

    if str(filepath).startswith("blend://"):
        blend_name = filepath[8:] or display_name
        stem = blend_name
        basename = blend_name
        family_stem, weight_label, _rank = parse_font_stem(blend_name)
        family_key = family_key_from_stem(blend_name)
        parts = [display_name, blend_name, blend_name.replace("_", " ")]
    else:
        basename = os.path.basename(filepath)
        stem, _ext = os.path.splitext(basename)
        family_stem, weight_label, _rank = parse_font_stem(stem)
        family_key = family_key_for_filepath(filepath)
        parts = [
            display_name,
            basename,
            stem,
            family_stem,
            family_key,
            weight_label,
        ]
        parts.extend(read_font_search_name_strings(filepath))
        catalog_display_name = display_name
        for mode in ("FILENAME", "FAMILY", "FULL", "POSTSCRIPT"):
            label = display_name_for_filepath(
                filepath,
                catalog_display_name=catalog_display_name,
                mode=mode,
            )
            if label:
                parts.append(label)
        parts.extend(_split_tokens(stem))
    if family_stem and weight_label:
        family_display = family_stem.replace("_", " ").replace("-", " ").strip()
        parts.extend((family_stem, family_key, weight_label))
        parts.append(f"{family_stem} {weight_label}")
        if family_display:
            parts.append(f"{family_display} {weight_label}")
    parts = list(dict.fromkeys(part for part in parts if part))
    for name in list(parts):
        parts.extend(_split_tokens(name))
    parts = list(dict.fromkeys(part for part in parts if part))

    joined = " ".join(parts)
    extras = [joined]
    normalized = unicodedata.normalize("NFKC", joined)
    if normalized != joined:
        extras.append(normalized)
    joined_has_cjk = _has_cjk(joined)
    if joined_has_cjk:
        kana = _kana_fold(joined)
        if kana != joined:
            extras.append(kana)
    extras.extend(alias_tokens_for_text(joined, *parts))
    if joined_has_cjk:
        full_py, init_py = _pinyin_variants(joined)
        if full_py:
            extras.append(full_py)
        if init_py:
            extras.append(init_py)
        for name in parts:
            if _has_cjk(name):
                full_py, init_py = _pinyin_variants(name)
                if full_py:
                    extras.append(full_py)
                if init_py:
                    extras.append(init_py)

    blob = " ".join(dict.fromkeys(value.lower() for value in extras if value)).strip()
    index = _SearchIndex(blob=blob, tokens=tuple(dict.fromkeys(blob.split())))
    _SEARCH_CACHE[key] = index
    _DISK_CACHE_DIRTY = True
    if _WARM_STATE is None:
        _queue_search_cache_save()
    return index


def _catalog_search_index(item) -> _SearchIndex:
    return _build_catalog_search_index(
        getattr(item, "display_name", "") or "",
        getattr(item, "filepath", "") or "",
    )


def build_catalog_search_blob(item) -> str:
    """Compatibility accessor for callers that only need normalized text."""
    return _catalog_search_index(item).blob


@lru_cache(maxsize=128)
def _query_variants(filter_text: str) -> tuple[str, ...]:
    base = filter_text.strip().lower()
    if not base:
        return ()
    variants = {base, _kana_fold(base).lower(), unicodedata.normalize("NFKC", base).lower()}
    for token in _QUERY_SPLIT.split(base):
        token = token.strip()
        if not token:
            continue
        variants.add(token)
        variants.add(_kana_fold(token).lower())
    for alias in alias_tokens_for_query(filter_text):
        norm = alias.lower()
        variants.add(norm)
        variants.add(_kana_fold(norm).lower())
        variants.add(unicodedata.normalize("NFKC", norm).lower())
    if _has_cjk(base):
        full_py, init_py = _pinyin_variants(base)
        if full_py:
            variants.add(full_py)
        if init_py:
            variants.add(init_py)
    return tuple(variant for variant in variants if variant)


@lru_cache(maxsize=128)
def _query_plan(filter_text: str) -> _QueryPlan:
    text = filter_text.strip().lower()
    ascii_tokens = (
        tuple(token for token in _QUERY_SPLIT.split(text) if token)
        if text.isascii()
        else ()
    )
    return _QueryPlan(variants=_query_variants(filter_text), ascii_tokens=ascii_tokens)


def _query_in_index(query: str, index: _SearchIndex) -> bool:
    """Match typeahead prefixes on index tokens; avoid mid-word hits like sour→resource."""
    if not query:
        return False
    query = query.lower().strip()
    if not query:
        return False
    if _has_cjk(query):
        return query in index.blob

    tokens = index.tokens
    if not tokens:
        return False

    parts = [part for part in _QUERY_SPLIT.split(query) if part]
    if not parts:
        return False
    if len(parts) > 1:
        return all(_query_part_in_index(part, tokens, index.blob) for part in parts)
    return _query_part_in_index(parts[0], tokens, index.blob)


def _query_part_in_index(part: str, tokens: tuple[str, ...], blob: str) -> bool:
    if any(token.startswith(part) for token in tokens):
        return True
    if len(part) >= 4 and f" {part} " in f" {blob} ":
        return True
    return False


def catalog_item_passes_name(item, text_filter: str) -> bool:
    if not text_filter:
        return True
    index = _catalog_search_index(item)
    if not index.blob:
        return False
    plan = _query_plan(text_filter)
    for query in plan.variants:
        if _query_in_index(query, index):
            return True
    if plan.ascii_tokens and all(
        _query_in_index(token, index) for token in plan.ascii_tokens
    ):
        return True
    return False


def _tag_search_warm_redraw(state, *, force=False):
    now = perf_counter()
    if not force and now - float(state.get("last_redraw", 0.0)) < 0.1:
        return
    state["last_redraw"] = now
    try:
        from .font_preview import tag_ui_redraw

        tag_ui_redraw(bpy.context, all_windows=True)
        from ..hud.draw import tag_redraw

        tag_redraw()
    except Exception:
        pass


def _finish_search_warm():
    global _WARM_STATE, _WARM_TIMER_REGISTERED, _DISK_CACHE_DIRTY, _LAST_WARM_STATS

    state = _WARM_STATE
    _WARM_STATE = None
    _WARM_TIMER_REGISTERED = False
    if state is not None:
        keys = state.get("keys")
        if keys is not None:
            stale = set(_SEARCH_CACHE).difference(keys)
            if stale:
                for key in stale:
                    _SEARCH_CACHE.pop(key, None)
                _DISK_CACHE_DIRTY = True
        _LAST_WARM_STATS = {
            "total": int(state.get("total", 0)),
            "reused": int(state.get("reused", 0)),
            "built": int(state.get("built", 0)),
        }
        if state.get("built", 0):
            _DISK_CACHE_DIRTY = True
        _queue_search_cache_save()
        _tag_search_warm_redraw(state, force=True)
    return None


def _search_warm_step():
    state = _WARM_STATE
    if state is None:
        return _finish_search_warm()

    deadline = perf_counter() + _WARM_BUDGET_SECONDS
    processed = 0
    while processed < _WARM_MAX_ITEMS and perf_counter() < deadline:
        try:
            display_name, filepath = next(state["entries"])
        except StopIteration:
            return _finish_search_warm()
        key = _cache_key(filepath)
        state.setdefault("keys", set()).add(key)
        if key in _SEARCH_CACHE:
            state["reused"] = int(state.get("reused", 0)) + 1
        else:
            state["built"] = int(state.get("built", 0)) + 1
        _build_catalog_search_index(display_name, filepath)
        state["processed"] += 1
        processed += 1
    _tag_search_warm_redraw(state)
    return 0.01


def queue_font_search_warm(catalog) -> None:
    """Warm searchable font metadata in short background slices."""
    global _WARM_STATE, _WARM_TIMER_REGISTERED

    _cancel_search_warm()
    if catalog is None or len(catalog) == 0:
        return
    _ensure_disk_cache_loaded()
    entries = tuple(
        (
            getattr(item, "display_name", "") or "",
            getattr(item, "filepath", "") or "",
        )
        for item in catalog
    )
    _WARM_STATE = {
        "entries": iter(entries),
        "processed": 0,
        "total": len(entries),
        "reused": 0,
        "built": 0,
        "keys": set(),
        "last_redraw": 0.0,
    }
    _WARM_TIMER_REGISTERED = True
    bpy.app.timers.register(_search_warm_step, first_interval=0.05)


def font_search_warming() -> bool:
    return bool(_WARM_TIMER_REGISTERED and _WARM_STATE is not None)


def font_search_warm_progress() -> tuple[int, int]:
    state = _WARM_STATE
    if state is None:
        return 0, 0
    return int(state["processed"]), int(state["total"])


def _cancel_search_warm() -> None:
    global _WARM_STATE, _WARM_TIMER_REGISTERED

    if _WARM_TIMER_REGISTERED:
        try:
            bpy.app.timers.unregister(_search_warm_step)
        except ValueError:
            pass
    _WARM_STATE = None
    _WARM_TIMER_REGISTERED = False


def unregister_font_search_warm() -> None:
    _cancel_search_warm()
    _cancel_search_cache_save()
    _write_search_cache_now()
