"""Small Blender-hosted font catalog/filter benchmark."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from time import perf_counter

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
    package = importlib.util.module_from_spec(spec)
    sys.modules["TextHelper"] = package
    spec.loader.exec_module(package)
    return package


def _timed(callback):
    start = perf_counter()
    result = callback()
    return (perf_counter() - start) * 1000.0, result


def main():
    package = _load_package(_source_path_from_args())
    package.register()
    obj = None
    try:
        data = bpy.data.curves.new("TH Benchmark", "FONT")
        data.body = "Text Helper"
        obj = bpy.data.objects.new("TH Benchmark", data)
        bpy.context.scene.collection.objects.link(obj)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        from TextHelper.utils.font_loader import iter_system_fonts, refresh_font_catalog
        from TextHelper.utils.font_catalog_filter import (
            filtered_font_groups,
            invalidate_catalog_filter_cache,
        )
        from TextHelper.utils import font_family
        from TextHelper.utils.font_name_meta import invalidate_font_name_cache
        from TextHelper.utils.font_search import invalidate_font_search_cache

        scan_ms, fonts = _timed(iter_system_fonts)
        refresh_ms, count = _timed(
            lambda: refresh_font_catalog(bpy.context.window_manager, force=True)
        )

        invalidate_font_name_cache()
        invalidate_family = getattr(font_family, "invalidate_font_family_cache", None)
        if invalidate_family is not None:
            invalidate_family()
        invalidate_font_search_cache()
        invalidate_catalog_filter_cache()
        first_ms, groups = _timed(lambda: filtered_font_groups(bpy.context))
        cached_ms, _ = _timed(lambda: filtered_font_groups(bpy.context))

        bpy.context.window_manager.th_state.font_filter = "noto"
        search_ms, search_groups = _timed(lambda: filtered_font_groups(bpy.context))

        print(f"TEXTHELPER_BENCH_SCAN_MS={scan_ms:.3f}")
        print(f"TEXTHELPER_BENCH_REFRESH_MS={refresh_ms:.3f}")
        print(f"TEXTHELPER_BENCH_FILTER_COLD_MS={first_ms:.3f}")
        print(f"TEXTHELPER_BENCH_FILTER_CACHED_MS={cached_ms:.3f}")
        print(f"TEXTHELPER_BENCH_SEARCH_MS={search_ms:.3f}")
        print(f"TEXTHELPER_BENCH_FONTS={len(fonts)}")
        print(f"TEXTHELPER_BENCH_CATALOG={count}")
        print(f"TEXTHELPER_BENCH_GROUPS={len(groups)}")
        print(f"TEXTHELPER_BENCH_SEARCH_GROUPS={len(search_groups)}")
    finally:
        package.unregister()
        if obj is not None:
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if data.users == 0:
                bpy.data.curves.remove(data)


if __name__ == "__main__":
    main()
