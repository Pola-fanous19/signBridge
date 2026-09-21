if "bpy" in locals():
    import importlib
    from . import preferences
    importlib.reload(preferences)
else:
    from . import preferences

import bpy

classes = preferences.classes


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
