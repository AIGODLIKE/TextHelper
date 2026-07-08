"""Compare _('...') usage in code against locale JSON tables."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
I18N = Path(__file__).resolve().parent

msgids: set[str] = set()
pattern = re.compile(r'_\(\s*(["\'])(.*?)\1\s*(?:\)|\.)', re.DOTALL)
for path in ROOT.rglob("*.py"):
    if "i18n" in path.parts:
        continue
    text = path.read_text(encoding="utf-8")
    for match in pattern.finditer(text):
        msgids.add(match.group(2))

for filename, value_key in (
    ("_catalog.json", "zh_HANS"),
    ("zh_Hant.json", "zh_Hant"),
    ("ja_JP.json", "ja_JP"),
):
    payload = json.loads((I18N / filename).read_text(encoding="utf-8"))
    keys = {item["msgid"] for item in payload}
    missing = sorted(msgids - keys)
    print(f"=== {filename} ({value_key}) ===")
    print(f"  entries: {len(payload)}  unique msgids: {len(keys)}  used in code: {len(msgids)}")
    print(f"  missing: {len(missing)}")
    for item in missing:
        print(f"    - {item!r}")
