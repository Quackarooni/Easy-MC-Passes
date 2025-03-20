import bpy


def fetch_user_preferences(attr_id=None):
    prefs = bpy.context.preferences.addons[__package__].preferences

    if attr_id is None:
        return prefs
    else:
        return getattr(prefs, attr_id)


def get_addon_properties(context=None):
    if context is None:
        context = bpy.context
    
    try:
        return context.scene.EMP_Properties
    except AttributeError:
        return
    

def get_addon_property(prop_name, scene=None):
    if scene is None:
        scene = bpy.context.scene
    
    return getattr(scene.EMP_Properties, prop_name)


def clear_helper_datablocks():
    scenes = bpy.data.scenes

    for scene_name in ("EMP_Export_Passes", "EMP_Workbench_Cavity", "EMP_Shading_and_Shadows", "EMP_Cryptomatte", "EMP_Solo_Masks"):
        if scene_name in scenes:
            scenes.remove(scenes[scene_name])

    materials = bpy.data.materials    

    for mat_name in ("EMP_BlankMaterial",):
        if mat_name in materials:
            materials.remove(materials[mat_name])

    collections = bpy.data.collections

    for col in collections:
        if col.name.startswith("EMP_"):
            collections.remove(col)


def load_image(name, path, replace_existing=False):
    if replace_existing:
        images = bpy.data.images
        if name in images:
            images.remove(images[name])

    img = bpy.data.images.load(path)
    img.name = name

    return img


pass_link_map = {
    "Combined" : ("Main Passes", "Image"),
    "Color" : ("Main Passes", "DiffCol"),
    "Mist" : ("Main Passes", "Mist"),
    "Normal" : ("Main Passes", "Normal"),
    "Emission" : ("Main Passes", "Emit"),
    "Freestyle" : ("Main Passes", "Freestyle"),
    "Shading" : ("Shading Passes", "Combined_EMP_ShadingPass"),
    "Shadow" : ("Shading Passes", "Combined_EMP_ShadowPass"),
    "Cavity" : ("Cavity Pass", "Image"),
}


def link_pass_sockets(tree, render_pass):
    nodes = tree.nodes
    output_node1 = nodes["File Output (Images)"]
    output_node2 = nodes["File Output (EXR)"]
    pass_name = render_pass.name

    input_node, input_soc = pass_link_map[pass_name]
    input_node = nodes[input_node]

    tree.links.new(input_node.outputs[input_soc], output_node1.inputs[pass_name])
    tree.links.new(input_node.outputs[input_soc], output_node2.inputs[render_pass.exr_output_name])


def link_mask_sockets(tree, mask):
    nodes = tree.nodes
    output_node1 = nodes["File Output (Images)"]
    output_node2 = nodes["File Output (EXR)"]

    if not mask.invert:
        input_node = tree.nodes[mask.name]
        input_soc = "Alpha" if mask.solo else "Matte"
    else:
        input_node = tree.nodes[f"Invert_{mask.name}"]
        input_soc = 0

    tree.links.new(input_node.outputs[input_soc], output_node1.inputs[mask.name])
    tree.links.new(input_node.outputs[input_soc], output_node2.inputs[mask.exr_output_name])


def get_enabled_passes(collection):
    for render_pass in collection:
        if render_pass.render:
            yield render_pass


def get_mask_layers(selection_type=None):
    if selection_type is None:
        for layer in get_addon_property("mask_layers"):
            if layer.render:
                yield layer
    else:
        for layer in get_addon_property("mask_layers"):
            if layer.render and layer.selection_type == selection_type:
                yield layer


def add_node(tree, node_type, *_, **props):
    node = tree.nodes.new(node_type)

    for prop, value in props.items():
        setattr(node, prop, value)

    return node


def create_scene(base_scene=None, name="Scene", clear_tree=False):

    if base_scene is not None:
        new_scene = base_scene.copy()
    else:
        new_scene = bpy.data.scenes.new(name)
    
    new_scene.name = name
    new_scene.use_nodes = True
    
    if clear_tree:
        tree = new_scene.node_tree
        tree.nodes.clear()

    return new_scene


def create_file_outputs(node, outputs):
    slots = node.file_slots
    slots.clear()

    for output in outputs:
        slots.new(output.name)


def create_exr_outputs(node, outputs):
    slots = node.file_slots
    slots.clear()

    for output in outputs:
        slots.new(output.exr_output_name)


def get_multilayer_render_path():
    scene = bpy.data.scenes["EMP_Export_Passes"]
    output_node = scene.node_tree.nodes["File Output (EXR)"]
    scene.render.filepath = output_node.base_path
    scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"

    return scene.render.frame_path(frame=scene.frame_current)


def create_light(name, type, *_, **props):
    lights = bpy.data.lights
    light = lights.new(name, type)

    for prop, value in props.items():
        setattr(light, prop, value)

    return light


def create_collection(scene, name):
    collections = bpy.data.collections

    col = collections.new(name)
    scene.collection.children.link(col)
    return col


