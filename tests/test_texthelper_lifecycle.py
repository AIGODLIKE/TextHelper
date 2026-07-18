"""Isolated installed-extension lifecycle smoke test for Text Helper."""

from __future__ import annotations

import addon_utils
import bpy
import sys


def _module_name_from_args() -> str:
    try:
        separator = sys.argv.index("--")
        return sys.argv[separator + 1]
    except (ValueError, IndexError):
        raise SystemExit("Usage: blender --python test_texthelper_lifecycle.py -- <module-name>")


def _loaded(module_name: str) -> bool:
    return bool(addon_utils.check(module_name)[1])


def main():
    module_name = _module_name_from_args()

    assert module_name in bpy.context.preferences.addons, f"{module_name} is not enabled in preferences"
    assert _loaded(module_name), f"{module_name} did not load at startup"
    assert hasattr(bpy.types.TextCurve, "text_helper")
    assert hasattr(bpy.types.WindowManager, "th_state")

    addon_utils.disable(module_name, default_set=False)
    assert not _loaded(module_name), f"{module_name} did not unregister"
    assert not hasattr(bpy.types.TextCurve, "text_helper")
    assert not hasattr(bpy.types.WindowManager, "th_state")

    module = addon_utils.enable(module_name, default_set=False, persistent=False)
    assert module is not None, f"{module_name} could not be enabled again"
    assert _loaded(module_name), f"{module_name} did not reload"
    assert hasattr(bpy.types.TextCurve, "text_helper")
    assert hasattr(bpy.types.WindowManager, "th_state")

    addon_utils.disable(module_name, default_set=False)
    assert not _loaded(module_name), f"{module_name} failed final unregister"
    assert not hasattr(bpy.types.TextCurve, "text_helper")
    assert not hasattr(bpy.types.WindowManager, "th_state")

    print("TEXTHELPER_INSTALL_ENABLE_TEST=PASS")
    print("TEXTHELPER_UNREGISTER_TEST=PASS")


if __name__ == "__main__":
    main()
