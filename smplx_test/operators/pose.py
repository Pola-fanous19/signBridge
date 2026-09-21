import pickle

import bpy
import numpy as np
from bpy.props import BoolProperty, StringProperty
from bpy_extras.io_utils import ImportHelper
from mathutils import Quaternion

from ..utils.constants import ADDON_ROOT
from ..utils.model_spec import get_active_model_spec
from ..utils.pose import rodrigues_from_pose, set_pose_from_rodrigues
from ..utils.shapekeys import smplx_ensure_valid_shapekey_slider_ranges


class SMPLXSetPoseshapes(bpy.types.Operator):
    bl_idname = "object.smplx_set_poseshapes"
    bl_label = "Update Pose Shapes"
    bl_description = ("Sets and updates corrective poseshapes for current pose")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object and parent is armature
            return ( ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE')) or (context.object.type == 'ARMATURE'))
        except: return False

    # https://github.com/gulvarol/surreal/blob/master/datageneration/main_part1.py
    # Computes rotation matrix through Rodrigues formula as in cv2.Rodrigues
    def rodrigues_to_mat(self, rotvec):
        theta = np.linalg.norm(rotvec)
        r = (rotvec/theta).reshape(3, 1) if theta > 0. else rotvec
        cost = np.cos(theta)
        mat = np.asarray([[0, -r[2], r[1]],
                        [r[2], 0, -r[0]],
                        [-r[1], r[0], 0]], dtype=object)
        return(cost*np.eye(3) + (1-cost)*r.dot(r.T) + np.sin(theta)*mat)

    # https://github.com/gulvarol/surreal/blob/master/datageneration/main_part1.py
    # Calculate weights of pose corrective blend shapes
    # Input is the flat pose vector of all model joints; output is weights for all joints except pelvis
    def rodrigues_to_posecorrective_weight(self, pose):
        rod_rots = np.asarray(pose).reshape(-1, 3)
        mat_rots = [self.rodrigues_to_mat(rod_rot) for rod_rot in rod_rots]
        bshapes = np.concatenate([(mat_rot - np.eye(3)).ravel() for mat_rot in mat_rots[1:]])
        return(bshapes)

    def execute(self, context):
        obj = bpy.context.object

        spec = get_active_model_spec(context)
        if spec is None:
            self.report({'WARNING'}, "No SMPL model active")
            return {'CANCELLED'}

        # Get armature pose in rodrigues representation
        if obj.type == 'ARMATURE':
            armature = obj
            obj = bpy.context.object.children[0]
        else:
            armature = obj.parent

        smplx_ensure_valid_shapekey_slider_ranges(obj)

        num_joints = len(spec.joint_names)
        pose = [0.0] * (num_joints * 3)

        for index, joint_name in enumerate(spec.joint_names):
            joint_pose = rodrigues_from_pose(armature, joint_name)
            pose[index*3 + 0] = joint_pose[0]
            pose[index*3 + 1] = joint_pose[1]
            pose[index*3 + 2] = joint_pose[2]

        poseweights = self.rodrigues_to_posecorrective_weight(pose)

        # Set weights for pose corrective shape keys
        for index, weight in enumerate(poseweights):
            obj.data.shape_keys.key_blocks["Pose%03d" % index].value = weight

        # Set checkbox without triggering update function
        context.window_manager.smplx_tool["smplx_corrective_poseshapes"] = True

        return {'FINISHED'}


class SMPLXResetPoseshapes(bpy.types.Operator):
    bl_idname = "object.smplx_reset_poseshapes"
    bl_label = "Reset"
    bl_description = ("Resets corrective poseshapes for current pose")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object and parent is armature
            return ( ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE')) or (context.object.type == 'ARMATURE'))
        except: return False

    def execute(self, context):
        obj = bpy.context.object

        if obj.type == 'ARMATURE':
            obj = bpy.context.object.children[0]

        for key_block in obj.data.shape_keys.key_blocks:
            if key_block.name.startswith("Pose"):
                key_block.value = 0.0

        return {'FINISHED'}


class SMPLXSetHandpose(bpy.types.Operator):
    bl_idname = "object.smplx_set_handpose"
    bl_label = "Set"
    bl_description = ("Set selected hand pose")
    bl_options = {'REGISTER', 'UNDO'}

    hand_poses = None

    @classmethod
    def poll(cls, context):
        try:
            if not (((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE')) or (context.object.type == 'ARMATURE')):
                return False
            spec = get_active_model_spec(context)
            return spec is not None and bool(spec.handposes_file)
        except: return False

    def execute(self, context):
        obj = bpy.context.object
        if obj.type == 'MESH':
            armature = obj.parent
        else:
            armature = obj

        spec = get_active_model_spec(context)
        if spec is None or not spec.handposes_file:
            self.report({'WARNING'}, "No hand pose data for this model")
            return {'CANCELLED'}

        if self.hand_poses is None:
            data_path = ADDON_ROOT / "data" / spec.handposes_file
            with np.load(data_path, allow_pickle=True) as data:
                self.hand_poses = data["hand_poses"].item()

        hand_pose_name = context.window_manager.smplx_tool.smplx_handpose
        print("Setting hand pose: " + hand_pose_name)

        if hand_pose_name not in self.hand_poses:
            self.report({"ERROR"}, f"Desired hand pose not existing: {hand_pose_name}")
            return {"CANCELLED"}

        (left_hand_pose, right_hand_pose) = self.hand_poses[hand_pose_name]

        hand_pose = np.concatenate( (left_hand_pose, right_hand_pose) ).reshape(-1, 3)

        # Hand bones live at the end of joint_names (after pelvis + body + optional face).
        num_hand_bones = 2 * spec.num_hand_joints
        hand_joint_start_index = len(spec.joint_names) - num_hand_bones
        for index in range(num_hand_bones):
            pose_rodrigues = hand_pose[index]
            bone_name = spec.joint_names[index + hand_joint_start_index]
            set_pose_from_rodrigues(armature, bone_name, pose_rodrigues)

        # Update corrective poseshapes if used
        if context.window_manager.smplx_tool.smplx_corrective_poseshapes and spec.has_corrective_poseshapes:
            bpy.ops.object.smplx_set_poseshapes('EXEC_DEFAULT')

        return {'FINISHED'}


class SMPLXWritePose(bpy.types.Operator):
    bl_idname = "object.smplx_write_pose"
    bl_label = "Write Pose To Console"
    bl_description = ("Writes SMPL-X flat hand pose thetas to console window")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh or armature is active object
            return (context.object.type == 'MESH') or (context.object.type == 'ARMATURE')
        except: return False

    def execute(self, context):
        obj = bpy.context.object

        spec = get_active_model_spec(context)
        if spec is None:
            self.report({'WARNING'}, "No SMPL model active")
            return {'CANCELLED'}

        if obj.type == 'MESH':
            armature = obj.parent
        else:
            armature = obj

        num_joints = len(spec.joint_names)
        pose = [0.0] * (num_joints * 3)

        for index, joint_name in enumerate(spec.joint_names):
            joint_pose = rodrigues_from_pose(armature, joint_name)
            pose[index*3 + 0] = joint_pose[0]
            pose[index*3 + 1] = joint_pose[1]
            pose[index*3 + 2] = joint_pose[2]

        print("\npose = " + str(pose))

        return {'FINISHED'}


class SMPLXResetPose(bpy.types.Operator):
    bl_idname = "object.smplx_reset_pose"
    bl_label = "Reset Pose"
    bl_description = ("Resets pose to default zero pose")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return ( ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE')) or (context.object.type == 'ARMATURE'))
        except: return False

    def execute(self, context):
        obj = bpy.context.object

        if obj.type == 'MESH':
            armature = obj.parent
        else:
            armature = obj

        for bone in armature.pose.bones:
            if bone.rotation_mode != 'QUATERNION':
                bone.rotation_mode = 'QUATERNION'
            bone.rotation_quaternion = Quaternion()

        # Reset corrective pose shapes
        bpy.ops.object.smplx_reset_poseshapes('EXEC_DEFAULT')

        return {'FINISHED'}


class SMPLXLoadPose(bpy.types.Operator, ImportHelper):
    bl_idname = "object.smplx_load_pose"
    bl_label = "Load Pose"
    bl_description = ("Load relaxed-hand model pose from file")
    bl_options = {'REGISTER', 'UNDO'}

    filter_glob: StringProperty(
        default="*.pkl",
        options={'HIDDEN'}
    )

    update_shape: BoolProperty(
        name="Update shape parameters",
        description="Update shape parameters using the beta shape information in the loaded file",
        default=True
    )

    hand_pose_relaxed = None

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh or armature is active object
            return ( ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE')) or (context.object.type == 'ARMATURE'))
        except: return False

    def execute(self, context):
        obj = bpy.context.object

        spec = get_active_model_spec(context)
        if spec is None:
            self.report({'WARNING'}, "No SMPL model active")
            return {'CANCELLED'}

        if obj.type == 'MESH':
            armature = obj.parent
        else:
            armature = obj
            obj = armature.children[0]
            context.view_layer.objects.active = obj # mesh needs to be active object for recalculating joint locations

        if self.hand_pose_relaxed is None and spec.handposes_file:
            data_path = ADDON_ROOT / "data" / spec.handposes_file
            with np.load(data_path, allow_pickle=True) as data:
                hand_poses = data["hand_poses"].item()
                (left_hand_pose, right_hand_pose) = hand_poses["relaxed"]
                self.hand_pose_relaxed = np.concatenate( (left_hand_pose, right_hand_pose) ).reshape(-1, 3)

        print("Loading: " + self.filepath)

        translation = None
        global_orient = None
        body_pose = None
        jaw_pose = None
        left_hand_pose = None
        right_hand_pose = None
        betas = None
        expression = None
        with open(self.filepath, "rb") as f:
            data = pickle.load(f, encoding="latin1")

            if "transl" in data:
                translation = np.array(data["transl"]).reshape(3)

            if "global_orient" in data:
                global_orient = np.array(data["global_orient"]).reshape(3)

            body_pose = np.array(data["body_pose"])
            if body_pose.shape != (1, spec.num_body_joints * 3):
                print(f"Invalid body pose dimensions: {body_pose.shape}")
                return {'CANCELLED'}

            body_pose = body_pose.reshape(spec.num_body_joints, 3)

            if spec.has_expressions:
                jaw_pose = np.array(data["jaw_pose"]).reshape(3)
                expression = np.array(data["expression"]).reshape(-1).tolist()

            left_hand_pose = np.array(data["left_hand_pose"]).reshape(-1, 3)
            right_hand_pose = np.array(data["right_hand_pose"]).reshape(-1, 3)

            betas = np.array(data["betas"]).reshape(-1).tolist()

        # Update shape if selected
        if self.update_shape:
            bpy.ops.object.mode_set(mode='OBJECT')
            for index, beta in enumerate(betas):
                key_block_name = f"Shape{index:03}"

                if key_block_name in obj.data.shape_keys.key_blocks:
                    obj.data.shape_keys.key_blocks[key_block_name].value = beta
                else:
                    print(f"ERROR: No key block for: {key_block_name}")

            if spec.regressor_template is not None:
                bpy.ops.object.smplx_update_joint_locations('EXEC_DEFAULT')

        if global_orient is not None:
            set_pose_from_rodrigues(armature, "pelvis", global_orient)

        # Body pose starts with left_hip (joint_names[1])
        for index in range(spec.num_body_joints):
            pose_rodrigues = body_pose[index]
            bone_name = spec.joint_names[index + 1]
            set_pose_from_rodrigues(armature, bone_name, pose_rodrigues)

        if spec.has_expressions and jaw_pose is not None:
            set_pose_from_rodrigues(armature, "jaw", jaw_pose)

        # Hand bones live at the end of joint_names: left hand first, then right hand.
        hand_start = len(spec.joint_names) - 2 * spec.num_hand_joints
        for i in range(spec.num_hand_joints):
            bone_name = spec.joint_names[hand_start + i]
            pose_relaxed_rodrigues = self.hand_pose_relaxed[i] if self.hand_pose_relaxed is not None else None
            set_pose_from_rodrigues(armature, bone_name, left_hand_pose[i], pose_relaxed_rodrigues)

        for i in range(spec.num_hand_joints):
            bone_name = spec.joint_names[hand_start + spec.num_hand_joints + i]
            pose_relaxed_rodrigues = self.hand_pose_relaxed[spec.num_hand_joints + i] if self.hand_pose_relaxed is not None else None
            set_pose_from_rodrigues(armature, bone_name, right_hand_pose[i], pose_relaxed_rodrigues)

        if translation is not None:
            armature.location = (translation[0], -translation[2], translation[1])

        # Activate corrective poseshapes
        if spec.has_corrective_poseshapes:
            bpy.ops.object.smplx_set_poseshapes('EXEC_DEFAULT')

        if spec.has_expressions and expression is not None:
            for index, exp in enumerate(expression):
                key_block_name = f"Exp{index:03}"

                if key_block_name in obj.data.shape_keys.key_blocks:
                    obj.data.shape_keys.key_blocks[key_block_name].value = exp
                else:
                    print(f"ERROR: No key block for: {key_block_name}")

        return {'FINISHED'}


classes = (
    SMPLXSetPoseshapes,
    SMPLXResetPoseshapes,
    SMPLXSetHandpose,
    SMPLXWritePose,
    SMPLXResetPose,
    SMPLXLoadPose,
)
