if "bpy" in locals():
    import importlib
    from . import viewport
    importlib.reload(viewport)
else:
    from . import viewport

import bpy

classes = viewport.classes


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
