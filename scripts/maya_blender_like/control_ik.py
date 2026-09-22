"""Blender's Inverse Kinematics on the controls of a converted rig.

Maya's ikHandle only solves joints, and the rig's joints follow their controls. So IK on a
control builds its own joint chain in MECH, one joint at each control of the chain plus one at
the owner's tail (Blender's IK brings the owner bone's tail to the target), solves it with an
ikHandle toward the target (and pole), and turns each control of the chain like its IK joint.

The chain is plumbing, rebuilt whenever the settings change or edit mode moves the rest.
"""
from maya import cmds
import maya.api.OpenMaya as om

from . import controls, custom_shapes, mechanisms, stack

OWNER_ATTRIBUTE = "mblIkOwner"        # same message the joint IK uses, so owner_constraints finds both
CHAIN_ATTRIBUTE = "mblIkChain"        # message: handle -> first IK joint
COUNT_ATTRIBUTE = "mblChainCount"
DRIVE_SUFFIX = "_mblIk"


def chain(owner, chain_count):
    """Controls from the chain's top to the owner. chain_count 0: every control above, like Blender."""
    result = [owner]
    while chain_count <= 0 or len(result) < chain_count:
        parent = cmds.listRelatives(result[0], parent=True, fullPath=True)
        if not parent or not controls.is_control(parent[0]):
            break
        result.insert(0, parent[0])
    return result


def add(owner, target=None, pole=None, chain_count=2):
    owner = cmds.ls(owner, long=True)[0]
    links = chain(owner, chain_count)
    positions = [cmds.xform(c, query=True, worldSpace=True, translation=True) for c in links]
    positions.append(_tail(owner))
    name = owner.rsplit("|", 1)[-1]

    cmds.select(clear=True)
    joints = [cmds.joint(position=p, name="{}_ik{}".format(name, i)) for i, p in enumerate(positions)]
    cmds.joint(joints[0], edit=True, orientJoint="xyz", secondaryAxisOrient="yup", children=True, zeroScaleOrient=True)
    cmds.joint(joints[-1], edit=True, orientJoint="none")
    mech = mechanisms.mech_group("|" + owner.split("|")[1])
    first = cmds.ls(cmds.parent(joints[0], mech)[0], long=True)[0]
    joints = [first] + (cmds.listRelatives(first, allDescendents=True, type="joint", fullPath=True) or [])[::-1]
    cmds.setAttr(first + ".visibility", False)

    above = cmds.listRelatives(links[0], parent=True, fullPath=True)
    if above:
        # The chain hangs from whatever the top control hangs from.
        cmds.parentConstraint(above[0], first, maintainOffset=True)
        cmds.scaleConstraint(above[0], first, maintainOffset=True)

    handle = cmds.ikHandle(startJoint=joints[0], endEffector=joints[-1], solver="ikRPsolver", name=name + "_ik")[0]
    handle = cmds.ls(cmds.parent(handle, mech)[0], long=True)[0]
    cmds.setAttr(handle + ".visibility", False)
    cmds.addAttr(handle, longName=OWNER_ATTRIBUTE, attributeType="message")
    cmds.connectAttr(owner + ".message", handle + "." + OWNER_ATTRIBUTE)
    cmds.addAttr(handle, longName=CHAIN_ATTRIBUTE, attributeType="message")
    cmds.connectAttr(first + ".message", handle + "." + CHAIN_ATTRIBUTE)
    cmds.addAttr(handle, longName=COUNT_ATTRIBUTE, attributeType="long")
    cmds.setAttr(handle + "." + COUNT_ATTRIBUTE, chain_count)
    # Tie the controls to the chain while it still matches them, before the target pulls it.
    for control, joint in zip(links, joints):
        with stack.unlocked(control, ("rotate",)):
            cmds.orientConstraint(joint, control, maintainOffset=True, name=control.rsplit("|", 1)[-1] + DRIVE_SUFFIX)
    if target:
        cmds.pointConstraint(target, handle, maintainOffset=False)
    if pole:
        cmds.poleVectorConstraint(pole, handle)
    return handle


def is_control_ik(handle):
    return cmds.attributeQuery(CHAIN_ATTRIBUTE, node=handle, exists=True)


def remove(handle):
    """Delete the handle, its joint chain and the constraints turning the controls; controls go back to rest rotation."""
    owner = (cmds.listConnections(handle + "." + OWNER_ATTRIBUTE, source=True, destination=False) or [None])[0]
    first = (cmds.listConnections(handle + "." + CHAIN_ATTRIBUTE, source=True, destination=False) or [None])[0]
    count = cmds.getAttr(handle + "." + COUNT_ATTRIBUTE)
    cmds.delete(handle)
    if first:
        cmds.delete(first)
    if owner:
        for control in chain(cmds.ls(owner, long=True)[0], count):
            for constraint in cmds.listRelatives(control, children=True, type="orientConstraint", fullPath=True) or []:
                if constraint.endswith(DRIVE_SUFFIX):
                    cmds.delete(constraint)
            for axis in "XYZ":
                if cmds.getAttr(control + ".rotate" + axis, settable=True):
                    cmds.setAttr(control + ".rotate" + axis, 0)


def _tail(control):
    """World position of the control's bone tail."""
    local = om.MVector(*custom_shapes.bone_direction(control)) * custom_shapes.bone_length(control)
    world = om.MMatrix(cmds.getAttr(control + ".worldMatrix"))
    point = om.MPoint(local) * world
    return (point.x, point.y, point.z)
