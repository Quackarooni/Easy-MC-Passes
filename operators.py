import bpy
from bpy.types import Operator

import os
from pathlib import Path

from . import utils
from .utils import (
    add_node, 
    create_matte_masks,
    clear_helper_datablocks,
    fetch_user_preferences,
    get_addon_property,
    get_mask_layers,
    get_multilayer_render_path,
    link_mask_sockets,
    link_pass_sockets,
    load_image,
    create_scene, 
    create_solo_view_layers,
    create_file_outputs, 
    create_file_masks,
    create_exr_outputs,
    init_main_passes_scene, 
    init_cavity_scene, 
    init_cryptomatte_scene,
    init_shading_scene,
    init_solo_scene
    )


render_screen = []
multilayer_export_path = ""


class EMP_OT_EXPORT_PASSES(Operator):
    bl_idname = "render.emp_export_passes"
    bl_label = "Export Passes"
    bl_description = "Render enabled passes & masks and export them as images"
    bl_options = {'REGISTER'} 

    @classmethod
    def poll(cls, context):
        outputs = (*get_addon_property("render_passes"), *get_addon_property("mask_layers"))
        any_passes_enabled = any(i.render for i in outputs)

        is_engine_valid = context.scene.render.engine in {'BLENDER_EEVEE_NEXT', 'CYCLES'}

        return any_passes_enabled and is_engine_valid

    def execute(self, context):
        scene = context.scene

        export_path = get_addon_property("export_path")
        prefs = fetch_user_preferences()

        collection = get_addon_property("render_passes")
        passes = tuple(utils.get_enabled_passes(collection))
        masks = tuple(get_mask_layers())

        names = tuple(i.name for i in passes)
        main_passes = tuple(i.name for i in passes if i.name not in {"Shading", "Shadow", "Cavity"})
        
        clear_helper_datablocks()

        main_scene = create_scene(scene, "EMP_Export_Passes", clear_tree=True)
        init_main_passes_scene(main_scene, passes=main_passes)

        tree = main_scene.node_tree
        output_node = add_node(tree, "CompositorNodeOutputFile", name="File Output (Images)", base_path=export_path, width=360, location=(500.0, 450.0))
        output_node.file_slots.clear()

        if prefs.view_passes_after_render:
            exr_output_node = add_node(tree, "CompositorNodeOutputFile", name="File Output (EXR)", base_path=export_path + "Multilayer", width=360, location=(500.0, 160.0))
            exr_output_node.format.file_format = "OPEN_EXR_MULTILAYER"
            exr_output_node.file_slots.clear()

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

        if len(masks) > 0:
            cryptomatte_scene = create_scene(scene, "EMP_Cryptomatte", clear_tree=True)
            init_cryptomatte_scene(cryptomatte_scene)
            
            solo_scene = create_scene(name="EMP_Solo_Masks", clear_tree=True)
            init_solo_scene(solo_scene)
            create_solo_view_layers(solo_scene)

            create_matte_masks(cryptomatte_scene, solo_scene, tree, masks, start_location=(-320.0, -400.0))

        create_file_outputs(output_node, passes)
        create_file_masks(output_node, masks)

        if prefs.view_passes_after_render:
            create_exr_outputs(exr_output_node, (*passes, *masks))

        for render_pass in passes:
            link_pass_sockets(tree, render_pass)
        
        for mask in masks:
            link_mask_sockets(tree, mask)

        if prefs.view_passes_after_render:
            bpy.ops.render.render('INVOKE_SCREEN', scene=main_scene.name)
            # context.scene disappears when invoked in the handler
            # so temporarily store it in a list that can be called by the handler
            render_screen.append(context.screen)
            
            global multilayer_export_path    
            multilayer_export_path = get_multilayer_render_path()

            bpy.app.handlers.render_complete.append(load_multilayer_image)
            return {'FINISHED'}
        else:
            op_mode = 'INVOKE_SCREEN' if prefs.force_render_window else 'EXEC_SCREEN'
            bpy.ops.render.render(op_mode, scene=main_scene.name)
            self.report({'INFO'}, f"Successfully exported files at \"{export_path}\"")
            return {'FINISHED'}


def load_multilayer_image(*args, **kwargs):
    img = load_image(name="EMP_Render Result", path=multilayer_export_path, replace_existing=True)

    screen = render_screen.pop(0)
    for area in screen.areas:
        if area.type == 'IMAGE_EDITOR':
            area.spaces.active.image = img

    bpy.app.handlers.render_complete.remove(load_multilayer_image)
    bpy.app.timers.register(clear_helper_datablocks, first_interval=0.1)


class EMP_OT_OPEN_FILE_EXPLORER(Operator):
    bl_idname = "render.emp_open_file_explorer"
    bl_label = "Open in File Explorer"
    bl_description = "Open the specified export path in your system's file explorer"
    bl_options = {'REGISTER', 'INTERNAL'} 

    @classmethod
    def poll(cls, context):
        export_path = bpy.path.abspath(get_addon_property("export_path"))
        return Path(export_path).exists()

    def execute(self, context):
        export_path = bpy.path.abspath(get_addon_property("export_path"))
        os.startfile(export_path)
        return {'FINISHED'}


classes = (
    EMP_OT_EXPORT_PASSES,
    EMP_OT_OPEN_FILE_EXPLORER,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)