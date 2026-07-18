"""Regression tests for completely opting out of the optional HUD runtime."""

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


def _drain_runtime_ensure(runtime) -> None:
    callback = runtime._ensure_timer
    if callback is None:
        return
    if bpy.app.timers.is_registered(callback):
        bpy.app.timers.unregister(callback)
    callback()


def main():
    package = _load_package(_source_path_from_args())
    package.register()
    obj = None
    original_get_prefs = None
    original_ensure_all_windows = None
    try:
        from TextHelper import preferences, runtime, sync
        from TextHelper.ops import font_list, hud_modal
        from TextHelper.utils import addon_prefs

        data = bpy.data.curves.new("TH HUD Opt Out", "FONT")
        data.body = "Text Helper"
        obj = bpy.data.objects.new("TH HUD Opt Out", data)
        bpy.context.scene.collection.objects.link(obj)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        original_ensure_all_windows = runtime.ensure_all_windows
        runtime.ensure_all_windows = lambda _context=None: False
        assert sync.is_subscribers_active()
        runtime.ensure(bpy.context)
        assert runtime.is_draw_registered()

        previous_epoch = hud_modal._RUNTIME_EPOCH
        preferences._floating_toolbar_changed(
            SimpleNamespace(show_floating_toolbar=False),
            bpy.context,
        )
        assert not runtime.is_draw_registered()
        assert runtime._ensure_timer is None
        assert not sync.is_subscribers_active()
        assert hud_modal._RUNTIME_EPOCH == previous_epoch + 1
        for operator in hud_modal._iter_hud_modal_operators():
            assert getattr(operator, "_th_stop_requested", False)

        preferences._floating_toolbar_changed(
            SimpleNamespace(show_floating_toolbar=True),
            bpy.context,
        )
        _drain_runtime_ensure(runtime)
        assert sync.is_subscribers_active()
        assert runtime.is_draw_registered()

        runtime.disable(bpy.context)
        sync.unregister()
        original_get_prefs = addon_prefs.get_addon_prefs
        addon_prefs.get_addon_prefs = lambda _context: SimpleNamespace(
            show_floating_toolbar=False,
        )
        sync.register()
        assert not sync.is_subscribers_active()

        for cls in (
            font_list.TH_OT_refresh_system_fonts,
            font_list.TH_OT_regenerate_font_previews,
            font_list.TH_OT_rebuild_font_search_index,
        ):
            assert "REGISTER" not in getattr(cls, "bl_options", set())

        print("TEXTHELPER_HUD_RUNTIME_OPT_OUT_TEST=PASS")
        print("TEXTHELPER_HUD_RUNTIME_RESTART_TEST=PASS")
        print("TEXTHELPER_HUD_SUBSCRIBER_LAZY_TEST=PASS")
        print("TEXTHELPER_SIDE_EFFECT_REDO_TEST=PASS")
    finally:
        if original_get_prefs is not None:
            try:
                addon_prefs.get_addon_prefs = original_get_prefs
            except Exception:
                pass
        if original_ensure_all_windows is not None:
            try:
                runtime.ensure_all_windows = original_ensure_all_windows
            except Exception:
                pass
        try:
            package.unregister()
        except Exception:
            pass
        if obj is not None:
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if data.users == 0:
                bpy.data.curves.remove(data)


if __name__ == "__main__":
    main()
