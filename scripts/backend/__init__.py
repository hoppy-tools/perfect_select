import sys
import bpy
import importlib
import os
import glob

backend_module = None


def get_platform_backend_modules(platform=sys.platform):
    modules_dir = os.path.dirname(__file__)
    modules_search = "backend_module_v*_{platform}*".format(platform=platform)
    files = glob.glob(os.path.join(modules_dir, modules_search))
    return [os.path.basename(f).rsplit(".", 1).pop(0) for f in files]


def get_default_module_name():
    blender_version = bpy.app.version
    blender_version_strings = [str(i) for i in blender_version]
    platform_backend_modules = get_platform_backend_modules()
    platform_backend_modules = [m for m in platform_backend_modules if "_".join(blender_version_strings[:2]) in m]
    if platform_backend_modules:
        return platform_backend_modules[0]
    return None


def import_backend_module(module_name=None):
    global backend_module

    if module_name is None:
        module_name = bpy.context.preferences.addons["perfect_select"].preferences.backend_module
        if module_name == 'default':
            module_name = get_default_module_name()
    if module_name:
        try:
            backend_module = importlib.import_module(f"perfect_select.backend.{module_name}")
        except ModuleNotFoundError:
            backend_module = None
    else:
        backend_module = None


def get_backend_module():
    return backend_module
