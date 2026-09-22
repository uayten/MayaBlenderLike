"""Blender-like layout and colors: Outliner on the right above the Channel Box, gray viewport, orange selection.

The Blender Like workspace travels with the repository: workspaces/Blender_Like.json is
installed on a machine that doesn't have it yet, and Blender Like > Save Workspace to GitHub
copies your current layout back into the repository and pushes it.
"""
import os
import shutil
import subprocess

from maya import cmds

from . import config

LAYOUT_NAME = "Blender Like"
LAYOUT_FILE = "Blender_Like.json"   # Maya's file name for the layout in prefs/workspaces
REPOSITORY = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPOSITORY_LAYOUT = os.path.join(REPOSITORY, "workspaces", LAYOUT_FILE)

# Blender's default theme, as 0-1 RGB.
VIEWPORT_BACKGROUND = (0.239, 0.239, 0.239)   # #3D3D3D
LEAD_SELECTION = (1.0, 0.667, 0.251)          # active object, #FFAA40


def _prefs_layout():
    return os.path.join(cmds.internalVar(userPrefDir=True), "workspaces", LAYOUT_FILE)


def apply_layout():
    """Make Blender Like the current workspace: yours if Maya has it, else the repository's, else a new one."""
    if LAYOUT_NAME in (cmds.workspaceLayoutManager(listLayouts=True) or []):
        cmds.workspaceLayoutManager(setCurrent=LAYOUT_NAME)
        return
    if os.path.isfile(REPOSITORY_LAYOUT):
        cmds.workspaceLayoutManager(i=REPOSITORY_LAYOUT)
        cmds.workspaceLayoutManager(setCurrent=LAYOUT_NAME)
        return
    if not cmds.workspaceControl("Outliner", exists=True):
        cmds.OutlinerWindow()
    # Outliner goes above the Channel Box / Attribute Editor, like Blender's Outliner over Properties.
    cmds.workspaceControl("Outliner", edit=True, dockToControl=("ChannelBoxLayerEditor", "top"))
    cmds.workspaceLayoutManager(saveAs=LAYOUT_NAME)
    cmds.workspaceLayoutManager(setCurrent=LAYOUT_NAME)


def save_workspace_to_github():
    """Save the current Blender Like layout, copy it into the repository, commit and push."""
    if cmds.workspaceLayoutManager(query=True, current=True) != LAYOUT_NAME:
        cmds.warning("Switch to the {} workspace first (top right of Maya).".format(LAYOUT_NAME))
        return
    cmds.workspaceLayoutManager(save=True)
    os.makedirs(os.path.dirname(REPOSITORY_LAYOUT), exist_ok=True)
    shutil.copyfile(_prefs_layout(), REPOSITORY_LAYOUT)

    def git(*args):
        return subprocess.run(["git"] + list(args), cwd=REPOSITORY, capture_output=True, text=True, timeout=60)

    try:
        git("add", REPOSITORY_LAYOUT)
        if git("diff", "--cached", "--quiet").returncode == 0:
            cmds.headsUpMessage("Workspace unchanged: nothing to push", time=2.0)
            return
        git("commit", "-m", "Update Blender Like workspace")
        pushed = git("push")
    except (OSError, subprocess.TimeoutExpired) as error:
        cmds.warning("Workspace saved in the repository, but git failed: {}".format(error))
        return
    if pushed.returncode != 0:
        cmds.warning("Workspace committed locally, push failed: " + pushed.stderr.strip())
    else:
        cmds.headsUpMessage("Workspace saved to GitHub", time=2.0)
        print("MayaBlenderLike: workspace pushed to GitHub")


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
        ("Bone & Constraints Panel", "import maya_blender_like.constraints_panel as p; p.show()"),
        ("Add Constraint (with Targets)   Shift+Ctrl+C", "import maya_blender_like.constraints_panel as p; p.add_constraint_menu()"),
        None,
        ("Object Mode", "import maya_blender_like.modes as m; m.go(m.OBJECT)"),
        ("Edit Mode (rig)   Tab", "import maya_blender_like.modes as m; m.go(m.EDIT)"),
        ("Pose Mode", "import maya_blender_like.modes as m; m.go(m.POSE)"),
        ("Pose as Rest Pose", "import maya_blender_like.menus as m; m._pose_as_rest()"),
        None,
        ("Save Workspace to GitHub", "import maya_blender_like.interface as i; i.save_workspace_to_github()"),
        None,
        ("Hotkeys and Help (README)", "import webbrowser; webbrowser.open('https://github.com/uayten/MayaBlenderLike#contents')"),
    ]
    for item in items:
        if item is None:
            cmds.menuItem(divider=True, parent=MENU_NAME)
        else:
            cmds.menuItem(label=item[0], command=item[1], sourceType="python", parent=MENU_NAME)

    # Custom shapes for every selected joint at once (the Bone & Constraints panel does one joint).
    from . import custom_shapes
    submenu = cmds.menuItem(label="Custom Shape (selected joints / controls)", subMenu=True, tearOff=True, parent=MENU_NAME)
    for shape in custom_shapes.SHAPES:
        cmds.menuItem(label=shape, parent=submenu, sourceType="python",
                      command="import maya_blender_like.custom_shapes as c; from maya import cmds; "
                              "c.assign(cmds.ls(selection=True, long=True), {!r})".format(shape))
    cmds.menuItem(divider=True, parent=submenu)
    cmds.menuItem(label="Remove", parent=submenu, sourceType="python",
                  command="import maya_blender_like.custom_shapes as c; from maya import cmds; "
                          "c.remove(cmds.ls(selection=True, type='joint'))")

    rig = "import maya_blender_like.modes as m; joints = m.rig_joints(); "
    cmds.menuItem(label="Armature In Front: On", parent=MENU_NAME, sourceType="python",
                  command=rig + "import maya_blender_like.custom_shapes as c; c.set_in_front(joints, True)")
    cmds.menuItem(label="Armature In Front: Off", parent=MENU_NAME, sourceType="python",
                  command=rig + "import maya_blender_like.custom_shapes as c; c.set_in_front(joints, False)")

    # A skeleton from Blender -> controls at 0 / 0 / 1 driving joints, mechanism chains in MECH.
    cmds.menuItem(label="Convert to MayaBlenderLike Rig", parent=MENU_NAME, sourceType="python",
                  annotation="Controls for the bones, mechanisms apart: select the armature first",
                  command="import maya_blender_like.mechanisms as m; m.convert_selected_rig()")
    cmds.menuItem(label="Apply Blender Rig Data (.json)...", parent=MENU_NAME, sourceType="python",
                  annotation="Locks, collections, custom shapes and constraints exported from Blender",
                  command="import maya_blender_like.rig_data as r; r.apply_from_dialog()")


def apply():
    if config.ENABLE_LAYOUT:
        apply_layout()
    if config.ENABLE_COLORS:
        apply_colors()
