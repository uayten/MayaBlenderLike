"""Blender's three modes for Maya: object mode, pose mode and edit mode.

Each mode only lets you select what Blender's does, from the viewport and from any other
editor (the selection is checked after every change):
- Object mode (default): everything but joints, for working on the scene.
- Pose mode, for animating: joints and controls only; only the selected joint highlights
  (not its whole hierarchy), and Alt+G/R/S return joints to their rest.
- Edit mode, for editing the rig: the rig's joints only; joints go to their rest pose, the skin is paused so the
  mesh stays still, moving a joint leaves its children in place, joints are drawn light blue.
  Leaving it makes the new placement the rest (rotation goes into jointOrient), rebinds the
  skin so the mesh doesn't jump, and reapplies the pose on top.

Tab: from object mode with a rig selected (a joint, or a group or control with joints under
it), enter edit mode; from edit or pose mode, back to object mode; with a mesh selected, Maya's
object / component toggle (Blender's mesh edit mode).
Ctrl+Tab: a menu at the cursor to pick the mode.

A label in the top-left corner of the viewport always says which mode you are in.
"""
from maya import cmds, mel
import maya.api.OpenMaya as om

from . import rest

HUD_NAME = "MBL_ModeIndicator"
ACTIVE_HUD_NAME = "MBL_ActiveIndicator"
EDIT_COLOR = 18   # Maya color index: light blue, like Blender's edit bones
OBJECT, POSE, EDIT = "object", "pose", "edit"
LABELS = {OBJECT: "Object Mode", POSE: "Pose Mode", EDIT: "Edit Mode"}

# selectPref -selectionChildHighlightMode: 1 highlights only the selected node, not its children.
HIGHLIGHT_SELECTED_ONLY = 1
# What the viewport lets you click in each mode (Maya selection masks). Other editors, like the
# Outliner, ignore masks, so the selection is also checked after every change.
SELECTION_MASKS = {
    OBJECT: {"joint": False, "polymesh": True, "nurbsSurface": True, "subdiv": True, "nurbsCurve": True, "locator": True},
    POSE: {"joint": True, "polymesh": False, "nurbsSurface": False, "subdiv": False, "nurbsCurve": True, "locator": False},
    EDIT: {"joint": True, "polymesh": False, "nurbsSurface": False, "subdiv": False, "nurbsCurve": False, "locator": False},
}
FORBIDDEN_MESSAGES = {
    OBJECT: "Object Mode: joints are posed in Pose Mode and edited in Edit Mode (Ctrl+Tab)",
    POSE: "Pose Mode: only joints and controls can be selected",
    EDIT: "Edit Mode: only the rig's joints can be selected",
}

_session = None
_mode = OBJECT


def is_editing():
    return _session is not None


def current_mode():
    return EDIT if _session is not None else _mode


def tab():
    if current_mode() != OBJECT:
        go(OBJECT)
        return
    if rig_joints():
        go(EDIT)
    else:
        mel.eval("SelectToggleMode")
        _refresh_indicator()


def ctrl_tab():
    mode_menu()


def mode_menu():
    """Blender's Ctrl+Tab: pick the mode from a menu at the cursor."""
    from . import menus
    current = current_mode()
    entries = []
    for mode in (OBJECT, EDIT, POSE):
        mark = "●  " if mode == current else "     "   # filled circle marks the current mode
        entries.append((mark + LABELS[mode], lambda m=mode: go(m)))
    menus.popup("Mode", entries, undo=False)


def go(mode):
    """Switch to object, pose or edit mode from whatever mode is current."""
    if mode == current_mode():
        return
    if mode == EDIT:
        joints = rig_joints()
        if not joints:
            cmds.warning("Edit Mode: select the rig first (a joint, or a group or control with joints under it).")
            return
        if _mode == POSE:
            set_mode(OBJECT)
        enter_edit(joints)
        return
    exit_edit()
    set_mode(mode)


def rig_joints():
    """Joints in the selection, under the selected groups, or in the rig a selected control belongs to."""
    selection = cmds.ls(selection=True, long=True) or []
    joints = cmds.ls(selection, type="joint", long=True)
    if joints:
        return joints
    transforms = cmds.ls(selection, transforms=True, long=True)
    if not transforms:
        return []
    found = cmds.listRelatives(transforms, allDescendents=True, type="joint", fullPath=True) or []
    if found:
        return found
    # A control (curve) has no joints under it: take the joints of the top group it lives in (RIG|CTRL|...).
    controls = [t for t in transforms if cmds.listRelatives(t, shapes=True, type="nurbsCurve")]
    tops = sorted({"|" + c.split("|")[1] for c in controls})
    if not tops:
        return []
    return cmds.listRelatives(tops, allDescendents=True, type="joint", fullPath=True) or []


