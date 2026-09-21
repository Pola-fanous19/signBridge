if "bpy" in locals():
    import importlib
    from . import smplx_properties
    importlib.reload(smplx_properties)
else:
    from . import smplx_properties

import bpy
from bpy.props import PointerProperty

from .smplx_properties import PG_SMPLXProperties

classes = (PG_SMPLXProperties,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    # Store properties under WindowManager (not Scene) so that they are not saved
    # in .blend files and always show default values after loading.
    bpy.types.WindowManager.smplx_tool = PointerProperty(type=PG_SMPLXProperties)


def unregister():
    del bpy.types.WindowManager.smplx_tool
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
