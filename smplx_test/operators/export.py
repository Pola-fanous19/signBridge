from math import radians

import bpy
import numpy as np
from bpy.props import BoolProperty, EnumProperty
from bpy_extras.io_utils import ExportHelper
from mathutils import Vector

from ..utils.model_spec import get_active_model_spec


class SMPLXExportAlembic(bpy.types.Operator, ExportHelper):
    bl_idname = "object.smplx_export_alembic"
    bl_label = "Export Alembic ABC"
    bl_description = ("Export as Alembic geometry cache")
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".abc"

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return (context.object.type == 'MESH')
        except: return False

    def execute(self, context):
        bpy.ops.wm.alembic_export(filepath=self.filepath, selected=True, packuv=False, face_sets=True)
        print("Exported: " + self.filepath)

        return {'FINISHED'}


class SMPLXExportFBX(bpy.types.Operator, ExportHelper):
    bl_idname = "object.smplx_export_fbx"
    bl_label = "Export FBX"
    bl_description = ("Export skinned mesh in FBX format")
    bl_options = {'REGISTER', 'UNDO'}

    # ExportHelper mixin class uses this
    filename_ext = ".fbx"

    export_shape_keys: EnumProperty(
        name = "Blend Shapes",
        description = "Blend shape export settings",
        items = [ ("SHAPE_POSECORRECTIVES", "All: Shape + Posecorrectives", "Export shape keys for body shape and pose correctives"),
                  ("SHAPE", "Reduced: Shape space only", "Export only shape keys for body shape"),
                  ("POSECORRECTIVES", "Reduced: Posecorrectives only", "Bake shape and expression into mesh, export only shape keys for pose correctives"),
                  ("NONE", "None: Apply shape space", "Do not export any shape keys, shape keys for body shape will be baked into mesh") ],
    )


    target_format: EnumProperty(
        name="Format",
        items=(
            ("UNITY", "Unity", ""),
            ("UNREAL", "Unreal", ""),
        ),
    )

    animation_only: BoolProperty(
        name="Animation Only",
        description="Export only the animation (armature) without the mesh",
        default=False,
    )

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return (context.object.type == 'MESH')
        except: return False

    def execute(self, context):

        obj = bpy.context.object

        spec = get_active_model_spec(context)
        if spec is None:
            self.report({'WARNING'}, "No SMPL model active")
            return {'CANCELLED'}

        armature_original = obj.parent
        skinned_mesh_original = obj

        # Operate on temporary copy of skinned mesh and armature
        bpy.ops.object.select_all(action='DESELECT')
        skinned_mesh_original.select_set(True)
        armature_original.select_set(True)
        bpy.context.view_layer.objects.active = skinned_mesh_original
        bpy.ops.object.duplicate()
        skinned_mesh = bpy.context.object
        armature = skinned_mesh.parent

        # Apply armature object location to armature root bone and skinned mesh so that armature and skinned mesh are at origin before export
        context.view_layer.objects.active = armature
        armature_offset = Vector(armature.location)
        armature.location = (0, 0, 0)
        bpy.ops.object.mode_set(mode='EDIT')
        for edit_bone in armature.data.edit_bones:
            if edit_bone.name != "root":
                edit_bone.translate(armature_offset)

        bpy.ops.object.mode_set(mode='OBJECT')
        context.view_layer.objects.active = skinned_mesh
        mesh_location = Vector(skinned_mesh.location)
        skinned_mesh.location = mesh_location + armature_offset
        bpy.ops.object.transform_apply(location = True)

        # Reset pose
        bpy.ops.object.smplx_reset_pose('EXEC_DEFAULT')

        if ( (self.export_shape_keys == 'SHAPE') or (self.export_shape_keys == 'NONE') ):
            # Remove pose corrective shape keys
            print("Removing pose corrective shape keys")
            num_shape_keys = len(skinned_mesh.data.shape_keys.key_blocks.keys())

            current_shape_key_index = 0
            for index in range(0, num_shape_keys):
                bpy.context.object.active_shape_key_index = current_shape_key_index

                if bpy.context.object.active_shape_key is not None:
                    if bpy.context.object.active_shape_key.name.startswith('Pose'):
                        bpy.ops.object.shape_key_remove(all=False)
                    else:
                        current_shape_key_index = current_shape_key_index + 1

        if self.export_shape_keys == 'NONE':
            # Bake and remove shape keys
            print("Baking shape and removing shape keys for shape")

            # Zero out all pose corrective weights so that they do not contribute to baked shape
            for key_block in skinned_mesh.data.shape_keys.key_blocks:
                if key_block.name.startswith("Pose"):
                    key_block.value = 0.0

            # Create shape mix for current shape
            bpy.ops.object.shape_key_add(from_mix=True)
            num_shape_keys = len(skinned_mesh.data.shape_keys.key_blocks.keys())

            # Remove all shape keys except newly added one
            bpy.context.object.active_shape_key_index = 0
            for count in range(0, num_shape_keys):
                bpy.ops.object.shape_key_remove(all=False)

        elif self.export_shape_keys == 'POSECORRECTIVES':
            # Bake shape and expression into Base shape key
            print("Baking shape and expression into Base shape key")

            # Zero out all pose corrective weights so that they do not contribute to baked shape
            for key_block in skinned_mesh.data.shape_keys.key_blocks:
                if key_block.name.startswith("Pose"):
                    key_block.value = 0.0

            # Create shape mix from current shape and expression
            bpy.ops.object.shape_key_add(from_mix=True)
            bpy.context.object.active_shape_key.name = "ShapeMix"

            # Copy shape mix vertices intp Base shape key
            bpy.context.object.active_shape_key_index = 0 # Select Base shape key
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.blend_from_shape(shape="ShapeMix", blend=1, add=False)
            bpy.ops.object.mode_set(mode='OBJECT')

            # Remove all shape and expression keys and shape mix
            num_shape_keys = len(skinned_mesh.data.shape_keys.key_blocks.keys())
            current_shape_key_index = 1
            for _ in range(1, num_shape_keys):
                bpy.context.object.active_shape_key_index = current_shape_key_index

                if bpy.context.object.active_shape_key is not None:
                    name = bpy.context.object.active_shape_key.name
                    if name.startswith("Shape") or name.startswith("Exp"):
                        bpy.ops.object.shape_key_remove(all=False)
                    else:
                        current_shape_key_index = current_shape_key_index + 1
            bpy.context.object.active_shape_key_index = 0

        # Model (skeleton and skinned mesh) needs to have rotation of (90, 0, 0) when exporting so that it will have rotation (0, 0, 0) when imported into Unity
        bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.select_all(action='DESELECT')
        skinned_mesh.select_set(True)
        skinned_mesh.rotation_euler = (radians(-90), 0, 0)
        bpy.context.view_layer.objects.active = skinned_mesh
        bpy.ops.object.transform_apply(location = False, rotation = True, scale = False)
        skinned_mesh.rotation_euler = (radians(90), 0, 0)
        skinned_mesh.select_set(False)

        armature.select_set(True)
        armature.rotation_euler = (radians(-90), 0, 0)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.transform_apply(location = False, rotation = True, scale = False)
        armature.rotation_euler = (radians(90), 0, 0)

        if self.target_format == "UNREAL":
            # Scale armature by 100 so that Unreal FBX importer can be used with default scale 1.
            # This ensures that attached objects to imported skeleton in Unreal will keep scale 1.

            armature.scale = (100, 100, 100)

            # Scale keyframed pelvis locations if available
            if armature.animation_data is not None:
                action = armature.animation_data.action
                if bpy.app.version >= (5, 0, 0):
                    from bpy_extras import anim_utils
                    action_slot = armature.animation_data.action_slot
                    channelbag = anim_utils.action_get_channelbag_for_slot(action, action_slot)
                    fcurves = channelbag.fcurves
                else:
                    fcurves = action.fcurves
                for fcurve in fcurves:
                    if fcurve.data_path.endswith("location"):
                        for keyframe_point in fcurve.keyframe_points:
                            keyframe_point.co[1] = keyframe_point.co[1] * 100
                            keyframe_point.handle_left[1] = keyframe_point.handle_left[1] * 100
                            keyframe_point.handle_right[1] = keyframe_point.handle_right[1] * 100

            bpy.ops.object.transform_apply(location = False, rotation = False, scale = True)

        # Select armature and skinned mesh for export
        skinned_mesh.select_set(True)

        # Rename armature and skinned mesh to not contain Blender copy suffix
        gender = skinned_mesh_original[f"{spec.id}_gender"]

        target_mesh_name = spec.mesh_name_template.format(gender=gender)
        target_armature_name = spec.armature_name_template.format(gender=gender)
        temp_mesh_name = f"{spec.id}-temp-mesh"
        temp_armature_name = f"{spec.id}-temp-armature"

        if target_mesh_name in bpy.data.objects:
            bpy.data.objects[target_mesh_name].name = temp_mesh_name
        skinned_mesh.name = target_mesh_name

        if target_armature_name in bpy.data.objects:
            bpy.data.objects[target_armature_name].name = temp_armature_name
        armature.name = target_armature_name

        object_types = {'ARMATURE', 'MESH', 'OTHER'}
        if self.animation_only:
            object_types = {'ARMATURE'}

        # Default FBX export settings export all animations. Since we duplicated the armature we have a copy of the animation and the original animation.
        # We avoid export of both by only exporting the active animation for the armature (bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False).
        # Disable keyframe simplification to ensure that exported FBX animation properly matches up with exported Alembic cache.
        bpy.ops.export_scene.fbx(filepath=self.filepath,
                                 use_selection=True,
                                 apply_scale_options="FBX_SCALE_ALL",
                                 object_types=object_types,
                                 use_custom_props=True,
                                 add_leaf_bones=False,
                                 bake_anim_use_nla_strips=False,
                                 bake_anim_use_all_actions=False,
                                 bake_anim_simplify_factor=0)

        print("Exported: " + self.filepath)

        # Remove temporary copies of armature and skinned mesh
        bpy.ops.object.select_all(action='DESELECT')
        skinned_mesh.select_set(True)
        armature.select_set(True)
        bpy.ops.object.delete()

        bpy.ops.object.select_all(action='DESELECT')
        skinned_mesh_original.select_set(True)
        bpy.context.view_layer.objects.active = skinned_mesh_original

        if temp_mesh_name in bpy.data.objects:
            bpy.data.objects[temp_mesh_name].name = target_mesh_name

        if temp_armature_name in bpy.data.objects:
            bpy.data.objects[temp_armature_name].name = target_armature_name

        return {'FINISHED'}


