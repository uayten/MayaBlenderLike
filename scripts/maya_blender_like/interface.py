"""Blender-like layout and colors: Outliner on the right above the Channel Box, gray viewport, orange selection."""
from maya import cmds

from . import config

LAYOUT_NAME = "Blender Like"

# Blender's default theme, as 0-1 RGB.
VIEWPORT_BACKGROUND = (0.239, 0.239, 0.239)   # #3D3D3D
LEAD_SELECTION = (1.0, 0.667, 0.251)          # active object, #FFAA40


def apply_layout():
    """Create the Blender Like workspace once and make it current. Later edits are yours: save them in Maya."""
    if LAYOUT_NAME in (cmds.workspaceLayoutManager(listLayouts=True) or []):
        cmds.workspaceLayoutManager(setCurrent=LAYOUT_NAME)
        return
    if not cmds.workspaceControl("Outliner", exists=True):
        cmds.OutlinerWindow()
    # Outliner goes above the Channel Box / Attribute Editor, like Blender's Outliner over Properties.
    cmds.workspaceControl("Outliner", edit=True, dockToControl=("ChannelBoxLayerEditor", "top"))
    cmds.workspaceLayoutManager(saveAs=LAYOUT_NAME)
    cmds.workspaceLayoutManager(setCurrent=LAYOUT_NAME)


def apply_colors():
    cmds.displayPref(displayGradient=False)
    cmds.displayRGBColor("background", *VIEWPORT_BACKGROUND)
    cmds.displayRGBColor("lead", *LEAD_SELECTION)


def toggle_grid_snap():
    """Blender's Shift+Tab: toggle snapping (grid snap in Maya)."""
    enabled = not cmds.snapMode(query=True, grid=True)
    cmds.snapMode(grid=enabled)
    cmds.headsUpMessage("Grid snap " + ("on" if enabled else "off"), time=1.0)


def apply():
    if config.ENABLE_LAYOUT:
        apply_layout()
    if config.ENABLE_COLORS:
        apply_colors()
