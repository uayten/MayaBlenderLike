"""Blender-style hotkey set, built on top of Maya_Default.

Command names come from Maya 2026's scripts/startup/hotkeySetup.mel.
An uppercase key means Shift + that key.
"""
from maya import cmds

from . import config

# (key, modifiers, press command, release command)
BINDINGS = [
    # G move, R rotate, S scale. W and E keep their Maya behavior.
    ("g", {}, "TranslateToolWithSnapMarkingMenuNameCommand", "TranslateToolWithSnapMarkingMenuPopDownNameCommand"),
    ("r", {}, "RotateToolWithSnapMarkingMenuNameCommand", "RotateToolWithSnapMarkingMenuPopDownNameCommand"),
    ("s", {}, "ScaleToolWithSnapMarkingMenuNameCommand", "ScaleToolWithSnapMarkingMenuPopDownNameCommand"),
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

    for key, modifiers, press, release in BINDINGS:
        cmds.hotkey(keyShortcut=key, name=press, releaseName=release, **modifiers)
