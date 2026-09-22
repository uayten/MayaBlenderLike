"""Blender-style hotkey set, built on top of Maya_Default.

Maya command names come from Maya 2026's scripts/startup/hotkeySetup.mel.
An uppercase key means Shift + that key.
"""
from maya import cmds

from . import config

RUNTIME_CATEGORY = "Custom Scripts.MayaBlenderLike"

# Commands this module adds to Maya: (runtime command, annotation, Python code).
# Each becomes a runtime command (listed in the Hotkey Editor under Custom Scripts)
# plus a name command "<runtime>NameCommand" that hotkeys point to.
CUSTOM_COMMANDS = [
    ("MBL_ModalMove", "Move, modal in the viewport (Blender G)",
     "import maya_blender_like.modal as m; m.start(m.TRANSLATE)"),
    ("MBL_ModalRotate", "Rotate, modal in the viewport (Blender R)",
     "import maya_blender_like.modal as m; m.start(m.ROTATE)"),
    ("MBL_ModalScale", "Scale, modal in the viewport (Blender S)",
     "import maya_blender_like.modal as m; m.start(m.SCALE)"),
    ("MBL_ExtrudeJoints", "Extrude selected joints (Blender E); rotate tool otherwise",
     "import maya_blender_like.modal as m; m.start(m.TRANSLATE, extrude=True)"),
    ("MBL_ClearTranslate", "Clear location (Blender Alt+G)",
     "import maya_blender_like.transforms as t; t.clear('translate')"),
    ("MBL_ClearRotate", "Clear rotation (Blender Alt+R)",
     "import maya_blender_like.transforms as t; t.clear('rotate')"),
    ("MBL_ClearScale", "Clear scale (Blender Alt+S)",
     "import maya_blender_like.transforms as t; t.clear('scale')"),
    ("MBL_AddMenu", "Add menu (Blender Shift+A)",
     "import maya_blender_like.menus as m; m.add_menu()"),
    ("MBL_ApplyMenu", "Apply menu (Blender Ctrl+A)",
     "import maya_blender_like.menus as m; m.apply_menu()"),
    ("MBL_DeleteMenu", "Delete menu (Blender X)",
     "import maya_blender_like.menus as m; m.delete_menu()"),
    ("MBL_ShowAll", "Reveal hidden objects (Blender Alt+H)",
     "from maya import mel; mel.eval('ShowAll')"),
    ("MBL_ToggleChannelBox", "Toggle Channel Box (Blender N)",
     "from maya import mel; mel.eval('ToggleChannelBox')"),
    ("MBL_ToggleAttributeEditor", "Toggle Attribute Editor (Blender Properties)",
     "from maya import mel; mel.eval('ToggleAttributeEditor')"),
    ("MBL_ToggleGridSnap", "Toggle grid snap (Blender Shift+Tab)",
     "import maya_blender_like.interface as i; i.toggle_grid_snap()"),
    ("MBL_Tab", "Edit mode on joints, object/component toggle otherwise (Blender Tab)",
     "import maya_blender_like.modes as m; m.tab()"),
    ("MBL_CtrlTab", "Leave edit mode to pose mode (Blender Ctrl+Tab)",
     "import maya_blender_like.modes as m; m.ctrl_tab()"),
    ("MBL_AddConstraint", "Add Constraint with Targets (Blender Shift+Ctrl+C)",
     "import maya_blender_like.constraints_panel as p; p.add_constraint_menu()"),
]

ALT = {"altModifier": True}
CTRL = {"ctrlModifier": True}
SHIFT = {"shiftModifier": True}


