"""Find RNA/UI English strings missing from _catalog.json."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
I18N = Path(__file__).resolve().parent
catalog = json.loads((I18N / "_catalog.json").read_text(encoding="utf-8"))
keys = {item["msgid"] for item in catalog}
pat = re.compile(r'(?:name|description|bl_label|bl_description)\s*=\s*["\']([^"\']+)["\']')
enum_pat = re.compile(r'\("[^"]+",\s*"([^"]+)",\s*"([^"]+)"\)')
found = set()
for path in ROOT.rglob("*.py"):
    if "i18n" in path.parts or "__pycache__" in path.parts:
        continue
    text = path.read_text(encoding="utf-8")
    found.update(m.group(1) for m in pat.finditer(text))
    for m in enum_pat.finditer(text):
        found.add(m.group(1))
        found.add(m.group(2))
not_in = sorted(s for s in found if s and s not in keys)
print(f"missing from catalog: {len(not_in)}")
for s in not_in:
    print(f"  {s!r}")
