import os
import bpy
from bpy.utils.toolsystem import ToolDef
from gpu_extras.presets import draw_circle_2d

from .previews import get_preview


@ToolDef.from_fn
def perfect_select_tool():
    def draw_settings(context, layout, tool):
        reg = context.region.type
        is_header = reg == 'TOOL_HEADER'

        props = tool.operator_properties("perfect_select.perfect_select")
        row = layout.row()
        row.use_property_split = False
        row.prop(props, "mode", text="", expand=True, icon_only=True)

        tool_settings = bpy.context.scene.perfect_select_tool_settings
        sub = layout if is_header else layout.column(align=True)
        sub.prop(tool_settings, "pattern_source")
        if tool_settings.pattern_source == "OBJECT":
            sub.prop(tool_settings, "pattern_data")
        elif tool_settings.pattern_source == "IMAGE":
            sub.prop_search(tool_settings, "pattern_data_image", bpy.data, "images")

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

        if context.scene.perfect_select_tool_settings.show_select_cursor:
            props = tool.operator_properties("perfect_select.perfect_select")
            draw_circle_2d(xy, (1.0,) * 4, props.radius, 32)

    return dict(
        idname="perfect_select.perfect_select_tool",
        label="Perfect Select",
        description=(
            "Select"
        ),
        icon="ops.perfect_select.perfect_select",
        keymap="perfect_select.perfect_select_keymap",
        operator="perfect_select.perfect_select",
        draw_settings=draw_settings,
        draw_cursor=draw_cursor
    )


def get_tool_list(space_type, context_mode):
    from bl_ui.space_toolsystem_common import ToolSelectPanelHelper
    cls = ToolSelectPanelHelper._tool_class_from_space_type(space_type)
    return cls._tools[context_mode]


def register_tool():
    tools = get_tool_list('VIEW_3D', 'EDIT_MESH')
    for index, tool in enumerate(tools, 1):
        if isinstance(tool, ToolDef) and tool.label == "Cursor":
            break
    tools[:index] += None, perfect_select_tool


def unregister_tool():
    tools = get_tool_list('VIEW_3D', 'EDIT_MESH')

    index = tools.index(perfect_select_tool) - 1
    tools.pop(index)
    tools.remove(perfect_select_tool)

    active_tool = bpy.context.workspace.tools.from_space_view3d_mode("EDIT_MESH", create=False)
    if active_tool is not None and active_tool.idname == "perfect_select.perfect_select_tool":
        bpy.ops.wm.tool_set_by_id(name="builtin.select_circle")


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


def perfect_select_draw_callback(self, context):
    if context.area != self.draw_area:
        return

    co = (self.x, self.y)
    if self._snap_point:
        co = self._snap_point
        snap_color = (*bpy.context.preferences.themes[0].view_3d.vertex_select, 1.0)
        draw_circle_2d(co, snap_color, 6, 16)
    draw_circle_2d(co, (1.0,) * 4, self.radius, 32)


def register():
    from bl_ui.space_toolsystem_common import _icon_cache
    bpy.types.VIEW3D_PT_snapping.append(perfect_select_snapping_panel)
    bpy.types.VIEW3D_MT_select_edit_mesh.append(perfect_select_menu)

    icon_filename = os.path.join(os.path.dirname(__file__), "datafiles", "ops.perfect_select.perfect_select.dat")
    _icon_cache['ops.perfect_select.perfect_select'] = bpy.app.icons.new_triangles_from_file(icon_filename)
    register_tool()


def unregister():
    unregister_tool()
    bpy.types.VIEW3D_PT_snapping.remove(perfect_select_snapping_panel)
    bpy.types.VIEW3D_MT_select_edit_mesh.remove(perfect_select_menu)

