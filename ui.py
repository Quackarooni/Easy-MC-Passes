import bpy
from bpy.types import Panel


class EMP_PT_PASS_MANAGER(Panel):
    bl_label = "Pass Manager"
    bl_space_type = 'VIEW_3D'
    bl_region_type = "UI"
    bl_category = "Easy MC Passes"

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout
        layout.label(text="This is a test label.")


classes = (
    EMP_PT_PASS_MANAGER,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)