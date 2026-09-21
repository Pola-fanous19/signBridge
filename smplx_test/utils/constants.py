import tomllib
from pathlib import Path

SHAPEKEY_VALUE_RANGE = 10

ADDON_ROOT = Path(__file__).resolve().parent.parent

with (ADDON_ROOT / "blender_manifest.toml").open("rb") as _f:
    ADDON_VERSION = tomllib.load(_f)["version"]
