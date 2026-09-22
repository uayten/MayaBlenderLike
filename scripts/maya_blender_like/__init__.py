"""MayaBlenderLike: Blender-style hotkeys, viewport navigation and grid for Maya."""
from maya import cmds

from . import config


def startup():
    """Apply every enabled feature. Called once by userSetup.py when Maya's UI is up.

    Hotkeys, menus, grid and labels go in right away. The viewport event filter, which runs
    Maya commands on every mouse move over a viewport, waits until Maya has nothing left to
    load (Bifrost, USD, Arnold and other plugins keep loading after the window appears);
    until then the viewport behaves like stock Maya.
    """
    if cmds.about(batch=True):
        return

    if config.ENABLE_HOTKEYS:
        _run("hotkeys", lambda: _import("hotkeys").apply())
    if config.ENABLE_GRID:
        _run("grid", lambda: _import("grid").apply())
    if config.ENABLE_LAYOUT or config.ENABLE_COLORS:
        _run("interface", lambda: _import("interface").apply())
    _run("menu", lambda: _import("interface").create_main_menu())
    if config.ENABLE_MODE_INDICATOR:
        _run("mode indicator", lambda: _import("modes").install_indicator())
    _run("armature in front", lambda: _import("custom_shapes").install())
    if config.ENABLE_ARMATURE_MODES:
        _run("object / pose modes", lambda: _import("modes").install())

    # lowestPriority: runs only when Maya's queue is empty, i.e. after the plugins finish loading.
    cmds.evalDeferred(_start_viewport_filter, lowestPriority=True)


def _start_viewport_filter():
    if config.ENABLE_NAVIGATION:
        _run("navigation", lambda: _import("navigation").install())
    cmds.headsUpMessage("MayaBlenderLike ready", time=2.0)


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
