"""Sync SMPLX_PT_Model 'add' controls to the active body model on selection.

Subscribes to ``(LayerObjects, "active")`` via msgbus so the panel mirrors the
active SMPL mesh (e.g. selecting a SMPL+H mesh flips body_model to ``"smplh"``
and hides the SMPL-X-only smplx_version / smplx_uv rows). The sync is one-shot
on selection — the user can still change dropdowns afterwards to add a
different model.
"""

import bpy
from bpy.app.handlers import persistent

from ..utils.model_spec import sync_tool_to_active

_owner = object()  # msgbus owner sentinel


def _on_active_changed():
    sync_tool_to_active(bpy.context)


def _subscribe():
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.LayerObjects, "active"),
        owner=_owner,
        args=(),
        notify=_on_active_changed,
    )


@persistent
def _on_load_post(_dummy):
    # msgbus subscriptions are wiped on file load.
    _subscribe()
    sync_tool_to_active(bpy.context)


def register():
    _subscribe()
    if _on_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_load_post)
    # Cover case of enabling addon with a body model mesh already selected
    sync_tool_to_active(bpy.context)


def unregister():
    if _on_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load_post)
    bpy.msgbus.clear_by_owner(_owner)
