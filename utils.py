import bpy


def fetch_user_preferences(attr_id=None):
    prefs = bpy.context.preferences.addons[__package__].preferences

    if attr_id is None:
        return prefs
    else:
        return getattr(prefs, attr_id)


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


def link_pass_sockets(tree, pass_name):
    nodes = tree.nodes
    output_node1 = nodes["File Output (Images)"]
    output_node2 = nodes["File Output (EXR)"]
    output_soc = pass_name

    input_node, input_soc = pass_link_map[pass_name]
    input_node = nodes[input_node]

    tree.links.new(input_node.outputs[input_soc], output_node1.inputs[output_soc])
    tree.links.new(input_node.outputs[input_soc], output_node2.inputs[output_soc])


def get_enabled_passes(collection):
    for render_pass in collection:
        if render_pass.render:
            yield render_pass


def add_node(tree, node_type, *_, **props):
    node = tree.nodes.new(node_type)

    for prop, value in props.items():
        setattr(node, prop, value)

    return node


def copy_scene(scene, name, clear_tree=False):
    new_scene = scene.copy()
    new_scene.name = name
    
    if clear_tree:
        tree = new_scene.node_tree
        tree.nodes.clear()

    return new_scene


def create_file_outputs(node, outputs):
    slots = node.file_slots
    slots.clear()

    for output in outputs:
        slots.new(output)


def create_light(name, type, *_, **props):
    lights = bpy.data.lights
    light = lights.new(name, type)

    for prop, value in props.items():
        setattr(light, prop, value)

    return light


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

    objects = bpy.data.objects
    shading_light = objects.new(name="EMP_ShadingPass_Light", object_data=shading_light_data)
    shadow_light = objects.new(name="EMP_ShadowPass_Light", object_data=shadow_light_data)
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