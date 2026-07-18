"""Cross-process checks for the installed extension's optional HUD runtime."""

from __future__ import annotations

import importlib
import sys

import bpy


def _args() -> tuple[str, str]:
    try:
        separator = sys.argv.index("--")
        return sys.argv[separator + 1], sys.argv[separator + 2]
    except (ValueError, IndexError):
        raise SystemExit(
            "Usage: blender --python test_texthelper_installed_hud_opt_out.py "
            "-- <module-name> <disable|startup>"
        )


def _disable_and_save(module_name: str) -> None:
    package = importlib.import_module(module_name)
    runtime = importlib.import_module(f"{module_name}.runtime")
    sync = importlib.import_module(f"{module_name}.sync")
    hud_modal = importlib.import_module(f"{module_name}.ops.hud_modal")
    prefs = bpy.context.preferences.addons[module_name].preferences

    data = bpy.data.curves.new("TH Installed HUD Opt Out", "FONT")
    data.body = "Text Helper"
    obj = bpy.data.objects.new("TH Installed HUD Opt Out", data)
    bpy.context.scene.collection.objects.link(obj)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    original_ensure_all_windows = runtime.ensure_all_windows
    runtime.ensure_all_windows = lambda _context=None: False
    try:
        prefs.show_floating_toolbar = True
        assert runtime.ensure(bpy.context) is False
        assert runtime.is_draw_registered()
        assert sync.is_subscribers_active()

        previous_epoch = hud_modal._RUNTIME_EPOCH
        prefs.show_floating_toolbar = False
        assert not runtime.is_draw_registered()
        assert runtime._ensure_timer is None
        assert not sync.is_subscribers_active()
        assert hud_modal._RUNTIME_EPOCH == previous_epoch + 1

        bpy.ops.wm.save_userpref()
        print("TEXTHELPER_INSTALLED_HUD_DISABLE_TEST=PASS")
        print("TEXTHELPER_INSTALLED_HUD_PREF_SAVE_TEST=PASS")
    finally:
        runtime.ensure_all_windows = original_ensure_all_windows
        bpy.data.objects.remove(obj, do_unlink=True)
        if data.users == 0:
            bpy.data.curves.remove(data)


def _verify_disabled_startup(module_name: str) -> None:
    importlib.import_module(module_name)
    runtime = importlib.import_module(f"{module_name}.runtime")
    sync = importlib.import_module(f"{module_name}.sync")
    prefs = bpy.context.preferences.addons[module_name].preferences

    assert prefs.show_floating_toolbar is False
    assert not runtime.is_draw_registered()
    assert runtime._ensure_timer is None
    assert not sync.is_subscribers_active()

    print("TEXTHELPER_INSTALLED_HUD_DISABLED_STARTUP_TEST=PASS")
    print("TEXTHELPER_INSTALLED_HUD_SUBSCRIBER_LAZY_TEST=PASS")


def main() -> None:
    module_name, mode = _args()
    assert module_name in bpy.context.preferences.addons
    if mode == "disable":
        _disable_and_save(module_name)
    elif mode == "startup":
        _verify_disabled_startup(module_name)
    else:
        raise SystemExit(f"Unknown mode: {mode}")


if __name__ == "__main__":
    main()
