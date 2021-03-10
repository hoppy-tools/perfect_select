import bpy
from bpy.types import Operator
from .properties import PerfectSelectOperatorProperties, ExtendToEdgeLoopsOperatorProperties
from .backend.select import (extend_to_edge_loops_execute,
                             perfect_select_invoke,
                             perfect_select_execute,
                             perfect_select_modal)


class PERFECT_SELECT_OT_extend_to_edge_loops(ExtendToEdgeLoopsOperatorProperties, Operator):
    bl_label = "Extend to Boundary Loops"
    bl_idname = "perfect_select.extend_to_edge_loops"
    bl_options = {'UNDO', 'REGISTER'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT'

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        return extend_to_edge_loops_execute(context, self)


class PERFECT_SELECT_OT_perfect_select(PerfectSelectOperatorProperties, Operator):
    bl_label = "Perfect Select"
    bl_idname = "perfect_select.perfect_select"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return bool(obj and obj.type == 'MESH' and obj.mode == 'EDIT')

    def invoke(self, context, event):
        perfect_select_invoke(context, event, self)
        return self.execute(context)

    def execute(self, context):
        return perfect_select_execute(context, self)

    def modal(self, context, event):
        return perfect_select_modal(context, event, self)


def register():
    bpy.utils.register_class(PERFECT_SELECT_OT_extend_to_edge_loops)
    bpy.utils.register_class(PERFECT_SELECT_OT_perfect_select)


def unregister():
    bpy.utils.unregister_class(PERFECT_SELECT_OT_perfect_select)
    bpy.utils.unregister_class(PERFECT_SELECT_OT_extend_to_edge_loops)
