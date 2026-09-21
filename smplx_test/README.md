# SMPL-X Blender Add-on

This add-on allows you to add [SMPL-X](https://smpl-x.is.tue.mpg.de) or [SMPL+H](https://mano.is.tue.mpg.de/) body models as skinned meshes to your current Blender scene. Each mesh consists of a shape specific rig, as well as shape keys (blend shapes) for shape, expression (SMPL-X) and pose correctives.

+ Requirements: Blender 4.5+, tested with 4.5.8 and 5.1.1
+ Additional dependencies: None
+ Supported body models:
  + SMPL-X
    + SMPL-X locked head (no head bun)
      + default model, bundled in add-on release
    + SMPL-X v1.1 (optional)
      + available as DLC on [SMPL-X Website](https://smpl-x.is.tue.mpg.de)
    + 300 shape components, 100 expression components
    + female/male/neutral

  + SMPL+H (optional)
    + available as DLC on [MANO Website](https://mano.is.tue.mpg.de/)
    + 300 shape components, no expression components
    + female/male/neutral
    + backwards compatible with SMPL model

## Features
+ Add female/male/neutral SMPL-X/SMPL+H mesh to current scene
+ Set sample albedo texture
+ Set body shape from height and weight measurements (SMPL-X)
+ Randomize/reset shape
+ Update joint locations
+ Position feet on ground plane (z=0)
+ Randomize/reset face expression shape (SMPL-X)
+ Enable/disable pose correctives
+ Change hand pose (flat, relaxed)
+ Write current pose in SMPL-X rotation vector (theta) notation to console
+ Load SMPL-X pose from .pkl file
    + Format: Full body pose with 55 joints in Rodrigues notation
    + Over 3000 sample poses are available at https://agora.is.tuebingen.mpg.de/
        + Sign In > Download > Ground Truth Fittings > SMPL-X fits
+ Create animated body from SMPL-X/SMPL+H animation .npz file (AMASS or SMPL-X orientation)
    + SMPL-X: Use "Locked Head" model version when working with animation files from AMASS
+ Alembic (.abc) export of animated body as animated vertex geometry cache
    + Keyframed pose correctives are always baked into the vertices on export
    + Alembic animation can be imported into other third-party tools
        + Unreal Engine
            + Alembic Import settings: Geometry Cache, Scale (100, -100, 100), Rotation (90, 0, 0)
    + We recommend latest Blender release for up-to-date Alembic format support
+ FBX export
    + Export to Unity or Unreal Engine
        + Imported FBX will import in Unity/Unreal without rotations and without scaling
    + Shape key export options:
        + Body shape and pose correctives
        + Body shape without pose correctives
        + None (bakes current body shape into mesh, removes all pose correctives)
        + Pose correctives only (bakes current body shape and expression into mesh, keeps all shape keys for pose correctives)

## Installation
1. Register at https://smpl-x.is.tue.mpg.de and download the SMPL-X for Blender add-on. The ZIP release file will include the required SMPL-X (locked head) model which is not included in the code repository.
2. If you already used older versions of the add-on: Uninstall previously installed versions of this extension add-on or legacy add-on in Blender and restart Blender
3. Blender>Edit>Preferences>Get Extensions>Install from Disk [[Reference](https://docs.blender.org/manual/en/latest/editors/preferences/extensions.html)]
4. Select downloaded `SMPL-X for Blender` add-on ZIP file (`smplx_blender_addon-*.zip`) and install
5. Check in Blender>Edit>Preferences>Add-ons that `SMPL-X for Blender` add-on is enabled. The preferences panel will show you the status of the installed body models.
6. Enable sidebar in 3D Viewport>View>Sidebar
7. All add-on functions are available in `SMPL Models` tab of sidebar

### Installation of Optional Body Model DLC
+ Download `SMPL-X Blender Add-on DLC` zip files
  + SMPL-X v1.1: https://smpl-x.is.tue.mpg.de
    + `smplx_blender_addon_dlc_smplx1.1-*.zip`
  + SMPL+H: https://mano.is.tue.mpg.de
    + `smplx_blender_addon_dlc_smplh-*.zip`
+ Extract all data files (.blend/.json) contained in ZIP `smplx_blender_addon/data/` folder to Blender add-on `data/` folder of installed plugin
  + Add-on folder root path is listed in Blender>Preferences>Get Extensions>SMPL-X for Blender>Path
  + Example path for Windows 11 Blender 4.5:
    + `%APPDATA%\Blender Foundation\Blender\4.5\extensions\user_default\smplx_blender_addon\data`
+ Restart Blender and check in Blender>Preferences>Add-ons>`SMPL-X for Blender` that models are installed

## Usage
+ [Short overview video](https://www.youtube.com/watch?v=DY2k29Jef94)
+ [CVPR 2021 tutorial video](https://www.youtube.com/watch?v=m8i00zG6mZI&t=107s)

## Notes
+ If you work with multiple models in one scene, then only the add-on GUI model section (type, body) will update to reflect the state of the newly selected SMPL-X/SMPL+H model mesh
+ To maintain editor responsiveness the add-on does not automatically recalculate joint locations when you change the shape manually via Blender shape keys. Use the `Update Joint Locations` button to update the joint locations after a manual shape key weight change.
+ To maintain editor responsiveness, the add-on does not automatically recalculate the corrective pose shape keys when you change the armature pose. Use the `Update Pose Shapes` button to update the pose corrective shape key weights after pose changes.
+ Setting shape from height and weight should be used with the v1.1 model for best results
+ This add-on supports both `locked head (no head bun)` and `v1.1 (head bun)` SMPL-X model versions. Make sure to select the correct SMPL-X version before using the AddAnimation option.
  + Always use `locked head` when working with AMASS animations
+ Use the following FBX importer settings when re-importing Unreal FBX files into Blender which were exported with the "Export FBX" button of this add-on:
  + Scale: 0.01
  + Animation>Offset: 0

## Known Issues
+ The new C++ Blender FBX importer (`bpy.ops.wm.fbx_import`) does not correctly set slider ranges for all imported shape keys
  + This can be observed by importing an Unreal FBX with keyframed pose correctives which was exported with `Export FBX` button. You will then see orange shape keys for strong joint bend poses, which indicate that the default range of [0, 1] is used. This will then clamp negative values to 0.
  + Issue validated in Blender 4.5.8 and 5.1.1
  + We recommend using the legacy FBX importer (`bpy.ops.import_scene.fbx`) which does not have this issue

## License
+ See [LICENSE.md](LICENSE.md) for further license information including commercial licensing

+ Generated SMPL-X body mesh data using this add-on:
  + Licensed under SMPL-X Model or Body License, depending on use case
    + https://smpl-x.is.tue.mpg.de/modellicense.html
    + https://smpl-x.is.tue.mpg.de/bodylicense.html

  + Attribution for publications:
    + You agree to cite the most recent paper describing the model as specified on the SMPL-X website: https://smpl-x.is.tue.mpg.de

## Acknowledgements
+ We thank [Meshcapade](https://meshcapade.com/) for providing the SMPL-X female/male sample textures under [Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)](https://creativecommons.org/licenses/by-nc/4.0/) license.

+ Sergey Prokudin (rainbow texture data)

+ Vassilis Choutas (betas-to-joints regressor)

+ Lea Müller and Vassilis Choutas (measurements-to-betas regressor)

## Changelog
See [CHANGELOG.md](CHANGELOG.md) for the full version history.

## Contact
+ smplx-blender@tue.mpg.de
