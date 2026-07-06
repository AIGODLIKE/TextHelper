from . import sidebar
from . import toolbar


__all__ = ["register", "unregister"]


def register():
    sidebar.register()
    toolbar.register()


def unregister():
    toolbar.unregister()
    sidebar.unregister()

