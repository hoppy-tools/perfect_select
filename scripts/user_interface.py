import os
import bpy

from math import sin, cos, pi

from bpy.types import WorkSpaceTool, GizmoGroup
from gpu_extras.presets import draw_circle_2d
from bl_keymap_utils.io import keyconfig_init_from_data
from bl_ui.space_toolsystem_common import _icon_cache

from .utils import is_blender3

import gpu
import bgl
from gpu.types import (
    GPUBatch,
    GPUVertBuf,
    GPUVertFormat,
)

from .previews import get_preview

DASHED_SHADER_VERT = None
DASHED_SHADER_FRAG = None

keymaps = []

if is_blender3():
    def set_uniform_array_float(shader, name, v_len, value):
        shader.uniform_vector_float(shader.uniform_from_name(name),
                                    gpu.types.Buffer("FLOAT", (v_len, 4), value), v_len*2, 2)
else:
    def set_uniform_array_float(shader, name, v_len, value):
        for i in range(v_len):
            shader.uniform_float(f"{name}[{i}]", value[i])


def perfect_select_keymap():
    items = []
    keymap = (
        "perfect_select.perfect_select_keymap",
        {"space_type": 'VIEW_3D', "region_type": 'WINDOW'},
        {"items": items},
    )

    items.extend([
        ("perfect_select.perfect_select",
         {"type": 'LEFTMOUSE', "value": 'PRESS'},
         {"properties": [("wait_for_input", False), ("mode", "SET")]}),
        ("perfect_select.perfect_select",
         {"type": 'LEFTMOUSE', "value": 'PRESS', "ctrl": True},
         {"properties": [("wait_for_input", False), ("mode", "SUB")]}),
    ])

    return keymap


class PerfectSelectWidget(GizmoGroup):
    bl_idname = "perfect_select.widget"
    bl_label = "Perfect Select Widget"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D'}

    @classmethod
    def poll(cls, context):
        tool_settings = bpy.context.scene.perfect_select_tool_settings
        return tool_settings.show_selection_gizmos

    def setup(self, context):
        mpr = self.gizmos.new("GIZMO_GT_arrow_3d")



