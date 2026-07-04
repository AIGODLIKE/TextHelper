"""Full i18n parity audit across locale JSON files."""
import json
import sys
from pathlib import Path

I18N = Path(__file__).resolve().parent
LOCALES = (
    ("zh_HANS", "_catalog.json", "zh_HANS"),
    ("zh_Hant", "zh_Hant.json", "zh_Hant"),
    ("ja_JP", "ja_JP.json", "ja_JP"),
)


def load_tables():
    tables = {}
    for loc, filename, value_key in LOCALES:
        payload = json.loads((I18N / filename).read_text(encoding="utf-8"))
        table = {}
        dupes = []
        for item in payload:
            key = (item["context"], item["msgid"])
            if key in table:
                dupes.append(key)
            table[key] = item.get(value_key, "")
        tables[loc] = {"table": table, "dupes": dupes, "count": len(payload)}
    return tables


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    tables = load_tables()
    base_keys = set(tables["zh_HANS"]["table"])

    print("=== locale file stats ===")
    for loc, _, _ in LOCALES:
        info = tables[loc]
        print(f"  {loc}: entries={info['count']} keys={len(info['table'])} dupes={len(info['dupes'])}")

    for loc, _, value_key in LOCALES[1:]:
        keys = set(tables[loc]["table"])
        missing = sorted(base_keys - keys)
        extra = sorted(keys - base_keys)
        print(f"\n=== {loc} key parity vs zh_HANS ===")
        print(f"  missing: {len(missing)}  extra: {len(extra)}")
        for key in missing:
            print(f"    - [{key[0]}] {key[1]!r}")
        for key in extra[:5]:
            print(f"    + extra [{key[0]}] {key[1]!r}")

    print("\n=== empty or identical-to-English translations ===")
    for loc, _, value_key in LOCALES:
        same = []
        empty = []
        for key, item in tables[loc]["table"].items():
            msgid = key[1]
            val = item if isinstance(item, str) else ""
            if not val.strip():
                empty.append(msgid)
            elif val == msgid and len(msgid) > 3 and not msgid.isupper():
                same.append(msgid)
        print(f"  {loc}: empty={len(empty)} untranslated(same as EN)={len(same)}")
        for msg in empty[:10]:
            print(f"    empty: {msg!r}")
        for msg in sorted(same)[:15]:
            print(f"    same: {msg!r}")
        if len(same) > 15:
            print(f"    ... and {len(same)-15} more same-as-English")

    # zh_Hant vs zh_HANS identical (possible missed conversion)
    hans = tables["zh_HANS"]["table"]
    hant = tables["zh_Hant"]["table"]
    identical = []
    for key in base_keys:
        if key not in hant:
            continue
        hv = hant[key]
        sv = hans[key]
        if hv and sv and hv == sv and any("\u4e00" <= c <= "\u9fff" for c in sv):
            identical.append((key, sv))
    print(f"\n=== zh_Hant identical to zh_HANS (possible simplified leftovers) ===")
    print(f"  count: {len(identical)}")
    for key, val in identical[:20]:
        print(f"    [{key[0]}] {key[1]!r} -> {val!r}")
    if len(identical) > 20:
        print(f"    ... and {len(identical)-20} more")

    import re

    ROOT = I18N.parent
    catalog_keys = set(tables["zh_HANS"]["table"].keys())
    op_strings = set()
    op_pat = re.compile(r'bl_(?:label|description)\s*=\s*(?:\(\s*)?"([^"]+)"')
    for path in ROOT.rglob("*.py"):
        if "i18n" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for match in op_pat.finditer(text):
            value = match.group(1).strip()
            if value and len(value) > 1:
                op_strings.add(value)

    def in_catalog(msgid):
        return ("Operator", msgid) in catalog_keys or ("*", msgid) in catalog_keys

    op_missing = sorted(s for s in op_strings if not in_catalog(s))
    print(f"\n=== operator bl_label / bl_description missing from catalog ===")
    print(f"  count: {len(op_missing)}")
    for msg in op_missing:
        print(f"    - {msg!r}")

    layout_text = (ROOT / "hud" / "layout.py").read_text(encoding="utf-8")
    tip_keys = set(re.findall(r'(?:tip_key|title_key)="([^"]+)"', layout_text))
    tip_missing = sorted(s for s in tip_keys if not in_catalog(s))
    print(f"\n=== HUD tip/title keys missing from catalog ===")
    print(f"  count: {len(tip_missing)}")
    for msg in tip_missing:
        print(f"    - {msg!r}")

    poll_raw = set()
    poll_wrapped = set()
    poll_pat_raw = re.compile(r'poll_message_set\("([^"]+)"')
    poll_pat_wrap = re.compile(r'poll_message_set\(_\("([^"]+)"')
    for path in ROOT.rglob("*.py"):
        if "i18n" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        poll_raw.update(poll_pat_raw.findall(text))
        poll_wrapped.update(poll_pat_wrap.findall(text))
    print(f"\n=== poll_message_set (hardcoded English, not _()) ===")
    for msg in sorted(poll_raw):
        print(f"    - {msg!r}  in_catalog={in_catalog(msg)}")
    print(f"  wrapped with _(): {sorted(poll_wrapped)}")


if __name__ == "__main__":
    main()
