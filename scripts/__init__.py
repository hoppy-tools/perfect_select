bl_info = {
    "name": "Perfect Select",
    "author": "Dawid Czech",
    "version": (1, 1),
    "blender": (2, 83, 0),
    "category": "Mesh",
}

from bpy import utils
from .backend import get_default_module_name


submodules = ['properties', 'operators', 'previews', 'user_interface']

register, unregister = utils.register_submodule_factory(__name__, submodules)