class PerfectSelectTool(WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'

    bl_idname = "perfect_select.perfect_select_tool"
    bl_label = "Perfect Select"
    bl_description = (
        "Perfect Select\n"
        "with multiple lines"
    )
    bl_icon = "ops.perfect_select.perfect_select"
    bl_widget = 'perfect_select.widget'
    bl_keymap = "perfect_select.perfect_select_keymap"

    def draw_settings(context, layout, tool):
        reg = context.region.type
        is_header = reg == 'TOOL_HEADER'
        tool_settings = bpy.context.scene.perfect_select_tool_settings

        props = tool.operator_properties("perfect_select.perfect_select")
        row = layout.row()
        row.use_property_split = False
        row.prop(props, "mode", text="", expand=True, icon_only=True)

        sub = row.row(align=True)
        sub.prop(tool_settings, "show_selection_gizmos", text="", icon="GIZMO")

        sub = row.row(align=True)
        sub.label(icon='MOD_MIRROR')
        sub.prop(props, "mirror", expand=True, toggle=True, text="")

        sub = layout if is_header else layout.column(align=True)

        sub.prop(tool_settings, "pattern_source", text="" if is_header else None)
        if tool_settings.pattern_source == "OBJECT":
            sub.prop(tool_settings, "pattern_data", text="" if is_header else None)
        elif tool_settings.pattern_source == "IMAGE":
            sub.prop_search(tool_settings, "pattern_data_image", bpy.data, "images", text="" if is_header else None)

        if tool_settings.pattern_source == "OBJECT" and tool_settings.pattern_data \
                or tool_settings.pattern_source == "IMAGE" and tool_settings.pattern_data_image:
            sub = layout if is_header else layout.column(align=True)
            sub.prop(tool_settings, "pattern_resolution")
            if tool_settings.pattern_source == "OBJECT":
                sub.prop(tool_settings, "pattern_projection")

            if not is_header:
                box = layout.box()
                preview = get_preview()
                box.template_icon(icon_value=preview.icon_id, scale=7)

        layout.prop(props, "radius")
        layout.prop(props, "use_preselect")
        layout.prop(props, "align_to_normal")

    def draw_cursor(context, tool, xy):
        if not hasattr(context.scene, "perfect_select_tool_settings"):
            return

        tool_settings = context.scene.perfect_select_tool_settings
        tool_settings.update_snap_co(xy)
        props = tool.operator_properties("perfect_select.perfect_select")
        if tool_settings.pattern_source == "CIRCLE":
            draw_circle_2d(xy, (1.0,) * 4, props.radius, segments=32)
        else:
            draw_box_2d(xy, (1.0,) * 4, props.radius, props.radius)


def perfect_select_menu(self, context):
    layout = self.layout
    layout.separator()
    layout.operator("perfect_select.perfect_select")
    layout.operator("perfect_select.extend_to_edge_loops")


def perfect_select_snapping_panel(self, context):
    tool_settings = context.tool_settings
    ps_tool_setting = context.scene.perfect_select_tool_settings

    layout = self.layout
    col = layout.column()
    col.prop(ps_tool_setting, 'use_snap_perfect_select', toggle=1)
    if ps_tool_setting.use_snap_perfect_select and \
            any(e in tool_settings.snap_elements for e in ("EDGE", "EDGE_MIDPOINT", "EDGE_PERPENDICULAR")):
        col.prop(ps_tool_setting, 'use_snap_edge_slide')


def perfect_select_draw_callback(operator, context):
    if context.area != operator.draw_area:
        return

    tool_setting = context.scene.perfect_select_tool_settings
    co = (operator.x, operator.y)
    if operator.snap_point:
        co = operator.snap_point
        snap_color = (*bpy.context.preferences.themes[0].view_3d.vertex_select, 1.0)
        draw_circle_2d(co, snap_color, 6, segments=16)

    bgl.glLineWidth(2.0)
    if tool_setting.pattern_source == "CIRCLE":
        draw_circle_2d_dashed(co, 2, ((0.25, 0.25, 0.25, 1.0), (1.0, 1.0, 1.0, 1.0)), operator.radius, segments=32)
    else:
        draw_box_2d_dashed(co, 2, ((0.25, 0.25, 0.25, 1.0), (1.0, 1.0, 1.0, 1.0)), operator.radius, operator.radius)
    bgl.glLineWidth(1.0)


def draw_circle_2d_dashed(position, colors_len, colors, radius, *, segments=32):
    with gpu.matrix.push_pop():
        gpu.matrix.translate(position)
        gpu.matrix.scale_uniform(radius)
        mul = (1.0 / (segments - 1)) * (pi * 2)
        verts = [(sin(i * mul), cos(i * mul)) for i in range(segments)]
        fmt = GPUVertFormat()
        pos_id = fmt.attr_add(id="pos", comp_type='F32', len=2, fetch_mode='FLOAT')
        vbo = GPUVertBuf(len=len(verts), format=fmt)
        vbo.attr_fill(id=pos_id, data=verts)

        bgl.glEnable(bgl.GL_BLEND)
        batch = GPUBatch(type='TRI_FAN', buf=vbo)
        shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
        batch.program_set(shader)
        shader.uniform_float("color", (1.0, 1.0, 1.0, 0.02))
        batch.draw()
        bgl.glDisable(bgl.GL_BLEND)

        batch = GPUBatch(type='LINE_LOOP', buf=vbo)
        shader = gpu.types.GPUShader(DASHED_SHADER_VERT, DASHED_SHADER_FRAG)
        batch.program_set(shader)
        viewport = bgl.Buffer(bgl.GL_INT, 4)
        bgl.glGetIntegerv(bgl.GL_VIEWPORT, viewport)
        shader.uniform_float("viewport_size", (viewport[2], viewport[3]))
        shader.uniform_int("colors_len", 2)
        set_uniform_array_float(shader, "colors", colors_len, colors)
        shader.uniform_float("dash_width", 4.0)
        shader.uniform_float("dash_factor", 0.5)
        batch.draw()


def draw_box_2d_dashed(position, colors_len, colors, side_a, side_b):
    with gpu.matrix.push_pop():
        gpu.matrix.translate(position)
        gpu.matrix.scale((side_a, side_b))
        verts = [(-1, 1), (1, 1), (1, -1), (-1, -1)]
        fmt = GPUVertFormat()
        pos_id = fmt.attr_add(id="pos", comp_type='F32', len=2, fetch_mode='FLOAT')
        vbo = GPUVertBuf(len=len(verts), format=fmt)
        vbo.attr_fill(id=pos_id, data=verts)

        bgl.glEnable(bgl.GL_BLEND)
        batch = GPUBatch(type='TRI_FAN', buf=vbo)
        shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
        batch.program_set(shader)
        shader.uniform_float("color", (1.0, 1.0, 1.0, 0.02))
        batch.draw()
        bgl.glDisable(bgl.GL_BLEND)

        batch = GPUBatch(type='LINE_LOOP', buf=vbo)
        shader = gpu.types.GPUShader(DASHED_SHADER_VERT, DASHED_SHADER_FRAG)
        batch.program_set(shader)
        viewport = bgl.Buffer(bgl.GL_INT, 4)
        bgl.glGetIntegerv(bgl.GL_VIEWPORT, viewport)
        shader.uniform_float("viewport_size", (viewport[2], viewport[3]))
        shader.uniform_int("colors_len", 2)
        shader.uniform_float("dash_width", 8.0)
        shader.uniform_float("dash_factor", 0.5)
        set_uniform_array_float(shader, "colors", colors_len, colors)
        batch.draw()


def draw_box_2d(position, color, side_a, side_b):
    with gpu.matrix.push_pop():
        gpu.matrix.translate(position)
        gpu.matrix.scale((side_a, side_b))
        verts = [(-1, 1), (1, 1), (1, -1), (-1, -1)]
        fmt = GPUVertFormat()
        pos_id = fmt.attr_add(id="pos", comp_type='F32', len=2, fetch_mode='FLOAT')
        vbo = GPUVertBuf(len=len(verts), format=fmt)
        vbo.attr_fill(id=pos_id, data=verts)
        batch = GPUBatch(type='LINE_LOOP', buf=vbo)
        shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
        batch.program_set(shader)
        shader.uniform_float("color", color)
        batch.draw()


def register_keymaps():
    wm = bpy.context.window_manager

    keymap = perfect_select_keymap()

    kc = wm.keyconfigs.addon
    keyconfig_init_from_data(kc, [keymap])
    keymaps.append((kc, kc.keymaps[keymap[0]]))

    kc = wm.keyconfigs.default
    keyconfig_init_from_data(kc, [keymap])
    keymaps.append((kc, kc.keymaps[keymap[0]]))


def unregister_keymaps():
    for (kc, km) in keymaps:
        try:
            kc.keymaps.remove(km)
        except RuntimeError:
            pass


def register():
    global DASHED_SHADER_VERT
    global DASHED_SHADER_FRAG
    with open(os.path.abspath(os.path.join(__file__, '..', 'shaders', '2D_line_dashed.vert')), "r") as file:
        DASHED_SHADER_VERT = file.read()

    with open(os.path.abspath(os.path.join(__file__, '..', 'shaders', '2D_line_dashed.frag')), "r") as file:
        DASHED_SHADER_FRAG = file.read()

    bpy.types.VIEW3D_PT_snapping.append(perfect_select_snapping_panel)
    bpy.types.VIEW3D_MT_select_edit_mesh.append(perfect_select_menu)

    icon_filename = os.path.join(os.path.dirname(__file__), "datafiles", "ops.perfect_select.perfect_select.dat")
    _icon_cache['ops.perfect_select.perfect_select'] = bpy.app.icons.new_triangles_from_file(icon_filename)
    register_keymaps()
    bpy.utils.register_class(PerfectSelectWidget)
    bpy.utils.register_tool(PerfectSelectTool, after={"builtin.select_lasso"}, separator=False, group=False)


def unregister():
    bpy.utils.unregister_tool(PerfectSelectTool)
    bpy.utils.unregister_class(PerfectSelectWidget)
    unregister_keymaps()
    bpy.types.VIEW3D_PT_snapping.remove(perfect_select_snapping_panel)
    bpy.types.VIEW3D_MT_select_edit_mesh.remove(perfect_select_menu)
