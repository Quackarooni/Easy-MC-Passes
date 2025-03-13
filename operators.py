import bpy
from bpy.types import Operator

from . import utils
from .utils import (
    add_node, 
    create_matte_masks,
    get_addon_property,
    get_mask_layers,
    get_multilayer_render_path,
    link_mask_sockets,
    link_pass_sockets,
    load_image,
    create_scene, 
    create_file_outputs, 
    init_main_passes_scene, 
    init_cavity_scene, 
    init_cryptomatte_scene,
    init_shading_scene
    )


render_screen = []


class EMP_OT_EXPORT_PASSES(Operator):
    bl_idname = "render.emp_export_passes"
    bl_label = "Export Passes"
    bl_options = {'REGISTER'} 

    @classmethod
    def poll(cls, context):
        outputs = (*get_addon_property("render_passes"), *get_addon_property("mask_layers"))

        any_passes_enabled = any(i.render for i in outputs)
        return any_passes_enabled

    def execute(self, context):
        scene = context.scene
        scenes = context.blend_data.scenes

        export_path = get_addon_property("export_path")

        collection = get_addon_property("render_passes")
        passes = tuple(utils.get_enabled_passes(collection))
        names = tuple(i.name for i in passes)
        main_passes = tuple(i.name for i in passes if i.name not in {"Shading", "Shadow", "Cavity"})
        
        object_masks = tuple(get_mask_layers(selection_type="OBJECT"))
        material_masks = tuple(get_mask_layers(selection_type="MATERIAL"))

        for scene_name in ("EMP_Export_Passes", "EMP_Workbench_Cavity", "EMP_Shading_and_Shadows", "EMP_Cryptomatte"):
            if scene_name in scenes:
                scenes.remove(scenes[scene_name])

        scenes = context.blend_data.scenes
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

        if len((*object_masks, *material_masks)) > 0:
            crpytomatte_scene = create_scene(scene, "EMP_Cryptomatte", clear_tree=True)
            init_cryptomatte_scene(crpytomatte_scene, object_masks, material_masks)
            create_matte_masks(crpytomatte_scene, tree, object_masks, mask_type="OBJECT", start_location=(0.0, -150.0))
            create_matte_masks(crpytomatte_scene, tree, material_masks, mask_type="MATERIAL",start_location=(500.0, -150.0))

        object_mask_names = (m.name for m in object_masks)
        material_mask_names = (m.name for m in material_masks)
        output_names = (*names, *object_mask_names, *material_mask_names)

        create_file_outputs(output_node, outputs=output_names)
        create_file_outputs(exr_output_node, outputs=output_names)

        for render_pass in passes:
            link_pass_sockets(tree, render_pass.name)
        
        for mask in (*object_masks, *material_masks):
            link_mask_sockets(tree, mask)

        return {'FINISHED'}
        bpy.ops.render.render('INVOKE_SCREEN', scene=main_scene.name)

        # context.scene disappears when invoked in the handler
        # so temporarily store it in a list that can be called by the handler
        render_screen.append(context.screen)
        bpy.app.handlers.render_complete.append(load_multilayer_image)
        return {'FINISHED'}


def load_multilayer_image(*args, **kwargs):
    filepath = get_multilayer_render_path()
    img = load_image(name="EMP_Render Result", path=filepath, replace_existing=True)

    screen = render_screen.pop(0)
    for area in screen.areas:
        if area.type == 'IMAGE_EDITOR':
            area.spaces.active.image = img

    bpy.app.handlers.render_complete.remove(load_multilayer_image)


classes = (
    EMP_OT_EXPORT_PASSES,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)