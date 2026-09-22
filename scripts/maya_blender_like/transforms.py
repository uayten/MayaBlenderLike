"""Blender's Alt+G / Alt+R / Alt+S: clear location, rotation or scale of the selection."""
from maya import cmds

RESET_VALUES = {"translate": 0.0, "rotate": 0.0, "scale": 1.0}
CHANNELS = ("translate", "rotate", "scale")


def clear(channel):
    """Reset translate, rotate or scale on the selection, skipping locked or driven channels.

    Objects and controls go to 0 (1 for scale). A joint's translate and rotate hold its rest
    position, so joints go back to their bind pose instead, like a Blender bone to rest.
    Joints without a bind pose (not skinned) are skipped with a warning.
    """
    nodes = cmds.ls(selection=True, transforms=True, long=True) or []
    if not nodes:
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
        cmds.warning("Clear {}: no bind pose for {}; joints without skin have no stored rest. "
                     "Animate controls with offset groups instead.".format(channel, ", ".join(_short(j) for j in unbound)))


def _bind_pose_values(joints, channel):
    """Bind-pose values of one channel per joint, read by restoring the pose and then undoing the restore by hand."""
    rest_values, unbound = {}, []
    for joint in joints:
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


def _set_channel(node, channel, values):
    for axis, value in zip("XYZ", values):
        attribute = "{}.{}{}".format(node, channel, axis)
        # settable is False for locked or connected (constrained, driven) channels.
        if cmds.getAttr(attribute, settable=True):
            cmds.setAttr(attribute, value)


def _short(node):
    return node.rsplit("|", 1)[-1]
