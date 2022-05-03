import os

import bpy
import bgl
import gpu
import numpy

from math import radians

from bpy.utils import previews
from mathutils import Matrix, Vector, Color, Euler
from gpu_extras.batch import batch_for_shader


PREVIEW_WIDTH = 512
PREVIEW_HEIGHT = 512


PREVIEW_SHADER_VERT = None
PREVIEW_SHADER_FRAG = None

preview_collection = None


def get_preview():
    preview_name = "select"
    if preview_name in preview_collection:
        preview = preview_collection.get(preview_name)
    else:
        preview = preview_collection.new(preview_name)
        preview.image_size = (PREVIEW_WIDTH, PREVIEW_HEIGHT)
    return preview


def render(image, check_size):
    shader = gpu.types.GPUShader(PREVIEW_SHADER_VERT, PREVIEW_SHADER_FRAG)
    batch = batch_for_shader(
        shader, 'TRI_FAN',
        {
            "pos": ((-1, -1), (1, -1), (1, 1), (-1, 1)),
            "texCoord": ((0, 0), (1, 0), (1, 1), (0, 1)),
        },
    )
    if image.gl_load():
        return

    offscreen = gpu.types.GPUOffScreen(PREVIEW_WIDTH, PREVIEW_HEIGHT)
    with offscreen.bind():
        bgl.glActiveTexture(bgl.GL_TEXTURE0)
        bgl.glBindTexture(bgl.GL_TEXTURE_2D, image.bindcode)
        shader.bind()
        shader.uniform_int("image", 0)
        shader.uniform_float("pattern_color", get_active_color())
        shader.uniform_float("check_size", check_size)
        batch.draw(shader)

        buffer = bgl.Buffer(bgl.GL_FLOAT, PREVIEW_WIDTH * PREVIEW_HEIGHT * 4)
        bgl.glReadBuffer(bgl.GL_BACK)
        bgl.glReadPixels(0, 0, PREVIEW_WIDTH, PREVIEW_HEIGHT, bgl.GL_RGBA, bgl.GL_FLOAT, buffer)

    offscreen.free()
    image.gl_free()
    return buffer


def render_preview(scene=None, obj=None, camera_obj=None, axis=None, resolution=512, only_chess=False):
    preview = get_preview()
    if only_chess:
        image = bpy.data.images.new("_tmp_perfect_select_img", PREVIEW_WIDTH, PREVIEW_HEIGHT, alpha=True)
        image.pixels = preview.image_pixels_float[:]
    elif obj.bl_rna.name == "Image":
        image = obj.copy()
        image.scale(PREVIEW_WIDTH, PREVIEW_HEIGHT)
    else:
        image = bpy.data.images.new("_tmp_perfect_select_img", PREVIEW_WIDTH, PREVIEW_HEIGHT, alpha=True)
        bound_box = [Vector(b) for b in obj.bound_box]
        cam_center = Vector()
        for b in bound_box:
            cam_center += b
        bounds_center = cam_center / len(bound_box)

        camera_obj.location = bounds_center
        bound_x_len = max(0.1, (bound_box[0] - bound_box[4]).length)
        bound_y_len = max(0.1, (bound_box[0] - bound_box[3]).length)
        bound_z_len = max(0.1, (bound_box[0] - bound_box[1]).length)
        if axis == "X":
            camera_obj.location[0] -= bound_x_len
            camera_obj.rotation_euler = Euler((radians(90), 0.0, -radians(90)), 'XYZ')
            camera_obj.data.ortho_scale = max(bound_y_len, bound_z_len)
        elif axis == "-X":
            camera_obj.location[0] += bound_x_len
            camera_obj.rotation_euler = Euler((radians(90), 0.0, radians(90)), 'XYZ')
            camera_obj.data.ortho_scale = max(bound_y_len, bound_z_len)

        elif axis == "Y":
            camera_obj.location[1] -= bound_y_len
            camera_obj.rotation_euler = Euler((radians(90), 0.0, 0.0), 'XYZ')
            camera_obj.data.ortho_scale = max(bound_x_len, bound_z_len)
        elif axis == "-Y":
            camera_obj.location[1] += bound_y_len
            camera_obj.rotation_euler = Euler((radians(90), 0.0, radians(180)), 'XYZ')
            camera_obj.data.ortho_scale = max(bound_x_len, bound_z_len)

        elif axis == "Z":
            camera_obj.location[2] += bound_z_len
            camera_obj.rotation_euler = Euler((0.0, 0.0, 0.0), 'XYZ')
            camera_obj.data.ortho_scale = max(bound_x_len, bound_y_len)
        elif axis == "-Z":
            camera_obj.location[2] -= bound_z_len
            camera_obj.rotation_euler = Euler((radians(180), 0.0, 0.0), 'XYZ')
            camera_obj.data.ortho_scale = max(bound_x_len, bound_y_len)

        _get_render_result(scene, image)

    buffer = render(image, 64 / (512/resolution))
    if buffer is not None:
        preview.image_pixels_float = buffer

    bpy.data.images.remove(image)
    return buffer


