def get_enabled_passes(collection):
    for render_pass in collection:
        if render_pass.render:
            yield render_pass