"""Blender-hosted translation coverage tests for user-facing font status text."""

from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import re
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


def _catalog_msgids(source: Path) -> set[str]:
    payload = json.loads((source / "i18n" / "_catalog.json").read_text(encoding="utf-8-sig"))
    return {item["msgid"] for item in payload}


def _validate_catalogs(source: Path) -> None:
    definitions = (
        ("_catalog.json", "zh_HANS"),
        ("zh_Hant.json", "zh_Hant"),
        ("ja_JP.json", "ja_JP"),
    )
    key_sets = []
    for filename, value_key in definitions:
        payload = json.loads(
            (source / "i18n" / filename).read_text(encoding="utf-8-sig")
        )
        key_sets.append({(item["context"], item["msgid"]) for item in payload})
        for item in payload:
            translated = item.get(value_key, "")
            assert translated, f"{filename} has an empty translation for {item['msgid']}"
            source_fields = re.findall(r"\{[^{}]*\}", item["msgid"])
            translated_fields = re.findall(r"\{[^{}]*\}", translated)
            assert source_fields == translated_fields, (
                f"{filename} changed placeholders for {item['msgid']}"
            )
    assert all(keys == key_sets[0] for keys in key_sets), (
        "translation catalogs do not contain identical context/msgid keys"
    )


def _declared_ui_strings(source: Path) -> set[str]:
    result = set()

    def add_constant(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value:
            result.add(node.value)

    def add_enum_items(node):
        if not isinstance(node, (ast.Tuple, ast.List)):
            return
        for item in node.elts:
            if not isinstance(item, (ast.Tuple, ast.List)):
                continue
            for position in (1, 2):
                if position < len(item.elts):
                    add_constant(item.elts[position])

    for path in source.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if (
                    isinstance(node.func, ast.Name)
                    and node.func.id == "_"
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)
                ):
                    result.add(node.args[0].value)
                function_name = (
                    node.func.attr
                    if isinstance(node.func, ast.Attribute)
                    else node.func.id
                    if isinstance(node.func, ast.Name)
                    else ""
                )
                if (
                    function_name == "queue_operator_report"
                    and len(node.args) > 1
                ):
                    add_constant(node.args[1])
                for keyword in node.keywords:
                    if (
                        keyword.arg in {"name", "description", "text", "placeholder"}
                        and isinstance(keyword.value, ast.Constant)
                        and isinstance(keyword.value.value, str)
                    ):
                        result.add(keyword.value.value)
                    elif keyword.arg == "items":
                        add_enum_items(keyword.value)
            if isinstance(node, ast.ClassDef):
                for statement in node.body:
                    if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
                        continue
                    target = statement.targets[0]
                    if (
                        isinstance(target, ast.Name)
                        and target.id in {"bl_label", "bl_description"}
                    ):
                        if isinstance(statement.value, ast.Constant):
                            add_constant(statement.value)
                        elif isinstance(statement.value, (ast.Tuple, ast.List)):
                            parts = [
                                item.value.strip()
                                for item in statement.value.elts
                                if isinstance(item, ast.Constant)
                                and isinstance(item.value, str)
                                and item.value.strip()
                            ]
                            if parts:
                                result.add(" ".join(parts))
    return {value for value in result if value and value not in {"S"}}


def main():
    source = _source_path_from_args()
    package = _load_package(source)
    package.register()
    view = bpy.context.preferences.view
    original_language = view.language
    original_translate = view.use_translate_interface
    try:
        _validate_catalogs(source)
        msgids = _catalog_msgids(source)
        missing = _declared_ui_strings(source) - msgids
        assert not missing, f"missing UI translations: {sorted(missing)}"

        targeted = (
            ("*", "Loading fonts…"),
            ("*", "Click refresh to load system fonts"),
            ("*", "Indexing font names… {:d}/{:d}"),
            ("*", "Font preview cache cleared — rebuilding thumbnails"),
            ("*", "Font refresh complete — preview thumbnails are rebuilding"),
            ("Operator", "Font refresh complete — preview thumbnails are rebuilding"),
            ("Operator", "Font filters restored to defaults"),
            ("*", "Font search index: {:d} cached"),
            ("*", "Font search index cleared — rebuilding in background"),
            ("Operator", "Font search index cleared — rebuilding in background"),
            ("Operator", "Rebuild Font Search Index"),
        )
        view.use_translate_interface = True
        for locale in ("zh_HANS", "zh_HANT", "ja_JP"):
            view.language = locale
            for context, msgid in targeted:
                translated = bpy.app.translations.pgettext(msgid, context)
                assert translated and translated != msgid, (
                    f"{locale} did not translate {context}:{msgid}"
                )
                assert translated.count("{:d}") == msgid.count("{:d}")

        print("TEXTHELPER_I18N_STATIC_COVERAGE_TEST=PASS")
        print("TEXTHELPER_I18N_CATALOG_PARITY_TEST=PASS")
        print("TEXTHELPER_I18N_FONT_STATUS_TEST=PASS")
    finally:
        view.language = original_language
        view.use_translate_interface = original_translate
        package.unregister()


if __name__ == "__main__":
    main()