def create_solo_view_layers(scene):
    mask_view_layers = []

    for mask in get_mask_layers():
        if mask.solo:
            col = create_collection(scene, name=mask.view_layer_name)
            
            view_layer = scene.view_layers.new(mask.view_layer_name)
            view_layer.use_pass_combined = True
            mask_view_layers.append(view_layer)

            clear_passes(scene.render, view_layer)

            for obj in mask.solo_objects:
                if obj is not None:
                    col.objects.link(obj)

    for view_layer in mask_view_layers:
        for layer_col in view_layer.layer_collection.children:
            layer_col.exclude = (layer_col.name != view_layer.name)


def create_matte_masks(cryptomatte_scene, solo_scene, tree, masks, start_location):
    for i, mask in enumerate(masks):
        view_layer_name = mask.view_layer_name
        location = (start_location[0], start_location[1] - i*45)

        if mask.solo:
            node = add_node(tree, "CompositorNodeRLayers",
                name=mask.name, label=mask.name, scene=solo_scene, location=location)
            node.hide = True
        else:
            node = add_node(tree, "CompositorNodeCryptomatteV2",
                name=mask.name, label=mask.name, scene=cryptomatte_scene, location=location)
            node.hide = True

        if mask.invert:
            invert_node = add_node(tree, "CompositorNodeMath", name=f"Invert_{mask.name}", label="Invert", operation="SUBTRACT", location=location)
            invert_node.hide = True
            invert_node.location.x += 260.0
            invert_node.inputs[0].default_value = 1.0

            sock_name = "Alpha" if mask.solo else "Matte"
            tree.links.new(node.outputs[sock_name], invert_node.inputs[1])

        if mask.solo:
            node.layer = mask.view_layer_name
        else:
            node.layer_name = mask.layer_name(view_layer_name)
            node.matte_id = mask.matte_id


def set_standard_view_transform(scene):
    scene.display_settings.display_device = 'sRGB'
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1


def create_blank_material(name):
    blank_material = bpy.data.materials.new(name)
    blank_material.use_nodes = True

    tree = blank_material.node_tree
    tree.nodes.clear()

    diffuse_bdsf = add_node(tree, "ShaderNodeBsdfDiffuse", location=(-155.0, 60.5))
    material_output = add_node(tree, "ShaderNodeOutputMaterial", location=(15.0, 70.0))
    tree.links.new(diffuse_bdsf.outputs["BSDF"], material_output.inputs["Surface"])

    return blank_material


def clear_passes(render, view_layer):
    render.use_freestyle = False
    view_layer.use_freestyle = False
    
    view_layer.use_pass_combined = False
    view_layer.use_pass_z = False
    view_layer.use_pass_mist = False
    view_layer.use_pass_position = False
    view_layer.use_pass_normal = False
    view_layer.use_pass_vector = False
    view_layer.use_pass_uv = False
    view_layer.use_pass_object_index = False
    view_layer.use_pass_material_index = False
    view_layer.use_pass_diffuse_direct = False
    view_layer.use_pass_diffuse_indirect = False
    view_layer.use_pass_diffuse_color = False
    view_layer.use_pass_glossy_direct = False
    view_layer.use_pass_glossy_indirect = False
    view_layer.use_pass_glossy_color = False
    view_layer.use_pass_transmission_direct = False
    view_layer.use_pass_transmission_indirect = False
    view_layer.use_pass_transmission_color = False
    view_layer.use_pass_emit = False
    view_layer.use_pass_environment = False
    view_layer.use_pass_ambient_occlusion = False
    view_layer.use_pass_cryptomatte_object = False
    view_layer.use_pass_cryptomatte_material = False
    view_layer.use_pass_cryptomatte_asset = False
    
    if hasattr(view_layer, "cycles"):
        view_layer.cycles.denoising_store_passes = False
        view_layer.cycles.pass_debug_sample_count = False
        view_layer.cycles.use_pass_volume_direct = False
        view_layer.cycles.use_pass_volume_indirect = False
        view_layer.cycles.use_pass_shadow_catcher = False


def init_cavity_scene(scene):
    render = scene.render
    render.engine = 'BLENDER_WORKBENCH'
    render.use_freestyle = False
    scene.display.render_aa = '32' # Anti-aliasing Samples

    shading = scene.display.shading
    
    shading.show_backface_culling = False
    shading.show_xray = False
    shading.show_shadows = False
    shading.use_dof = False
    shading.show_specular_highlight = False

    shading.light = 'FLAT'
    shading.color_type = 'SINGLE'
    shading.single_color = (0.5, 0.5, 0.5)

    shading.show_cavity = True
    shading.cavity_type = 'SCREEN'
    shading.curvature_ridge_factor = 2.0
    shading.curvature_valley_factor = 0.0

    set_standard_view_transform(scene)


