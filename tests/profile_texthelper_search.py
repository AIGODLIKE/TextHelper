"""Profile Text Helper's cached font-name search inside Blender."""

from __future__ import annotations

import cProfile
import importlib.util
from pathlib import Path
import pstats
import sys

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
        data = bpy.data.curves.new("TH Search Profile", "FONT")
        data.body = "Text Helper"
        obj = bpy.data.objects.new("TH Search Profile", data)
        bpy.context.scene.collection.objects.link(obj)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        from TextHelper.utils.font_catalog_filter import (
            filtered_font_groups,
            invalidate_catalog_filter_cache,
        )
        from TextHelper.utils.font_loader import refresh_font_catalog

        refresh_font_catalog(bpy.context.window_manager, force=True)
        state = bpy.context.window_manager.th_state
        state.th_font_picker_hide_unsupported = False
        state.font_filter = ""
        invalidate_catalog_filter_cache()
        filtered_font_groups(bpy.context)

        state.font_filter = "noto"
        invalidate_catalog_filter_cache()
        profiler = cProfile.Profile()
        profiler.enable()
        groups = filtered_font_groups(bpy.context)
        profiler.disable()
        stats = pstats.Stats(profiler, stream=sys.stdout).strip_dirs().sort_stats("cumtime")
        stats.print_stats(25)
        print(f"TEXTHELPER_PROFILE_SEARCH_GROUPS={len(groups)}")
    finally:
        package.unregister()
        if obj is not None:
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if data.users == 0:
                bpy.data.curves.remove(data)


if __name__ == "__main__":
    main()
