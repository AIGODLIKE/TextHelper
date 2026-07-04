"""Rescan fonts and rebuild preview thumbnails after disk files change."""

from __future__ import annotations


def perform_font_system_refresh(context) -> int:
    """Clear failure caches, rescan folders, and queue visible previews."""
    from ..hud.draw import tag_redraw
    from .font_language import invalidate_font_language_cache
    from .font_loader import refresh_font_catalog, reset_font_catalog_scan
    from .font_preview import invalidate_font_previews, tag_ui_redraw, warm_font_preview_queue

    reset_font_catalog_scan()
    invalidate_font_previews(clear_files=True)
    try:
        invalidate_font_language_cache()
    except Exception:
        pass
    count = refresh_font_catalog(context.window_manager, force=True)
    warm_font_preview_queue(context)
    tag_ui_redraw(context)
    tag_redraw()
    return count
