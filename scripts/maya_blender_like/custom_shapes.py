"""Blender's bone custom shapes for Maya joints.

A curve shape is parented under the joint itself (Maya's native technique): the joint is
drawn and clicked through the curve, and its bone can be hidden, like Blender's Custom Shape
with Wireframe display. It is plain Maya data, so anyone who opens the file sees and selects
the shapes without this module. FBX exports skip the curves and keep a clean skeleton.

Shapes are built in bone space: their Y axis runs along the bone (toward the first child
joint) and they are scaled by the bone length, like Blender's "Scale to Bone Length".
"""
import math

from maya import cmds
import maya.api.OpenMaya as om

TAG = "mblCustomShape"
DEFAULT_LENGTH_CM = 10.0   # size reference for joints without a child

# Unit shapes (points, degree, closed) with Y along the bone, as in Blender's bone space.
def _circle(points=16, y=0.0, radius=1.0, plane="xz"):
    result = []
    for i in range(points + 1):
        a = 2 * math.pi * i / points
        u, v = radius * math.cos(a), radius * math.sin(a)
        result.append({"xz": (u, y, v), "xy": (u, v, 0), "yz": (0, u, v)}[plane])
    return result


SHAPES = {
    "Circle": [_circle()],
    "Square": [[(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1), (-1, 0, -1)]],
    "Cube": [[(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1), (-1, -1, -1), (-1, 1, -1), (1, 1, -1),
              (1, 1, 1), (-1, 1, 1), (-1, 1, -1), (1, 1, -1), (1, -1, -1), (1, -1, 1), (1, 1, 1),
              (-1, 1, 1), (-1, -1, 1)]],
    "Sphere": [_circle(plane="xz"), _circle(plane="xy"), _circle(plane="yz")],
    "Diamond": [[(0, 1, 0), (1, 0, 0), (0, -1, 0), (-1, 0, 0), (0, 1, 0), (0, 0, 1), (0, -1, 0),
                 (0, 0, -1), (0, 1, 0)], [(1, 0, 0), (0, 0, 1), (-1, 0, 0), (0, 0, -1), (1, 0, 0)]],
    "Arrow": [[(0, 0, 0), (0, 1, 0), (-0.2, 0.75, 0), (0, 1, 0), (0.2, 0.75, 0)]],
    "Line": [[(0, 0, 0), (0, 1, 0)]],
}

# Maya color indices with the names Blender users would look for.
COLORS = {"Yellow": 17, "Orange": 21, "Red": 13, "Pink": 20, "Blue": 6, "Light Blue": 18,
          "Green": 14, "Light Green": 26, "Purple": 9, "White": 16}


def shapes(joint):
    """The custom shape curves under a joint."""
    return [s for s in cmds.listRelatives(joint, shapes=True, fullPath=True, type="nurbsCurve") or []
            if cmds.attributeQuery(TAG, node=s, exists=True)]


def settings(joint):
    """Current custom shape of a joint: name, size, color, bone hidden. None if it has no custom shape."""
    found = shapes(joint)
    if not found:
        return None
    first = found[0]
    return {"shape": cmds.getAttr(first + ".mblShapeName"), "size": cmds.getAttr(first + ".mblShapeSize"),
            "color": cmds.getAttr(first + ".overrideColor"), "hide_bone": cmds.getAttr(joint + ".drawStyle") == 2}


def assign(joints, shape="Circle", size=1.0, color=COLORS["Yellow"], hide_bone=True, source=None):
    """Give each joint a custom shape. shape: a SHAPES name, or source: a curve transform to copy."""
    cmds.undoInfo(openChunk=True, chunkName="custom_shape")
    try:
        for joint in cmds.ls(joints, type="joint", long=True):
            _clear_shapes(joint)
            for curve_shape in _build(joint, shape, size, source):
                cmds.addAttr(curve_shape, longName=TAG, attributeType="bool", defaultValue=True)
                cmds.addAttr(curve_shape, longName="mblShapeName", dataType="string")
                cmds.setAttr(curve_shape + ".mblShapeName", "Custom" if source else shape, type="string")
                cmds.addAttr(curve_shape, longName="mblShapeSize", attributeType="double", defaultValue=size)
                cmds.setAttr(curve_shape + ".overrideEnabled", True)
                cmds.setAttr(curve_shape + ".overrideColor", color)
            cmds.setAttr(joint + ".drawStyle", 2 if hide_bone else 0)
    finally:
        cmds.undoInfo(closeChunk=True)


def remove(joints):
    cmds.undoInfo(openChunk=True, chunkName="remove_custom_shape")
    try:
        for joint in cmds.ls(joints, type="joint", long=True):
            _clear_shapes(joint)
            cmds.setAttr(joint + ".drawStyle", 0)
    finally:
        cmds.undoInfo(closeChunk=True)


def _clear_shapes(joint):
    found = shapes(joint)
    if found:
        cmds.delete(found)


def _build(joint, shape, size, source):
    """Curves created under a temporary transform in bone space, then moved onto the joint."""
    length = bone_length(joint)
    holder = cmds.group(empty=True, name="mblShapeHolder")
    holder = cmds.parent(holder, joint, relative=True)[0]
    if source:
        copy = cmds.duplicate(source, returnRootsOnly=True)[0]
        for curve_shape in cmds.listRelatives(copy, shapes=True, fullPath=True, type="nurbsCurve") or []:
            cmds.parent(curve_shape, holder, relative=True, shape=True)
        cmds.delete(copy)
        scale = size
    else:
        for points in SHAPES[shape]:
            curve = cmds.curve(degree=1, point=points)
            cmds.parent(cmds.listRelatives(curve, shapes=True, fullPath=True)[0], holder, relative=True, shape=True)
            cmds.delete(curve)
        scale = size * length
    # Bone space: shape Y along the direction to the first child joint.
    rotation = om.MQuaternion(om.MVector(0, 1, 0), _bone_direction(joint)).asEulerRotation()
    cmds.setAttr(holder + ".rotate", *[math.degrees(v) for v in (rotation.x, rotation.y, rotation.z)])
    cmds.setAttr(holder + ".scale", scale, scale, scale)
    cmds.makeIdentity(holder, apply=True, rotate=True, scale=True)
    created = []
    for curve_shape in cmds.listRelatives(holder, shapes=True, fullPath=True) or []:
        created.extend(cmds.parent(curve_shape, joint, relative=True, shape=True))
    cmds.delete(holder)
    joint_name = joint.rsplit("|", 1)[-1]
    return [cmds.rename(s, "{}_customShape{}".format(joint_name, i if i else "")) for i, s in enumerate(created)]


def bone_length(joint):
    child = _first_child(joint)
    if child is None:
        return DEFAULT_LENGTH_CM
    return om.MVector(cmds.getAttr(child + ".translate")[0]).length() or DEFAULT_LENGTH_CM


def _bone_direction(joint):
    child = _first_child(joint)
    if child is None:
        return om.MVector(0, 1, 0)
    direction = om.MVector(cmds.getAttr(child + ".translate")[0])
    return direction.normal() if direction.length() > 1e-6 else om.MVector(0, 1, 0)


def _first_child(joint):
    children = cmds.listRelatives(joint, children=True, type="joint", fullPath=True) or []
    return children[0] if children else None
