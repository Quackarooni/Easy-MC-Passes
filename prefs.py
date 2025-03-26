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
from .utils import add_node, fetch_user_preferences, get_addon_property, get_addon_properties, ui_draw_enum_prop

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
        ("Environment"),
        ("Ambient Occlusion"),
        ("Direction Masks"),
    )

    for default in defaults:
        if default not in prop_collection:
            prop_item = prop_collection.add()
            prop_item.name = default


class EMPRenderPass(PropertyGroup):
    def __repr__(self):
        return f"bpy.data.scenes['{bpy.context.scene.name}'].{self.__class__.__name__}['{self.name}']"

    name: StringProperty(name="Name", default="Default")
    render: BoolProperty(name="Render", default=True, options=set())

    @property
    def exr_output_name(self):
        return f'Image.{self.name.replace(".", "_")}'

    def draw(self, layout):
        col = layout.column()
        if self.name in {"Shading", "Shadow"}:
            data = get_addon_properties()
            col.prop(data, "light_direction")
            
        if self.name == "Freestyle":
            layout.use_property_split = True
            layout.use_property_decorate = False
            rd = bpy.context.scene.render
            
            row = layout.row()
            row.prop(rd, "line_thickness_mode", expand=True, text="Thickness Mode")
            if rd.line_thickness_mode == 'ABSOLUTE':
                layout.prop(rd, "line_thickness", text="Thickness")


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

    def clear_unused_selection(self, context):
        if self.selection_type == "OBJECT":
            self.property_unset("selection_material")
            self.property_unset("selection_collection")
        elif self.selection_type == "MATERIAL":
            self.property_unset("selection_object")
            self.property_unset("selection_collection")
        elif self.selection_type == "COLLECTION":
            self.property_unset("selection_material")
            self.property_unset("selection_object")
        else:
            raise ValueError()

    name: StringProperty(name="Name", default="Mask", update=set_unique_name)
    render: BoolProperty(name="Render", default=True, options=set())
    invert: BoolProperty(name="Invert Mask", default=False, options=set(),
        description="Invert the resulting mask, such that selected and unselected areas are swapped"
        )
    solo: BoolProperty(name="Solo", default=False, options=set(),
        description="Render the selection in a separate layer isolated from other objects"
        )
    obj_include_children: BoolProperty(name="Include Children", default=True, options=set(),
        description="Include all objects parented to this object as a part of the selection"
        )

    selection_type : EnumProperty(
        name="Selection Type",
        default="OBJECT",
        items=(
            ("OBJECT", "Object", "", "OBJECT_DATA", 0),
            ("MATERIAL", "Material", "", "MATERIAL_DATA", 1),
            ("COLLECTION", "Collection", "", "OUTLINER_COLLECTION", 2),
            ),
        update=clear_unused_selection
        )

    selection_object : PointerProperty(name="Selection", type=bpy.types.Object)
    selection_material : PointerProperty(name="Selection", type=bpy.types.Material)
    selection_collection : PointerProperty(name="Selection", type=bpy.types.Collection)

    def initialize_name(self):
        self.name = self.name

    @property
    def exr_output_name(self):
        return f'Masks.{self.name.replace(".", "_")}'
    
    @property
    def view_layer_name(self):
        if self.solo:
            return f'EMP_Solo_{self.name.replace(".", "_")}'
        else:
            return bpy.context.scene.view_layers[0].name

    @property
    def solo_objects(self):
        if self.selection_type == "OBJECT":
            obj = self.selection_object
            yield obj

            if obj and self.obj_include_children:
                for child in obj.children_recursive:
                    yield child

        elif self.selection_type == "MATERIAL":
            material = self.selection_material
            if material is not None:
                user_map = bpy.data.user_map(subset=(material,))
                material_users = user_map[material]
                for obj in bpy.context.scene.collection.all_objects:
                    if obj.data in material_users:
                        yield obj

        elif self.selection_type == "COLLECTION":
            col = self.selection_collection
            if col is None:
                yield None
            else:
                for obj in col.all_objects:
                    yield obj

    def layer_name(self, view_layer_name):
        selection_type = self.selection_type
        if selection_type == "OBJECT":
            return f"{view_layer_name}.CryptoObject"
        elif selection_type == "MATERIAL":
            return f"{view_layer_name}.CryptoMaterial"
        elif selection_type == "COLLECTION":
            return f"{view_layer_name}.CryptoObject"
        else:
            raise ValueError

    @property
    def matte_id(self):
        selection_type = self.selection_type
        if selection_type == "OBJECT":
            obj = self.selection_object
            if obj is None:
                return ""

            if self.obj_include_children:
                objects = (obj, *(obj.children_recursive))
                return ", ".join((o.name for o in objects))
            else:
                return self.selection_object.name
            
        elif selection_type == "MATERIAL":
            mat = self.selection_material
            if mat is None:
                return ""
            
            return mat.name
        
        elif selection_type == "COLLECTION":
            col = self.selection_collection
            if col is None:
                return ""
            
            return ", ".join((o.name for o in col.all_objects))
        
        else:
            raise ValueError

    def enable_pass(self, view_layer):
        if self.selection_type in {"OBJECT", "COLLECTION"}:
            view_layer.use_pass_cryptomatte_object = True
        elif self.selection_type == "MATERIAL":
            view_layer.use_pass_cryptomatte_material = True
        else:
            raise ValueError

    def draw(self, layout):
        layout.prop(self, "name")
        ui_draw_enum_prop(layout, self, "selection_type")

        col = layout.column()
        if self.selection_type == "OBJECT":
            ui_draw_enum_prop(col, self, "selection_object")
            col.prop(self, "obj_include_children")
        elif self.selection_type == "MATERIAL":
            ui_draw_enum_prop(col, self, "selection_material")
        elif self.selection_type == "COLLECTION":
            ui_draw_enum_prop(col, self, "selection_collection")
        else:
            raise ValueError()

        col = layout.column()
        col.prop(self, "invert")
        col.prop(self, "solo")


