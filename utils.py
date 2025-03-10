def get_enabled_passes(collection):
    for render_pass in collection:
        if render_pass.render:
            yield render_pass


def add_node(tree, node_type, *_, **props):
    node = tree.nodes.new(node_type)

    for prop, value in props.items():
        setattr(node, prop, value)

    return node


def create_file_outputs(node, outputs):
    slots = node.file_slots
    slots.clear()

    for output in outputs:
        slots.new(output)