"""Blender-hosted regression tests for reversible picker hover previews."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import bpy


def _source_path_from_args() -> Path:
    try:
        separator = sys.argv.index("--")
        source = sys.argv[separator + 1]
    except (ValueError, IndexError):
        raise SystemExit("Usage: blender --python test_texthelper_picker_preview.py -- <source-dir>")
    return Path(source).resolve()


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


def _make_text(name, body):
    data = bpy.data.curves.new(name, "FONT")
    data.body = body
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.select_set(True)
    return obj


def main():
    package = _load_package(_source_path_from_args())
    package.register()
    objects = []
    try:
        bpy.ops.object.select_all(action="DESELECT")
        objects = [_make_text("TH Preview A", "Alpha"), _make_text("TH Preview B", "Beta")]
        bpy.context.view_layer.objects.active = objects[0]

        from TextHelper.utils.picker_preview import (
            begin_preview,
            cancel_preview,
            prepare_preview_commit,
            preview_font,
            preview_preset,
        )

        originals = [
            (
                obj.data.size,
                obj.data.space_character,
                obj.data.space_word,
                obj.data.space_line,
                obj.data.shear,
                obj.data.text_helper.th_preset,
            )
            for obj in objects
        ]

        assert begin_preview(bpy.context, "TEST_PRESET")
        assert preview_preset(bpy.context, "TEST_PRESET", "HEADING")
        assert all(obj.data.text_helper.th_preset == "HEADING" for obj in objects)
        assert cancel_preview(bpy.context, "TEST_PRESET")
        restored = [
            (
                obj.data.size,
                obj.data.space_character,
                obj.data.space_word,
                obj.data.space_line,
                obj.data.shear,
                obj.data.text_helper.th_preset,
            )
            for obj in objects
        ]
        assert restored == originals, (originals, restored)

        assert begin_preview(bpy.context, "TEST_COMMIT")
        assert preview_preset(bpy.context, "TEST_COMMIT", "CAPTION")
        assert prepare_preview_commit(bpy.context, "TEST_COMMIT")
        assert [obj.data.text_helper.th_preset for obj in objects] == [
            original[-1] for original in originals
        ]

        from TextHelper.utils.font_loader import iter_system_fonts

        fonts = iter_system_fonts()
        if fonts:
            original_fonts = [
                (
                    obj.data.font,
                    obj.data.font_bold,
                    obj.data.font_italic,
                    obj.data.font_bold_italic,
                    obj.data.size,
                )
                for obj in objects
            ]
            assert begin_preview(bpy.context, "TEST_FONT")
            assert preview_font(bpy.context, "TEST_FONT", fonts[0]["filepath"], 0)
            assert cancel_preview(bpy.context, "TEST_FONT")
            restored_fonts = [
                (
                    obj.data.font,
                    obj.data.font_bold,
                    obj.data.font_italic,
                    obj.data.font_bold_italic,
                    obj.data.size,
                )
                for obj in objects
            ]
            assert restored_fonts == original_fonts

        print("TEXTHELPER_PICKER_PREVIEW_CANCEL_TEST=PASS")
        print("TEXTHELPER_PICKER_PREVIEW_COMMIT_BASELINE_TEST=PASS")
    finally:
        package.unregister()
        for obj in objects:
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if data.users == 0:
                bpy.data.curves.remove(data)


if __name__ == "__main__":
    main()
