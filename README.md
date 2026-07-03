# Text Helper

**Version 1.8.5** · Blender **5.2+** · [GPL-3.0-or-later](LICENSE)

Text Helper makes working with Blender text objects faster: multi-line editing in the sidebar, a floating viewport toolbar, system font browsing with live previews, and vertical (column) text workflows.

Maintainer: **ACGGIT**

---

## Features

### Sidebar (N-panel)

- Multi-line **textbox** (Blender 5.2+) with configurable visible line count
- Horizontal / **vertical** text modes with column order (RTL / LTR)
- Paste and clear actions (clipboard permission)
- Halfwidth-character warnings and one-click fullwidth fix for vertical text

### Floating viewport toolbar (HUD)

- Draggable toolbar below the selected text object
- Style presets, **GPU font picker**, bold / italic / underline / strikethrough
- Case toggles, alignment, spacing sliders (size, character, word, line height, shear)
- Double-click empty space to enter / exit text edit mode

### Fonts

- Scan **system fonts** on Windows, macOS, and Linux
- Search, sort, script/language filter, **font weight picker**, thumbnail previews
- Browse custom `.ttf` / `.otf` files; optional live preview on hover

### Other

- Simplified Chinese UI (auto-detected from Blender locale)
- Traditional Chinese UI (`zh_Hant`)
- Japanese UI (`ja_JP`)
- Customizable HUD accent color and scale

---

## Installation

### Blender Extensions (recommended)

1. Download `TextHelper-1.8.5.zip` from [Releases](https://github.com/AIGODLIKE/TextHelper/releases) (when published), or build locally (see below).
2. In Blender: **Edit → Preferences → Get Extensions → Install from Disk…**
3. Select the zip and enable **Text Helper**.

### Manual / development

1. Clone this repository into your extensions folder, e.g.  
   `%APPDATA%\Blender Foundation\Blender\5.2\extensions\user_default\TextHelper`
2. Restart Blender or refresh extensions.

### Build zip locally (official)

From the `TextHelper` add-on directory:

```bash
blender --command extension validate
blender --command extension build
```

Output: `TextHelper-1.8.5.zip`

A helper script `_build_texthelper_zip.py` is also available in the parent `DATA` folder for quick local copies; use the Blender CLI output for Extension Store submissions.

---

## Recent changes (1.8.x)

- **1.8.5** — Default font preview sample text updated
- **1.8.4** — Traditional Chinese (`zh_Hant`) UI; Blender TW phrasing (e.g. 視圖區)
- **1.8.2** — Operator poll / i18n compliance fixes
- **1.8.0** — JSON-based i18n (zh_Hans, ja_JP), font weight picker, N-panel layout polish

---

Declared in `blender_manifest.toml`:

| Permission | Use |
|------------|-----|
| **files** | Load fonts from disk; cache preview thumbnails |
| **clipboard** | Paste text into the active text object |

No network access.

---

## Usage

1. Add or select a **Font** object.
2. Open the **Text Helper** tab in the 3D View sidebar.
3. Type or paste text; toggle the floating toolbar from the panel header (overlay icon).
4. Use **Font** on the HUD to open the viewport font picker, or adjust formatting from the toolbar.

Preferences: **Edit → Preferences → Add-ons → Text Helper**.

---

## Requirements

- Blender **5.2.0** or newer
- Multi-line sidebar textbox requires Blender **5.2+** (`UILayout.textbox`)

---

## Links

- [Issues & feedback](https://github.com/AIGODLIKE/TextHelper/issues)
- [中文说明](README.zh-CN.md)

---

## License

This add-on is free software licensed under the **GNU General Public License v3.0 or later**. See [LICENSE](LICENSE).
