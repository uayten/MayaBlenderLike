"""Blender-style constraint stack built from standard Maya nodes.

Blender evaluates an object's constraints in order, each blending into the result of the
previous one by its influence. Maya constraints have no order: two on the same channel fight.
This module rebuilds Blender's stack as a chain of plain transforms, outside the owner's
hierarchy:

    MBL_constraintStacks            hidden group at the world root
      <owner>_stack                 records the specs, message-connected to the owner
        <owner>_base                follows the owner's parent at the owner's rest
          c0_rest   c0_effect  c0   c0_effect carries the Maya constraint; c0 blends
            c1_rest c1_effect  c1   effect and rest by the influence (keyable on c0, c1...)
              ...
    owner <- parent + scale constraint from the last layer

Everything is a standard Maya node, so the rig opens and animates without this module, the
owner's hierarchy (a skeleton, for instance) is untouched, and FBX exports see normal joints.
Game engines never receive constraints of any kind: bake animation when exporting.

Limit Location / Rotation / Scale use Maya's transform limits on the owner itself, and IK
creates an ikHandle; neither takes part in the stack order.
"""
import contextlib
import json
import uuid

from maya import cmds

ROOT_GROUP = "MBL_constraintStacks"
SPEC_ATTRIBUTE = "mblStackSpecs"
OWNER_ATTRIBUTE = "mblOwner"
OWNER_REST_ATTRIBUTE = "mblOwnerRest"

# Blender name -> (label, stackable)
TYPES = {
    "COPY_LOCATION": ("Copy Location", True),
    "COPY_ROTATION": ("Copy Rotation", True),
    "COPY_SCALE": ("Copy Scale", True),
    "COPY_TRANSFORMS": ("Copy Transforms", True),
    "CHILD_OF": ("Child Of", True),
    "DAMPED_TRACK": ("Damped Track", True),
    "TRACK_TO": ("Track To", True),
    "LOCKED_TRACK": ("Locked Track", True),
    "STRETCH_TO": ("Stretch To", True),
}

# Blender's Add Constraint menu layout.
MENU = [
    ("Transform", ["COPY_LOCATION", "COPY_ROTATION", "COPY_SCALE", "COPY_TRANSFORMS",
                   "LIMIT_LOCATION", "LIMIT_ROTATION", "LIMIT_SCALE"]),
    ("Tracking", ["DAMPED_TRACK", "IK", "LOCKED_TRACK", "STRETCH_TO", "TRACK_TO"]),
    ("Relationship", ["CHILD_OF"]),
]
LABELS = dict((k, v[0]) for k, v in TYPES.items())
LABELS.update({"LIMIT_LOCATION": "Limit Location", "LIMIT_ROTATION": "Limit Rotation",
               "LIMIT_SCALE": "Limit Scale", "IK": "Inverse Kinematics"})

AXIS_VECTORS = {"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1),
                "-X": (-1, 0, 0), "-Y": (0, -1, 0), "-Z": (0, 0, -1)}


def new_spec(constraint_type, target=None):
    """A constraint spec with Blender's defaults."""
    spec = {
        "id": uuid.uuid4().hex,
        "type": constraint_type,
        "target": _uuid(target) if target else None,
        "influence": 1.0,
        "enabled": True,
        "axes": [True, True, True],
        "offset": False,
        "track_axis": "Y",
        "up_axis": "Z",
        "lock_axis": "Z",
    }
    return spec


# --- reading ---

def stack_node(owner):
    """The <owner>_stack group that records the owner's specs, or None."""
    for node in cmds.listConnections(owner + ".message", destination=True, source=False) or []:
        if cmds.attributeQuery(SPEC_ATTRIBUTE, node=node, exists=True):
            return cmds.ls(node, long=True)[0]
    return None


def specs(owner):
    node = stack_node(owner)
    if node is None:
        return []
    return json.loads(cmds.getAttr(node + "." + SPEC_ATTRIBUTE) or "[]")


def layer(owner, spec_id):
    """The layer transform of one spec (where influence and enabled live), or None."""
    node = stack_node(owner)
    if node is None:
        return None
    for child in cmds.listRelatives(node, allDescendents=True, fullPath=True, type="transform") or []:
        if cmds.attributeQuery("mblSpecId", node=child, exists=True) and cmds.getAttr(child + ".mblSpecId") == spec_id:
            return child
    return None


