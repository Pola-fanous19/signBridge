from math import radians
from pathlib import Path

import bpy
import numpy as np
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty
from bpy_extras.io_utils import ImportHelper
from mathutils import Quaternion, Vector

from ..utils.constants import ADDON_ROOT
from ..utils.model_spec import MODELS
from ..utils.pose import set_pose_from_rodrigues


class SMPLXAddAnimation(bpy.types.Operator, ImportHelper):
    bl_idname = "object.smplx_add_animation"
    bl_label = "Add Animation"
    bl_description = ("Load AMASS/SMPL-X animation and create animated SMPL-X/SMPL+H body")
    bl_options = {'REGISTER', 'UNDO'}

    filter_glob: StringProperty(
        default="*.npz",
        options={'HIDDEN'}
    )

    anim_format: EnumProperty(
        name="Format",
        items=(
            ("AMASS", "AMASS", ""),
            ("SMPL-X", "SMPL-X", ""),
        ),
    )

    rest_position: EnumProperty(
        name="Body rest position",
        items=(
            ("SMPL-X", "SMPL-X", "Use default SMPL-X rest position (feet below the floor)"),
            ("GROUNDED", "Grounded", "Use feet-on-floor rest position"),
        ),
    )

    hand_reference: EnumProperty(
        name="Hand pose reference",
        items=(
            ("FLAT", "Flat", "Use flat hand as hand pose reference"),
            ("RELAXED", "Relaxed", "Use relaxed hand as hand pose reference"),
        ),
    )

    keyframe_corrective_pose_weights: BoolProperty(
        name="Use keyframed corrective pose weights",
        description="Keyframe the weights of the corrective pose shapes for each frame. This increases animation load time and slows down editor real-time playback.",
        default=False
    )

    target_framerate: IntProperty(
        name="Target framerate [fps]",
        description="Target framerate for animation in frames-per-second. Lower values will speed up import time.",
        default=30,
        min = 1,
        max = 120
    )

    hand_pose_relaxed = None

    @classmethod
    def poll(cls, context):
        try:
            # Always enable button
            return True
        except: return False

    def execute(self, context):

        target_framerate = self.target_framerate

        if self.hand_reference == "RELAXED":
            if self.hand_pose_relaxed is None:
                data_path = ADDON_ROOT / "data" / "smplx_handposes.npz"
                with np.load(data_path, allow_pickle=True) as data:
                    hand_poses = data["hand_poses"].item()
                    (left_hand_pose, right_hand_pose) = hand_poses["relaxed"]
                    self.hand_pose_relaxed = np.concatenate( (left_hand_pose, right_hand_pose) ).reshape(-1, 3)

        # Load .npz file
        print("Loading: " + self.filepath)
        with np.load(self.filepath) as data:
            # Check for valid AMASS file
            if ("trans" not in data) or ("gender" not in data) or (("mocap_frame_rate" not in data) and ("mocap_framerate" not in data)) or ("betas" not in data) or ("poses" not in data):
                self.report({"ERROR"}, "Invalid AMASS animation data file")
                return {"CANCELLED"}

            trans = data["trans"]
            gender = str(data["gender"])
            mocap_framerate = int(data["mocap_frame_rate"]) if "mocap_frame_rate" in data else int(data["mocap_framerate"])
            betas = data["betas"]
            poses = data["poses"]

            if mocap_framerate < target_framerate:
                self.report({"ERROR"}, f"Mocap framerate ({mocap_framerate}) below target framerate ({target_framerate})")
                return {"CANCELLED"}

        # Identify model family from the joint count packed into poses.
        num_pose_joints = poses.shape[1] // 3
        spec = next((m for m in MODELS.values() if len(m.joint_names) == num_pose_joints), None)
        if spec is None:
            self.report({"ERROR"}, f"Unsupported joint count {num_pose_joints} in animation file")
            return {"CANCELLED"}

        if (context.active_object is not None):
            bpy.ops.object.mode_set(mode='OBJECT')

        # Add gender specific model
        context.window_manager.smplx_tool.body_model = spec.id
        context.window_manager.smplx_tool.smplx_gender = gender
        context.window_manager.smplx_tool.smplx_handpose = "flat"
        bpy.ops.scene.smplx_add_gender()

        obj = context.view_layer.objects.active
        armature = obj.parent

        # Append animation name to armature name
        armature.name = armature.name + "_" + Path(self.filepath).stem

        context.scene.render.fps = target_framerate
        context.scene.frame_start = 1

        # Set shape and update joint locations
        bpy.ops.object.mode_set(mode='OBJECT')
        for index, beta in enumerate(betas):
            key_block_name = f"Shape{index:03}"

            if key_block_name in obj.data.shape_keys.key_blocks:
                obj.data.shape_keys.key_blocks[key_block_name].value = beta
            else:
                print(f"ERROR: No key block for: {key_block_name}")

        bpy.ops.object.smplx_update_joint_locations('EXEC_DEFAULT')

        height_offset = 0
        if self.rest_position == "GROUNDED":
            bpy.ops.object.smplx_snap_ground_plane('EXEC_DEFAULT')
            height_offset = armature.location[2]

            obj["smplx_bind_pose_height_offset"] = height_offset

            # Apply location offsets to armature and skinned mesh
            bpy.context.view_layer.objects.active = armature
            armature.select_set(True)
            obj.select_set(True)
            bpy.ops.object.transform_apply(location = True, rotation=False, scale=False) # apply to selected objects
            armature.select_set(False)

            # Fix root bone location
            bpy.ops.object.mode_set(mode='EDIT')
            bone = armature.data.edit_bones["root"]
            bone.head = (0.0, 0.0, 0.0)
            bone.tail = (0.0, 0.0, 0.1)
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.context.view_layer.objects.active = obj

        # Keyframe poses
        step_size = int(mocap_framerate / target_framerate)

        num_frames = trans.shape[0]
        num_keyframes = int(num_frames / step_size)

        if self.keyframe_corrective_pose_weights:
            print(f"Adding pose keyframes with keyframed corrective pose weights: {num_keyframes}")
        else:
            print(f"Adding pose keyframes: {num_keyframes}")

        if len(bpy.data.actions) == 0:
            # Set end frame if we don't have any previous animations in the scene
            context.scene.frame_end = num_keyframes
        elif num_keyframes > context.scene.frame_end:
            context.scene.frame_end = num_keyframes

        wm = context.window_manager
        show_progress = not bpy.app.background and num_keyframes > 0
        if show_progress:
            # Percentage-based scale so the cursor's fractional-percent row
            # (2 decimal digits on Windows) always reads "00".
            wm.progress_begin(0, 100)
        try:
            for index, frame in enumerate(range(0, num_frames, step_size)):
                if (index % 100) == 0:
                    print(f"  {index}/{num_keyframes}")
                if show_progress and (index % 10) == 0:
                    wm.progress_update(index * 100 // num_keyframes)
                current_frame = index + 1
                current_pose = poses[frame].reshape(-1, 3)
                current_trans = trans[frame]
                for bone_index, bone_name in enumerate(spec.joint_names):
                    if bone_name == "pelvis":
                        # Keyframe pelvis location
                        if self.rest_position == "GROUNDED":
                            current_trans[1] = current_trans[1] - height_offset # SMPL-X local joint coordinates are Y-Up

                        armature.pose.bones[bone_name].location = Vector((current_trans[0], current_trans[1], current_trans[2]))
                        armature.pose.bones[bone_name].keyframe_insert('location', frame=current_frame)

                    # Keyframe bone rotation
                    pose_rodrigues = current_pose[bone_index]

                    if self.hand_reference == "FLAT":
                        set_pose_from_rodrigues(armature, bone_name, pose_rodrigues)
                    else:
                        # Relaxed hand pose uses different coordinate system for fingers
                        finger_names = ["index", "middle", "pinky", "ring", "thumb"]
                        if not any([x in bone_name for x in finger_names]):
                            set_pose_from_rodrigues(armature, bone_name, pose_rodrigues)
                        else:
                            # Finger rotations are relative to relaxed hand pose
                            hand_start_index = len(spec.joint_names) - 2 * spec.num_hand_joints
                            relaxed_hand_joint_index = bone_index - hand_start_index
                            pose_relaxed_rodrigues = self.hand_pose_relaxed[relaxed_hand_joint_index]
                            set_pose_from_rodrigues(armature, bone_name, pose_rodrigues, pose_relaxed_rodrigues)

                    armature.pose.bones[bone_name].keyframe_insert('rotation_quaternion', frame=current_frame)

                if self.keyframe_corrective_pose_weights:
                    # Calculate corrective poseshape weights for current pose and keyframe them.
                    # Note: This significantly increases animation load time and also reduces real-time playback speed in Blender viewport.
                    bpy.ops.object.smplx_set_poseshapes('EXEC_DEFAULT')
                    for key_block in obj.data.shape_keys.key_blocks:
                        if key_block.name.startswith("Pose"):
                            key_block.keyframe_insert("value", frame=current_frame)
        finally:
            if show_progress:
                wm.progress_end()

        if self.anim_format == "AMASS":
            # AMASS target floor is XY ground plane for SMPL-X template in OpenGL Y-up space (XZ ground plane).
            # Since SMPL-X Blender model is Z-up (and not Y-up) for rest/template pose, we need to adjust root node rotation to ensure that the resulting animated body is on Blender XY ground plane.
            bone_name = "root"
            if armature.pose.bones[bone_name].rotation_mode != 'QUATERNION':
                armature.pose.bones[bone_name].rotation_mode = 'QUATERNION'
            armature.pose.bones[bone_name].rotation_quaternion = Quaternion((1.0, 0.0, 0.0), radians(-90))
            armature.pose.bones[bone_name].keyframe_insert('rotation_quaternion', frame=1)

        print(f"  {num_keyframes}/{num_keyframes}")
        context.scene.frame_set(1)

        return {'FINISHED'}


classes = (
    SMPLXAddAnimation,
)