class EasyMCPassesDirectionMasks(PropertyGroup):
    pos_x : BoolProperty(name="+X", default=True, options=set())
    pos_y : BoolProperty(name="+Y", default=True, options=set())
    pos_z : BoolProperty(name="+Z", default=True, options=set())
    neg_x : BoolProperty(name="-X", default=True, options=set())
    neg_y : BoolProperty(name="-Y", default=True, options=set())
    neg_z : BoolProperty(name="-Z", default=True, options=set())

    props = ("pos_x", "pos_y", "pos_z", "neg_x", "neg_y", "neg_z",)
    prop_name_map = {
        "pos_x" : "Dir_PosX",
        "pos_y" : "Dir_PosY",
        "pos_z" : "Dir_PosZ",
        "neg_x" : "Dir_NegX",
        "neg_y" : "Dir_NegY",
        "neg_z" : "Dir_NegZ",
    }

    def draw(self, layout):
        layout.label(text="Directions:")

        row = layout.grid_flow()
        col1 = row.column()
        col2 = row.column()
        col1.use_property_split = True
        col2.use_property_split = True
        col1.ui_units_x = 5
        col2.ui_units_x = 5

        for prop_name in self.props:
            if prop_name.startswith("pos"):
                col1.prop(self, prop_name)
            else:
                col2.prop(self, prop_name)

    def output_name(self, prop_name, is_exr):
        output_name = self.prop_name_map[prop_name]
        if is_exr:
            output_name = f"Image.{output_name}"

        return output_name
    
    @property
    def has_outputs(self):
        return len(tuple(self.enabled_masks)) > 0

    @property
    def enabled_masks(self):
        for prop_name in self.props:
            if getattr(self, prop_name):
                yield prop_name

    def create_outputs(self, slots, is_exr):
        for prop_name in self.enabled_masks:
            slot_name = self.output_name(prop_name, is_exr=is_exr)
            slots.new(slot_name)

            slot = slots[slot_name]
            slot.use_node_format = False
            slot.format.file_format = 'PNG'
            slot.format.color_mode = 'RGBA'

    def link_sockets(self, tree, output_node, is_exr):
        for prop_name in self.enabled_masks:
            math_node = tree.nodes[self.output_name(prop_name, is_exr=False)]
            tree.links.new(math_node.outputs["Value"], output_node.inputs[self.output_name(prop_name, is_exr=is_exr)])

    def add_nodes(self, tree, start_location):
        sep_xyz = tree.nodes["EMP_DirMaskXYZ"]

        for i, prop_name in enumerate(self.enabled_masks):
            location = (start_location[0], start_location[1] - i*45)
            name = self.output_name(prop_name, is_exr=False)
            math_node = add_node(tree, node_type="CompositorNodeMath", name=name, label=name, operation="MULTIPLY", location=location)
            math_node.hide = True

            value = 1 if prop_name.startswith("pos") else -1
            math_node.inputs[1].default_value = value

            target_socket = prop_name[-1].upper()
            tree.links.new(sep_xyz.outputs[target_socket], math_node.inputs[0])


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
    mask_engine: EnumProperty(
        name="Engine",
        default="BLENDER_EEVEE_NEXT",
        description="Engine to use for rendering",
        items=(
            ("BLENDER_EEVEE_NEXT", "EEVEE", ""),
            ("CYCLES", "Cycles", ""),
            ),
        options=set()
        )
    
    mask_eevee_samples : IntProperty(name="Samples", min=1, default=16, options=set(),
        description="Number of samples per pixel for rendering"                             
        )
    mask_cycles_samples : IntProperty(name="Samples", min=1, default=256, options=set(),
        description="Number of samples per pixel for rendering"
        )

    export_path : StringProperty(name="Export Path", subtype='FILE_PATH',
        description="Directory where the various image outputs will be exported to"
        )
    light_direction : FloatVectorProperty(name="Light Direction", subtype="EULER", precision=5, step=100,
        description="The direction of the lighting calculated in Shading & Shadow passes"
        )

    mask_type: EnumProperty(
        name="Mask Type",
        default="ALPHA",
        description="How the masks will be exported as",
        items=(
            ("ALPHA", "Alpha", "Render masks as PNG image with transparency"),
            ("BLACK_AND_WHITE", "Black & White", "Render masks as black and white images"),
            ),
        options=set()
        )
    
    direction_masks : PointerProperty(name="Direction Masks", type=EasyMCPassesDirectionMasks)


class EasyMCPassesPreferences(AddonPreferences):
    bl_idname = __package__
    
    default_export_path : StringProperty(name="Default Export Path", default="/tmp\\", subtype='FILE_PATH')
    view_passes_after_render : BoolProperty(name="Create EXR for Viewing", default=True,
        description="Create an EXR file with the exported passes that gets viewed after render"
        )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "default_export_path")
        layout.prop(self, "view_passes_after_render")

        keymap_layout.draw_keyboard_shorcuts(self, layout, context)


keymap_layout.register_properties(preferences=EasyMCPassesPreferences)


@persistent
def onFileLoaded(dummy):
    setDefaultCollectionValue()


classes = (
    EMPRenderPass,
    EMPMaskLayer,
    EasyMCPassesDirectionMasks,
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