def target_name(spec_or_uuid):
    value = spec_or_uuid.get("target") if isinstance(spec_or_uuid, dict) else spec_or_uuid
    if not value:
        return None
    found = cmds.ls(value, long=True)
    return found[0] if found else None


# --- editing (each call rebuilds the chain from the specs) ---

def add(owner, constraint_type, target=None):
    spec = new_spec(constraint_type, target)
    items = specs(owner) + [spec]
    build(owner, items)
    return spec


def update(owner, spec_id, **changes):
    items = specs(owner)
    for spec in items:
        if spec["id"] == spec_id:
            if "target" in changes and changes["target"]:
                changes["target"] = _uuid(changes["target"])
            spec.update(changes)
    build(owner, items)


def remove(owner, spec_id):
    build(owner, [s for s in specs(owner) if s["id"] != spec_id])


def move(owner, spec_id, step):
    items = specs(owner)
    index = next(i for i, s in enumerate(items) if s["id"] == spec_id)
    other = index + step
    if 0 <= other < len(items):
        items[index], items[other] = items[other], items[index]
        build(owner, items)


def apply(owner, spec_id):
    """Blender's Apply: keep the owner where the stack puts it now and remove that constraint."""
    world = cmds.xform(owner, query=True, worldSpace=True, matrix=True)
    remove(owner, spec_id)
    _set_owner_rest_from_world(owner, world)


# --- building ---

def build(owner, items):
    """Delete the owner's chain and rebuild it from the specs; an empty list removes the stack."""
    owner = cmds.ls(owner, long=True)[0]
    cmds.undoInfo(openChunk=True, chunkName="constraint_stack")
    try:
        live = _live_values(owner)
        owner_rest = _teardown(owner)
        items = [s for s in items if TYPES.get(s["type"], (None, False))[1]]
        if not items:
            return
        if owner_rest is None:
            owner_rest = _local_values(owner)
        stack = _create_stack_node(owner, items, owner_rest)
        previous = _create_base(owner, stack)
        for index, spec in enumerate(items):
            previous = _create_layer(previous, index, spec, live.get(spec["id"]))
        _hide(stack)
        with unlocked(owner):
            cmds.parentConstraint(previous, owner, maintainOffset=False, name=_short(owner) + "_stackParent")
            cmds.scaleConstraint(previous, owner, maintainOffset=False, name=_short(owner) + "_stackScale")
    finally:
        cmds.undoInfo(closeChunk=True)


def _teardown(owner):
    """Remove the owner's chain and constraints; returns the owner's own rest values recorded at creation."""
    node = stack_node(owner)
    if node is None:
        return None
    owner_rest = json.loads(cmds.getAttr(node + "." + OWNER_REST_ATTRIBUTE))
    for constraint in cmds.listRelatives(owner, children=True, fullPath=True, type="constraint") or []:
        if "_stack" in constraint.rsplit("|", 1)[-1]:
            cmds.delete(constraint)
    cmds.delete(node)
    _set_local_values(owner, owner_rest)
    return owner_rest


def _create_stack_node(owner, items, owner_rest):
    if not cmds.objExists(ROOT_GROUP):
        cmds.group(empty=True, world=True, name=ROOT_GROUP)
    stack = cmds.group(empty=True, parent=ROOT_GROUP, name=_short(owner) + "_stack")
    stack = cmds.ls(stack, long=True)[0]
    cmds.addAttr(stack, longName=SPEC_ATTRIBUTE, dataType="string")
    cmds.setAttr(stack + "." + SPEC_ATTRIBUTE, json.dumps(items), type="string")
    cmds.addAttr(stack, longName=OWNER_REST_ATTRIBUTE, dataType="string")
    cmds.setAttr(stack + "." + OWNER_REST_ATTRIBUTE, json.dumps(owner_rest), type="string")
    cmds.addAttr(stack, longName=OWNER_ATTRIBUTE, attributeType="message")
    cmds.connectAttr(owner + ".message", stack + "." + OWNER_ATTRIBUTE)
    return stack


