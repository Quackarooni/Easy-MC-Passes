import bpy
from bpy.types import (
    AddonPreferences,
    PropertyGroup,
    )
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    IntProperty,
    StringProperty,
    )

import re

from .keymaps import keymap_layout
from bpy.app.handlers import persistent


def setDefaultCollectionValue():
    prop_collection = bpy.context.scene.EMP_render_passes
    # set default value if <myCollection> is empty
    defaults = (
        ("Name 1"),
        ("Name 2")
    )

    for default in defaults:
        if default not in prop_collection:
            prop_item = prop_collection.add()
            prop_item.name = default


class EMPRenderPass(PropertyGroup):
    def parent_collection(self):
        # this gets the collection that the element is in
        path = self.path_from_id()
        match = re.match('(.*)\[\d*\]', path)
        parent = self.id_data
        try:
            coll_path = match.group(1)
        except AttributeError:
            raise TypeError("Property not element in a collection.") 
        else:
            return parent.path_resolve(coll_path)

    @staticmethod
    def unduped_name(name):
        unduped_name, *_ = re.split("\.\d+$", name)
        return unduped_name

    name: StringProperty(name="name", default="Property")
    render: BoolProperty(name="render", default=True)
    value_int: IntProperty(name="int")

    def draw(self, layout):
        layout.prop(self, "name")


class EasyMCPassesPreferences(AddonPreferences):
    bl_idname = __package__

    def draw(self, context):
        layout = self.layout
        keymap_layout.draw_keyboard_shorcuts(self, layout, context)


keymap_layout.register_properties(preferences=EasyMCPassesPreferences)


@persistent
def onFileLoaded(dummy):
    setDefaultCollectionValue()


classes = (
    EMPRenderPass,
    EasyMCPassesPreferences,
    )


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    setattr(bpy.types.Scene, "EMP_render_passes", CollectionProperty(type=EMPRenderPass))
    setattr(bpy.types.Scene, "list_index", IntProperty())

    bpy.app.handlers.load_post.append(onFileLoaded)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    bpy.app.handlers.load_post.remove(onFileLoaded)

    delattr(bpy.types.Scene, "EMP_render_passes")
    delattr(bpy.types.Scene, "list_index")