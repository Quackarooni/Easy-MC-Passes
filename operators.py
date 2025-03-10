import bpy
from bpy.types import Operator

from . import utils

class EMP_OT_EXPORT_PASSES(Operator):
    bl_idname = "render.emp_export_passes"
    bl_label = "Export Passes"
    bl_options = {'REGISTER'} 

    @classmethod
    def poll(cls, context):
        any_passes_enabled = any(i.render for i in context.scene.EMP_render_passes)
        return any_passes_enabled

    def execute(self, context):
        collection = context.scene.EMP_render_passes
        passes = utils.get_enabled_passes(collection)

        return {'FINISHED'}


classes = (
    EMP_OT_EXPORT_PASSES,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)