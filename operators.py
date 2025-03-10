import bpy
from bpy.types import Operator

from . import utils
from .utils import add_node, copy_scene, create_file_outputs, init_cavity_scene


class EMP_OT_EXPORT_PASSES(Operator):
    bl_idname = "render.emp_export_passes"
    bl_label = "Export Passes"
    bl_options = {'REGISTER'} 

    @classmethod
    def poll(cls, context):
        any_passes_enabled = any(i.render for i in context.scene.EMP_render_passes)
        return any_passes_enabled

    def execute(self, context):
        scene = context.scene
        main_scene = copy_scene(scene, "EMP_Export_Passes")
        cavity_scene = copy_scene(scene, "EMP_Workbench_Cavity")
        shading_scene = copy_scene(scene, "EMP_Shading_and_Shadows")

        init_cavity_scene(cavity_scene)

        collection = scene.EMP_render_passes
        passes = utils.get_enabled_passes(collection)

        tree = context.scene.node_tree

        output_node = add_node(tree, "CompositorNodeOutputFile", width=360)
        exr_output_node = add_node(tree, "CompositorNodeOutputFile", width=360)
        exr_output_node.format.file_format = "OPEN_EXR_MULTILAYER"

        names = tuple(i.name for i in passes)
        create_file_outputs(output_node, outputs=names)
        create_file_outputs(exr_output_node, outputs=names)

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