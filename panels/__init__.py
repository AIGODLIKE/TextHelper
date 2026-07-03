from . import sidebar



__all__ = ["register", "unregister"]





def register():

    sidebar.register()





def unregister():

    sidebar.unregister()

