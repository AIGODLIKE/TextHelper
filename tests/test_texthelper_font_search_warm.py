"""Blender-hosted tests for the time-sliced font search index."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from time import perf_counter
from types import SimpleNamespace

import bpy


def _source_path_from_args() -> Path:
    separator = sys.argv.index("--")
    return Path(sys.argv[separator + 1]).resolve()


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
    obj = None
    try:
        data = bpy.data.curves.new("TH Search Warm", "FONT")
        data.body = "Text Helper"
        obj = bpy.data.objects.new("TH Search Warm", data)
        bpy.context.scene.collection.objects.link(obj)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        from TextHelper.utils import font_search
        from TextHelper.utils.font_catalog_filter import (
            filtered_font_groups,
            invalidate_catalog_filter_cache,
        )
        from TextHelper.utils.font_loader import refresh_font_catalog

        wm = bpy.context.window_manager
        refresh_font_catalog(wm, force=True)
        catalog = wm.th_state.font_catalog
        assert len(catalog) > 0
        assert font_search.font_search_warming()
        assert bpy.app.timers.is_registered(font_search._search_warm_step)

        font_search._cancel_search_warm()
        entries = tuple(
            (item.display_name or "", item.filepath or "")
            for item in catalog
        )
        original_budget = font_search._WARM_BUDGET_SECONDS
        original_max = font_search._WARM_MAX_ITEMS
        try:
            font_search._WARM_BUDGET_SECONDS = 1.0
            font_search._WARM_MAX_ITEMS = 17
            font_search._WARM_STATE = {
                "entries": iter(entries),
                "processed": 0,
                "total": len(entries),
            }
            font_search._WARM_TIMER_REGISTERED = True
            ticks = 0
            last_processed = 0
            while font_search.font_search_warming():
                font_search._search_warm_step()
                processed, total = font_search.font_search_warm_progress()
                if total:
                    assert processed >= last_processed
                    last_processed = processed
                ticks += 1
                assert ticks < 1000
        finally:
            font_search._WARM_BUDGET_SECONDS = original_budget
            font_search._WARM_MAX_ITEMS = original_max

        assert ticks > 1
        assert len(font_search._SEARCH_CACHE) > 0

        sample = next(
            (
                item.display_name
                for item in catalog
                if item.display_name and len(item.display_name.split()[0]) >= 3
            ),
            "",
        )
        query = sample.split()[0][:3].lower()
        assert query
        noto = SimpleNamespace(
            display_name="Noto Sans CJK SC",
            filepath="blend://NotoSansCJKSC-Regular",
        )
        resource = SimpleNamespace(
            display_name="Resource Sans",
            filepath="blend://ResourceSans-Regular",
        )
        assert font_search.catalog_item_passes_name(noto, "noto")
        assert font_search.catalog_item_passes_name(noto, "notosanscjk")
        assert not font_search.catalog_item_passes_name(resource, "source")

        wm.th_state.th_font_picker_hide_unsupported = False
        wm.th_state.font_filter = query
        invalidate_catalog_filter_cache()
        started = perf_counter()
        groups = filtered_font_groups(bpy.context)
        warm_search_ms = (perf_counter() - started) * 1000.0
        assert groups

        font_search.queue_font_search_warm(catalog)
        assert bpy.app.timers.is_registered(font_search._search_warm_step)
        font_search.invalidate_font_search_cache()
        assert not font_search.font_search_warming()
        assert not bpy.app.timers.is_registered(font_search._search_warm_step)

        print("TEXTHELPER_SEARCH_WARM_CHUNK_TEST=PASS")
        print("TEXTHELPER_SEARCH_WARM_CANCEL_TEST=PASS")
        print("TEXTHELPER_SEARCH_TOKEN_BOUNDARY_TEST=PASS")
        print(f"TEXTHELPER_SEARCH_WARM_TICKS={ticks}")
        print(f"TEXTHELPER_SEARCH_WARM_QUERY_MS={warm_search_ms:.3f}")
    finally:
        package.unregister()
        if obj is not None:
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if data.users == 0:
                bpy.data.curves.remove(data)


if __name__ == "__main__":
    main()
