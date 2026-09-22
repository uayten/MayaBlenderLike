"""Rest pose of joints, Blender's edit-mode rest, stored as hidden attributes on each joint.

The skeleton stays made of standard Maya joints; the rest values are three extra hidden
attributes per joint, so other animators, Maya tools and FBX exports see a normal skeleton.
"""
import math

from maya import cmds
import maya.api.OpenMaya as om

CHANNELS = ("translate", "rotate", "scale")
REST_ATTRIBUTES = {"translate": "mblRestTranslate", "rotate": "mblRestRotate", "scale": "mblRestScale"}


def has_rest(joint):
    return cmds.attributeQuery(REST_ATTRIBUTES["translate"], node=joint, exists=True)


def values(joint, channel):
    """Stored rest values of one channel, or None if the joint has no stored rest."""
    if not has_rest(joint):
        return None
    return cmds.getAttr("{}.{}".format(joint, REST_ATTRIBUTES[channel]))[0]


def store(joints):
    """Record the joints' current translate / rotate / scale as their rest."""
    for joint in joints:
        for channel, attribute in REST_ATTRIBUTES.items():
            if not cmds.attributeQuery(attribute, node=joint, exists=True):
                cmds.addAttr(joint, longName=attribute, attributeType="double3")
                for axis in "XYZ":
                    cmds.addAttr(joint, longName=attribute + axis, attributeType="double", parent=attribute)
            cmds.setAttr("{}.{}".format(joint, attribute), *cmds.getAttr("{}.{}".format(joint, channel))[0])


def restore(joints):
    """Put joints back at their stored rest; joints without one are left alone."""
    for joint in joints:
        for channel in CHANNELS:
            rest = values(joint, channel)
            if rest is None:
                continue
            for axis, value in zip("XYZ", rest):
                attribute = "{}.{}{}".format(joint, channel, axis)
                if cmds.getAttr(attribute, settable=True):
                    cmds.setAttr(attribute, value)


def freeze_rotation(joint):
    """Move rotate into jointOrient without changing the joint's orientation.

    Maya's Freeze Transformations refuses joints with skin; this does the same math by hand,
    so a joint at rest reads rotate 0, as Maya riggers expect.
    """
    if not all(cmds.getAttr("{}.rotate{}".format(joint, axis), settable=True) for axis in "XYZ"):
        return
    order = cmds.getAttr(joint + ".rotateOrder")
    rotate = om.MEulerRotation([math.radians(v) for v in cmds.getAttr(joint + ".rotate")[0]], order)
    orient = om.MEulerRotation([math.radians(v) for v in cmds.getAttr(joint + ".jointOrient")[0]], om.MEulerRotation.kXYZ)
    # Maya composes a joint's rotation as rotate, then jointOrient (row vectors: R * JO).
    combined = (rotate.asQuaternion() * orient.asQuaternion()).asEulerRotation()
    cmds.setAttr(joint + ".rotate", 0, 0, 0)
    cmds.setAttr(joint + ".jointOrient", *[math.degrees(v) for v in (combined.x, combined.y, combined.z)])


def roots(joints):
    """Top joint of each given joint's hierarchy: the skeleton as a whole, Blender's armature."""
    found = set()
    for joint in joints:
        root = cmds.ls(joint, long=True)[0]
        while True:
            parent = cmds.listRelatives(root, parent=True, fullPath=True, type="joint")
            if not parent:
                break
            root = parent[0]
        found.add(root)
    return sorted(found)


def skeleton(joints):
    """Every joint in the hierarchies the given joints belong to."""
    result = []
    for root in roots(joints):
        result.append(root)
        result.extend(cmds.listRelatives(root, allDescendents=True, fullPath=True, type="joint") or [])
    return result


def skin_clusters(joints):
    clusters = set()
    for joint in joints:
        clusters.update(cmds.listConnections(joint + ".worldMatrix", type="skinCluster") or [])
    return sorted(clusters)


def rebind(joints):
    """Make the joints' current placement the skin's bind: the mesh keeps its shape at this pose.

    Sets each influence's bindPreMatrix to the joint's current world inverse and resets the
    bind pose, which is what Blender does when an armature's rest changes in edit mode.
    """
    joints = set(cmds.ls(joints, long=True))
    for cluster in skin_clusters(joints):
        for index in cmds.getAttr(cluster + ".matrix", multiIndices=True) or []:
            source = cmds.listConnections("{}.matrix[{}]".format(cluster, index), source=True, destination=False)
            if not source:
                continue
            joint = cmds.ls(source[0], long=True)[0]
            if joint in joints:
                inverse = cmds.getAttr(joint + ".worldInverseMatrix")
                cmds.setAttr("{}.bindPreMatrix[{}]".format(cluster, index), inverse, type="matrix")
    for pose in set(cmds.dagPose(list(joints), query=True, bindPose=True) or []):
        members = cmds.dagPose(pose, query=True, members=True) or []
        cmds.dagPose(members, reset=True, name=pose)
