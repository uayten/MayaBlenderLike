"""MayaBlenderLike: Blender-style hotkeys, viewport navigation and grid for Maya."""
from maya import cmds

from . import config


def startup():
    """Apply every enabled feature. Called once by userSetup.py when Maya starts."""
    if cmds.about(batch=True):
        return

    if config.ENABLE_HOTKEYS:
        _run("hotkeys", lambda: _import("hotkeys").apply())
    if config.ENABLE_NAVIGATION:
        _run("navigation", lambda: _import("navigation").install())
    if config.ENABLE_GRID:
        _run("grid", lambda: _import("grid").apply())
    if config.ENABLE_LAYOUT or config.ENABLE_COLORS:
        _run("interface", lambda: _import("interface").apply())


def _import(name):
    import importlib
    return importlib.import_module(__name__ + "." + name)


def _run(feature, action):
    # One broken feature must not stop the others from loading.
    try:
        action()
        print("MayaBlenderLike: {} applied".format(feature))
    except Exception as error:
        cmds.warning("MayaBlenderLike: {} failed: {}".format(feature, error))
