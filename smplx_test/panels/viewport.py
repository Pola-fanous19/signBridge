import bpy

from ..utils.constants import ADDON_VERSION
from ..utils.model_spec import MODELS, get_active_model_spec, is_variant_installed, resolve_variant_key


def _active_has_shape_keys(context) -> bool:
    obj = getattr(context, "object", None)
    if obj is None:
        return False
    if obj.type == "ARMATURE":
        obj = next((c for c in obj.children if c.type == "MESH"), None)
    if obj is None or obj.type != "MESH" or obj.data.shape_keys is None:
        return False
    return any(kb.name.startswith("Shape") for kb in obj.data.shape_keys.key_blocks)


class SMPLX_PT_Model(bpy.types.Panel):
    bl_label = "SMPL Body Models"
    bl_category = "SMPL Models"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        wm = context.window_manager
        layout = self.layout
        col = layout.column(align=True)

        # Add block — gated on the to-be-added model
        add_spec = MODELS[wm.smplx_tool.body_model]
        col.prop(wm.smplx_tool, "body_model")
        if "locked_head" in add_spec.blend_files:
            col.prop(wm.smplx_tool, "smplx_version")
        col.prop(wm.smplx_tool, "smplx_gender")
        if add_spec.has_uv_variants:
            col.prop(wm.smplx_tool, "smplx_uv")

        variant_key = resolve_variant_key(add_spec, wm.smplx_tool)
        installed = is_variant_installed(add_spec, variant_key)
        row = col.row()
        row.enabled = installed
        row.operator("scene.smplx_add_gender", text="Add")
        if not installed:
            col.label(text="Body model not installed", icon='ERROR')

        # Texture block — gated on the active model
        active_spec = get_active_model_spec(context)
        if active_spec is not None and active_spec.has_textures:
            col.separator()
            col.label(text="Texture:")
            row = col.row(align=True)
            split = row.split(factor=0.75, align=True)
            split.prop(wm.smplx_tool, "smplx_texture")
            split.operator("object.smplx_set_texture", text="Set")


class SMPLX_PT_Shape(bpy.types.Panel):
    bl_label = "Shape"
    bl_category = "SMPL Models"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        spec = get_active_model_spec(context)
        if spec is None:
            col.label(text="No SMPL model selected")
            return

        wm = context.window_manager
        has_shape_keys = _active_has_shape_keys(context)

        if has_shape_keys and spec.has_measurements_to_betas:
            col.prop(wm.smplx_tool, "smplx_height")
            col.prop(wm.smplx_tool, "smplx_weight")
            col.operator("object.smplx_measurements_to_shape")
            col.separator()

        if has_shape_keys:
            row = col.row(align=True)
            split = row.split(factor=0.75, align=True)
            split.operator("object.smplx_random_shape")
            split.operator("object.smplx_reset_shape")
            col.separator()

        col.operator("object.smplx_snap_ground_plane")

        if has_shape_keys and spec.regressor_template is not None:
            col.separator()
            col.operator("object.smplx_update_joint_locations")

        if has_shape_keys and spec.has_expressions:
            col.separator()
            row = col.row(align=True)
            split = row.split(factor=0.75, align=True)
            split.operator("object.smplx_random_expression_shape")
            split.operator("object.smplx_reset_expression_shape")


class SMPLX_PT_Pose(bpy.types.Panel):
    bl_label = "Pose"
    bl_category = "SMPL Models"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        spec = get_active_model_spec(context)
        if spec is None:
            col.label(text="No SMPL model selected")
            return

        wm = context.window_manager

        if spec.has_corrective_poseshapes:
            col.prop(wm.smplx_tool, "smplx_corrective_poseshapes")
            col.separator()
            col.operator("object.smplx_set_poseshapes")
            col.separator()

        col.label(text="Hand Pose:")
        row = col.row(align=True)
        split = row.split(factor=0.75, align=True)
        split.prop(wm.smplx_tool, "smplx_handpose")
        split.operator("object.smplx_set_handpose", text="Set")

        col.separator()
        col.operator("object.smplx_write_pose")
        col.separator()
        col.operator("object.smplx_load_pose")


class SMPLX_PT_Animation(bpy.types.Panel):
    bl_label = "Animation"
    bl_category = "SMPL Models"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        col.operator("object.smplx_add_animation")


class SMPLX_PT_Export(bpy.types.Panel):
    bl_label = "Export"
    bl_category = "SMPL Models"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        spec = get_active_model_spec(context)
        if spec is not None:
            col.operator("object.smplx_export_alembic")
            col.separator()

            col.operator("object.smplx_export_fbx")
            col.separator()

            col.operator("object.smplx_export_shape")
            col.separator()

            row = col.row(align=True)
            row.operator("ed.undo", icon='LOOP_BACK')
            row.operator("ed.redo", icon='LOOP_FORWARDS')
            col.separator()
        else:
            col.label(text="No SMPL model selected")
            col.separator()

        col.label(text=f"Version: {ADDON_VERSION}")


classes = (
    SMPLX_PT_Model,
    SMPLX_PT_Shape,
    SMPLX_PT_Pose,
    SMPLX_PT_Animation,
    SMPLX_PT_Export,
)
