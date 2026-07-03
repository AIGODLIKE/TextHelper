# Text Helper

**Version 1.7.1** · Blender **5.2+** · [GPL-3.0-or-later](LICENSE)

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
- Search, sort, script/language filter, thumbnail previews
- Browse custom `.ttf` / `.otf` files; optional live preview on hover

### Other

- Simplified Chinese UI (auto-detected from Blender locale)
- Customizable HUD accent color and scale

---

## Installation

### Blender Extensions (recommended)

1. Download `TextHelper-1.7.1.zip` from [Releases](https://github.com/AIGODLIKE/TextHelper/releases) (when published), or build locally (see below).
2. In Blender: **Edit → Preferences → Get Extensions → Install from Disk…**
3. Select the zip and enable **Text Helper**.

### Manual / development

1. Clone this repository into your extensions folder, e.g.  
   `%APPDATA%\Blender Foundation\Blender\5.2\extensions\user_default\TextHelper`
2. Restart Blender or refresh extensions.

### Build zip locally

From the parent folder that contains `_build_texthelper_zip.py`:

```bash
python _build_texthelper_zip.py
```

Output: `TextHelper-1.7.1.zip`

---

## Permissions

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