def set_mode(mode):
    """Object or pose mode (edit mode goes through enter_edit)."""
    global _mode
    _mode = mode
    _set_child_highlight(HIGHLIGHT_SELECTED_ONLY if mode == POSE else _user_child_highlight())
    _apply_selection_rules()


def _apply_selection_rules():
    """Viewport selection masks for the current mode, then drop anything the mode forbids."""
    for kind, allowed in SELECTION_MASKS[current_mode()].items():
        try:
            cmds.selectType(**{kind: allowed})
        except (RuntimeError, TypeError):
            pass  # not available in batch mode
    _enforce_selection()
    _refresh_indicator()


def _allowed(node, mode):
    if mode == OBJECT:
        return not cmds.ls(node, type="joint")
    if "." in node:
        return False  # components belong to mesh editing, in object mode
    if mode == EDIT:
        return bool(_session) and cmds.ls(node, long=True)[0] in _session.joint_set
    # Pose mode: joints, and controls (transforms with curve shapes).
    return bool(cmds.ls(node, type="joint")) or bool(cmds.listRelatives(node, shapes=True, type="nurbsCurve"))


def _enforce_selection():
    """Remove what the current mode forbids from the selection, whichever editor it came from."""
    selection = cmds.ls(selection=True, long=True) or []
    mode = current_mode()
    kept = [s for s in selection if _allowed(s, mode)]
    if len(kept) == len(selection):
        return
    # The correction itself shouldn't cost an extra Ctrl+Z.
    cmds.undoInfo(stateWithoutFlush=False)
    try:
        cmds.select(kept, replace=True) if kept else cmds.select(clear=True)
    finally:
        cmds.undoInfo(stateWithoutFlush=True)
    cmds.headsUpMessage(FORBIDDEN_MESSAGES[mode], time=2.0)


def _user_child_highlight():
    # Object mode shows the user's own preference (Preferences > Selection).
    try:
        return cmds.optionVar(query="selectionChildHighlightMode")
    except RuntimeError:
        return 0


def _set_child_highlight(value):
    try:
        cmds.selectPref(selectionChildHighlightMode=value)
    except (RuntimeError, TypeError):
        pass  # not available in batch mode


def install():
    """Start in object mode and keep every selection within the current mode's rules."""
    cmds.scriptJob(event=["SelectionChanged", _enforce_selection])
    set_mode(OBJECT)


def enter_edit(joints):
    global _session
    if _session is not None:
        return
    cmds.undoInfo(openChunk=True, chunkName="enter_edit_mode")
    try:
        _session = EditSession(rest.skeleton(joints))
    finally:
        cmds.undoInfo(closeChunk=True)
    _set_child_highlight(HIGHLIGHT_SELECTED_ONLY)
    _apply_selection_rules()


def exit_edit():
    global _session
    if _session is None:
        return
    session, _session = _session, None
    cmds.undoInfo(openChunk=True, chunkName="exit_edit_mode")
    try:
        session.finish()
    finally:
        cmds.undoInfo(closeChunk=True)
    _refresh_indicator()


def apply_pose_as_rest(joints):
    """Blender's Apply > Pose as Rest Pose: the current pose becomes the rest; the mesh returns to its bind shape."""
    joints = rest.skeleton(joints)
    cmds.undoInfo(openChunk=True, chunkName="pose_as_rest")
    try:
        for joint in joints:
            rest.freeze_rotation(joint)
        rest.store(joints)
        rest.rebind(joints)
    finally:
        cmds.undoInfo(closeChunk=True)


