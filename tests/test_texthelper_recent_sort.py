"""Regression test for cached Recent sorting across picker reopen/draw cycles."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
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


def _first_family(groups) -> str:
    assert groups
    return groups[0].family_key


def main():
    package = _load_package(_source_path_from_args())
    package.register()
    try:
        from TextHelper.utils import font_catalog_filter, font_loader, font_recent

        context = bpy.context
        wm = context.window_manager
        state = wm.th_state
        prefs = SimpleNamespace(font_recent_keys="[]")
        original_get_addon_prefs = font_recent.get_addon_prefs
        font_recent.get_addon_prefs = lambda _context: prefs

        font_loader.reset_font_catalog_scan()
        state.font_catalog.clear()
        for display_name, filepath in (
            ("Alpha", "blend://Alpha-Regular"),
            ("Bravo", "blend://Bravo-Regular"),
            ("Charlie", "blend://Charlie-Regular"),
        ):
            item = state.font_catalog.add()
            item.display_name = display_name
            item.filepath = filepath

        state.font_filter = ""
        state.font_sort = "RECENT"
        state.font_language = "ALL"
        state.th_font_picker_hide_unsupported = False
        state.th_font_picker_multi_weight_only = False
        state.th_font_picker_favorites_only = False
        state.th_font_picker_variable_only = False
        font_recent.clear_recent_families(context)
        font_catalog_filter.invalidate_catalog_filter_cache()

        initial = font_catalog_filter.filtered_font_groups(context)
        assert _first_family(initial) == "alpha"
        initial_key = font_catalog_filter._FILTER_CACHE_KEY
        initial_generation = font_recent.recent_generation()

        font_recent.touch_recent_family(context, "blend://Charlie-Regular")
        assert font_recent.recent_generation() == initial_generation + 1
        assert font_catalog_filter._FILTER_CACHE_KEY is None
        reopened = font_catalog_filter.filtered_font_groups(context)
        print("TEXTHELPER_RECENT_SORT_AFTER_CHARLIE=" + ",".join(group.family_key for group in reopened))
        print(f"TEXTHELPER_RECENT_SORT_PREFS={prefs.font_recent_keys}")
        assert _first_family(reopened) == "charlie"
        assert font_catalog_filter._FILTER_CACHE_KEY != initial_key

        font_recent.touch_recent_family(context, "blend://Bravo-Regular")
        reopened_again = font_catalog_filter.filtered_font_groups(context)
        assert _first_family(reopened_again) == "bravo"

        stable_generation = font_recent.recent_generation()
        font_recent.touch_recent_family(context, "blend://Bravo-Regular")
        assert font_recent.recent_generation() == stable_generation

        print("TEXTHELPER_RECENT_SORT_INVALIDATION_TEST=PASS")
        print("TEXTHELPER_RECENT_SORT_REOPEN_TEST=PASS")
        print("TEXTHELPER_RECENT_SORT_STABLE_TOUCH_TEST=PASS")
    finally:
        try:
            font_recent.get_addon_prefs = original_get_addon_prefs
            font_catalog_filter.invalidate_catalog_filter_cache()
        except Exception:
            pass
        package.unregister()


if __name__ == "__main__":
    main()