def _create_base(owner, stack):
    """A transform at the owner's world placement that follows the owner's parent."""
    base = cmds.group(empty=True, parent=stack, name=_short(owner) + "_base")
    base = cmds.ls(base, long=True)[0]
    cmds.xform(base, worldSpace=True, matrix=cmds.xform(owner, query=True, worldSpace=True, matrix=True))
    parent = cmds.listRelatives(owner, parent=True, fullPath=True)
    if parent:
        cmds.parentConstraint(parent[0], base, maintainOffset=True)
        cmds.scaleConstraint(parent[0], base, maintainOffset=True)
    return base


def _create_layer(previous, index, spec, live):
    prefix = "c{}_".format(index)
    rest = _child(previous, prefix + "rest")
    effect = _child(previous, prefix + "effect")
    result = _child(previous, prefix + spec["type"].lower())

    target = target_name(spec)
    if target:
        _constrain_effect(effect, target, spec)

    cmds.addAttr(result, longName="mblSpecId", dataType="string")
    cmds.setAttr(result + ".mblSpecId", spec["id"], type="string")
    cmds.addAttr(result, longName="influence", attributeType="double", minValue=0, maxValue=1, keyable=True)
    cmds.addAttr(result, longName="enabled", attributeType="bool", keyable=True)
    influence = live["influence"] if live else spec["influence"]
    cmds.setAttr(result + ".influence", influence)
    cmds.setAttr(result + ".enabled", live["enabled"] if live else spec["enabled"])
    if live and live.get("curve"):
        cmds.connectAttr(live["curve"] + ".output", result + ".influence", force=True)

    # weight(effect) = influence * enabled, weight(rest) = 1 - that: Blender's influence blend.
    weight = _create_multiply(_short(result) + "_weight")
    cmds.connectAttr(result + ".influence", weight + ".input1")
    cmds.connectAttr(result + ".enabled", weight + ".input2")
    remainder = cmds.createNode("reverse", name=_short(result) + "_restWeight")
    cmds.connectAttr(weight + ".output", remainder + ".inputX")
    for command in (cmds.parentConstraint, cmds.scaleConstraint):
        constraint = command(effect, rest, result, maintainOffset=False)[0]
        aliases = command(constraint, query=True, weightAliasList=True)
        cmds.connectAttr(weight + ".output", "{}.{}".format(constraint, aliases[0]))
        cmds.connectAttr(remainder + ".outputX", "{}.{}".format(constraint, aliases[1]))
        if command is cmds.parentConstraint:
            cmds.setAttr(constraint + ".interpType", 2)  # shortest
    return result


def _constrain_effect(effect, target, spec):
    kind = spec["type"]
    skip = [axis for axis, used in zip("xyz", spec["axes"]) if not used]
    offset = spec["offset"]
    if kind == "COPY_LOCATION":
        cmds.pointConstraint(target, effect, maintainOffset=offset, skip=skip or "none")
    elif kind == "COPY_ROTATION":
        cmds.orientConstraint(target, effect, maintainOffset=offset, skip=skip or "none")
    elif kind == "COPY_SCALE":
        cmds.scaleConstraint(target, effect, maintainOffset=offset, skip=skip or "none")
    elif kind == "COPY_TRANSFORMS":
        cmds.parentConstraint(target, effect, maintainOffset=False)
        cmds.scaleConstraint(target, effect, maintainOffset=False)
    elif kind == "CHILD_OF":
        # Blender's Child Of with Set Inverse: follow the target from where it is now.
        cmds.parentConstraint(target, effect, maintainOffset=True)
        cmds.scaleConstraint(target, effect, maintainOffset=True)
    elif kind == "DAMPED_TRACK":
        cmds.aimConstraint(target, effect, aimVector=AXIS_VECTORS[spec["track_axis"]], worldUpType="none")
    elif kind == "TRACK_TO":
        # Blender's up is world Z; after the FBX axis conversion that is Maya's world Y (scene up).
        cmds.aimConstraint(target, effect, aimVector=AXIS_VECTORS[spec["track_axis"]],
                           upVector=AXIS_VECTORS[spec["up_axis"]], worldUpType="scene")
    elif kind == "LOCKED_TRACK":
        parent = cmds.listRelatives(effect, parent=True, fullPath=True)[0]
        cmds.aimConstraint(target, effect, aimVector=AXIS_VECTORS[spec["track_axis"]],
                           upVector=AXIS_VECTORS[spec["lock_axis"]], worldUpType="objectrotation",
                           worldUpObject=parent, worldUpVector=AXIS_VECTORS[spec["lock_axis"]])
    elif kind == "STRETCH_TO":
        axis = spec["track_axis"]
        cmds.aimConstraint(target, effect, aimVector=AXIS_VECTORS[axis], worldUpType="none")
        # Scale along the aim axis by current distance / distance at creation.
        distance = cmds.createNode("distanceBetween", name=_short(effect) + "_distance")
        cmds.connectAttr(effect + ".worldMatrix[0]", distance + ".inMatrix1")
        cmds.connectAttr(target + ".worldMatrix[0]", distance + ".inMatrix2")
        rest_length = cmds.getAttr(distance + ".distance") or 1.0
        ratio = cmds.createNode("multiplyDivide", name=_short(effect) + "_stretch")
        cmds.setAttr(ratio + ".operation", 2)
        cmds.connectAttr(distance + ".distance", ratio + ".input1X")
        cmds.setAttr(ratio + ".input2X", rest_length)
        cmds.connectAttr(ratio + ".outputX", "{}.scale{}".format(effect, axis[-1].upper()))


