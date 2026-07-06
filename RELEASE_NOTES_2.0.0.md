## Text Helper 2.0.0

Requires **Blender 5.2+**.

### Highlights

- **Multi-line character limit**: default **20,000** characters; configurable in add-on preferences (**256–50,000**, Blender hard cap 50,000). N-panel sidebar shows `current / limit`.
- **Extension platform readiness**: lazy undo/redo handler registration; consistent text-limit enforcement for horizontal and vertical text; official `blender --command extension build` packaging.
- **Add Text** operator creates FONT curves via low-level API (no `bpy.ops.object.text_add` wrapper).
- **Manifest**: extension tag set to `User Interface`.

### Since 1.9.17 (cumulative)

This major release includes all improvements developed through 1.9.x:

- Viewport **header toolbar** (formatting, font/weight popovers, spacing sliders)
- **Font search** with pinyin/kana helpers, favorites, filters, async glyph checks
- **HUD** inline slider editing, theme-aware colors, multi-select batch editing
- **i18n**: Japanese and Traditional Chinese UI; operator tooltip translation fixes
- Font picker performance, Bfont handling, weight grouping, and many bug fixes

See [README.md](https://github.com/AIGODLIKE/TextHelper/blob/main/README.md) for the full 1.9.x changelog.

### Install

1. Download `TextHelper-2.0.0.zip` below
2. Blender: **Edit → Preferences → Get Extensions → Install from Disk…**
3. Enable **Text Helper**
