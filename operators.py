import bpy
from bpy.types import Operator


class EMP_Template_OT_Operator(Operator):
    bl_idname = "node.addon_name_operator"
    bl_label = "Addon's operator baseclass"
    bl_options = {'REGISTER', 'UNDO_GROUPED'} 

    @classmethod
    def poll(cls, context):
        pass

    def execute(self, context):
        pass


classes = (
    EMP_Template_OT_Operator,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)