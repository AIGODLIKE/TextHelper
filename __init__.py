ADDON_PACKAGE = __package__

import bpy

from . import i18n, ops, panels, preferences, props, runtime, sync


def register():
    i18n.register(ADDON_PACKAGE)
    preferences.register()
    props.register()
    sync.register()
    ops.register()
    panels.register()
    from .utils.font_preview import init_font_preview_cache

    init_font_preview_cache()


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
    from .utils.font_blf import clear_font_failure_cache

    clear_font_failure_cache()
    i18n.unregister()
