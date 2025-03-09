import bpy
from bpy.types import Operator, Panel, UIList


def clamp(value, lower, upper):
    return lower if value < lower else upper if value > upper else value


def get_active_scene(context):
    try:
        return context.scene
    except AttributeError:
        return


def get_collection_property(context):
    return getattr(context.scene, "EMP_render_passes")


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
        scene = context.scene

        row = layout.row()
        row.template_list("EMP_PT_UL_PASSES", "", scene, "EMP_render_passes", scene, "list_index")

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

        collection = get_collection_property(context)

        try:
            active_prop = collection[scene.list_index]
            active_prop.draw(layout)
        except IndexError:
            pass
        

class EMP_PT_UL_PASSES(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        # Make sure your code supports all 3 layout types 
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.separator()
            row.prop(item, "render", text="")
            row.prop(item, "name", text="", emboss=False)
            
        elif self.layout_type in {'GRID'}: 
            layout.alignment = 'CENTER' 
            layout.label(text="")


class EMP_OT_ADD_PASS(Operator): 
    bl_idname = "my_list.new_item" 
    bl_label = "Add Property" 
    bl_description = "Add a custom object property for all users of the current material"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context): 
        collection = get_collection_property(context)
        collection.add()
        
        material = get_active_scene(context)
        max_index = len(collection) - 1

        intended_index = clamp(material.list_index + 1, lower=0, upper=max_index)
        material.list_index = intended_index
        collection.move(max_index, intended_index)

        return {'FINISHED'}


class EMP_OT_REMOVE_PASS(Operator): 
    bl_idname = "my_list.delete_item" 
    bl_label = "Remove Property" 
    bl_description = "Remove selected property for all users of the current material"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod 
    def poll(cls, context): 
        prop = get_collection_property(context)
        
        return get_active_scene(context)

    def execute(self, context):
        material = get_active_scene(context)
        prop = get_collection_property(context)
        index = material.list_index

        prop.remove(index) 
        material.list_index = min(max(0, index - 1), len(prop) - 1) 
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
        return get_active_scene(context)

    def move_index(self, collection, material, index): 
        list_length = len(collection) - 1 # (index starts at 0) 
        new_index = index + (-1 if self.direction == 'UP' else 1)
        material.list_index = max(0, min(new_index, list_length)) 

    def execute(self, context): 
        material = get_active_scene(context)
        index = material.list_index
        my_list = get_collection_property(context)

        neighbor = index + (-1 if self.direction == 'UP' else 1) 
        my_list.move(neighbor, index) 
        
        self.move_index(my_list, material, index) 
        return{'FINISHED'}
    

classes = (
    EMP_PT_PASS_MANAGER,
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