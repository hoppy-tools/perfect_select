import bpy
import bmesh

from itertools import chain

from bpy.types import Operator
from mathutils import Vector, Matrix

from .properties import (PerfectSelectOperatorProperties, ExtendToEdgeLoopsOperatorProperties,
                         get_selection_pattern_buffer)
from .user_interface import perfect_select_draw_callback
from .math_utils import (matrix_decompose_4x4, is_backface, create_kdtree, intersect_point_section_2d,
                         points_3d_to_region_2d, points_pairs_3d_to_region_2d, region_2d_to_points_3d)


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
        self._bms = {}
        original_faces_selection = []
        original_select_modes = []
        tool_select_mode = context.tool_settings.mesh_select_mode[:]
        context.tool_settings.mesh_select_mode = (False, True, True)
        for obj in context.objects_in_mode_unique_data:
            obj.update_from_editmode()
            bm = self._bms[obj] = bmesh.from_edit_mesh(obj.data)
            original_faces_selection.append([f for f in bm.faces if f.select])
            original_select_modes.append(bm.select_mode)

        bpy.ops.mesh.region_to_loop('EXEC_DEFAULT')

        obj_selected_edges = []
        for obj, bm in self._bms.items():
            selected_edges = [e for e in bm.edges if e.select]
            self.tag_boundary_loops(bm)
            obj_selected_edges.append(selected_edges)

        bpy.ops.mesh.select_all(action='DESELECT')
        context.tool_settings.mesh_select_mode = tool_select_mode

        for idx, (obj, bm) in enumerate(self._bms.items()):
            original_faces = original_faces_selection[idx]
            selected_edges = obj_selected_edges[idx]

            self.search_in_outer_faces(selected_edges, original_faces, select=True)

            bm.select_mode = original_select_modes[idx]
            bm.select_flush_mode()

            self.clean_tags(bm)

        return {'FINISHED'}

    @classmethod
    def search_in_outer_faces(self, selected_edges, selected_faces,  *, select=False):
        outer_faces = []
        for edge in selected_edges:
            for face in edge.link_faces:
                if face not in outer_faces and face not in selected_faces:
                    outer_faces.append(face)

        faces_to_select = []
        while outer_faces:
            face = outer_faces.pop()
            face_verts_on_selection = [v for e in face.edges for v in e.verts if e in selected_edges]

            counter = 0
            for edge in face.edges:
                if edge in selected_edges:
                    counter += 1
                if counter <= 1 and any(True for v in edge.verts if v in face_verts_on_selection):
                    continue
                if counter > 1 or edge.tag:
                    break
            else:
                continue

            faces_to_select.append(face)
            if select:
                face.select = True

            selected_faces.append(face)
            for edge in face.edges:
                if edge in selected_edges:
                    selected_edges.remove(edge)
                else:
                    selected_edges.append(edge)
                    for _face in edge.link_faces:
                        if _face not in outer_faces and _face not in faces_to_select and _face not in selected_faces:
                            outer_faces.append(_face)
        if select:
            for face in selected_faces:
                face.select = True

        return faces_to_select

    @classmethod
    def tag_boundary_loops(cls, bm):
        bpy.ops.mesh.loop_multi_select('EXEC_DEFAULT')
        for e in bm.edges:
            if e.select:
                e.tag = True

    @staticmethod
    def clean_tags(bm):
        for e in bm.edges:
            if e.tag:
                e.tag = False


