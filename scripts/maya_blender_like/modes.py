"""Blender's object mode, pose mode and edit mode for Maya skeletons.

Object mode (default) and pose mode are real states, switched with Ctrl+Tab:
- Object mode: clicking any joint selects its whole skeleton (the top joint), like selecting
  an armature; the whole hierarchy highlights.
- Pose mode: joints are selected one by one and only the selected joint highlights; Alt+G/R/S
  return joints to rest. Pose mode stays on with nothing selected.

Tab with joints selected enters edit mode for their skeleton:
- joints go to their rest pose, the skin is paused so the mesh stays still,
- moving or rotating a joint leaves its children in place,
- the joints are drawn light blue.

Tab again (or Ctrl+Tab) leaves edit mode, back to the mode you came from:
- the new joint placement becomes the rest (rotation goes into jointOrient),
- the skin is rebound at the new rest, so the mesh doesn't jump,
- the pose you had before is reapplied on top of the new rest.

Tab with anything else selected keeps Maya's object / component toggle (Blender's mesh edit mode).

A label in the top-left corner of the viewport always says which mode you are in.
"""
from maya import cmds, mel
import maya.api.OpenMaya as om

from . import rest

HUD_NAME = "MBL_ModeIndicator"
EDIT_COLOR = 18   # Maya color index: light blue, like Blender's edit bones
OBJECT, POSE = "object", "pose"

# selectPref -selectionChildHighlightMode: 0 always highlights children, 1 never.
HIGHLIGHT_CHILDREN, HIGHLIGHT_SELECTED_ONLY = 0, 1

_session = None
_mode = OBJECT
_mode_before_edit = OBJECT


def is_editing():
    return _session is not None


def current_mode():
    return _mode


def tab():
    if _session is not None:
        exit_edit()
        return
    joints = cmds.ls(selection=True, type="joint", long=True)
    if joints:
        enter_edit(joints)
    else:
        mel.eval("SelectToggleMode")
        _refresh_indicator()


def ctrl_tab():
    """Toggle object / pose mode; from edit mode, go to pose mode."""
    if _session is not None:
        exit_edit()
        set_mode(POSE)
        return
    set_mode(OBJECT if _mode == POSE else POSE)


def set_mode(mode):
    global _mode
    _mode = mode
    _set_child_highlight(HIGHLIGHT_CHILDREN if mode == OBJECT else HIGHLIGHT_SELECTED_ONLY)
    if mode == OBJECT:
        _select_armatures()
    _refresh_indicator()


def _set_child_highlight(value):
    try:
        cmds.selectPref(selectionChildHighlightMode=value)
    except (RuntimeError, TypeError):
        pass  # not available in batch mode


def _select_armatures():
    """Object mode: a selected joint stands for its whole skeleton, like Blender's armature object."""
    selection = cmds.ls(selection=True, long=True) or []
    joints = cmds.ls(selection, type="joint", long=True)
    if not joints:
        return
    wanted = [s for s in selection if s not in joints] + rest.roots(joints)
    if set(wanted) != set(selection):
        cmds.select(wanted, replace=True)


def _on_selection_changed():
    if _mode == OBJECT and _session is None:
        _select_armatures()


def install():
    """Start in object mode, keep selections consistent with it, and show the mode indicator."""
    cmds.scriptJob(event=["SelectionChanged", _on_selection_changed])
    set_mode(OBJECT)


def enter_edit(joints):
    global _session, _mode_before_edit
    if _session is not None:
        return
    _mode_before_edit = _mode
    cmds.undoInfo(openChunk=True, chunkName="enter_edit_mode")
    try:
        _session = EditSession(rest.skeleton(joints))
    finally:
        cmds.undoInfo(closeChunk=True)
    _set_child_highlight(HIGHLIGHT_SELECTED_ONLY)
    _refresh_indicator()


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
    set_mode(_mode_before_edit)


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
        return "Edit Mode  -  Armature    (Tab: leave)"
    selection = cmds.ls(selection=True) or []
    # Component mode, or components selected (vertices, edges, faces: "mesh.vtx[3]").
    if cmds.selectMode(query=True, component=True) or any("." in s for s in selection):
        return "Edit Mode  -  Mesh    (Tab: leave)"
    if _mode == POSE:
        return "Pose Mode    (Ctrl+Tab: object mode, Tab: edit)"
    return "Object Mode    (Ctrl+Tab: pose mode)"


def install_indicator():
    """Always-on mode label in the top-left corner of every viewport."""
    if cmds.headsUpDisplay(HUD_NAME, exists=True):
        cmds.headsUpDisplay(HUD_NAME, remove=True)
    block = cmds.headsUpDisplay(nextFreeBlock=0)
    cmds.headsUpDisplay(HUD_NAME, section=0, block=block, blockSize="large", label="",
                        labelFontSize="large", dataFontSize="large",
                        command=mode_text, event="SelectionChanged")
    # Object / component switches don't change the selection event, so refresh on them too.
    cmds.scriptJob(event=["SelectModeChanged", _refresh_indicator])


def _refresh_indicator():
    if cmds.headsUpDisplay(HUD_NAME, exists=True):
        cmds.headsUpDisplay(HUD_NAME, refresh=True)


def _show_hud(visible):
    # Edit mode starts or ends: the indicator reads the mode from the session, so just redraw it.
    _refresh_indicator()
