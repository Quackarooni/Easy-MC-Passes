import bpy
from bpy.types import Operator, Panel, UIList

from .operators import EMP_OT_EXPORT_PASSES, EMP_OT_OPEN_FILE_EXPLORER
from .utils import get_addon_property, get_addon_properties, ui_draw_enum_prop


def clamp(value, lower, upper):
    return lower if value < lower else upper if value > upper else value


class EMP_PT_PASS_MANAGER(Panel):
    bl_label = "Pass Manager"
    bl_space_type = 'VIEW_3D'
    bl_region_type = "UI"
    bl_category = "Easy MC Passes"

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        data = get_addon_properties()
        row.template_list("EMP_PT_UL_PASSES", "", data, "render_passes", data, "active_pass_index")

        try:
            collection =  data.render_passes
            active_prop = collection[data.active_pass_index]
            active_prop.draw(layout)
        except IndexError:
            pass


class EMP_PT_EXPORT_PASSES(Panel):
    bl_label = "Export Passes"
    bl_space_type = 'VIEW_3D'
    bl_region_type = "UI"
    bl_category = "Easy MC Passes"

    @classmethod
    def poll(cls, context):
        return True
    
    def draw(self, context):
        layout = self.layout
        data = get_addon_properties()
        
        layout.prop(data, "export_path", text="", placeholder="Export Path")
        layout.operator(EMP_OT_EXPORT_PASSES.bl_idname)
        layout.operator(EMP_OT_OPEN_FILE_EXPLORER.bl_idname, icon="FOLDER_REDIRECT")
        

class EMP_PT_UL_PASSES(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        # Make sure your code supports all 3 layout types 
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.separator()
            row.prop(item, "render", text="")
            row.label(text=item.name)
            
        elif self.layout_type in {'GRID'}: 
            layout.alignment = 'CENTER' 
            layout.label(text="")


class EMP_PT_MASK_LAYERS(Panel):
    bl_label = "Masks"
    bl_space_type = 'VIEW_3D'
    bl_region_type = "UI"
    bl_category = "Easy MC Passes"

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        data = get_addon_properties()
        row.template_list("EMP_PT_UL_MASKS", "", data, "mask_layers", data, "active_mask_index")
        collection = get_addon_property("mask_layers")

        ops_col = row.column()

        add_remove_col = ops_col.column(align=True)
        props = add_remove_col.operator("my_list.new_item", icon='ADD', text="")
        props = add_remove_col.operator("my_list.delete_item", icon='REMOVE', text="")

        ops_col.separator()

        up_down_col = ops_col.column(align=True)
        props = up_down_col.operator("my_list.move_item", icon='TRIA_UP', text="")
        props.direction = 'UP'
        props = up_down_col.operator("my_list.move_item", icon='TRIA_DOWN', text="")
        props.direction = 'DOWN'

        try:
            active_prop = collection[data.active_mask_index]
            active_prop.draw(layout)
        except IndexError:
            pass

        header, panel = layout.panel("EMP_PT_MASK_RENDER_SETTINGS", default_closed=True)
        header.label(text="Render Settings")
        if panel:
            panel.use_property_split = True
            data = get_addon_properties()
            col = panel.column()
            col.prop(data, "mask_engine")
            if data.mask_engine == "BLENDER_EEVEE_NEXT":
                col.prop(data, "mask_eevee_samples")
            elif data.mask_engine == "CYCLES":
                col.prop(data, "mask_cycles_samples")


class EMP_PT_UL_MASKS(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        # Make sure your code supports all 3 layout types 
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.separator()
            row.prop(item, "render", text="")
            row.prop(item, "name", text="", emboss=False)

            icon = "CLIPUV_DEHLT" if item.invert else "CLIPUV_HLT"
            row.prop(item, "invert", text="", emboss=False, icon=icon)

            icon = "POINTCLOUD_POINT" if item.solo else "POINTCLOUD_DATA"
            row.prop(item, "solo", text="", emboss=False, icon=icon)
            
        elif self.layout_type in {'GRID'}: 
            layout.alignment = 'CENTER' 
            layout.label(text="")


class EMP_OT_ADD_MASK(Operator): 
    bl_idname = "my_list.new_item" 
    bl_label = "Add Mask" 
    bl_description = "Add a custom mask to render"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context): 
        collection = get_addon_property("mask_layers")
        prop = collection.add()
        prop.initialize_name()

        data = get_addon_properties()
        max_index = len(collection) - 1

        intended_index = clamp(data.active_mask_index + 1, lower=0, upper=max_index)
        data.active_mask_index = intended_index
        collection.move(max_index, intended_index)

        return {'FINISHED'}


class EMP_OT_REMOVE_MASK(Operator): 
    bl_idname = "my_list.delete_item" 
    bl_label = "Remove Mask" 
    bl_description = "Remove currently selected mask"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod 
    def poll(cls, context):
        mask_layers = get_addon_property("mask_layers")
        return len(mask_layers) > 0

    def execute(self, context):
        data = get_addon_properties()
        prop = get_addon_property("mask_layers")
        index = data.active_mask_index

        prop.remove(index) 
        data.active_mask_index = min(max(0, index - 1), len(prop) - 1) 
        return{'FINISHED'}


class EMP_OT_MOVE_MASK(Operator): 
    bl_idname = "my_list.move_item" 
    bl_label = "Move Mask" 
    bl_options = {"REGISTER", "UNDO"}

    direction: bpy.props.EnumProperty(
        items=(
            ('UP', 'Up', ""), 
            ('DOWN', 'Down', ""),
            )
        ) 

    @classmethod
    def description(cls, context, props):
        if props.direction == "UP":
            return "Move selected mask higher up the list"
        elif props.direction == "DOWN":
            return "Move selected mask lower down the list"
        else:
            raise ValueError

    @classmethod 
    def poll(cls, context):
        mask_layers = get_addon_property("mask_layers")
        return len(mask_layers) > 0

    def move_index(self, collection, data, index): 
        list_length = len(collection) - 1 # (index starts at 0) 
        new_index = index + (-1 if self.direction == 'UP' else 1)
        data.active_mask_index = max(0, min(new_index, list_length)) 

    def execute(self, context): 
        data = get_addon_properties()
        index = data.active_mask_index
        my_list = get_addon_property("mask_layers")

        neighbor = index + (-1 if self.direction == 'UP' else 1) 
        my_list.move(neighbor, index) 
        
        self.move_index(my_list, data, index) 
        return{'FINISHED'}
    

classes = (
    EMP_PT_PASS_MANAGER,
    EMP_PT_MASK_LAYERS,
    EMP_PT_EXPORT_PASSES,
    EMP_PT_UL_PASSES,
    EMP_PT_UL_MASKS,
    EMP_OT_ADD_MASK,
    EMP_OT_REMOVE_MASK,
    EMP_OT_MOVE_MASK,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)