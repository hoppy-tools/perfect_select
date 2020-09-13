import bpy
import os
import numpy

from bpy.props import EnumProperty, BoolProperty, IntProperty, FloatVectorProperty, StringProperty, PointerProperty

from .previews import render_preview, get_preview, PREVIEW_WIDTH, PREVIEW_HEIGHT


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


def filter_objects(self, object):
    return object.type in ("MESH", "CURVE", "SURFACE", "FONT", "GPENCIL")


def filter_images(self, image):
    return image.type != 'RENDER_RESULT'


class ExtendToEdgeLoopsOperatorProperties:
    pass


class PerfectSelectOperatorProperties:
    x:                  IntProperty()
    y:                  IntProperty()
    mode:               EnumProperty(name="Mode",
                                     items=(("SET", "Set", "Set a new selection", "SELECT_SET", 0),
                                            ("ADD", "Extend", "Extend existing selection", "SELECT_EXTEND", 1),
                                            ("SUB", "Subtract", "Subtract existing selection", "SELECT_SUBTRACT", 2)),
                                     default="SET")
    radius:             IntProperty(name="Radius", min=5, default=25)
    wait_for_input:     BoolProperty(default=True)
    align_to_normal:    BoolProperty(name="Align to normal", default=False,
                                     description="Align selection area to faces normal.")
    use_preselect:      BoolProperty(name="Preselect", default=False,
                                     description="Apply selection after button release.")


class PerfectSelectToolSettings(bpy.types.PropertyGroup):
    snap_loc:                   FloatVectorProperty(name="Snap Position", size=2)
    snap_enabled:               BoolProperty(name="Snap Enabled", default=False)
    use_snap_perfect_select:    BoolProperty(name="Perfect Select", default=True,
                                             description="Perfect Select is affected by snapping settings.")
    use_snap_edge_slide:        BoolProperty(name="Slide on edge loop", default=False,
                                             description="Slide on edge loop.")
    show_select_cursor:         BoolProperty(default=True)

    pattern_data:               PointerProperty(name="Object", description="Select pattern from object",
                                                update=update_preview, type=bpy.types.Object, poll=filter_objects)
    pattern_data_image:         PointerProperty(name="Image", description="Select pattern from image",
                                                update=update_preview, type=bpy.types.Image, poll=filter_images)
    pattern_resolution:         IntProperty(name="Resolution", min=32, max=512, default=256,
                                            update=update_preview_chess)
    pattern_projection:         EnumProperty(name="Projection",
                                             items=(("X", "Left", "Left"),
                                                    ("-X", "Right", "Right"),
                                                    ("Y", "Front", "Front"),
                                                    ("-Y", "Back", "Back"),
                                                    ("Z", "Top", "Top"),
                                                    ("-Z", "Bottom", "Bottom")),
                                             default="Y", update=update_preview)
    pattern_source:             EnumProperty(name="Pattern", description="Select Pattern",
                                             items=(("CIRCLE", "Circle", "Circle"),
                                                    ("BOX", "Box", "Box"),
                                                    ("OBJECT", "Object", "Object"),
                                                    ("IMAGE", "Image", "Image"),),
                                             default="CIRCLE", update=update_preview)


def register():
    bpy.utils.register_class(PerfectSelectToolSettings)
    bpy.types.Scene.perfect_select_tool_settings = bpy.props.PointerProperty(type=PerfectSelectToolSettings)


def unregister():
    del bpy.types.Scene.perfect_select_tool_settings
    bpy.utils.unregister_class(PerfectSelectToolSettings)