pass_name_map = {
    "Combined" : "use_pass_combined",
    "Z" : "use_pass_z",
    "Mist" : "use_pass_mist",
    "Position" : "use_pass_position",
    "Normal" : "use_pass_normal",
    "Vector" : "use_pass_vector",
    "UV" : "use_pass_uv",
    "Object index" : "use_pass_object_index",
    "Material index" : "use_pass_material_index",
    "Color" : "use_pass_diffuse_color",
    "Diffuse Direct" : "use_pass_diffuse_direct",
    "Diffuse Indirect" : "use_pass_diffuse_indirect",
    "Diffuse color" : "use_pass_diffuse_color",
    "Glossy Direct" : "use_pass_glossy_direct",
    "Glossy Indirect" : "use_pass_glossy_indirect",
    "Glossy Color" : "use_pass_glossy_color",
    "Transmission Direct" : "use_pass_transmission_direct",
    "Transmission Indirect" : "use_pass_transmission_indirect",
    "Transmission Color" : "use_pass_transmission_color",
    "Emission" : "use_pass_emit",
    "Environment" : "use_pass_environment",
    "Ambient Occlusion" : "use_pass_ambient_occlusion"
}

def add_pass(scene, pass_name):
    view_layer = scene.view_layers[0]

    if pass_name == "Freestyle":
        scene.render.use_freestyle = True
        view_layer.use_freestyle = True
        view_layer.freestyle_settings.as_render_pass = True
        
    else:
        setattr(view_layer, pass_name_map[pass_name], True)


def init_main_passes_scene(scene, passes):
    render = scene.render
    render.engine = 'CYCLES'

    view_layer = scene.view_layers[0]
    clear_passes(render, view_layer)

    for pass_name in passes:
        add_pass(scene, pass_name)


def init_shading_scene(scene):
    render = scene.render
    render.engine = 'CYCLES'

    view_layer = scene.view_layers[0]
    clear_passes(render, view_layer)
    
    shading_light_data = create_light(name="EMP_ShadingPass_Light", type='SUN', angle=0, use_shadow=False)
    shading_light_data.cycles.max_bounces = 0
    shadow_light_data = create_light(name="EMP_ShadowPass_Light", type='SUN', angle=0)
    shadow_light_data.cycles.max_bounces = 0

    light_direction = get_addon_property("light_direction")

    objects = bpy.data.objects
    shading_light = objects.new(name="EMP_ShadingPass_Light", object_data=shading_light_data)
    shadow_light = objects.new(name="EMP_ShadowPass_Light", object_data=shadow_light_data)
    shading_light.rotation_euler = light_direction
    shadow_light.rotation_euler = light_direction
    scene.collection.objects.link(shading_light)
    scene.collection.objects.link(shadow_light)

    lightgroups = view_layer.lightgroups
    shading_light_group = lightgroups.add(name="EMP_ShadingPass")
    shadow_light_group = lightgroups.add(name="EMP_ShadowPass")

    shading_light.lightgroup = shading_light_group.name
    shadow_light.lightgroup = shadow_light_group.name

    blank_material = create_blank_material("EMP_BlankMaterial")
    view_layer.material_override = blank_material

    set_standard_view_transform(scene)

    depsgraph = bpy.context.evaluated_depsgraph_get() 
    depsgraph.update()


def init_cryptomatte_scene(scene):
    render = scene.render
    view_layer = scene.view_layers[0]

    object_masks = tuple(get_mask_layers(selection_type="OBJECT"))
    material_masks = tuple(get_mask_layers(selection_type="MATERIAL"))
    collection_masks = tuple(get_mask_layers(selection_type="COLLECTION"))
    
    clear_passes(render, view_layer)

    if len((*object_masks, *collection_masks)) > 0:
        view_layer.use_pass_cryptomatte_object = True

    if len(material_masks) > 0:
        view_layer.use_pass_cryptomatte_material = True

    set_standard_view_transform(scene)
    apply_mask_scene_settings(scene)


def init_solo_scene(scene):
    render = scene.render
    view_layer = scene.view_layers[0]
    active_camera = bpy.context.scene.camera
    
    clear_passes(render, view_layer)
    scene.collection.objects.link(active_camera)
    scene.camera = active_camera

    scene.render.film_transparent = True
    apply_mask_scene_settings(scene)

    active_scene = bpy.context.scene
    scene.cycles.feature_set = active_scene.cycles.feature_set
    scene.cycles.device = active_scene.cycles.device


def get_prop_name(data, prop_name):
    return data.__annotations__[prop_name].keywords["name"] 


def ui_draw_enum_prop(layout, data, prop_name):
    col = layout.column()
    col.label(text=f"{get_prop_name(data, prop_name)}:")
    col.prop(data, prop_name, text="")


def apply_mask_scene_settings(scene):
    engine = get_addon_property("mask_engine")
    scene.render.engine = engine
    scene.display.render_aa = '32'

    scene.eevee.taa_render_samples = 16
    scene.cycles.samples = 16

    # Disable depth-of-field if engine is EEVEE
    # since it is incompatible with cryptomatte
    scene.eevee.bokeh_max_size = 0