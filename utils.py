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