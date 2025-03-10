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

    scene.display_settings.display_device = 'sRGB'
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