class EditSession(object):

    def __init__(self, joints):
        self.joints = joints
        self.joint_set = set(cmds.ls(joints, long=True))
        self.pose = {j: cmds.xform(j, query=True, objectSpace=True, matrix=True) for j in joints}
        self._ensure_rest()
        rest.restore(joints)
        self.old_rest = {j: cmds.xform(j, query=True, objectSpace=True, matrix=True) for j in joints}
        self.envelopes = {c: cmds.getAttr(c + ".envelope") for c in rest.skin_clusters(joints)}
        for cluster in self.envelopes:
            cmds.setAttr(cluster + ".envelope", 0)
        self.colors = {j: (cmds.getAttr(j + ".overrideEnabled"), cmds.getAttr(j + ".overrideColor")) for j in joints}
        for joint in joints:
            _set_color(joint, True, EDIT_COLOR)
        self.move_preserve = _tool_preserve_children(True)
        _show_hud(True)

    def _ensure_rest(self):
        # First edit of a skeleton: its rest is the bind pose if skinned, otherwise its current placement.
        missing = [j for j in self.joints if not rest.has_rest(j)]
        if not missing:
            return
        poses = cmds.dagPose(missing, query=True, bindPose=True) or []
        if poses:
            snapshot = {j: cmds.xform(j, query=True, objectSpace=True, matrix=True) for j in self.joints}
            cmds.dagPose(missing, restore=True, name=poses[0])
            rest.store(missing)
            for joint, matrix in snapshot.items():
                cmds.xform(joint, objectSpace=True, matrix=matrix)
        else:
            rest.store(missing)

    def finish(self):
        joints = self.joints
        for joint in joints:
            rest.freeze_rotation(joint)
        rest.store(joints)
        rest.rebind(joints)
        for cluster, envelope in self.envelopes.items():
            cmds.setAttr(cluster + ".envelope", envelope)
        # Reapply the pose relative to the new rest: pose = delta * rest, so new = delta * new rest.
        for joint in joints:
            delta = om.MMatrix(self.pose[joint]) * om.MMatrix(self.old_rest[joint]).inverse()
            new_rest = om.MMatrix(cmds.xform(joint, query=True, objectSpace=True, matrix=True))
            if not delta.isEquivalent(om.MMatrix(), 1e-6):
                _set_local_matrix(joint, delta * new_rest)
        for joint, (enabled, color) in self.colors.items():
            _set_color(joint, enabled, color)
        _tool_preserve_children(self.move_preserve)
        _show_hud(False)


def _set_local_matrix(joint, matrix):
    if all(cmds.getAttr("{}.{}{}".format(joint, c, a), settable=True) for c in ("translate", "rotate", "scale") for a in "XYZ"):
        cmds.xform(joint, objectSpace=True, matrix=list(matrix))


def _set_color(joint, enabled, color):
    try:
        cmds.setAttr(joint + ".overrideEnabled", enabled)
        cmds.setAttr(joint + ".overrideColor", color)
    except RuntimeError:
        pass  # locked or connected drawing overrides


def _tool_preserve_children(enabled):
    """Set Maya's move / rotate / scale tools to leave children in place; returns the previous setting."""
    try:
        previous = cmds.manipMoveContext("Move", query=True, preserveChildPosition=True)
        for context, command in (("Move", cmds.manipMoveContext), ("Rotate", cmds.manipRotateContext), ("Scale", cmds.manipScaleContext)):
            command(context, edit=True, preserveChildPosition=enabled)
        return previous
    except (RuntimeError, TypeError):
        return False


def mode_text():
    """The mode shown in the viewport corner, as in Blender's header."""
    if _session is not None:
        return "Edit Mode  -  Rig    (Tab: object mode, Ctrl+Tab: modes)"
    selection = cmds.ls(selection=True) or []
    # Component mode, or components selected (vertices, edges, faces: "mesh.vtx[3]").
    if cmds.selectMode(query=True, component=True) or any("." in s for s in selection):
        return "Edit Mode  -  Mesh    (Tab: leave)"
    if _mode == POSE:
        return "Pose Mode    (Tab: object mode, Ctrl+Tab: modes)"
    return "Object Mode    (Tab: edit rig, Ctrl+Tab: modes)"


def active_text():
    """The active (last selected) object under the mode, like Blender's "Armature : Bone" line."""
    selection = cmds.ls(selection=True) or []
    if not selection:
        return ""
    active = selection[-1].rsplit("|", 1)[-1]
    kind = "Bone" if cmds.ls(selection[-1], type="joint") else "Active"
    extra = "   (+{} selected)".format(len(selection) - 1) if len(selection) > 1 else ""
    return "{}: {}{}".format(kind, active, extra)


def install_indicator():
    """Always-on mode label, and the active object's name under it, in the top-left corner of every viewport."""
    for name, command in ((HUD_NAME, mode_text), (ACTIVE_HUD_NAME, active_text)):
        if cmds.headsUpDisplay(name, exists=True):
            cmds.headsUpDisplay(name, remove=True)
        block = cmds.headsUpDisplay(nextFreeBlock=0)
        cmds.headsUpDisplay(name, section=0, block=block, blockSize="large", label="",
                            labelFontSize="large", dataFontSize="large",
                            command=command, event="SelectionChanged")
    # Object / component switches don't change the selection event, so refresh on them too.
    cmds.scriptJob(event=["SelectModeChanged", _refresh_indicator])


def _refresh_indicator():
    for name in (HUD_NAME, ACTIVE_HUD_NAME):
        if cmds.headsUpDisplay(name, exists=True):
            cmds.headsUpDisplay(name, refresh=True)


def _show_hud(visible):
    # Edit mode starts or ends: the indicator reads the mode from the session, so just redraw it.
    _refresh_indicator()
