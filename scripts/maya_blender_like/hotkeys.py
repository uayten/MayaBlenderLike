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
    # Tab toggles object/component mode (F8 keeps working).
    ("Tab", {}, "NameComToggle_ObjectComponent_Editing", ""),
    # A select all, Alt+A deselect, Home frame all.
    ("a", {}, "NameComSelect_All", ""),
    ("a", {"altModifier": True}, "NameComSelectNone", ""),
    ("Home", {}, "NameComFit_All_in_Active_Panel_MMenu", "NameComFit_All_in_Active_Panel_MMenu_release"),
    # Shift+D duplicate, Ctrl+P parent, Alt+P unparent.
    ("D", {}, "NameComDuplicate_Selected", ""),
    ("p", {"ctrlModifier": True}, "NameComParent_Selected", ""),
    ("p", {"altModifier": True}, "NameComUnparent_Selected", ""),
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
