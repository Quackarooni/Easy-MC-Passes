from .keymap_ui import KeymapItemDef, KeymapStructure, KeymapLayout
from .operators import (
    EMP_Template_OT_Operator,
)


keymap_structure = KeymapStructure(
    [
        KeymapItemDef(EMP_Template_OT_Operator.bl_idname, keymap_name="Node Editor", space_type="NODE_EDITOR"),
    ]
)


keymap_layout = KeymapLayout(layout_structure=keymap_structure)


def register():
    keymap_structure.register()


def unregister():
    keymap_structure.unregister()
