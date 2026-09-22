"""Viewport grid sized for real-world objects in centimeters."""
from maya import cmds

from . import config


def apply():
    _set_grid()
    # Reapply after File > New and File > Open, in case the scene resets the grid.
    for event in ("NewSceneOpened", "SceneOpened"):
        cmds.scriptJob(event=[event, _set_grid])


def _set_grid():
    cmds.grid(size=config.GRID_HALF_SIZE_CM, spacing=config.GRID_SPACING_CM, divisions=config.GRID_DIVISIONS)
    cmds.grid(toggle=True)
