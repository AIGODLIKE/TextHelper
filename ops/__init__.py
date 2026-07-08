from . import format, presets, text, hud_modal, spacing_menus, fonts, font_list, font_favorites, orientation, font_language, font_search_input

modules = (format, presets, text, hud_modal, spacing_menus, fonts, font_list, font_favorites, orientation, font_language, font_search_input)


def register():
    for mod in modules:
        mod.register()


def unregister():
    for mod in reversed(modules):
        mod.unregister()
