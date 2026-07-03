"""Addon UI translations (English source + zh_HANS + ja_JP)."""

import json
from pathlib import Path

import bpy
from bpy.app.translations import pgettext_iface as _


_I18N_DIR = Path(__file__).resolve().parent


def _table_from_json(filename: str, value_key: str) -> dict:
    payload = json.loads((_I18N_DIR / filename).read_text(encoding="utf-8"))
    table: dict[tuple[str, str], str] = {}
    for item in payload:
        table[(item["context"], item["msgid"])] = item[value_key]
    return table


_OWNER = None


_TRANSLATIONS = {
    "zh_HANS": _table_from_json("_catalog.json", "zh_HANS"),
    "ja_JP": _table_from_json("ja_JP.json", "ja_JP"),
}


def register(owner=None):
    global _OWNER
    _OWNER = owner if owner is not None else __name__.rsplit(".", 1)[0]
    bpy.app.translations.register(_OWNER, _TRANSLATIONS)


def unregister():
    global _OWNER
    if _OWNER:
        bpy.app.translations.unregister(_OWNER)
        _OWNER = None


__all__ = ("_", "register", "unregister")
