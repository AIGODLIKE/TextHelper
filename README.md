# Please use Blender 5.2 or newer

# Text Helper

A Blender add-on that lets you edit 3D text as naturally as drinking water.
Everything you want — **multi-line text input**, **live font preview**, **invalid font exclusion**, **font family weight selection**, **one-click horizontal/vertical layout**, and an **ultra-comfortable UI** — is here!

<img width="2560" height="1380" alt="image" src="https://github.com/user-attachments/assets/b7cd58c7-2943-4c40-840e-67e30e1009b1" />

---

## Highlights

### Multi-line text

https://github.com/user-attachments/assets/b7d06527-94dc-4f77-ae7a-d5b3cc7e12ba

<img width="1920" height="1034" alt="Multi-line textinput" src="https://github.com/user-attachments/assets/78887700-2bcb-40a7-a76e-1fc7cc98ee75" />

- Multi-line text input (requires Blender 5.2+)
- New line = Shift+Enter | Confirm = Enter

### Fonts

https://github.com/user-attachments/assets/adf5a290-0b00-45e4-88f3-e48734f28172

<img width="1920" height="1034" alt="FontSelector" src="https://github.com/user-attachments/assets/435197f9-1233-4d37-a79d-b1412a803869" />

- **Live preview**: Preview font and weight in real time; use the current input as preview text (or the font name / a custom string)
- **Live apply**: Change font and weight on hover
- **Invalid font exclusion**: Automatically match fonts that support your input (tip: when text turns into “□”, open the font library to fix — works great!)
- **Weight merging**: Merge weights within the same font family
- **Filters**: Filter by language, support status, or multi-weight families
- **Search**: Search fonts (English input only for now; paste other languages to search)
- **Cross-platform**: Scan **system fonts** (Windows / macOS / Linux)

### Horizontal & vertical layout

https://github.com/user-attachments/assets/c6e7aafe-1c71-4a4c-872e-7ea1068af498

<img width="1920" height="1034" alt="Horizontal  vertical text modes" src="https://github.com/user-attachments/assets/87920b34-dda8-4bbe-b8af-ce882137bcb4" />


- **Horizontal** / **Vertical**: One-click switch; vertical mode supports left-to-right and right-to-left column order

- **Fullwidth fix (alignment fix)**: Detect halfwidth characters and convert to fullwidth to fix alignment (note: some fonts with special glyphs may look odd)

https://github.com/user-attachments/assets/b02935a9-20d5-4253-bfa8-67867faa306c

<img width="1920" height="1034" alt="FixFont" src="https://github.com/user-attachments/assets/cc8c8ab1-de71-4907-a78f-6d6798205a0b" />


### Floating viewport toolbar (HUD)

https://github.com/user-attachments/assets/df5342b7-7d49-47f3-ab6a-f1b6f32632e4

<img width="1920" height="1034" alt="TextEdit" src="https://github.com/user-attachments/assets/32b73339-c424-47e8-a28f-6f0b3badc31a" />


- Draggable; appears near the selected text
- Style presets, **GPU font picker**, bold / italic / underline / strikethrough
- Case toggles, alignment, spacing sliders (size, character, word, line height, shear, etc.)
- Double-click empty space to enter / exit text edit mode

### Other

- Simplified Chinese UI (auto-detected from Blender locale)
- Traditional Chinese UI (`zh_Hant`)
- Japanese UI (`ja_JP`)
- Customizable HUD accent color and scale

---

## Installation

### Extension platform (recommended)

1. Download `TextHelper-X.X.X.zip` from [Releases](https://github.com/AIGODLIKE/TextHelper/releases), or build locally (see below).
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

Output: `TextHelper-1.9.6.zip`

A helper script `_build_texthelper_zip.py` is also available in the parent `DATA` folder for quick local copies; use the Blender CLI output for Extension Store submissions.

---

## Known limitations

- For performance, font glyph matching samples only the first line of characters. If unknown characters appear, place them on the first line first to help font matching.
- Vertical text: fullwidth fix does not work for fonts that lack fullwidth glyphs.
- Vertical text: fullwidth fix may look poor on special symbols in some non-standard fonts.


## Recent changes (1.8.x / 1.9.x)

- **1.9.6** — Refresh icon tooltip on hover; status message "Font information refreshed" after click
- **1.9.5** — Viewport font picker refresh control is a compact icon button (slot 3) with hover and press feedback
- **1.9.4** — Visible **Force Refresh Previews** button in viewport font picker, font menu, and add-on preferences
- **1.9.3** — Fix font previews stopping after manual font file replacement; refresh button now clears load-failure caches and rebuilds thumbnails
- **1.9.2** — New text objects default text box size and offsets to zero
- **1.9.1** — Extension store compliance: maintainer email, remove legacy bl_info, safer preview cache init, lazy msgbus/load_post subscribers
- **1.9.0** — Fix deferred font catalog load crash (`UnboundLocalError` on macOS)
- **1.8.6** — README rewrite with feature highlights and demo videos
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
- Multi-line sidebar textbox requires Blender **5.2+**

---

## Links

- [Issues & feedback](https://github.com/AIGODLIKE/TextHelper/issues)
- [中文说明](README.zh-CN.md)

---

## License

This add-on is free software licensed under the **GNU General Public License v3.0 or later**. See [LICENSE](LICENSE).
