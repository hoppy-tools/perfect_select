import os

import bpy
import bgl
import gpu

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


def register():
    global preview_collection, PREVIEW_SHADER_VERT, PREVIEW_SHADER_FRAG
    preview_collection = previews.new()

    with open(os.path.abspath(os.path.join(__file__, '..', 'shaders', 'preview.vert')), "r") as file:
        PREVIEW_SHADER_VERT = file.read()

    with open(os.path.abspath(os.path.join(__file__, '..', 'shaders', 'preview.frag')), "r") as file:
        PREVIEW_SHADER_FRAG = file.read()


def unregister():
    global preview_collection, PREVIEW_SHADER_VERT, PREVIEW_SHADER_FRAG
    preview_collection.close()
    preview_collection = None
    PREVIEW_SHADER_VERT = None
    PREVIEW_SHADER_FRAG = None

