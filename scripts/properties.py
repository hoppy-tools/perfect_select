import bpy

from bpy.props import (EnumProperty, BoolProperty, BoolVectorProperty,
                       IntProperty, FloatVectorProperty, StringProperty, PointerProperty)

from .backend import get_platform_backend_modules, get_default_module_name, import_backend_module
from .previews import update_preview, update_preview_chess
from .backend.utils import create_bvhtree, get_unique_objects


def filter_objects(self, object):
    return object.type in ("MESH", "CURVE", "SURFACE", "FONT", "GPENCIL")


def filter_images(self, image):
    return image.type != 'RENDER_RESULT'


class ExtendToEdgeLoopsOperatorProperties:
    inner: BoolProperty(default=False)


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
    mirror:             BoolVectorProperty(name="Mirror", default=(False, False, False),
                                           description="Selection mirror", subtype="XYZ")


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

    snap_bvh = None
    snap_co = None

    @classmethod
    def create_snap_bvh(cls):
        cls.snap_bvh = []
        for obj in get_unique_objects():
            cls.snap_bvh.append(create_bvhtree(obj, bpy.context.evaluated_depsgraph_get()))

    @classmethod
    def update_snap_co(cls, xy):
        if not cls.snap_bvh:
            cls.create_snap_bvh()


def update_backend_module(self, context):
    import_backend_module()


class PerfectSelectAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    default_backend_module = get_default_module_name()
    backend_module: bpy.props.EnumProperty(
        name="Backend Module",
        items=[("default", "Auto", f"Use {default_backend_module}" if default_backend_module else "Use Python"),
               ("none", "Python", "Use only python scripts - slower but version independent")
               ] + [(m, m, '') for m in get_platform_backend_modules()],
        update=update_backend_module
    )

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, 'backend_module')

        # if self.default_backend_module is None:
        #    addon_fake_module = addon_utils.addons_fake_modules['perfect_select']
        #    addon_fake_module.bl_info['warning'] = "Compiled module cannot be found. " \
        #                                           "Your Blender version may not be supported in this addon release."


def register():
    bpy.utils.register_class(PerfectSelectToolSettings)
    bpy.utils.register_class(PerfectSelectAddonPreferences)
    bpy.types.Scene.perfect_select_tool_settings = bpy.props.PointerProperty(type=PerfectSelectToolSettings)


def unregister():
    del bpy.types.Scene.perfect_select_tool_settings
    bpy.utils.unregister_class(PerfectSelectAddonPreferences)
    bpy.utils.unregister_class(PerfectSelectToolSettings)
