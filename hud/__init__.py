from . import font_picker

__all__ = ["font_picker", "register", "unregister"]


def register():
    return


def unregister():
    font_picker.release_blf_cache()