class SMPLXExportShape(bpy.types.Operator, ExportHelper):
    bl_idname = "object.smplx_export_shape"
    bl_label = "Export Shape"
    bl_description = ("Export shape beta values in NPZ format")
    bl_options = {'REGISTER', 'UNDO'}

    # ExportHelper mixin class uses this
    filename_ext = ".npz"

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return (context.object.type == 'MESH')
        except: return False

    def execute(self, context):

        obj = bpy.context.object
        armature = obj.parent

        spec = get_active_model_spec(context)
        if spec is None:
            self.report({'WARNING'}, "No SMPL model active")
            return {'CANCELLED'}

        betas = []
        for index in range(300):
            key_block_name = f"Shape{index:03}"

            if key_block_name in obj.data.shape_keys.key_blocks:
                beta = obj.data.shape_keys.key_blocks[key_block_name].value
                betas.append(beta)

        version = obj.get("smplx_version")
        data = {}
        data["gender"] = obj[f"{spec.id}_gender"]
        data["mocap_frame_rate"] = 30
        data["model"] = f"{spec.id}_{version}" if version else spec.id
        data["betas"] = betas
        data["poses"] = [ [0.0] * 3 * len(spec.joint_names) ]
        data["trans"] = [ [0.0, 0.0, 0.0] ]
        data["info"] = "Shape only,default pose"

        bind_pose_height_offset = 0.0
        if "smplx_bind_pose_height_offset" in obj:
            bind_pose_height_offset = obj["smplx_bind_pose_height_offset"]
        else:
            # Store current SnapToGroundPlane armature height offset which for default pose equals the distance used to map default bind pose to grounded bind pose.
            # Armature must be in default pose for correct SnapToGroundPlane results.
            bind_pose_height_offset = armature.location[2]

        data["bind_pose_height_offset"] = bind_pose_height_offset

        np.savez_compressed(self.filepath, **data)
        print("Exported: " + self.filepath)

        return {'FINISHED'}


classes = (
    SMPLXExportAlembic,
    SMPLXExportFBX,
    SMPLXExportShape,
)
