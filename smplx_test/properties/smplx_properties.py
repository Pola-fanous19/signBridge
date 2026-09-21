import bpy
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, EnumProperty, FloatProperty

from ..utils.model_spec import MODELS, get_active_model_spec


def update_corrective_poseshapes(self, context):
    if self.smplx_corrective_poseshapes:
        bpy.ops.object.smplx_set_poseshapes('EXEC_DEFAULT')
    else:
        bpy.ops.object.smplx_reset_poseshapes('EXEC_DEFAULT')


def _texture_items(self, context):
    spec = get_active_model_spec(context) or MODELS[self.body_model]
    return list(spec.texture_items)


def _gender_items(self, context):
    return list(MODELS[self.body_model].gender_items)


class PG_SMPLXProperties(PropertyGroup):

    body_model: EnumProperty(
        name = "Type",
        description = "Body model type",
        items = [ ("smplx", "SMPL-X", ""), ("smplh", "SMPL+H", "") ],
        default = "smplx",
    )

    smplx_version: EnumProperty(
        name = "Version",
        description = "SMPL-X version",
        items = [ ("locked_head", "SMPL-X Locked Head", "SMPL-X locked head model without head bun"), ("v1.1", "SMPL-X v1.1", "SMPL-X v1.1 model with head bun") ]
    )

    smplx_gender: EnumProperty(
        name = "Body",
        description = "Body to load",
        items = _gender_items,
    )

    smplx_uv: EnumProperty(
        name = "UV",
        description = "SMPL-X UV version",
        items = [ ("UV_2023", "2023", "Latest UV layout with two eyeball regions"), ("UV_2021", "2021", "Original Blender add-on UV layout") ]
    )

    smplx_texture: EnumProperty(
        name = "",
        description = "Model texture",
        items = _texture_items,
    )

    smplx_corrective_poseshapes: BoolProperty(
        name = "Corrective Pose Shapes",
        description = "Enable/disable corrective pose shapes of SMPL-X model",
        update = update_corrective_poseshapes,
        default = True
    )

    smplx_handpose: EnumProperty(
        name = "",
        description = "SMPL-X hand pose",
        items = [ ("relaxed", "Relaxed", ""), ("flat", "Flat", "") ]
    )

    smplx_height: FloatProperty(name="Target Height [m]", default=1.70, min=1.4, max=2.2)

    smplx_weight: FloatProperty(name="Target Weight [kg]", default=60, min=40, max=110)
