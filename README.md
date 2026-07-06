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
- **Search**: Search by display name, filename, PostScript name, CJK family names; pinyin and kana helpers for Chinese/Japanese
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

Output: `TextHelper-2.0.0.zip`

A helper script `_build_texthelper_zip.py` is also available in the parent `DATA` folder for quick local copies; use the Blender CLI output for Extension Store submissions.

---

## Known limitations

- For performance, font glyph matching deduplicates characters and caps unique coverage checks at 2048 codepoints.
- Vertical text: fullwidth fix does not work for fonts that lack fullwidth glyphs.
- Vertical text: fullwidth fix may look poor on special symbols in some non-standard fonts.


## Recent changes

### 2.0.0

- **Multi-line character limit**: default 20,000 characters; configurable in add-on preferences (256–50,000; Blender hard cap 50,000). Sidebar shows `current / limit` while editing.
- **Extension compliance**: undo/redo handlers register lazily on first use; text limits enforced consistently in horizontal and vertical modes; official `blender --command extension build` packaging.
- **Add Text**: creates FONT curves via low-level API instead of wrapping `bpy.ops.object.text_add`.
- **Manifest**: extension tag set to `User Interface`.
- Cumulative improvements since **1.9.17** (header toolbar, font search/favorites/filters, HUD inline slider editing, multi-select batch editing, theme-aware HUD, ja/zh_Hant i18n, and fixes through 1.9.99) — see 1.9.x entries below.

### 1.9.x (1.8.x–1.9.x history)

