"""Addon UI translations (English source + zh_HANS + zh_Hant + ja_JP)."""

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
_REGISTERED_OWNERS: list[str] = []


def _translation_owners(primary: str) -> list[str]:
    owners: list[str] = []
    for candidate in (primary, primary.rsplit(".", 1)[-1]):
        if candidate and candidate not in owners:
            owners.append(candidate)
    return owners


def _hant_table() -> dict:
    return _table_from_json("zh_Hant.json", "zh_Hant")


_TRANSLATIONS = {
    "zh_HANS": _table_from_json("_catalog.json", "zh_HANS"),
    "zh_CN": _table_from_json("_catalog.json", "zh_HANS"),
    "zh_Hant": _hant_table(),
    "zh_HANT": _hant_table(),
    "ja_JP": _table_from_json("ja_JP.json", "ja_JP"),
}


def register(owner=None):
    global _OWNER, _REGISTERED_OWNERS
    _OWNER = owner if owner is not None else __name__.rsplit(".", 1)[0]
    _REGISTERED_OWNERS = []
    for mod in _translation_owners(_OWNER):
        bpy.app.translations.register(mod, _TRANSLATIONS)
        _REGISTERED_OWNERS.append(mod)


def unregister():
    global _OWNER, _REGISTERED_OWNERS
    for mod in reversed(_REGISTERED_OWNERS):
        try:
            bpy.app.translations.unregister(mod)
        except Exception:
            pass
    _REGISTERED_OWNERS = []
    _OWNER = None


__all__ = ("_", "register", "unregister")
