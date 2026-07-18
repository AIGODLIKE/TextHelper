"""Blender-hosted tests for the persistent, incremental font search cache."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
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


def _drain_warm(font_search, catalog) -> None:
    font_search.queue_font_search_warm(catalog)
    assert font_search.font_search_warming()
    if bpy.app.timers.is_registered(font_search._search_warm_step):
        bpy.app.timers.unregister(font_search._search_warm_step)
    ticks = 0
    while font_search.font_search_warming():
        font_search._search_warm_step()
        ticks += 1
        assert ticks < 1000
    font_search._cancel_search_cache_save()


def main():
    package = _load_package(_source_path_from_args())
    package.register()
    try:
        from TextHelper.utils import font_search

        with TemporaryDirectory(prefix="texthelper-search-cache-") as temp_dir:
            root = Path(temp_dir)
            alpha_path = root / "Alpha-Regular.ttf"
            bravo_path = root / "Bravo-Regular.ttf"
            alpha_path.write_bytes(b"not-a-font-alpha")
            bravo_path.write_bytes(b"not-a-font-bravo")
            catalog = (
                SimpleNamespace(display_name="Alpha", filepath=str(alpha_path)),
                SimpleNamespace(display_name="Bravo", filepath=str(bravo_path)),
            )

            font_search._CACHE_ROOT_OVERRIDE = root / "cache"
            font_search.invalidate_font_search_cache(clear_disk=True)
            _drain_warm(font_search, catalog)
            first_stats = font_search.font_search_cache_stats()
            assert first_stats["built"] == 2
            assert first_stats["reused"] == 0
            assert font_search._write_search_cache_now()

            cache_path = font_search._search_cache_path()
            assert cache_path is not None and cache_path.is_file()
            assert not cache_path.with_suffix(cache_path.suffix + ".tmp").exists()

            font_search.invalidate_font_search_cache(clear_disk=False)
            _drain_warm(font_search, catalog)
            reused_stats = font_search.font_search_cache_stats()
            assert reused_stats["reused"] == 2
            assert reused_stats["built"] == 0

            bravo_path.write_bytes(b"not-a-font-bravo-changed")
            font_search.invalidate_font_search_cache(clear_disk=False)
            _drain_warm(font_search, catalog)
            changed_stats = font_search.font_search_cache_stats()
            assert changed_stats["reused"] == 1
            assert changed_stats["built"] == 1
            assert len(font_search._SEARCH_CACHE) == 2
            assert font_search._write_search_cache_now()

            cache_path.write_text("{corrupt", encoding="utf-8")
            font_search.invalidate_font_search_cache(clear_disk=False)
            _drain_warm(font_search, catalog)
            corrupt_stats = font_search.font_search_cache_stats()
            assert corrupt_stats["built"] == 2
            assert corrupt_stats["reused"] == 0
            assert font_search._write_search_cache_now()
            assert not cache_path.with_suffix(cache_path.suffix + ".tmp").exists()

            print("TEXTHELPER_SEARCH_CACHE_PERSIST_TEST=PASS")
            print("TEXTHELPER_SEARCH_CACHE_REUSE_TEST=PASS")
            print("TEXTHELPER_SEARCH_CACHE_INCREMENTAL_TEST=PASS")
            print("TEXTHELPER_SEARCH_CACHE_CORRUPT_FALLBACK_TEST=PASS")
            print("TEXTHELPER_SEARCH_CACHE_ATOMIC_WRITE_TEST=PASS")
    finally:
        try:
            font_search.invalidate_font_search_cache(clear_disk=True)
            font_search._CACHE_ROOT_OVERRIDE = None
        except Exception:
            pass
        package.unregister()


if __name__ == "__main__":
    main()