# --- live values kept across rebuilds ---

def _live_values(owner):
    """Current influence (and its animation curve) per spec id, so a rebuild keeps them."""
    values = {}
    for spec in specs(owner):
        node = layer(owner, spec["id"])
        if node is None:
            continue
        curves = cmds.listConnections(node + ".influence", source=True, destination=False, type="animCurve") or []
        values[spec["id"]] = {"influence": cmds.getAttr(node + ".influence"),
                              "enabled": cmds.getAttr(node + ".enabled"),
                              "curve": curves[0] if curves else None}
        if curves:
            cmds.disconnectAttr(curves[0] + ".output", node + ".influence")
    return values


# --- helpers ---

@contextlib.contextmanager
def unlocked(node, channels=("translate", "rotate", "scale")):
    """Unlock the node's channels for the block, then lock them back.

    Blender's channel locks only stop the animator; constraints still move the bone. Maya refuses
    to connect a constraint to a locked channel, but keeps a connection made before locking.
    """
    plugs = ["{}.{}{}".format(node, c, a) for c in channels for a in "XYZ"]
    locked = [p for p in plugs if cmds.getAttr(p, lock=True)]
    for plug in locked:
        cmds.setAttr(plug, lock=False)
    try:
        yield
    finally:
        for plug in locked:
            cmds.setAttr(plug, lock=True)


def _local_values(node):
    return {c: list(cmds.getAttr("{}.{}".format(node, c))[0]) for c in ("translate", "rotate", "scale")}


def _set_local_values(node, values):
    for channel, triple in values.items():
        for axis, value in zip("XYZ", triple):
            attribute = "{}.{}{}".format(node, channel, axis)
            if cmds.getAttr(attribute, settable=True):
                cmds.setAttr(attribute, value)


def _set_owner_rest_from_world(owner, world):
    node = stack_node(owner)
    if node is None:
        cmds.xform(owner, worldSpace=True, matrix=world)
        return
    # The owner is driven by its stack: record the new placement as its own rest and rebuild.
    items = specs(owner)
    _teardown(owner)
    cmds.xform(owner, worldSpace=True, matrix=world)
    build(owner, items)


def _create_multiply(name):
    # Maya 2026 renamed multDoubleLinear to multDL; older versions only have the legacy name.
    node_type = "multDL" if "multDL" in (cmds.allNodeTypes() or []) else "multDoubleLinear"
    return cmds.createNode(node_type, name=name)


def _child(parent, name):
    node = cmds.group(empty=True, parent=parent, name=name)
    return cmds.ls(node, long=True)[0]


def _hide(stack):
    # The chain is plumbing: keep it out of the viewport, but visible in the Outliner for other riggers.
    cmds.setAttr(ROOT_GROUP + ".visibility", False)


def _short(node):
    return node.rsplit("|", 1)[-1]


def _uuid(node):
    return cmds.ls(node, uuid=True)[0]
