from . import format, presets, text, hud_modal, spacing_menus, fonts, font_list, orientation, font_language

modules = (format, presets, text, hud_modal, spacing_menus, fonts, font_list, orientation, font_language)


def register():
    for mod in modules:
        mod.register()


def unregister():
    for mod in reversed(modules):
        mod.unregister()
