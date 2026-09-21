if "bpy" in locals():
    import importlib
    from . import model, shape, pose, animation, export
    for _m in (model, shape, pose, animation, export):
        importlib.reload(_m)
else:
    from . import model, shape, pose, animation, export

import bpy

classes = (
    *model.classes,
    *shape.classes,
    *pose.classes,
    *animation.classes,
    *export.classes,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
