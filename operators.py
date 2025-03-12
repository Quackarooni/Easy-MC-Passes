import bpy
from bpy.types import Operator

from . import utils
from .utils import add_node, get_collection_property, get_export_path, link_pass_sockets, create_scene, create_file_outputs, init_main_passes_scene, init_cavity_scene, init_shading_scene


class EMP_OT_EXPORT_PASSES(Operator):
    bl_idname = "render.emp_export_passes"
    bl_label = "Export Passes"
    bl_options = {'REGISTER'} 

    @classmethod
    def poll(cls, context):
        any_passes_enabled = any(i.render for i in get_collection_property(context))
        return any_passes_enabled

    def execute(self, context):
        scene = context.scene
        scenes = context.blend_data.scenes

        export_path = get_export_path(context)

        collection = get_collection_property(context)
        passes = tuple(utils.get_enabled_passes(collection))
        names = tuple(i.name for i in passes)
        main_passes = tuple(i.name for i in passes if i.name not in {"Shading", "Shadow", "Cavity"})

        for scene_name in ("EMP_Export_Passes", "EMP_Workbench_Cavity", "EMP_Shading_and_Shadows"):
            if scene_name in scenes:
                scenes.remove(scenes[scene_name])

        main_scene = create_scene(scene, "EMP_Export_Passes", clear_tree=True)
        init_main_passes_scene(main_scene, passes=main_passes)

        tree = main_scene.node_tree
        output_node = add_node(tree, "CompositorNodeOutputFile", name="File Output (Images)", base_path=export_path, width=360, location=(500.0, 450.0))
        exr_output_node = add_node(tree, "CompositorNodeOutputFile", name="File Output (EXR)", base_path=export_path + "Multilayer", width=360, location=(500.0, 160.0))
        exr_output_node.format.file_format = "OPEN_EXR_MULTILAYER"

        main_passes_node = add_node(tree, "CompositorNodeRLayers", name="Main Passes", location=(0.0, 450.0))
        main_passes_node.scene = main_scene

        if ("Shading" in names) or ("Shadow" in names):
            shading_scene = create_scene(scene, "EMP_Shading_and_Shadows", clear_tree=True)
            init_shading_scene(shading_scene)

            shading_passes_node = add_node(tree, "CompositorNodeRLayers", name="Shading Passes", location=(0.0, 160.0))
            shading_passes_node.scene = shading_scene

        if ("Cavity" in names):
            cavity_scene = create_scene(scene, "EMP_Workbench_Cavity", clear_tree=True)
            init_cavity_scene(cavity_scene)

            cavity_pass_node = add_node(tree, "CompositorNodeRLayers", name="Cavity Pass", location=(0.0, -60.0))
            cavity_pass_node.scene = cavity_scene

        create_file_outputs(output_node, outputs=names)
        create_file_outputs(exr_output_node, outputs=names)

        for render_pass in passes:
            link_pass_sockets(tree, render_pass.name)

        bpy.ops.render.render('INVOKE_SCREEN', scene=main_scene.name)
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