class PERFECT_SELECT_OT_perfect_select(PerfectSelectOperatorProperties, Operator):
    bl_label = "Perfect Select"
    bl_idname = "perfect_select.perfect_select"
    bl_options = {'UNDO'}

    @staticmethod
    def _get_mouse_region_pos(event):
        return event.mouse_region_x, event.mouse_region_y

    def select_operator(self, x=None, y=None, radius=None, mode=None):
        x = x or self.x
        y = y or self.y
        radius = radius or self.radius
        mode = mode or self.mode

        tool_settings = bpy.context.scene.perfect_select_tool_settings
        if self.wait_for_input or tool_settings.pattern_source == "CIRCLE":
            bpy.ops.view3d.select_circle('EXEC_DEFAULT', x=x, y=y,
                                         wait_for_input=False, mode=mode, radius=radius)
        else:
            bpy.ops.view3d.select_box('EXEC_DEFAULT', xmin=x-radius, xmax=x+radius, ymin=y-radius, ymax=y+radius,
                                      wait_for_input=False, mode=mode)

    def extend_operator(self):
        if self._extend_to_loop:
            bpy.ops.perfect_select.extend_to_edge_loops('EXEC_DEFAULT')

    def _get_select_args(self, context):
        ps_tool_settings = self._get_tool_settings(context)
        use_snap = context.tool_settings.use_snap and ps_tool_settings.use_snap_perfect_select
        snap_edge_slide = ps_tool_settings.use_snap_edge_slide
        snap_elements = context.tool_settings.snap_elements
        snap_backface_culling = context.tool_settings.use_snap_backface_culling
        return context, use_snap, snap_elements, snap_edge_slide, snap_backface_culling

    def _init_loop(self, region, rv3d, mtx, mtx_sr, backface_culling=False):
        bpy.ops.mesh.select_all(action='DESELECT')
        self._snap_edge.select = True
        bpy.ops.mesh.loop_multi_select()

        eye = Vector(rv3d.view_matrix[2][:3])
        if not rv3d.is_perspective:
            eye.length = 10000  # change to clip_end
        else:
            eye.length = rv3d.view_distance
        eye_location = rv3d.view_location + eye

        if backface_culling:
            self._loop = [e for e in self._get_bms_selected_edges() if not is_backface(e.verts[0], eye_location, mtx, mtx_sr)]
        else:
            self._loop = [e for e in self._get_bms_selected_edges()]
        self._loop_2d = points_pairs_3d_to_region_2d(((mtx @ e.verts[0].co, mtx @ e.verts[1].co) for e in self._loop),
                                                     region, rv3d)

    def _del_loop(self):
        self._loop = None
        self._loop_2d = None

    def _filter_loop_edges(self, edges):
        return (e for e in edges if e in self._loop)

    def _get_bms_selected_verts(self, return_co_list=False):
        if not return_co_list:
            return [v for bm in self._bms.values() for v in bm.verts if v.select]

        def _add_to_co_list(v, obj, _co_list):
            _co_list.append(obj.matrix_world @ v.co)
            return v

        co_list = []
        verts = [_add_to_co_list(v, obj, co_list) for obj, bm in self._bms.items() for v in bm.verts if v.select]
        return verts, co_list

    def _get_bms_selected_edges(self, return_co_list=False):
        if not return_co_list:
            return [e for bm in self._bms.values() for e in bm.edges if e.select]

        def _add_to_co_list(e, obj, _co_list):
            _co_list.append((obj.matrix_world @ e.verts[0].co, obj.matrix_world @ e.verts[1].co))
            return e

        co_list = []
        edges = [_add_to_co_list(e, obj, co_list) for obj, bm in self._bms.items() for e in bm.edges if e.select]
        return edges, co_list

    def _get_bms_selected_faces(self):
        return [f for bm in self._bms.values() for f in bm.faces if f.select]

    def _get_bms_geom_iter(self, context):
        def _get_seqs(bm):
            if "VERT" in select_mode:
                yield from bm.verts
            if "EDGE" in select_mode:
                yield from bm.edges
            if "FACE" in select_mode:
                yield from bm.faces

        select_mode = self._bms[context.object].select_mode
        return (g for bm in self._bms.values() for g in chain(_get_seqs(bm)))

    def _snap(self, co, pos, vert, vert_co, mtx, mtx_sr, selection_normal, view_location, snap_elements, snap_edge_slide,
              snap_backface_culling, region, rv3d):
        pos_2d = Vector(pos[:2])
        points = []
        if "VERTEX" in snap_elements:
            points.append(Vector(co[:2]))
            selection_normal = vert.normal
            view_location = vert_co
        if any(e in snap_elements for e in ("EDGE", "EDGE_MIDPOINT", "EDGE_PERPENDICULAR")):
            edges = vert.link_edges
            if snap_edge_slide and self._snap_edge:
                if self._loop is None:
                    self._init_loop(region, rv3d, mtx, mtx_sr, snap_backface_culling)

                edges_co = [(mtx @ e.verts[0].co, mtx @ e.verts[1].co) for e in self._filter_loop_edges(edges)]
                if not edges_co:
                    edges = self._loop
                    edges_co_2d = self._loop_2d
                else:
                    edges_co_2d = points_pairs_3d_to_region_2d(edges_co, region, rv3d)
            else:
                edges_co = [(mtx @ e.verts[0].co, mtx @ e.verts[1].co) for e in vert.link_edges]
                edges_co_2d = points_pairs_3d_to_region_2d(edges_co, region, rv3d)

            if edges_co_2d:
                closest_points = [(i, e, intersect_point_section_2d(pos_2d, e[0], e[1])[0]) for i, e in
                                  enumerate(edges_co_2d)]
                closest_points.sort(key=lambda i: (i[2] - pos_2d).length)
                closest_index, closest_edge_co, closest_point = closest_points[0]
                closest_edge = edges[closest_index]
                if snap_edge_slide:
                    self._snap_edge = closest_edge
                    self._snap_edge_co = (mtx @ closest_edge.verts[0].co, mtx @ closest_edge.verts[1].co)

                selection_normal = (mtx_sr @ closest_edge.verts[0].normal + mtx_sr @ closest_edge.verts[1].normal) / 2
                view_location = (mtx @ closest_edge.verts[0].co + mtx @ closest_edge.verts[1].co) / 2
                if "EDGE" in snap_elements:
                    points.append(closest_point)
                if "EDGE_MIDPOINT" in snap_elements:
                    closest_edge_co = edges_co_2d[closest_index]
                    points.append(closest_edge_co[0].lerp(closest_edge_co[1], 0.5))
                if "EDGE_PERPENDICULAR" in snap_elements:
                    points.append(closest_edge_co[0] if (closest_edge_co[0] - pos_2d).length < (
                            closest_edge_co[1] - pos_2d).length else closest_edge_co[1])

        if points:
            points.sort(key=lambda v: (Vector(v) - pos_2d).length)
            co = points[0]
            self._snap_point = co

        return co, selection_normal, view_location

    def _mirror(self, context):
        mirror_axis = set()
        if context.object.data.use_mirror_x:
            mirror_axis.update("X")
        if context.object.data.use_mirror_y:
            mirror_axis.update("Y")
        if context.object.data.use_mirror_z:
            mirror_axis.update("Z")
        if mirror_axis:
            for bm in self._bms.values():
                bm.select_mode = {"VERT", "FACE", "EDGE"}
            bpy.ops.mesh.select_mirror(axis=mirror_axis, extend=True)
            self._select_flush()

    def _select_flush(self, value=True):
        for idx, bm in enumerate(self._bms.values()):
            bm.select_mode = self._bms_select_mode[idx]
            bm.select_flush_mode()
            bm.select_flush(value)

    def select(self, context, use_snap, snap_elements, snap_edge_slide, snap_backface_culling):
        def _set_original_selection(geom, force=False):
            if self._geom_selected_original is None or force:
                self._geom_selected_original = geom

        def _add_persistent_selection(geom):
            for geom_element in geom:
                geom_element.tag = True

        def _select(geom, value):
            for element in geom:
                element.select = value

        def _select_original(value=True):
            _select(self._geom_selected_original, value)

        def _select_persistent(value=True):
            geom = (g for g in self._get_bms_geom_iter(context) if g.tag)
            _select(geom, value)

        def _pattern_filter():
            pattern_buffer = self._pattern_buffer
            if pattern_buffer is None:
                return

            ps_tool_settings = self._get_tool_settings(context)
            resolution = ps_tool_settings.pattern_resolution - 1
            _verts, _verts_co = self._get_bms_selected_verts(True)

            radius = self.radius
            points_2d = points_3d_to_region_2d(_verts_co, region, rv3d)

            for idx, _co in enumerate(points_2d):
                _w = max(min((_co[0] - (co[0] - radius)) / (radius*2), 1.0), 0.0)
                _h = max(min((_co[1] - (co[1] - radius)) / (radius*2), 1.0), 0.0)
                _w = int(resolution * _w)
                _h = int(resolution * _h)
                if not pattern_buffer[_w][_h]:
                    _verts[idx].select = False
            self._select_flush(False)

        co = pos = Vector((self.x, self.y, 0.0))

        rv3d = context.space_data.region_3d
        region = context.region
        view_location = Vector((0.0, 0.0, 0.0))
        selection_normal = None

        if self._bms is None:
            self._bms = {}
            self._bms_select_mode = []
            for obj in context.objects_in_mode_unique_data:
                obj.update_from_editmode()
                self._bms[obj] = bmesh.from_edit_mesh(obj.data)
                self._bms_select_mode.append(self._bms[obj].select_mode)

        if self.mode == "SET" and not self._set_continue:
            bpy.ops.mesh.select_all(action='DESELECT')

        _set_original_selection([g for g in self._get_bms_geom_iter(context) if g.select])

        self.select_operator(mode="SET")
        if use_snap or self.align_to_normal:
            snap_edge = self._snap_edge
            snap_edge_co = self._snap_edge_co

            verts_selected, verts_co_selected = self._get_bms_selected_verts(True)

            index = 0
            restore_values = False
            if verts_co_selected:
                verts_co_2d = points_3d_to_region_2d(verts_co_selected, region, rv3d)
                kd = create_kdtree(verts_co_2d)
                co, index, dist = kd.find(co)
                if co is None:
                    restore_values = True
            if restore_values:
                co, index = pos, 0

            vert = verts_selected[index] if verts_selected else None
            if vert is None and snap_edge is not None:
                points_3d = region_2d_to_points_3d(pos[:2], region, rv3d)
                len_0 = (snap_edge_co[0] - points_3d).length
                len_1 = (snap_edge_co[1] - points_3d).length
                _index = int(len_0 > len_1)
                vert = snap_edge.verts[_index]
            if vert is not None:
                mtx = Matrix()
                for obj, bm in self._bms.items():
                    if vert in bm.verts:
                        mtx = obj.matrix_world
                        break
                mtx_t, mtx_s, mtx_r = matrix_decompose_4x4(mtx)
                mtx_sr = mtx_s @ mtx_r
                vert_co = mtx @ vert.co
                if use_snap:
                    co, selection_normal, view_location = self._snap(co, pos, vert, vert_co, mtx, mtx_sr,
                                                                     selection_normal,
                                                                     view_location,
                                                                     snap_elements, snap_edge_slide,
                                                                     snap_backface_culling,
                                                                     region, rv3d)
                else:
                    self._snap_point = None
                    view_location = vert_co
                    link_faces = vert.link_faces
                    if link_faces:
                        n = Vector((0.0, 0.0, 0.0))
                        for f in link_faces:
                            n += mtx_sr @ f.normal
                        selection_normal = n / len(link_faces)

        if self._snap_point:
            co = self._snap_point
            self.select_operator(co[0], co[1], mode="SET")

        if self.align_to_normal and not self.wait_for_input and selection_normal is not None:
            bpy.ops.mesh.select_all(action='DESELECT')
            old_view_location = rv3d.view_location.copy()
            rv3d.view_location = view_location

            old_view_rotation = rv3d.view_rotation.copy()
            view_rotation = selection_normal.rotation_difference(Vector((0, 0, 1)))
            rv3d.view_rotation = view_rotation.inverted()

            rv3d.update()
            self.select_operator(context.region.width / 2, context.region.height / 2, mode="SET")
            _pattern_filter()
            rv3d.view_location = old_view_location
            rv3d.view_rotation = old_view_rotation
            rv3d.update()
        else:
            _pattern_filter()

        self._mirror(context)

        if self.use_preselect and not self.wait_for_input:
            self._clean_tags(context)

        _add_persistent_selection(g for g in self._get_bms_geom_iter(context) if g.select)

        if self.mode == "ADD":
            _select_persistent(True)
            self.extend_operator()
            _select_original()
        elif self.mode == "SUB":
            sub_extra_selection = []
            if self._extend_to_loop:
                _select_persistent(True)
                self.extend_operator()
                sub_extra_selection = [g for g in self._get_bms_geom_iter(context) if g.select]
                _select_original()
            else:
                _select_original()
                _select_persistent(False)
            if sub_extra_selection:
                _select(sub_extra_selection, False)
        else:
            _select_persistent(True)
            self.extend_operator()

        self._select_flush()
        self._set_continue = True

        if self.wait_for_input:
            _set_original_selection([g for g in self._get_bms_geom_iter(context) if g.select], True)
            self._clean_tags(context)

    def _clean(self):
        self._del_loop()
        self._snap_point = None
        self._snap_edge = None
        self._snap_edge_co = None

    def _clean_tags(self, context):
        tagged_geom = (g for g in self._get_bms_geom_iter(context) if g.tag)
        for geom_element in tagged_geom:
            geom_element.tag = False

    def _clean_status_text(self, context):
        context.workspace.status_text_set(None)

    def _get_tool_settings(self, context):
        return context.scene.perfect_select_tool_settings

    def _get_ps_tool(self, context):
        tool = context.workspace.tools.from_space_view3d_mode(context.mode)
        return tool if tool.idname == "perfect_select.perfect_select_tool" else None

    def _check_init_attribs(self):
        names = ("_set_continue", "_bms", "_snap_point", "_snap_edge", "_snap_edge_co", "_loop",
                 "_geom_selected_original", "_extend_to_loop", "_select_enabled", "_pattern_buffer")
        for name in names:
            if not hasattr(self, name):
                setattr(self, name, None)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT'

    def invoke(self, context, event):
        self._check_init_attribs()
        self.draw_area = context.area
        self.x, self.y = self._get_mouse_region_pos(event)
        ps_tool_settings = self._get_tool_settings(context)
        ps_tool_settings.show_select_cursor = False

        if not self.wait_for_input:
            if ps_tool_settings.pattern_source in ("OBJECT", "IMAGE"):
                self._pattern_buffer = get_selection_pattern_buffer(ps_tool_settings.pattern_resolution)

            if self.mode == "SET":
                tool = self._get_ps_tool(context)
                if tool is not None:
                    props = tool.operator_properties("perfect_select.perfect_select")
                    self.mode = props.mode
            self.execute(context)
        else:
            self._select_enabled = False

        wm = context.window_manager
        if context.area.type == 'VIEW_3D':
            ws = context.workspace
            ws.status_text_set(self._get_status_text())

            handler_args = (self, context)
            self._draw_handle = bpy.types.SpaceView3D.draw_handler_add(perfect_select_draw_callback,
                                                                       handler_args,
                                                                       'WINDOW', 'POST_PIXEL')
            wm.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    def execute(self, context):
        self._check_init_attribs()
        self.select(*self._get_select_args(context))
        return {'FINISHED'}

    def modal(self, context, event):
        context.area.tag_redraw()
        ps_tool_settings = self._get_tool_settings(context)

        if not self.wait_for_input and event.type in ['LEFT_SHIFT', 'LEFT_CTRL']:
            if event.value == 'PRESS':
                self._extend_to_loop = event.shift
            if event.value == 'RELEASE':
                self._extend_to_loop = None

        if event.type in {'RIGHTMOUSE', 'ESC'}:
            bpy.types.SpaceView3D.draw_handler_remove(self._draw_handle, 'WINDOW')
            ps_tool_settings.show_select_cursor = True
            self._clean_status_text(context)
            self._clean_tags(context)
            return {'CANCELLED'}

        if event.type in ['MOUSEMOVE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'LEFT_SHIFT', 'LEFT_CTRL']:
            self.x, self.y = self._get_mouse_region_pos(event)
            if (self.wait_for_input and self._select_enabled) or not self.wait_for_input:
                self.execute(context)

        if event.type in ('WHEELUPMOUSE', 'WHEELDOWNMOUSE') and not event.ctrl:
            self.radius += 5 if event.type == 'WHEELDOWNMOUSE' else -5
            return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self._select_enabled = True
            if event.shift and self.wait_for_input:
                self.mode = "SUB"
            self.execute(context)

        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            if self.wait_for_input:
                self._select_enabled = False
                self.mode = "ADD"
                self._clean()
                return {'RUNNING_MODAL'}
            else:
                self._clean_status_text(context)

            self.wait_for_input = True
            self.mode = "ADD"
            bpy.types.SpaceView3D.draw_handler_remove(self._draw_handle, 'WINDOW')
            ps_tool_settings.show_select_cursor = True
            self._clean_tags(context)
            return {'FINISHED'}

        if event.type == 'LEFTMOUSE' and event.shift and event.value == 'RELEASE':
            if self.wait_for_input:
                self._select_enabled = False
                self.mode = "ADD"
                self._clean()
                return {'RUNNING_MODAL'}

        if event.type == "RET" and event.value == 'PRESS':
            bpy.types.SpaceView3D.draw_handler_remove(self._draw_handle, 'WINDOW')
            self.wait_for_input = True
            ps_tool_settings.show_select_cursor = True
            self._clean_tags(context)
            return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def _get_status_text(self):
        elements = [("WhDown/Pad+", "Add"),
                    ("WhUp/Pad-", "Subtract")]

        if self.wait_for_input:
            release_elements = [("ESC/RMB", "Cancel"),
                                ("Enter↵", "Confirm")]
            input_elements = [("LMB", "Select"), ("Shift⇧ LMB", "Deselect")]
            elements = release_elements + elements + input_elements
        else:
            extend_elements = [("Shift⇧", "Extend to Boundary Loops"),
                               # ("Ctrl", "Reduce to Boundary Loops")
                               ]
            elements.extend(extend_elements)

        return "        ".join("[{}] {}".format(*e) for e in elements)


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


keymaps = []


def register_keymaps():
    from bl_keymap_utils.io import keyconfig_init_from_data
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
        kc.keymaps.remove(km)


def register():
    from bpy.utils import register_class
    register_class(PERFECT_SELECT_OT_extend_to_edge_loops)
    register_class(PERFECT_SELECT_OT_perfect_select)
    register_keymaps()


def unregister():
    from bpy.utils import unregister_class
    unregister_class(PERFECT_SELECT_OT_perfect_select)
    unregister_class(PERFECT_SELECT_OT_extend_to_edge_loops)
    unregister_keymaps()
