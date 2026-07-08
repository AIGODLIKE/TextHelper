## Text Helper 2.2.28

Requires **Blender 5.2+**.

### Fixes

- **Multi-viewport HUD** — correct hit testing across split views and popup windows (single coordinate model)
- **Font family grouping** — merge weights such as Segoe UI Semilight and Bold Italic into one family instead of duplicate rows
- **Chinese / IME font search** — native search dialog with full IME support when filtering fonts

### Improvements

- **i18n** — 488 translated strings across English, Simplified Chinese, Traditional Chinese, and Japanese
- **Extension platform compliance** — manifest tags/copyright, `__package__` prefs lookup, cache paths, handler cleanup, lint pass

### Since 2.2.1

- HUD modal refactor for per-window interaction
- Font search input operator (`wm.texthelper_font_search_input`)
- Removed legacy add-on ID fallbacks and version-migration cruft

### Install

1. Download `TextHelper-2.2.28.zip` below
2. Blender: **Edit → Preferences → Get Extensions → Install from Disk…**
3. Enable **Text Helper**
