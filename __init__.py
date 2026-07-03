bl_info = {
    "name": "Text Helper",
    "author": "ACGGIT",
    "version": (1, 8, 5),
    "blender": (5, 2, 0),
    "location": "View3D > Sidebar > Text Helper",
    "description": "Easy text input & font management",
    "doc_url": "https://github.com/AIGODLIKE/TextHelper",
    "tracker_url": "https://github.com/AIGODLIKE/TextHelper/issues",
    "support": "COMMUNITY",
    "category": "Object",
    "license": "GPL-3.0-or-later",
}

ADDON_PACKAGE = __name__

import bpy

from . import i18n, ops, panels, preferences, props, runtime, sync


def register():
    i18n.register(ADDON_PACKAGE)
    preferences.register()
    props.register()
    sync.register()
    ops.register()
    panels.register()
    try:
        from .utils.font_preview import init_font_preview_cache

        init_font_preview_cache()
    except Exception:
        pass


def unregister():
    runtime.shutdown()
    panels.unregister()
    ops.unregister()
    sync.unregister()
    from .utils.ui_textbox import unregister as unregister_ui_textbox
    from .utils.font_loader import unregister_font_catalog_queue
    from .props import unregister_font_index_deferred

    unregister_ui_textbox()
    unregister_font_catalog_queue()
    unregister_font_index_deferred()
    props.unregister()
    preferences.unregister()
    from .utils.font_preview import release_font_previews

    release_font_previews()
    try:
        from .utils.font_blf import clear_font_failure_cache

        clear_font_failure_cache()
    except Exception:
        pass
    i18n.unregister()
