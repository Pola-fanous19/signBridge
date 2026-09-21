from .constants import SHAPEKEY_VALUE_RANGE


# Ensure that we have valid slider ranges
# This is needed for imported FBX files where the default range could be at default [0,1] for some shape keys after import
def smplx_ensure_valid_shapekey_slider_ranges(skinned_mesh):
    update_slider_ranges = False
    for key_name in ["Shape000", "Exp000", "Pose000"]:
        if key_name in skinned_mesh.data.shape_keys.key_blocks:
            key_block = skinned_mesh.data.shape_keys.key_blocks[key_name]
            if (key_block.slider_min > -SHAPEKEY_VALUE_RANGE) or (key_block.slider_max < SHAPEKEY_VALUE_RANGE):
                update_slider_ranges = True
                break

    if update_slider_ranges:
        for index, key_block in enumerate(skinned_mesh.data.shape_keys.key_blocks):
            if index == 0:
                continue # skip Base shape key

            key_block.slider_min = -SHAPEKEY_VALUE_RANGE
            key_block.slider_max = SHAPEKEY_VALUE_RANGE