def _get_render_result(scene, image):
    scene.use_nodes = True
    tree = bpy.context.scene.node_tree
    links = tree.links

    remove_viewer = 'Viewer Node' not in bpy.data.images

    for n in tree.nodes:
        tree.nodes.remove(n)

    rl = tree.nodes.new('CompositorNodeRLayers')
    v = tree.nodes.new('CompositorNodeViewer')
    v.use_alpha = True
    links.new(rl.outputs[0], v.inputs[0])

    bpy.ops.render.render()

    viewer = bpy.data.images['Viewer Node']
    image.pixels = viewer.pixels[:]

    if remove_viewer:
        bpy.data.images.remove(viewer)


def get_active_color(alpha=1.0):
    return (*bpy.context.preferences.themes[0].view_3d.vertex_select, alpha)


#
# Properties functions
#

def _create_tmp_scene_and_render(context, obj, axis, resolution):
    scene = bpy.data.scenes.new("_tmp_perfect_select")
    original_scene = bpy.context.window.scene
    context.window.scene = scene

    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.film_transparent = True
    scene.display.render_aa = "OFF"

    new_obj = obj.copy()
    new_data = obj.data.copy()
    new_obj.data = new_data
    new_obj.location = (0.0, 0.0, 0.0)
    new_obj.rotation_euler.zero()
    new_obj.scale = (1.0, 1.0, 1.0)
    scene.collection.objects.link(new_obj)

    camera = bpy.data.cameras.new("_tmp_perfect_select_camera")
    camera.type = 'ORTHO'
    camera_obj = bpy.data.objects.new("_tmp_perfect_select_camera", camera)
    camera_obj.location = (0.0, 0.0, 2.0)
    scene.collection.objects.link(camera_obj)
    scene.camera = camera_obj

    pixels = render_preview(scene, new_obj, camera_obj, axis, resolution)

    data_collections = {
        "MESH": bpy.data.meshes,
        "CURVE": bpy.data.curves,
        "SURFACE": bpy.data.curves,
        "FONT": bpy.data.curves,
        "GPENCIL": bpy.data.grease_pencils
    }

    scene.collection.objects.unlink(camera_obj)
    scene.collection.objects.unlink(new_obj)
    bpy.data.objects.remove(camera_obj)
    bpy.data.cameras.remove(camera)

    data_collection = data_collections.get(new_obj.type)
    bpy.data.objects.remove(new_obj)
    data_collection.remove(new_data)

    context.window.scene = original_scene
    bpy.data.scenes.remove(scene)

    return pixels


def _create_from_image_and_render(context, image, resolution):
    pixels = render_preview(None, image, None, None, resolution)
    return pixels


def update_preview(self, context):
    if self.pattern_source == "OBJECT":
        if self.pattern_data is None:
            return
        _create_tmp_scene_and_render(context, self.pattern_data, self.pattern_projection, self.pattern_resolution)
    elif self.pattern_source == "IMAGE":
        if self.pattern_data_image is None or not self.pattern_data_image.has_data:
            return
        _create_from_image_and_render(context, self.pattern_data_image, self.pattern_resolution)


def update_preview_chess(self, context):
    render_preview(resolution=self.pattern_resolution, only_chess=True)


def get_selection_pattern_buffer(resolution):
    preview = get_preview()
    pixels = preview.image_pixels_float
    pixels_buffer = numpy.asarray(pixels, dtype=numpy.bool)
    pixels_buffer = pixels_buffer[3::4]
    pixels_buffer = pixels_buffer.reshape((PREVIEW_WIDTH, PREVIEW_HEIGHT))
    pattern_buffer = numpy.asarray([[pixels_buffer[PREVIEW_WIDTH * h // resolution][PREVIEW_HEIGHT * w // resolution]
                                     for h in range(resolution)] for w in range(resolution)])
    return pattern_buffer


def register():
    global preview_collection, PREVIEW_SHADER_VERT, PREVIEW_SHADER_FRAG
    preview_collection = previews.new()

    with open(os.path.abspath(os.path.join(__file__, '..', 'shaders', 'image_preview.vert')), "r") as file:
        PREVIEW_SHADER_VERT = file.read()

    with open(os.path.abspath(os.path.join(__file__, '..', 'shaders', 'image_preview.frag')), "r") as file:
        PREVIEW_SHADER_FRAG = file.read()


def unregister():
    global preview_collection, PREVIEW_SHADER_VERT, PREVIEW_SHADER_FRAG
    preview_collection.close()
    preview_collection = None
    PREVIEW_SHADER_VERT = None
    PREVIEW_SHADER_FRAG = None
