import bpy
from bpy.types import (
    AddonPreferences,
    PropertyGroup,
    )
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
    )

import re
from collections import Counter

from .keymaps import keymap_layout
from .utils import get_collection_property

from bpy.app.handlers import persistent


def setDefaultCollectionValue():
    prop_collection = get_collection_property(bpy.context)
    # set default value if <myCollection> is empty
    defaults = (
        ("Combined"),
        ("Color"),
        ("Mist"),
        ("Normal"),
        ("Freestyle"),
        ("Cavity"),
        ("Shading"),
        ("Shadow"),
        ("Emission"),
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

    def __repr__(self):
        return f"bpy.data.scenes['{bpy.context.scene.name}'].{self.__class__.__name__}['{self.name}']"

    @staticmethod
    def unduped_name(name):
        unduped_name, *_ = re.split("\.\d+$", name)
        return unduped_name

    def make_name_unique(self, name):
        collection = self.parent_collection()
        counter = 1
        names = set(i.name for i in collection)

        stem = self.unduped_name(name)

        counts = Counter(i.name for i in collection)
        should_change_name = (counts[name] > 1)
        
        if should_change_name:
            while name in names:
                name = f"{stem}.{counter:03d}"
                counter += 1

        return name

    def set_unique_name(self, context):
        self["name"] = self.make_name_unique(self.name)

    name: StringProperty(name="Name", default="Default", update=set_unique_name)
    render: BoolProperty(name="Render", default=True)

    def initialize_name(self):
        self.name = self.name

    def draw(self, layout):
        layout.prop(self, "name")


class EasyMCPassesProperties(PropertyGroup):
    render_passes : CollectionProperty(type=EMPRenderPass)
    active_pass_index : IntProperty(min=0)


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
    EasyMCPassesProperties,
    EasyMCPassesPreferences,
    )


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    setattr(bpy.types.Scene, "EMP_Properties", PointerProperty(type=EasyMCPassesProperties))
    bpy.app.handlers.load_post.append(onFileLoaded)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    bpy.app.handlers.load_post.remove(onFileLoaded)
    delattr(bpy.types.Scene, "EMP_Properties")