"""Blender's bone custom shapes for Maya joints.

A curve shape is parented under the joint itself (Maya's native technique): the joint is
drawn and clicked through the curve, and its bone can be hidden, like Blender's Custom Shape
with Wireframe display. It is plain Maya data, so anyone who opens the file sees and selects
the shapes without this module. FBX exports skip the curves and keep a clean skeleton.

Shapes are built in bone space: their Y axis runs along the bone (toward the first child
joint) and they are scaled by the bone length, like Blender's "Scale to Bone Length".

On a converted rig (see mechanisms.py) the shape goes on the bone's control instead: asking
for a joint's custom shape reaches the control that drives it.
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


_W = 0.1   # Blender's octahedral bone: widest at 10% of its length, 10% wide
SHAPES = {
    "Bone": [[(-_W, _W, -_W), (_W, _W, -_W), (_W, _W, _W), (-_W, _W, _W), (-_W, _W, -_W)],
             [(0, 0, 0), (-_W, _W, -_W), (0, 1, 0), (_W, _W, _W), (0, 0, 0)],
             [(0, 0, 0), (_W, _W, -_W), (0, 1, 0), (-_W, _W, _W), (0, 0, 0)]],
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


def shape_owner(node):
    """Where a node's custom shape lives: the control of a joint driven by one, otherwise the node itself."""
    from . import controls
    node = cmds.ls(node, long=True)[0]
    if cmds.nodeType(node) == "joint":
        return controls.control_of(node) or node
    return node


def accepts(node):
    """Joints and controls can have a custom shape."""
    from . import controls
    return cmds.nodeType(node) == "joint" or controls.is_control(node)


def shapes(node):
    """The custom shape curves of a joint or control."""
    return [s for s in cmds.listRelatives(shape_owner(node), shapes=True, fullPath=True, type="nurbsCurve") or []
            if cmds.attributeQuery(TAG, node=s, exists=True)]


def settings(node):
    """Current custom shape: name, size, color, bone hidden. None if it has no custom shape."""
    found = shapes(node)
    if not found:
        return None
    first = found[0]
    owner = shape_owner(node)
    hidden = cmds.nodeType(owner) != "joint" or cmds.getAttr(owner + ".drawStyle") == 2
    return {"shape": cmds.getAttr(first + ".mblShapeName"), "size": cmds.getAttr(first + ".mblShapeSize"),
            "color": cmds.getAttr(first + ".overrideColor"), "hide_bone": hidden}


def assign(nodes, shape="Circle", size=1.0, color=COLORS["Yellow"], hide_bone=True, source=None):
    """Give each joint or control a custom shape. shape: a SHAPES name, or source: a curve transform to copy."""
    cmds.undoInfo(openChunk=True, chunkName="custom_shape")
    try:
        for owner in _owners(nodes):
            _clear_shapes(owner)
            for curve_shape in _build(owner, shape, size, source):
                tag(curve_shape, "Custom" if source else shape, size)
                cmds.setAttr(curve_shape + ".overrideEnabled", True)
                cmds.setAttr(curve_shape + ".overrideColor", color)
            if cmds.nodeType(owner) == "joint":
                cmds.setAttr(owner + ".drawStyle", 2 if hide_bone else 0)
    finally:
        cmds.undoInfo(closeChunk=True)


def remove(nodes):
    cmds.undoInfo(openChunk=True, chunkName="remove_custom_shape")
    try:
        for owner in _owners(nodes):
            _clear_shapes(owner)
            if cmds.nodeType(owner) == "joint":
                cmds.setAttr(owner + ".drawStyle", 0)
            else:
                build(owner, "Bone")   # a control can't go without a shape: back to the bone's
    finally:
        cmds.undoInfo(closeChunk=True)


def tag(curve_shape, name, size):
    cmds.addAttr(curve_shape, longName=TAG, attributeType="bool", defaultValue=True)
    cmds.addAttr(curve_shape, longName="mblShapeName", dataType="string")
    cmds.setAttr(curve_shape + ".mblShapeName", name, type="string")
    cmds.addAttr(curve_shape, longName="mblShapeSize", attributeType="double", defaultValue=size)


def build(owner, shape, size=1.0):
    """Tagged curves of a SHAPES name under a joint or control, in Maya's default color."""
    created = _build(owner, shape, size, None)
    for curve_shape in created:
        tag(curve_shape, shape, size)
    return created


def armature_joint(node):
    """A joint of the node's armature: the joint itself, the one a control drives, or one in the control's rig."""
    from . import controls
    if cmds.nodeType(node) == "joint":
        return node
    joint = controls.linked_joint(node)
    if joint:
        return joint
    top = "|" + cmds.ls(node, long=True)[0].split("|")[1]
    linked = [controls.linked_joint(c) for c in controls.in_rig(top)]
    return next((j for j in linked if j), None)


def _owners(nodes):
    result = []
    for node in cmds.ls(nodes, long=True):
        if accepts(node):
            owner = shape_owner(node)
            if owner not in result:
                result.append(owner)
    return result


