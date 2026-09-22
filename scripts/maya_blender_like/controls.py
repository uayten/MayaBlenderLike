"""Controls that stand for bones: what the animator poses, with channels at 0 / 0 / 1 at rest.

A control is a curve transform in the rig's CTRL group. Its rest lives in offsetParentMatrix
(Maya's own zero-offset), so translate and rotate read 0 and scale 1 at rest, like a Blender
pose bone. A control linked to a joint drives it through a parent + scale constraint; the joint
keeps its real values, so FBX exports still get a normal skeleton.

Control hierarchy mirrors the bone hierarchy: a bone's control is parented under its parent
bone's control.
"""
from maya import cmds
import maya.api.OpenMaya as om

CONTAINER_NAME = "CTRL"
CONTROL_TAG = "mblControl"
JOINT_LINK = "mblJoint"          # message: control -> the joint it drives
BONE_LENGTH = "mblBoneLength"    # bone length and direction (in the control's space) for custom shapes
BONE_AXIS = "mblBoneAxis"
LINK_SUFFIXES = ("_mblLink", "_mblLinkScale")


def is_control(node):
    return cmds.attributeQuery(CONTROL_TAG, node=node, exists=True)


def linked_joint(control):
    """The joint a control drives, or None."""
    if not cmds.attributeQuery(JOINT_LINK, node=control, exists=True):
        return None
    found = cmds.listConnections(control + "." + JOINT_LINK, source=True, destination=False) or []
    return cmds.ls(found[0], long=True)[0] if found else None


def control_of(joint):
    """The control that drives a joint, or None."""
    for node in cmds.listConnections(joint + ".message", source=False, destination=True, plugs=True) or []:
        if node.endswith("." + JOINT_LINK):
            return cmds.ls(node.split(".")[0], long=True)[0]
    return None


def in_rig(top):
    """Every control under a rig's top group, parents before children."""
    nodes = cmds.listRelatives(top, allDescendents=True, type="transform", fullPath=True) or []
    return sorted((n for n in nodes if is_control(n)), key=lambda n: n.count("|"))


def container(top):
    path = top + "|" + CONTAINER_NAME
    if cmds.objExists(path):
        return path
    return cmds.ls(cmds.group(empty=True, name=CONTAINER_NAME, parent=top), long=True)[0]


def create(joint, parent, name):
    """A control at the joint's world placement, under parent, with its rest in offsetParentMatrix."""
    from . import custom_shapes
    control = cmds.group(empty=True, name=name, parent=parent)
    control = cmds.ls(control, long=True)[0]
    cmds.addAttr(control, longName=CONTROL_TAG, attributeType="bool", defaultValue=True)
    cmds.addAttr(control, longName=BONE_LENGTH, attributeType="double",
                 defaultValue=custom_shapes.bone_length(joint))
    cmds.addAttr(control, longName=BONE_AXIS, attributeType="double3")
    for axis in "XYZ":
        cmds.addAttr(control, longName=BONE_AXIS + axis, attributeType="double", parent=BONE_AXIS)
    cmds.setAttr(control + "." + BONE_AXIS, *custom_shapes.bone_direction(joint))
    cmds.xform(control, worldSpace=True, matrix=cmds.xform(joint, query=True, worldSpace=True, matrix=True))
    zero(control)
    return control


def zero(node):
    """Move the node's local transform into offsetParentMatrix: same placement, channels at 0 / 0 / 1."""
    local = om.MMatrix(cmds.xform(node, query=True, objectSpace=True, matrix=True))
    offset = om.MMatrix(cmds.getAttr(node + ".offsetParentMatrix"))
    cmds.setAttr(node + ".offsetParentMatrix", list(local * offset), type="matrix")
    cmds.xform(node, objectSpace=True, matrix=list(om.MMatrix()))


def link(control, joint):
    """The joint follows the control; the control remembers which joint it drives."""
    if not cmds.attributeQuery(JOINT_LINK, node=control, exists=True):
        cmds.addAttr(control, longName=JOINT_LINK, attributeType="message")
    if linked_joint(control) != cmds.ls(joint, long=True)[0]:
        cmds.connectAttr(joint + ".message", control + "." + JOINT_LINK, force=True)
    name = joint.rsplit("|", 1)[-1]
    cmds.parentConstraint(control, joint, maintainOffset=False, name=name + LINK_SUFFIXES[0])
    cmds.scaleConstraint(control, joint, maintainOffset=False, name=name + LINK_SUFFIXES[1])


def unlink(joint):
    """Remove the constraints from the joint's control, leaving the joint where it is. The link record stays."""
    for constraint in cmds.listRelatives(joint, children=True, type="constraint", fullPath=True) or []:
        if constraint.endswith(LINK_SUFFIXES):
            cmds.delete(constraint)


def rest_worlds(controls):
    """World matrix of each control at rest (channels at 0 / 0 / 1), whatever the current pose."""
    worlds = {}
    for control in sorted(controls, key=lambda n: n.count("|")):
        worlds[control] = om.MMatrix(cmds.getAttr(control + ".offsetParentMatrix")) * _parent_rest(control, worlds)
    return worlds


def set_rest_worlds(worlds):
    """Give each control a new rest (world matrices), keeping its pose channels as they are."""
    for control in sorted(worlds, key=lambda n: n.count("|")):
        offset = worlds[control] * _parent_rest(control, worlds).inverse()
        cmds.setAttr(control + ".offsetParentMatrix", list(offset), type="matrix")


def _parent_rest(control, worlds):
    parent = cmds.listRelatives(control, parent=True, fullPath=True)
    if not parent:
        return om.MMatrix()
    if parent[0] in worlds:
        return worlds[parent[0]]
    return om.MMatrix(cmds.getAttr(parent[0] + ".worldMatrix"))
