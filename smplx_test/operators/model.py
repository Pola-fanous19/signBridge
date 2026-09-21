import bpy
import numpy as np

from ..utils.constants import ADDON_ROOT
from ..utils.model_spec import MODELS, is_variant_installed, resolve_variant_key


class SMPLXAddGender(bpy.types.Operator):
    bl_idname = "scene.smplx_add_gender"
    bl_label = "Add"
    bl_description = ("Add body model of selected gender to scene")
    bl_options = {'REGISTER', 'UNDO'}

    uv_2023 = None

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if in Object Mode
            if (context.active_object is None) or (context.active_object.mode == 'OBJECT'):
                return True
            else:
                return False
        except: return False

    def execute(self, context):
        wm = context.window_manager
        gender = wm.smplx_tool.smplx_gender
        spec = MODELS[wm.smplx_tool.body_model]
        variant = resolve_variant_key(spec, wm.smplx_tool)

        if not is_variant_installed(spec, variant):
            self.report({'ERROR'}, f"Body model file not installed: {spec.blend_files.get(variant, '?')}")
            return {'CANCELLED'}

        print(f"Adding {spec.display_name} ({gender})")

        model_file = spec.blend_files[variant]
        objects_path = ADDON_ROOT / "data" / model_file / "Object"
        object_name = spec.mesh_name_template.format(gender=gender)

        bpy.ops.wm.append(filename=object_name, directory=str(objects_path))

        # Select imported mesh
        object_name = context.selected_objects[0].name
        bpy.ops.object.select_all(action='DESELECT')
        context.view_layer.objects.active = bpy.data.objects[object_name]
        bpy.data.objects[object_name].select_set(True)
        obj = bpy.context.active_object

        obj["body_model"] = spec.id

        if spec.handposes_file:
            bpy.ops.object.smplx_set_handpose('EXEC_DEFAULT')

        if spec.has_uv_variants:
            uv_version = wm.smplx_tool.smplx_uv
            print(f"UV map: {uv_version}")
            obj["smplx_uv"] = uv_version

            if uv_version == "UV_2023":
                if self.uv_2023 is None:
                    uv_npz_path = ADDON_ROOT / "data" / "smplx_uv_2023.npz"
                    with np.load(uv_npz_path) as data:
                        self.uv_2023 = data["uv_coordinates"]

                uv_map = obj.data.uv_layers.active.data
                for i, face in enumerate(obj.data.polygons):
                    for j, loop_index in enumerate(face.loop_indices):
                        uv_map[loop_index].uv = self.uv_2023[i * len(face.loop_indices) + j]

        return {'FINISHED'}


class SMPLXSetTexture(bpy.types.Operator):
    bl_idname = "object.smplx_set_texture"
    bl_label = "Set"
    bl_description = ("Set selected texture")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if in active object is mesh
            if (context.object.type == 'MESH'):
                return True
            else:
                return False
        except: return False

    def execute(self, context):
        texture = context.window_manager.smplx_tool.smplx_texture
        print("Setting texture: " + texture)

        obj = bpy.context.object
        if (len(obj.data.materials) == 0) or (obj.data.materials[0] is None):
            self.report({'WARNING'}, "Selected mesh has no material: %s" % obj.name)
            return {'CANCELLED'}

        mat = obj.data.materials[0]
        links = mat.node_tree.links
        nodes = mat.node_tree.nodes

        # Find texture node
        node_texture = None
        for node in nodes:
            if node.type == 'TEX_IMAGE':
                node_texture = node
                break

        # Find shader node
        node_shader = None
        for node in nodes:
            if node.type.startswith('BSDF'):
                node_shader = node
                break

        if texture == 'NONE':
            # Unlink texture node
            if node_texture is not None:
                for link in node_texture.outputs[0].links:
                    links.remove(link)

                nodes.remove(node_texture)

                # 3D Viewport still shows previous texture when texture link is removed via script.
                # As a workaround we trigger desired viewport update by setting color value.
                node_shader.inputs[0].default_value = node_shader.inputs[0].default_value
        else:
            if node_texture is None:
                node_texture = nodes.new(type="ShaderNodeTexImage")

            if (texture == 'UV_GRID') or (texture == 'COLOR_GRID'):
                if texture not in bpy.data.images:
                    bpy.ops.image.new(name=texture, generated_type=texture)
                image = bpy.data.images[texture]
            else:
                if texture not in bpy.data.images:
                    texture_path = ADDON_ROOT / "data" / texture
                    image = bpy.data.images.load(str(texture_path))
                else:
                    image = bpy.data.images[texture]

            node_texture.image = image

            # Link texture node to shader node if not already linked
            if len(node_texture.outputs[0].links) == 0:
                links.new(node_texture.outputs[0], node_shader.inputs[0])

        # Switch viewport shading to Material Preview to show texture
        if bpy.context.space_data:
            if bpy.context.space_data.type == 'VIEW_3D':
                bpy.context.space_data.shading.type = 'MATERIAL'

        return {'FINISHED'}


classes = (
    SMPLXAddGender,
    SMPLXSetTexture,
)