- **1.9.86** — Weight grouping: PostScript prefix (GenYoGothic2) merges CJK/English name-table splits; abbrev suffixes (B, EL, …)
- **1.9.85** — Font prefs: Weight Grouping (OpenType family vs file name) for multi-weight merge
- **1.9.84** — Font picker: chunked async glyph filter when hiding unsupported fonts (fast list first, refine per frame)
- **1.9.83** — Font picker open perf: async catalog prefetch, filter cache, family-level glyph checks
- **1.9.82** — Fix operator hover tooltips not translating (description hook + i18n registration)
- **1.9.81** — HUD/Header ja: shorten slider labels (Font Size → 字級, Line Height → 行高, etc.)
- **1.9.80** — Header strikethrough position: popover next to S when enabled (not at slider row end)
- **1.9.79** — Bfont: remove bundled preview workaround; show「内置字体暂不支持」instead of thumbnail/glyph audit
- **1.9.78** — Bfont: skip false missing-glyph warnings; preview CJK via UI font stack
- **1.9.77** — Bfont preview: recognize Blender 5.2 `Bfont Regular` datablock name
- **1.9.76** — Bfont preview via bundled `bfont.ttf`; fix blend-font preview queue for `blend://` paths
- **1.9.75** — Header sliders read/write the same values as HUD (no RNA max clamp)
- **1.9.74** — Reload-safe BLF in HUD text fields; safer shutdown when Blender is quitting
- **1.9.73** — Fix HUD slider `blf` crash; Bfont/blend-embedded font previews; safer add-on shutdown
- **1.9.72** — HUD numeric fields and font search support drag-select, select-all (Ctrl+A), cut/copy/paste, and arrow-key navigation
- **1.9.71** — Font picker includes blend-embedded fonts (e.g. Bfont); searchable and applicable without a disk path
- **1.9.70** — Font search: suffix match (`font` finds `Bfont`); family+weight in index; multi-weight filter ignored while searching
- **1.9.69** — Font search supports prefix typeahead (`sourc` matches `source`; avoids mid-word hits like `sour` in `resource`)
- **1.9.68** — Font search excludes copyright/license name-table strings (fixes `source` matching Arial/Calibri via “open source”)
- **1.9.67** — Tighten font search aliases: no Noto↔思源 cross-match, no generic 黑体/宋体 groups, word-boundary for short English queries
- **1.9.66** — Font search: cross-language aliases (e.g. 思源 ↔ source/siyuan), index all display-name modes
- **1.9.65** — Fix add-on load error in N-panel text clamp (`global _module_sync_guard` syntax)
- **1.9.64** — Font name display preference applies to HUD/header current font; default is Family Name; N-panel text capped at 50,000 chars (Blender limit)
- **1.9.63** — Fix HUD spacing slider value field crash (`NameError: blf is not defined`)
- **1.9.62** — Fix OpenType name table parsing so CJK family names (e.g. 思源黑体) display in Family Name mode
- **1.9.61** — HUD spacing sliders: click value to type; slider max expands when value exceeds default range
- **1.9.60** — Fix CJK font filtering on Blender 4.2–4.3 (missing blf.NO_FALLBACK); fix Source Han rejected by Chinese script filter
- **1.9.59** — HUD font picker: hover tooltips for search, filters, sort, language, refresh, clear, favorites, and close
- **1.9.58** — Fix favorites chip i18n; reset notice when already default; HUD drag no longer undoable
- **1.9.57** — Filter reset moved to filter row end (× icon); status-bar notice when filters restore to defaults
- **1.9.56** — HUD toolbar position stored on the text object so font/format undo does not move it
- **1.9.55** — Font search hover highlight; reset button restores all filters to defaults
- **1.9.54** — Add-on preference for font name display: file name, family, full name, or PostScript
- **1.9.53** — HUD font picker: sort chip + clearer compact filter chips (parity with header popover)
- **1.9.52** — HUD font picker: record Recently Used only when the picker closes, not on hover preview
- **1.9.51** — Font list sort (Recently Used default); multi-field search with pinyin/kana helpers
- **1.9.50** — Font picker scrollbar track/thumb adapt to light/dark panel backdrop
- **1.9.49** — Font picker: search field matches filter chips; list/scrollbar colors adapt to light/dark UI
- **1.9.48** — Font picker title bar uses same background as outer panel shell
- **1.9.47** — Font picker outer panel background matches floating toolbar HUD backdrop
- **1.9.46** — Default HUD scale is 0.8
- **1.9.45** — Follow System: contrast-safe text colors for light/dark Blender themes (fields, chips, sliders)
- **1.9.44** — Follow System: sync HUD label/value text colors on toolbar, sliders, and picker panels
- **1.9.43** — HUD accent default preset is Blue again (Follow System remains available)
- **1.9.42** — Follow System HUD: hover matches pressed tool color; drag handle uses same base fill as other buttons
- **1.9.41** — HUD accent: removed Green and Cyan presets
- **1.9.40** — HUD accent: new “Follow System” preset matches Blender interface theme (tool header colors)
- **1.9.39** — HUD accent: active toggles use full accent color; default theme blue (#4772B3)
- **1.9.38** — Header font favorites: SOLO_OFF (unfavorited) / SOLO_ON (favorited)
- **1.9.37** — Font coverage filter checks all lines of text object body (deduplicated chars), not just the first line
- **1.9.35** — HUD font picker: chip hover feedback; refresh button moved to language row; equal-width filter chips
- **1.9.34** — HUD font picker favorite button hover highlight
- **1.9.33** — Fix header font favorite toggle: use Blender BOOKMARKS icon (Unicode stars do not render in UI)
- **1.9.31** — Header font list: star favorite toggle, family weight count, grouped rows; filter chips with translated labels
- **1.9.29** — Font favorites + filters (favorites, multi-weight, variable fonts); header refresh icon-only
- **1.9.27** — Preserve font weight names from filenames (Normal, Roman, etc.) instead of collapsing to Regular
- **1.9.25** — Header i18n; floating toolbar toggle before preset; hover preview in font/weight popovers
- **1.9.24** — Header toolbar: spacing sliders on one row, right-aligned; shorter control labels
- **1.9.23** — Header toolbar: after active tool settings; hide-unsupported font filter; case toggles; inline size/spacing/shear sliders; strike position
- **1.9.22** — Header toolbar: append after tool settings; font/weight popovers (text list, no thumbnails)
- **1.9.21** — Fix header toolbar: inject into viewport header via `VIEW3D_HT_*` hooks
- **1.9.20** — Viewport header toolbar mirrors HUD formatting when floating toolbar is off
- **1.9.19** — Fix HUD undo: refresh text curves after undo/redo; sliders apply RNA directly
- **1.9.18** — Multi-select batch editing; floating toolbar changes support undo
- **1.9.17** — Shorten Japanese strikethrough slider label to「取消位置」
- **1.9.16** — Shorten strikethrough slider label to "Strike Pos" in the viewport HUD
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
