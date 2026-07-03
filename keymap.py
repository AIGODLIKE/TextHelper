import bpy

_keymaps = []


def register():
    wm = bpy.context.window_manager
    if wm is None:
        return
    kc = wm.keyconfigs.addon
    if kc is None:
        return

    km = kc.keymaps.new(name="Text", space_type="EMPTY")
    kmi = km.keymap_items.new("font.texthelper_style_toggle", "B", "PRESS", ctrl=True)
    kmi.properties.style = "BOLD"
    _keymaps.append((km, kmi))

    kmi = km.keymap_items.new("font.texthelper_style_toggle", "I", "PRESS", ctrl=True)
    kmi.properties.style = "ITALIC"
    _keymaps.append((km, kmi))

    kmi = km.keymap_items.new("font.texthelper_style_toggle", "U", "PRESS", ctrl=True)
    kmi.properties.style = "UNDERLINE"
    _keymaps.append((km, kmi))

    kmi = km.keymap_items.new("font.texthelper_set_align", "L", "PRESS", ctrl=True, shift=True)
    kmi.properties.align = "LEFT"
    _keymaps.append((km, kmi))

    kmi = km.keymap_items.new("font.texthelper_set_align", "E", "PRESS", ctrl=True, shift=True)
    kmi.properties.align = "CENTER"
    _keymaps.append((km, kmi))

    kmi = km.keymap_items.new("font.texthelper_set_align", "R", "PRESS", ctrl=True, shift=True)
    kmi.properties.align = "RIGHT"
    _keymaps.append((km, kmi))


def unregister():
    for km, kmi in _keymaps:
        km.keymap_items.remove(kmi)
    _keymaps.clear()
