"""Verify the installed extension reuses its font search index across processes."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys

import bpy


def _args() -> tuple[str, str]:
    separator = sys.argv.index("--")
    module_name = sys.argv[separator + 1]
    mode = sys.argv[separator + 2] if len(sys.argv) > separator + 2 else "reuse"
    return module_name, mode


def _drain(font_search) -> None:
    if bpy.app.timers.is_registered(font_search._search_warm_step):
        bpy.app.timers.unregister(font_search._search_warm_step)
    ticks = 0
    while font_search.font_search_warming():
        font_search._search_warm_step()
        ticks += 1
        assert ticks < 1000
    font_search._cancel_search_cache_save()
    assert font_search._write_search_cache_now()


def main():
    module_name, mode = _args()
    assert module_name in bpy.context.preferences.addons
    package = importlib.import_module(module_name)
    font_loader = importlib.import_module(f"{module_name}.utils.font_loader")
    font_search = importlib.import_module(f"{module_name}.utils.font_search")

    if mode == "clear":
        font_search.clear_font_search_disk_cache()
    count = font_loader.refresh_font_catalog(
        bpy.context.window_manager,
        force=True,
    )
    assert count > 0
    assert font_search.font_search_warming()
    _drain(font_search)

    stats = font_search.font_search_cache_stats()
    cache_path = Path(str(stats["path"]))
    extension_root = Path(
        bpy.utils.extension_path_user(package.ADDON_PACKAGE)
    ).resolve()
    assert cache_path.is_file()
    assert extension_root in cache_path.resolve().parents
    assert int(stats["total"]) == count
    if mode == "clear":
        assert int(stats["built"]) == count
        assert int(stats["reused"]) == 0
        print("TEXTHELPER_INSTALLED_SEARCH_CACHE_BUILD_TEST=PASS")
    else:
        assert int(stats["reused"]) == count
        assert int(stats["built"]) == 0
        print("TEXTHELPER_INSTALLED_SEARCH_CACHE_REUSE_TEST=PASS")
    print(f"TEXTHELPER_INSTALLED_SEARCH_CACHE_FONTS={count}")
    print(f"TEXTHELPER_INSTALLED_SEARCH_CACHE_BYTES={cache_path.stat().st_size}")


if __name__ == "__main__":
    main()
