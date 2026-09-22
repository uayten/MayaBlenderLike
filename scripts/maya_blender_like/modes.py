"""Blender's edit mode and pose mode for Maya skeletons.

Tab with joints selected enters edit mode for their skeleton:
- joints go to their rest pose, the skin is paused so the mesh stays still,
- moving or rotating a joint leaves its children in place,
- the joints are drawn in a different color and the viewport shows EDIT MODE.

Tab again (or Ctrl+Tab) leaves edit mode:
- the new joint placement becomes the rest (rotation goes into jointOrient),
- the skin is rebound at the new rest, so the mesh doesn't jump,
- the pose you had before is reapplied on top of the new rest.

Pose mode is Maya's normal state: animate joints and controls; Alt+G/R/S return to rest.
Tab with anything else selected keeps Maya's object / component toggle.
"""
from maya import cmds, mel
import maya.api.OpenMaya as om

from . import rest

HUD_NAME = "MBL_EditModeHUD"
EDIT_COLOR = 18   # Maya color index: light blue, like Blender's edit bones

_session = None


def is_editing():
    return _session is not None


def tab():
    if _session is not None:
        exit_edit()
        return
    joints = cmds.ls(selection=True, type="joint", long=True)
    if joints:
        enter_edit(joints)
    else:
        mel.eval("SelectToggleMode")


def ctrl_tab():
    if _session is not None:
        exit_edit()
    else:
        cmds.headsUpMessage("Pose Mode", time=1.0)


def enter_edit(joints):
    global _session
    if _session is not None:
        return
    cmds.undoInfo(openChunk=True, chunkName="enter_edit_mode")
    try:
        _session = EditSession(rest.skeleton(joints))
    finally:
        cmds.undoInfo(closeChunk=True)


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


def _show_hud(visible):
    if cmds.headsUpDisplay(HUD_NAME, exists=True):
        cmds.headsUpDisplay(HUD_NAME, remove=True)
    if visible:
        block = cmds.headsUpDisplay(nextFreeBlock=0)
        cmds.headsUpDisplay(HUD_NAME, section=0, block=block, blockSize="large",
                            label="EDIT MODE  (Tab to leave)", labelFontSize="large")