def _bindings():
    """(key, modifiers, press command, release command)"""
    if config.ENABLE_MODAL_TRANSFORMS:
        # Press-only commands: no marking menu that a swallowed key release could leave open.
        transforms = [
            ("g", {}, "MBL_ModalMoveNameCommand", ""),
            ("r", {}, "MBL_ModalRotateNameCommand", ""),
            ("s", {}, "MBL_ModalScaleNameCommand", ""),
            ("e", {}, "MBL_ExtrudeJointsNameCommand", ""),
        ]
    else:
        transforms = [
            ("g", {}, "TranslateToolWithSnapMarkingMenuNameCommand", "TranslateToolWithSnapMarkingMenuPopDownNameCommand"),
            ("r", {}, "RotateToolWithSnapMarkingMenuNameCommand", "RotateToolWithSnapMarkingMenuPopDownNameCommand"),
            ("s", {}, "ScaleToolWithSnapMarkingMenuNameCommand", "ScaleToolWithSnapMarkingMenuPopDownNameCommand"),
        ]
    return transforms + [
        # Alt+G / Alt+R / Alt+S clear location, rotation, scale.
        ("g", ALT, "MBL_ClearTranslateNameCommand", ""),
        ("r", ALT, "MBL_ClearRotateNameCommand", ""),
        ("s", ALT, "MBL_ClearScaleNameCommand", ""),
        # Set Key moves from S to I; Repeat Last moves from G to Shift+R.
        ("i", {}, "NameComSet_Keyframe", ""),
        ("R", {}, "NameComRepeat_Last_Menu_Action", ""),
        # Tab: edit mode with joints selected, object/component toggle otherwise (F8 keeps working). Ctrl+Tab: pose mode.
        ("Tab", {}, "MBL_TabNameCommand", ""),
        ("Tab", CTRL, "MBL_CtrlTabNameCommand", ""),
        # A select all, Alt+A deselect, Home frame all.
        ("a", {}, "NameComSelect_All", ""),
        ("a", ALT, "NameComSelectNone", ""),
        ("Home", {}, "NameComFit_All_in_Active_Panel_MMenu", "NameComFit_All_in_Active_Panel_MMenu_release"),
        # Shift+D duplicate, Ctrl+P parent, Alt+P unparent.
        ("D", {}, "NameComDuplicate_Selected", ""),
        ("p", CTRL, "NameComParent_Selected", ""),
        ("p", ALT, "NameComUnparent_Selected", ""),
        # Shift+A add menu, Ctrl+A apply menu, X delete menu (Delete still deletes directly).
        ("A", {}, "MBL_AddMenuNameCommand", ""),
        ("a", CTRL, "MBL_ApplyMenuNameCommand", ""),
        ("x", {}, "MBL_DeleteMenuNameCommand", ""),
        # H hide selected, Shift+H hide unselected, Alt+H reveal all.
        ("h", {}, "NameComHide_Selected_Objects", ""),
        ("H", {}, "NameComHide_Unselected_Objects", ""),
        ("h", ALT, "MBL_ShowAllNameCommand", ""),
        # N toggles the Channel Box (Blender's sidebar), Shift+N the Attribute Editor.
        ("n", {}, "MBL_ToggleChannelBoxNameCommand", ""),
        ("N", {}, "MBL_ToggleAttributeEditorNameCommand", ""),
        # Shift+Ctrl+C: Add Constraint (with Targets): the active object is the last selected, the other is the target.
        ("C", CTRL, "MBL_AddConstraintNameCommand", ""),
        # Shift+Tab toggles grid snap (it was held X in Maya).
        ("Tab", SHIFT, "MBL_ToggleGridSnapNameCommand", ""),
    ]


def apply():
    name = config.HOTKEY_SET_NAME
    if cmds.hotkeySet(name, exists=True):
        cmds.hotkeySet(name, edit=True, current=True)
    else:
        cmds.hotkeySet(name, source="Maya_Default", current=True)

    failures = []
    for runtime, annotation, code in CUSTOM_COMMANDS:
        try:
            _define_command(runtime, annotation, code)
        except Exception as error:
            failures.append("command {}: {}".format(runtime, error))

    # One bad binding must not leave the rest unbound.
    for key, modifiers, press, release in _bindings():
        try:
            cmds.hotkey(keyShortcut=key, name=press, releaseName=release, **modifiers)
        except Exception as error:
            failures.append("{}{}: {}".format("+".join(m[:-8] for m in modifiers), key, error))

    if failures:
        raise RuntimeError("{} of the hotkeys failed:\n  ".format(len(failures)) + "\n  ".join(failures))


def _define_command(runtime, annotation, code):
    if cmds.runTimeCommand(runtime, exists=True):
        cmds.runTimeCommand(runtime, edit=True, annotation=annotation, command=code, commandLanguage="python")
    else:
        cmds.runTimeCommand(runtime, annotation=annotation, category=RUNTIME_CATEGORY,
                            command=code, commandLanguage="python")
    cmds.nameCommand(runtime + "NameCommand", annotation=annotation, command=runtime, sourceType="mel")


def report():
    """What is bound right now, for troubleshooting from the Script Editor."""
    lines = ["current hotkey set: " + cmds.hotkeySet(query=True, current=True)]
    for key, modifiers, press, _ in _bindings():
        bound = cmds.hotkey(key, query=True, name=True, **modifiers)
        lines.append("{:<14} {:<45} {}".format("+".join(m[:-8] for m in modifiers) + (" " if modifiers else "") + key,
                                               str(bound), "OK" if bound == press else "EXPECTED " + press))
    print("\n".join(lines))