def _clear_shapes(joint):
    found = shapes(joint)
    if found:
        cmds.delete(found)


def _build(joint, shape, size, source):
    """Curves created under a temporary transform in bone space, then moved onto the joint or control."""
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
    rotation = om.MQuaternion(om.MVector(0, 1, 0), om.MVector(bone_direction(joint))).asEulerRotation()
    cmds.setAttr(holder + ".rotate", *[math.degrees(v) for v in (rotation.x, rotation.y, rotation.z)])
    cmds.setAttr(holder + ".scale", scale, scale, scale)
    cmds.makeIdentity(holder, apply=True, rotate=True, scale=True)
    created = []
    for curve_shape in cmds.listRelatives(holder, shapes=True, fullPath=True) or []:
        created.extend(cmds.parent(curve_shape, joint, relative=True, shape=True))
    cmds.delete(holder)
    joint_name = joint.rsplit("|", 1)[-1]
    return [cmds.rename(s, "{}_customShape{}".format(joint_name, i if i else "")) for i, s in enumerate(created)]


# --- In Front (Blender: Armature > Viewport Display > In Front) ---

IN_FRONT_ATTRIBUTE = "mblInFront"


def in_front(joint):
    root = _root(joint)
    return bool(cmds.attributeQuery(IN_FRONT_ATTRIBUTE, node=root, exists=True)
                and cmds.getAttr(root + "." + IN_FRONT_ATTRIBUTE))


def set_in_front(joints, enabled):
    """Draw the armature through meshes: joints x-rayed in the viewports, its curves always on top.

    Maya can't x-ray joints one skeleton at a time, only per viewport (Joint X-Ray), so the joints of
    every skeleton show through while any armature has In Front on. Curves (custom shapes and the
    controls in the rig's group) get Always Draw On Top each. The setting is saved in the scene.
    """
    cmds.undoInfo(openChunk=True, chunkName="in_front")
    try:
        from . import rest
        for root in rest.roots(cmds.ls(joints, type="joint", long=True)):
            if not cmds.attributeQuery(IN_FRONT_ATTRIBUTE, node=root, exists=True):
                cmds.addAttr(root, longName=IN_FRONT_ATTRIBUTE, attributeType="bool")
            cmds.setAttr(root + "." + IN_FRONT_ATTRIBUTE, enabled)
            top = "|" + root.split("|")[1]
            for curve in cmds.listRelatives(top, allDescendents=True, type="nurbsCurve", fullPath=True) or []:
                cmds.setAttr(curve + ".alwaysDrawOnTop", enabled)
    finally:
        cmds.undoInfo(closeChunk=True)
    apply_viewports()


def apply_viewports():
    """Joint X-Ray in every viewport while any armature in the scene has In Front on."""
    enabled = any(cmds.getAttr(j + "." + IN_FRONT_ATTRIBUTE)
                  for j in cmds.ls(type="joint", long=True)
                  if cmds.attributeQuery(IN_FRONT_ATTRIBUTE, node=j, exists=True))
    for panel in cmds.getPanel(type="modelPanel") or []:
        try:
            cmds.modelEditor(panel, edit=True, jointXray=enabled)
        except RuntimeError:
            pass


def install():
    """Reapply In Front to the viewports whenever a scene opens.

    Opening a scene restores the panel settings saved in the file after the SceneOpened event,
    which would switch Joint X-Ray back off; so the reapply waits until Maya is idle.
    """
    later = lambda: cmds.evalDeferred(apply_viewports, lowestPriority=True)
    cmds.scriptJob(event=["SceneOpened", later])
    later()


def _root(joint):
    from . import rest
    return rest.roots([joint])[0]


def bone_length(node):
    """Length of a joint's bone (to its first child joint), or the one recorded on a control."""
    from . import controls
    if cmds.attributeQuery(controls.BONE_LENGTH, node=node, exists=True):
        return cmds.getAttr(node + "." + controls.BONE_LENGTH)
    child = _first_child(node)
    if child is None:
        return DEFAULT_LENGTH_CM
    return om.MVector(cmds.getAttr(child + ".translate")[0]).length() or DEFAULT_LENGTH_CM


def bone_direction(node):
    """Unit direction of a joint's bone in its own space, or the one recorded on a control."""
    from . import controls
    if cmds.attributeQuery(controls.BONE_AXIS, node=node, exists=True):
        return tuple(cmds.getAttr(node + "." + controls.BONE_AXIS)[0])
    child = _first_child(node)
    direction = om.MVector(cmds.getAttr(child + ".translate")[0]) if child else om.MVector()
    if direction.length() < 1e-6:
        return (0.0, 1.0, 0.0)
    direction.normalize()
    return (direction.x, direction.y, direction.z)


def _first_child(joint):
    children = cmds.listRelatives(joint, children=True, type="joint", fullPath=True) or []
    return children[0] if children else None
