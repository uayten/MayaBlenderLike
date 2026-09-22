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


MENU_NAME = "MBL_MainMenu"


def create_main_menu():
    """A "Blender Like" menu in Maya's main menu bar with the module's panels and actions."""
    if cmds.menu(MENU_NAME, exists=True):
        cmds.deleteUI(MENU_NAME)
    cmds.menu(MENU_NAME, parent="MayaWindow", label="Blender Like", tearOff=True)
    items = [
        ("Constraints Panel", "import maya_blender_like.constraints_panel as p; p.show()"),
        ("Add Constraint (with Targets)   Shift+Ctrl+C", "import maya_blender_like.constraints_panel as p; p.add_constraint_menu()"),
        None,
        ("Toggle Edit Mode   Tab", "import maya_blender_like.modes as m; m.tab()"),
        ("Pose as Rest Pose", "import maya_blender_like.menus as m; m._pose_as_rest()"),
        None,
        ("Hotkeys and Help (README)", "import webbrowser; webbrowser.open('https://github.com/uayten/MayaBlenderLike#contents')"),
    ]
    for item in items:
        if item is None:
            cmds.menuItem(divider=True, parent=MENU_NAME)
        else:
            cmds.menuItem(label=item[0], command=item[1], sourceType="python", parent=MENU_NAME)


def apply():
    if config.ENABLE_LAYOUT:
        apply_layout()
    if config.ENABLE_COLORS:
        apply_colors()
