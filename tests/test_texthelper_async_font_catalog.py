"""Blender-hosted tests for Text Helper's time-sliced font catalog scan."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from time import perf_counter

import bpy


def _source_path_from_args() -> Path:
    try:
        separator = sys.argv.index("--")
        return Path(sys.argv[separator + 1]).resolve()
    except (ValueError, IndexError):
        raise SystemExit(
            "Usage: blender --python test_texthelper_async_font_catalog.py -- <source-dir>"
        )


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


def main():
    package = _load_package(_source_path_from_args())
    package.register()
    try:
        from TextHelper.utils import font_loader

        wm = bpy.context.window_manager
        wm.th_state.font_catalog.clear()
        font_loader.reset_font_catalog_scan()

        original_budget = font_loader._CATALOG_SCAN_BUDGET_SECONDS
        original_chunk = font_loader._CATALOG_SCAN_MAX_CANDIDATES
        try:
            font_loader._CATALOG_SCAN_BUDGET_SECONDS = 1.0
            font_loader._CATALOG_SCAN_MAX_CANDIDATES = 23
            font_loader._catalog_scan_state = font_loader._new_catalog_scan_state(wm)
            font_loader._catalog_timer_registered = True

            ticks = 0
            last_scanned = 0
            while font_loader.font_catalog_loading():
                result = font_loader._do_deferred_catalog_load()
                ticks += 1
                progress = font_loader.font_catalog_load_progress()
                if result is not None:
                    assert progress["scanned"] >= last_scanned
                    last_scanned = progress["scanned"]
                    assert len(wm.th_state.font_catalog) == 0, (
                        "partial catalog became visible before atomic completion"
                    )
                assert ticks < 1000, "font catalog scan did not finish"

            assert ticks > 1, "scan was not split across timer-sized chunks"
            assert len(wm.th_state.font_catalog) > 0
            assert not font_loader.font_catalog_loading()
            assert font_loader.font_catalog_load_progress() == {"scanned": 0, "found": 0}

            wm.th_state.font_catalog.clear()
            font_loader._CATALOG_SCAN_BUDGET_SECONDS = original_budget
            font_loader._CATALOG_SCAN_MAX_CANDIDATES = original_chunk
            font_loader._catalog_scan_state = font_loader._new_catalog_scan_state(wm)
            font_loader._catalog_timer_registered = True
            default_tick_ms = []
            while font_loader.font_catalog_loading():
                started = perf_counter()
                font_loader._do_deferred_catalog_load()
                default_tick_ms.append((perf_counter() - started) * 1000.0)
                assert len(default_tick_ms) < 1000, "default font catalog scan did not finish"
            assert len(default_tick_ms) > 1

            wm.th_state.font_catalog.clear()
            font_loader._catalog_scan_state = font_loader._new_catalog_scan_state(wm)
            font_loader._catalog_timer_registered = False
            font_loader.reset_font_catalog_scan()
            assert font_loader._catalog_scan_state is None
            assert not font_loader.font_catalog_loading()
        finally:
            font_loader._CATALOG_SCAN_BUDGET_SECONDS = original_budget
            font_loader._CATALOG_SCAN_MAX_CANDIDATES = original_chunk

        print("TEXTHELPER_ASYNC_FONT_CATALOG_CHUNK_TEST=PASS")
        print("TEXTHELPER_ASYNC_FONT_CATALOG_ATOMIC_TEST=PASS")
        print("TEXTHELPER_ASYNC_FONT_CATALOG_CANCEL_TEST=PASS")
        print(f"TEXTHELPER_ASYNC_FONT_CATALOG_TICKS={len(default_tick_ms)}")
        print(f"TEXTHELPER_ASYNC_FONT_CATALOG_MAX_TICK_MS={max(default_tick_ms):.3f}")
    finally:
        package.unregister()


if __name__ == "__main__":
    main()
