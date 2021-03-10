import os
import bpy

from bpy.types import WorkSpaceTool
from gpu_extras.presets import draw_circle_2d
from bl_keymap_utils.io import keyconfig_init_from_data
from bl_ui.space_toolsystem_common import _icon_cache

from .previews import get_preview


keymaps = []


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
    bl_widget = None
    bl_keymap = "perfect_select.perfect_select_keymap"

    def draw_settings(context, layout, tool):
        reg = context.region.type
        is_header = reg == 'TOOL_HEADER'

        props = tool.operator_properties("perfect_select.perfect_select")
        row = layout.row()
        row.use_property_split = False
        row.prop(props, "mode", text="", expand=True, icon_only=True)
        row.separator(factor=1.0)

        sub = row.row()
        sub.scale_x = 0.5
        sub.label(icon='MOD_MIRROR')
        sub.separator(factor=0)
        sub.prop(props, "mirror", expand=True, toggle=True, text="")

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
        ps_tool_settings = context.scene.perfect_select_tool_settings
        if ps_tool_settings.show_select_cursor:
            ps_tool_settings.update_snap_co(xy)
            props = tool.operator_properties("perfect_select.perfect_select")
            draw_circle_2d(xy, (1.0,) * 4, props.radius, 32)


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
    bpy.types.VIEW3D_PT_snapping.append(perfect_select_snapping_panel)
    bpy.types.VIEW3D_MT_select_edit_mesh.append(perfect_select_menu)

    icon_filename = os.path.join(os.path.dirname(__file__), "datafiles", "ops.perfect_select.perfect_select.dat")
    _icon_cache['ops.perfect_select.perfect_select'] = bpy.app.icons.new_triangles_from_file(icon_filename)
    register_keymaps()
    bpy.utils.register_tool(PerfectSelectTool, after={"builtin.select_lasso"}, separator=False, group=False)


def unregister():
    bpy.utils.unregister_tool(PerfectSelectTool)
    unregister_keymaps()
    bpy.types.VIEW3D_PT_snapping.remove(perfect_select_snapping_panel)
    bpy.types.VIEW3D_MT_select_edit_mesh.remove(perfect_select_menu)
