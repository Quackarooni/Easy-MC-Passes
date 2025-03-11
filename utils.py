import bpy


def fetch_user_preferences(attr_id=None):
    prefs = bpy.context.preferences.addons[__package__].preferences

    if attr_id is None:
        return prefs
    else:
        return getattr(prefs, attr_id)


def get_enabled_passes(collection):
    for render_pass in collection:
        if render_pass.render:
            yield render_pass


def add_node(tree, node_type, *_, **props):
    node = tree.nodes.new(node_type)

    for prop, value in props.items():
        setattr(node, prop, value)

    return node


def copy_scene(scene, name):
    new_scene = scene.copy()
    new_scene.name = name
    
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


def init_shading_scene(scene):
    render = scene.render
    render.engine = 'CYCLES'
    render.use_freestyle = False

    view_layer = scene.view_layers[0]

    view_layer.use_pass_combined = False
    view_layer.use_pass_z = False
    view_layer.use_pass_mist = False
    view_layer.use_pass_position = False
    view_layer.use_pass_normal = False
    view_layer.use_pass_vector = False
    view_layer.use_pass_uv = False
    view_layer.cycles.denoising_store_passes = False
    view_layer.use_pass_object_index = False
    view_layer.use_pass_material_index = False
    view_layer.cycles.pass_debug_sample_count = False
    view_layer.use_pass_diffuse_direct = False
    view_layer.use_pass_diffuse_indirect = False
    view_layer.use_pass_diffuse_color = False
    view_layer.use_pass_glossy_direct = False
    view_layer.use_pass_glossy_indirect = False
    view_layer.use_pass_glossy_color = False
    view_layer.use_pass_transmission_direct = False
    view_layer.use_pass_transmission_indirect = False
    view_layer.use_pass_transmission_color = False
    view_layer.cycles.use_pass_volume_direct = False
    view_layer.cycles.use_pass_volume_indirect = False
    view_layer.use_pass_emit = False
    view_layer.use_pass_environment = False
    view_layer.use_pass_ambient_occlusion = False
    view_layer.cycles.use_pass_shadow_catcher = False
    view_layer.use_pass_cryptomatte_object = False
    view_layer.use_pass_cryptomatte_material = False
    view_layer.use_pass_cryptomatte_asset = False
    
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