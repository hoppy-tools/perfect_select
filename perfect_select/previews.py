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
    vertex_shader = '''
        in vec2 pos;
        in vec2 texCoord;

        out vec2 uvInterp;

        void main()
        {
            uvInterp = texCoord;
            gl_Position = vec4(pos, 0.0, 1.0);
        }
    '''

    fragment_shader = '''
        uniform sampler2D image;
        uniform vec4 pattern_color;
        uniform float check_size;

        in vec2 uvInterp;
        
        float dist(vec2 p0, vec2 pf)
        {
            return sqrt((pf.x-p0.x)*(pf.x-p0.x)+(pf.y-p0.y)*(pf.y-p0.y));
        }
        
        vec4 checker(vec2 uv, float check_size)
        {
          uv -= 0.5;
          
          float result = mod(floor(check_size * uv.x) + floor(check_size * uv.y), 2.0);
          float fin = sign(result);
          return vec4(fin, fin, fin, 1.0);
        }
        
        void main()
        {
            vec4 texture_color = texture(image, uvInterp);
            if(texture_color.w == 0.0){
                discard;
            }
            if(texture_color.xyz == vec3(1.0, 1.0, 1.0)) {
                discard;
            }
            
            vec2 res = vec2(512, 512);            
            vec4 final_color = pattern_color;
            float d = dist(res.xy*0.5, gl_FragCoord.xy)*0.001;
            final_color = mix(pattern_color, vec4(pattern_color.xyz*0.3, 1.0), d);

            texture_color = mix(checker(uvInterp, check_size), final_color, 0.9);
            
            gl_FragColor = texture_color;
        }
    '''

    shader = gpu.types.GPUShader(vertex_shader, fragment_shader)
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
    global preview_collection
    preview_collection = previews.new()


def unregister():
    global preview_collection
    preview_collection.close()
    preview_collection = None
