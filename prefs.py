import bpy
from bpy.types import (
    AddonPreferences,
    PropertyGroup,
    )
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatVectorProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
    )

import re
from collections import Counter

from .keymaps import keymap_layout
from .utils import fetch_user_preferences, get_addon_property, ui_draw_enum_prop

from bpy.app.handlers import persistent


def setDefaultCollectionValue():
    prop_collection = get_addon_property("render_passes")
    # set default value if <myCollection> is empty
    defaults = (
        ("Combined"),
        ("Color"),
        ("Mist"),
        ("Normal"),
        ("Emission"),
        ("Cavity"),
        ("Shading"),
        ("Shadow"),
        ("Freestyle"),
    )

    for default in defaults:
        if default not in prop_collection:
            prop_item = prop_collection.add()
            prop_item.name = default


class EMPRenderPass(PropertyGroup):
    def __repr__(self):
        return f"bpy.data.scenes['{bpy.context.scene.name}'].{self.__class__.__name__}['{self.name}']"

    name: StringProperty(name="Name", default="Default")
    render: BoolProperty(name="Render", default=True)

    def draw(self, layout):
        if self.name in {"Shading", "Shadow"}:
            data = bpy.context.scene.EMP_Properties
            col = layout.column()
            col.prop(data, "light_direction")


class EMPMaskLayer(PropertyGroup):
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

    name: StringProperty(name="Name", default="Mask", update=set_unique_name)
    render: BoolProperty(name="Render", default=True)
    invert: BoolProperty(name="Invert Mask", default=False, options=set())

    selection_type : EnumProperty(
        name="Selection Type",
        default="OBJECT",
        items=(
            ("OBJECT", "Object", "", "OBJECT_DATA", 0),
            ("MATERIAL", "Material", "", "MATERIAL_DATA", 1),
            ),
        )

    def initialize_name(self):
        self.name = self.name

    def draw(self, layout):
        layout.prop(self, "name")
        layout.prop(self, "invert")

        ui_draw_enum_prop(layout, self, "selection_type")


class EasyMCPassesProperties(PropertyGroup):
    def get_default_export_path(self):
        export_path = self.get("export_path", fetch_user_preferences("default_export_path"))
        self["export_path"] = export_path
        return export_path
        
    def set_default_export_path(self, value):
        self["export_path"] = value
    
    render_passes : CollectionProperty(name="Render Passes", type=EMPRenderPass)
    active_pass_index : IntProperty(name="Active Index", min=0)
    
    mask_layers : CollectionProperty(name="Mask", type=EMPMaskLayer)
    active_mask_index : IntProperty(name="Active Index", min=0)

    export_path : StringProperty(name="Export Path", subtype='FILE_PATH', get=get_default_export_path, set=set_default_export_path)
    light_direction : FloatVectorProperty(name="Light Direction", subtype="EULER", precision=5, step=100)


class EasyMCPassesPreferences(AddonPreferences):
    bl_idname = __package__
    
    default_export_path : StringProperty(name="Default Export Path", default="/tmp\\", subtype='FILE_PATH')

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "default_export_path")

        keymap_layout.draw_keyboard_shorcuts(self, layout, context)


keymap_layout.register_properties(preferences=EasyMCPassesPreferences)


@persistent
def onFileLoaded(dummy):
    setDefaultCollectionValue()


classes = (
    EMPRenderPass,
    EMPMaskLayer,
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