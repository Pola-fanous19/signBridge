# Changelog for SMPL-X Blender Extension Add-on
+ 20210505: Initial release
+ 20210525: Replace vertices-to-joints regressor with betas-to-joints regressor. Add rainbow texture (CC BY-NC 4.0).
+ 20210611: Add option to set shape from height and weight values for female and male models
+ 20210629: Add option to create animated body from AMASS SMPL-X animation file
+ 20220117: Add option to set height+weight for neutral SMPL-X model
+ 20220218: Add option to set animation target framerate. Lower values will speed up import time.
+ 20220311:
  + Fix pelvis location offset when importing AMASS animations
  + Add option to set animation import format (AMASS, SMPL-X)
  + Adjust Blender Timeline end frame when adding first animation
  + Use 30fps as new default target framerate
  + Add Alembic export button
+ 20220315:
  + Speed up animation import time
+ 20220326:
  + Add Unreal FBX export. Shape keys bake options can now be found in export dialog settings.
  + Fix unwanted duplicated animation sequence in FBX export
+ 20220623:
  + Add option to import animation onto grounded rest pose armature
  + Disable animation keyframe simplification for FBX export so that FBX animations match Alembic animations
  + Add support for 300 beta shape model
+ 20230120:
  + Add option to use relaxed hand reference frame when adding animation from file
+ 20230302:
  + Add SMPL-X locked head (no head bun) model and option to choose between v1.1 and locked head
    + Setting shape from height and weight is only correct for v1.1 model
  + The locked head (no head bun) model is the new default option
    + Use this model for AMASS animations
    + Python scripts which want to use v1.1 model need to update the code to select v1.1 model
  + Use models with 100 expressions
  + Use custom properties on mesh object to store version and gender for internal processing instead of depending on proper object name tags
+ 20240206:
  + Add support for UV map 2023 version and corresponding female/male sample textures
  + UV map 2023 is new default
+ 20240408:
  + Add option to export shape values (and optional bind pose height offset) to .npz
    + If animation was imported with grounded bind pose, the applied height offset change is stored as object property so that it can later be exported in the shape-only npz as `bind_pose_height_offset` key. This is needed to be able to later remap grounded bind pose animations to standard bind pose animations.
      + If body shape was created via shape key modification, then the offset result from SnapToGroundPlane is stored. Armature must be in default pose for correct SnapToGroundPlane height offset calculation.
+ 20240418:
  + Fix rainbow texture dark areas at vertices 4146 and 6553
+ 20241129:
  + Save custom properties when using "Export FBX" so that add-on can also be used for reimported SMPL-X FBX files
  + Ensure valid shape key slider ranges so that add-on can also be used for reimported SMPL-X FBX files where initial range is [0, 1]
  + Add new blend shape export option to FBX export for exporting only pose corrective blend shapes
    + bakes current body shape and expression into mesh, keeps all pose correctives
+ 20260402:
  + Add Blender 5.0 support for FBX Unreal animation export
+ 20260410:
  + Add FBX export option to export only animation without mesh (default: off)
+ 20260423:
  + Refactor legacy add-on code into subfolders and use new extension add-on definition introduced with Blender 4.2
  + Show status of installed body models in preferences panel (Edit>Preferences>Add-ons>SMPL-X for Blender)
  + Show cursor-based progress indicator when adding .npz animation
+ 20260505 (1.0.0):
  + Add support for SMPL+H model (female/male)
  + Rename sidebar to "SMPL Models"
  + Hide UI panels which are not available for currently selected model object
  + Remove deprecated SMPL-X v1.1 10-betas-to-joints regressors
  + Only allow adding a body model to the current scene if the model is available in data/ folder
    + SMPL-X locked head default model will be included in official add-on distribution
    + SMPL-X v1.1 is now an optional DLC install available at https://smpl-x.is.tue.mpg.de/
    + SMPL+H is an optional DLC install available at https://mano.is.tue.mpg.de/
+ 20260507 (1.0.1):
  + Add options to set UV2023 and UV2021 sample textures for SMPL+H
+ 20260508 (1.0.2):
  + Fix progress indicator error when loading very short animations
+ 20260511 (1.0.3):
  + Use new SMPL+H DLC (20260511) with 300 shape components and female/male/neutral model versions
