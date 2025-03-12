import bpy
from bpy.types import Operator, Panel, UIList

from .operators import EMP_OT_EXPORT_PASSES
from .utils import get_collection_property


def clamp(value, lower, upper):
    return lower if value < lower else upper if value > upper else value


def get_properties(context):
    try:
        return context.scene.EMP_Properties
    except AttributeError:
        return


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
        data = get_properties(context)
        row.template_list("EMP_PT_UL_PASSES", "", data, "render_passes", data, "active_pass_index")
        collection = get_collection_property(context)

        try:
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
        data = context.scene.EMP_Properties
        
        layout.prop(data, "export_path", text="", placeholder="Export Path")
        layout.operator(EMP_OT_EXPORT_PASSES.bl_idname)
        

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


class EMP_OT_ADD_PASS(Operator): 
    bl_idname = "my_list.new_item" 
    bl_label = "Add Property" 
    bl_description = "Add a custom object property for all users of the current data"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context): 
        collection = get_collection_property(context)
        prop = collection.add()
        prop.initialize_name()

        data = get_properties(context)
        max_index = len(collection) - 1

        intended_index = clamp(data.active_pass_index + 1, lower=0, upper=max_index)
        data.active_pass_index = intended_index
        collection.move(max_index, intended_index)

        return {'FINISHED'}


class EMP_OT_REMOVE_PASS(Operator): 
    bl_idname = "my_list.delete_item" 
    bl_label = "Remove Property" 
    bl_description = "Remove selected property for all users of the current data"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod 
    def poll(cls, context):
        return get_properties(context)

    def execute(self, context):
        data = get_properties(context)
        prop = get_collection_property(context)
        index = data.active_pass_index

        prop.remove(index) 
        data.active_pass_index = min(max(0, index - 1), len(prop) - 1) 
        return{'FINISHED'}


class EMP_OT_MOVE_PASS(Operator): 
    bl_idname = "my_list.move_item" 
    bl_label = "Move Item" 
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
            return "Move selected property higher up the list"
        elif props.direction == "DOWN":
            return "Move selected property lower down the list"
        else:
            raise ValueError

    @classmethod 
    def poll(cls, context): 
        return get_properties(context)

    def move_index(self, collection, data, index): 
        list_length = len(collection) - 1 # (index starts at 0) 
        new_index = index + (-1 if self.direction == 'UP' else 1)
        data.active_pass_index = max(0, min(new_index, list_length)) 

    def execute(self, context): 
        data = get_properties(context)
        index = data.active_pass_index
        my_list = get_collection_property(context)

        neighbor = index + (-1 if self.direction == 'UP' else 1) 
        my_list.move(neighbor, index) 
        
        self.move_index(my_list, data, index) 
        return{'FINISHED'}
    

classes = (
    EMP_PT_PASS_MANAGER,
    EMP_PT_EXPORT_PASSES,
    EMP_PT_UL_PASSES,
    EMP_OT_ADD_PASS,
    EMP_OT_REMOVE_PASS,
    EMP_OT_MOVE_PASS,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)