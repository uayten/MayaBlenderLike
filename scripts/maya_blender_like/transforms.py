"""Blender's Alt+G / Alt+R / Alt+S: clear location, rotation or scale of the selection."""
from maya import cmds

from . import drivers, rest

RESET_VALUES = {"translate": 0.0, "rotate": 0.0, "scale": 1.0}
CHANNELS = ("translate", "rotate", "scale")


def clear(channel):
    """Reset translate, rotate or scale on the selection, skipping locked or driven channels.

    Objects and controls go to 0 (1 for scale). A joint's translate and rotate hold its rest
    position, so joints go back to their rest instead, like a Blender bone: the rest stored by
    edit mode, or the skin's bind pose. Joints with neither are skipped with a warning.

    A node that follows a control through a constraint (a joint driven by CTRL_main, say)
    clears the control instead, since that is what puts the bone back.
    """
    nodes = cmds.ls(selection=True, transforms=True, long=True) or []
    if not nodes:
        return
    nodes, note = drivers.redirect(nodes)
    if note:
        cmds.headsUpMessage(note, time=2.0)
    nodes = [n for n in nodes if _settable(n, channel)]
    if not nodes:
        # Nothing can change: say so, and leave no empty step in the undo queue.
        cmds.warning("Clear {}: every selected channel is locked or driven.".format(channel))
        return
    joints = [n for n in nodes if cmds.nodeType(n) == "joint"]
    others = [n for n in nodes if n not in joints]

    cmds.undoInfo(openChunk=True, chunkName="clear_" + channel)
    try:
        for node in others:
            _set_channel(node, channel, [RESET_VALUES[channel]] * 3)
        rest_values, unbound = _bind_pose_values(joints, channel)
        for joint, values in rest_values.items():
            _set_channel(joint, channel, values)
    finally:
        cmds.undoInfo(closeChunk=True)

    if unbound:
        cmds.warning("Clear {}: no rest for {}. Enter and leave edit mode (Tab) once to record it.".format(
            channel, ", ".join(_short(j) for j in unbound)))


def _bind_pose_values(joints, channel):
    """Rest values of one channel per joint: the rest stored by edit mode, else the skin's bind pose."""
    rest_values, unbound = {}, []
    for joint in joints:
        stored = rest.values(joint, channel)
        if stored is not None:
            rest_values[joint] = stored
            continue
        # No stored rest: read the bind pose by restoring it and then undoing the restore by hand.
        poses = cmds.dagPose(joint, query=True, bindPose=True) or []
        if not poses:
            unbound.append(joint)
            continue
        # dagPose -restore resets the whole hierarchy below, so snapshot every member and put them back.
        members = cmds.ls(cmds.dagPose(poses[0], query=True, members=True) or [], long=True)
        snapshot = {m: {c: cmds.getAttr("{}.{}".format(m, c))[0] for c in CHANNELS} for m in members}
        cmds.dagPose(joint, restore=True, name=poses[0])
        rest_values[joint] = cmds.getAttr("{}.{}".format(joint, channel))[0]
        for member, values in snapshot.items():
            for name, value in values.items():
                _set_channel(member, name, value)
    return rest_values, unbound


def _settable(node, channel):
    return any(cmds.getAttr("{}.{}{}".format(node, channel, axis), settable=True) for axis in "XYZ")


def _set_channel(node, channel, values):
    for axis, value in zip("XYZ", values):
        attribute = "{}.{}{}".format(node, channel, axis)
        # settable is False for locked or connected (constrained, driven) channels.
        if cmds.getAttr(attribute, settable=True):
            cmds.setAttr(attribute, value)


def _short(node):
    return node.rsplit("|", 1)[-1]
