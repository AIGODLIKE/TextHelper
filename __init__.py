ADDON_PACKAGE = __package__

from . import i18n, ops, panels, preferences, props, runtime, sync


def register():
    i18n.register(ADDON_PACKAGE)
    preferences.register()
    props.register()
    sync.register()
    ops.register()
    panels.register()


def unregister():
    runtime.shutdown()
    from .utils.picker_preview import cancel_all_previews

    cancel_all_previews()
    panels.unregister()
    ops.unregister()
    sync.unregister()
    from .utils.ui_textbox import unregister as unregister_ui_textbox
    from .utils.font_loader import unregister_font_catalog_queue
    from .props import unregister_font_index_deferred

    unregister_ui_textbox()
    unregister_font_catalog_queue()
    from .utils.font_search import unregister_font_search_warm

    unregister_font_search_warm()
    from .utils.font_catalog_filter import invalidate_catalog_filter_cache

    invalidate_catalog_filter_cache()
    unregister_font_index_deferred()
    props.unregister()
    preferences.unregister()
    from .utils.font_preview import release_font_previews

    release_font_previews()
    from .utils.font_blf import clear_font_failure_cache

    clear_font_failure_cache()
    i18n.unregister()
