"""Verify font-status translations from an installed Text Helper extension."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys

import bpy


def _module_name_from_args() -> str:
    separator = sys.argv.index("--")
    return sys.argv[separator + 1]


def main():
    module_name = _module_name_from_args()
    assert module_name in bpy.context.preferences.addons
    package = importlib.import_module(module_name)
    source = Path(package.__file__).resolve().parent

    catalogs = (
        ("_catalog.json", "zh_HANS"),
        ("zh_Hant.json", "zh_Hant"),
        ("ja_JP.json", "ja_JP"),
    )
    targeted = {
        ("*", "Loading fonts…"),
        ("*", "Indexing font names… {:d}/{:d}"),
        ("*", "Font refresh complete — preview thumbnails are rebuilding"),
        ("Operator", "Font refresh complete — preview thumbnails are rebuilding"),
        ("*", "Font search index: {:d} cached"),
        ("*", "Font search index cleared — rebuilding in background"),
        ("Operator", "Font search index cleared — rebuilding in background"),
        ("Operator", "Rebuild Font Search Index"),
    }
    for filename, value_key in catalogs:
        payload = json.loads(
            (source / "i18n" / filename).read_text(encoding="utf-8-sig")
        )
        table = {
            (item["context"], item["msgid"]): item[value_key]
            for item in payload
        }
        for key in targeted:
            assert table.get(key), f"{filename} is missing {key}"

    view = bpy.context.preferences.view
    original_language = view.language
    original_translate = view.use_translate_interface
    try:
        view.use_translate_interface = True
        for locale in ("zh_HANS", "zh_HANT", "ja_JP"):
            view.language = locale
            for context, msgid in targeted:
                translated = bpy.app.translations.pgettext(msgid, context)
                assert translated and translated != msgid
    finally:
        view.language = original_language
        view.use_translate_interface = original_translate

    print("TEXTHELPER_INSTALLED_I18N_FONT_STATUS_TEST=PASS")


if __name__ == "__main__":
    main()
