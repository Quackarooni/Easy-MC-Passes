from .keymap_ui import KeymapItemDef, KeymapStructure, KeymapLayout
from .operators import (
    EMP_OT_EXPORT_PASSES,
)


keymap_structure = KeymapStructure(
    [
        KeymapItemDef(EMP_OT_EXPORT_PASSES.bl_idname, keymap_name="Node Editor", space_type="NODE_EDITOR"),
    ]
)


keymap_layout = KeymapLayout(layout_structure=keymap_structure)


def register():
    keymap_structure.register()


def unregister():
    keymap_structure.unregister()
