if "bpy" in locals():
    import importlib
    from . import selection
    importlib.reload(selection)
else:
    from . import selection

import bpy


def register():
    selection.register()


def unregister():
    selection.unregister()
