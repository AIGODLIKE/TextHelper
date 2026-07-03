"""Generate zh_Hant.json from _catalog.json (OpenCC s2twp + TW Blender phrasing). Dev-only; not shipped."""
import json
from pathlib import Path

import opencc

I18N = Path(__file__).resolve().parent
catalog = json.loads((I18N / "_catalog.json").read_text(encoding="utf-8"))
converter = opencc.OpenCC("s2twp")

# Match Blender official zh_Hant UI (e.g. Viewport -> 視圖區).
_PHRASE_OVERRIDES = (
    ("3D 视口", "3D 視圖區"),
    ("3D 視口", "3D 視圖區"),
    ("视口", "視圖區"),
    ("視口", "視圖區"),
    ("侧边栏", "側邊欄"),
    ("侧栏", "側邊欄"),
    ("文本框", "文字方塊"),
    ("缩略图", "縮圖"),
    ("缩略图", "縮圖"),
    ("像素", "像素"),
    ("软件", "軟體"),
    ("链接", "連結"),
    ("鼠标", "滑鼠"),
    ("默认", "預設"),
    ("磁盘", "磁碟"),
    ("文件", "檔案"),
    ("文件夹", "資料夾"),
)

# Longer phrases first when applying replacements.
_PHRASE_OVERRIDES = tuple(sorted(_PHRASE_OVERRIDES, key=lambda pair: len(pair[0]), reverse=True))


def _to_hant(zh_hans: str) -> str:
    if not zh_hans:
        return ""
    text = converter.convert(zh_hans)
    for src, dst in _PHRASE_OVERRIDES:
        text = text.replace(src, dst)
    return text


payload = []
for item in catalog:
    zh_hans = item.get("zh_HANS", "")
    payload.append(
        {
            "context": item["context"],
            "msgid": item["msgid"],
            "zh_Hant": _to_hant(zh_hans),
        }
    )

(I18N / "zh_Hant.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(f"Wrote {len(payload)} entries to zh_Hant.json")
