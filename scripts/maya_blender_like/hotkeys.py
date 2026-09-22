"""Blender-style hotkey set, built on top of Maya_Default.

Maya command names come from Maya 2026's scripts/startup/hotkeySetup.mel.
An uppercase key means Shift + that key.
"""
from maya import cmds

from . import config

# Commands this module adds to Maya: (name command, annotation, Python code).
CUSTOM_COMMANDS = [
    ("MBL_ClearTranslateNameCommand", "Clear location (Blender Alt+G)",
     "import maya_blender_like.transforms as t; t.clear('translate')"),
    ("MBL_ClearRotateNameCommand", "Clear rotation (Blender Alt+R)",
     "import maya_blender_like.transforms as t; t.clear('rotate')"),
    ("MBL_ClearScaleNameCommand", "Clear scale (Blender Alt+S)",
     "import maya_blender_like.transforms as t; t.clear('scale')"),
    ("MBL_AddMenuNameCommand", "Add menu (Blender Shift+A)",
     "import maya_blender_like.menus as m; m.add_menu()"),
    ("MBL_ApplyMenuNameCommand", "Apply menu (Blender Ctrl+A)",
     "import maya_blender_like.menus as m; m.apply_menu()"),
    ("MBL_DeleteMenuNameCommand", "Delete menu (Blender X)",
     "import maya_blender_like.menus as m; m.delete_menu()"),
    ("MBL_ShowAllNameCommand", "Reveal hidden objects (Blender Alt+H)",
     "from maya import mel; mel.eval('ShowAll')"),
    ("MBL_ToggleChannelBoxNameCommand", "Toggle Channel Box (Blender N)",
     "from maya import mel; mel.eval('ToggleChannelBox')"),
    ("MBL_ToggleAttributeEditorNameCommand", "Toggle Attribute Editor (Blender Properties)",
     "from maya import mel; mel.eval('ToggleAttributeEditor')"),
    ("MBL_ToggleGridSnapNameCommand", "Toggle grid snap (Blender Shift+Tab)",
     "import maya_blender_like.interface as i; i.toggle_grid_snap()"),
    ("MBL_TabNameCommand", "Edit mode on joints, object/component toggle otherwise (Blender Tab)",
     "import maya_blender_like.modes as m; m.tab()"),
    ("MBL_CtrlTabNameCommand", "Leave edit mode to pose mode (Blender Ctrl+Tab)",
     "import maya_blender_like.modes as m; m.ctrl_tab()"),
    ("MBL_AddConstraintNameCommand", "Add Constraint with Targets (Blender Shift+Ctrl+C)",
     "import maya_blender_like.constraints_panel as p; p.add_constraint_menu()"),
]

# (key, modifiers, press command, release command)
BINDINGS = [
    # G move, R rotate, S scale. W and E keep their Maya behavior.
    ("g", {}, "TranslateToolWithSnapMarkingMenuNameCommand", "TranslateToolWithSnapMarkingMenuPopDownNameCommand"),
    ("r", {}, "RotateToolWithSnapMarkingMenuNameCommand", "RotateToolWithSnapMarkingMenuPopDownNameCommand"),
    ("s", {}, "ScaleToolWithSnapMarkingMenuNameCommand", "ScaleToolWithSnapMarkingMenuPopDownNameCommand"),
    # Alt+G / Alt+R / Alt+S clear location, rotation, scale.
    ("g", {"altModifier": True}, "MBL_ClearTranslateNameCommand", ""),
    ("r", {"altModifier": True}, "MBL_ClearRotateNameCommand", ""),
    ("s", {"altModifier": True}, "MBL_ClearScaleNameCommand", ""),
    # Set Key moves from S to I; Repeat Last moves from G to Shift+R.
    ("i", {}, "NameComSet_Keyframe", ""),
    ("R", {}, "NameComRepeat_Last_Menu_Action", ""),
    # Tab: edit mode with joints selected, object/component toggle otherwise (F8 keeps working). Ctrl+Tab: pose mode.
    ("Tab", {}, "MBL_TabNameCommand", ""),
    ("Tab", {"ctrlModifier": True}, "MBL_CtrlTabNameCommand", ""),
    # A select all, Alt+A deselect, Home frame all.
    ("a", {}, "NameComSelect_All", ""),
    ("a", {"altModifier": True}, "NameComSelectNone", ""),
    ("Home", {}, "NameComFit_All_in_Active_Panel_MMenu", "NameComFit_All_in_Active_Panel_MMenu_release"),
    # Shift+D duplicate, Ctrl+P parent, Alt+P unparent.
    ("D", {}, "NameComDuplicate_Selected", ""),
    ("p", {"ctrlModifier": True}, "NameComParent_Selected", ""),
    ("p", {"altModifier": True}, "NameComUnparent_Selected", ""),
    # Shift+A add menu, Ctrl+A apply menu, X delete menu (Delete still deletes directly).
    ("A", {}, "MBL_AddMenuNameCommand", ""),
    ("a", {"ctrlModifier": True}, "MBL_ApplyMenuNameCommand", ""),
    ("x", {}, "MBL_DeleteMenuNameCommand", ""),
    # H hide selected, Shift+H hide unselected, Alt+H reveal all.
    ("h", {}, "NameComHide_Selected_Objects", ""),
    ("H", {}, "NameComHide_Unselected_Objects", ""),
    ("h", {"altModifier": True}, "MBL_ShowAllNameCommand", ""),
    # N toggles the Channel Box (Blender's sidebar), Shift+N the Attribute Editor.
    ("n", {}, "MBL_ToggleChannelBoxNameCommand", ""),
    ("N", {}, "MBL_ToggleAttributeEditorNameCommand", ""),
    # Shift+Ctrl+C: Add Constraint (with Targets): the active object is the last selected, the other is the target.
    ("C", {"ctrlModifier": True}, "MBL_AddConstraintNameCommand", ""),
    # Shift+Tab toggles grid snap (it was held X in Maya).
    ("Tab", {"shiftModifier": True}, "MBL_ToggleGridSnapNameCommand", ""),
]


def apply():
    name = config.HOTKEY_SET_NAME
    if cmds.hotkeySet(name, exists=True):
        cmds.hotkeySet(name, edit=True, current=True)
    else:
        cmds.hotkeySet(name, source="Maya_Default", current=True)

    for command, annotation, code in CUSTOM_COMMANDS:
        cmds.nameCommand(command, annotation=annotation, command=code, sourceType="python")

    for key, modifiers, press, release in BINDINGS:
        cmds.hotkey(keyShortcut=key, name=press, releaseName=release, **modifiers)
