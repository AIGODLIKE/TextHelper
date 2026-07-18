"""Blender-hosted regression tests for Text Helper background worker cleanup."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import bpy


def _source_path_from_args() -> Path:
    try:
        separator = sys.argv.index("--")
        source = sys.argv[separator + 1]
    except (ValueError, IndexError):
        raise SystemExit("Usage: blender --python test_texthelper_timer_lifecycle.py -- <source-dir>")
    return Path(source).resolve()


def _load_package(source: Path):
    spec = importlib.util.spec_from_file_location(
        "TextHelper",
        source / "__init__.py",
        submodule_search_locations=[str(source)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load TextHelper package from {source}")
    package = importlib.util.module_from_spec(spec)
    sys.modules["TextHelper"] = package
    spec.loader.exec_module(package)
    return package


def _registered(callback) -> bool:
    return callback is not None and bpy.app.timers.is_registered(callback)


def main():
    package = _load_package(_source_path_from_args())
    package.register()
    registered = True
    text_data = None
    temp_cache = None
    try:
        from TextHelper import sync
        from TextHelper.hud import slider_input
        from TextHelper.utils import (
            font_catalog_filter,
            font_loader,
            font_preview,
            font_search,
        )

        text_data = bpy.data.curves.new("TH Timer Lifecycle", "FONT")
        assert slider_input.focus_slider_value(bpy.context, "font_size", text_data)
        assert _registered(slider_input._CARET_TIMER)

        font_preview._schedule_queue()
        assert _registered(font_preview._QUEUE_TIMER)

        bpy.app.timers.register(font_catalog_filter._glyph_refine_step, first_interval=10.0)
        font_catalog_filter._GLYPH_TIMER_REGISTERED = True
        assert _registered(font_catalog_filter._glyph_refine_step)

        font_loader.reset_font_catalog_scan()
        font_loader.queue_font_catalog(bpy.context.window_manager)
        assert _registered(font_loader._do_deferred_catalog_load)

        font_search.queue_font_search_warm(bpy.context.window_manager.th_state.font_catalog)
        if len(bpy.context.window_manager.th_state.font_catalog) == 0:
            font_search._WARM_STATE = {
                "entries": iter((("Bfont", "blend://Bfont"),)),
                "processed": 0,
                "total": 1,
            }
            font_search._WARM_TIMER_REGISTERED = True
            bpy.app.timers.register(font_search._search_warm_step, first_interval=10.0)
        assert _registered(font_search._search_warm_step)

        temp_cache = TemporaryDirectory(prefix="texthelper-timer-cache-")
        font_search._CACHE_ROOT_OVERRIDE = Path(temp_cache.name)
        font_search._DISK_CACHE_DIRTY = True
        font_search._queue_search_cache_save()
        assert _registered(font_search._save_search_cache_step)

        sync._load_post(None)
        assert _registered(sync._load_timer)

        package.unregister()
        registered = False

        assert slider_input._CARET_TIMER is None
        assert font_preview._QUEUE_TIMER is None
        assert font_preview._REDRAW_TIMER is None
        assert not font_catalog_filter._GLYPH_TIMER_REGISTERED
        assert not _registered(font_catalog_filter._glyph_refine_step)
        assert not font_loader.font_catalog_loading()
        assert not _registered(font_loader._do_deferred_catalog_load)
        assert not font_search.font_search_warming()
        assert not _registered(font_search._search_warm_step)
        assert not font_search._SAVE_TIMER_REGISTERED
        assert not _registered(font_search._save_search_cache_step)
        assert sync._load_timer is None
        assert sync._bootstrap_timer is None

        print("TEXTHELPER_TIMER_START_TEST=PASS")
        print("TEXTHELPER_TIMER_CLEANUP_TEST=PASS")
    finally:
        if registered:
            try:
                package.unregister()
            except Exception:
                pass
        if text_data is not None:
            bpy.data.curves.remove(text_data)
        try:
            font_search._CACHE_ROOT_OVERRIDE = None
        except Exception:
            pass
        if temp_cache is not None:
            temp_cache.cleanup()


if __name__ == "__main__":
    main()
