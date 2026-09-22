"""Turn Blender mechanism bones into Maya's usual rig helpers.

Blender rigs use non-deforming bones as pivots, targets and helpers. In Maya the same job is
done by locators (a visible point, good as a constraint target or pivot) or groups (an
invisible transform, good as an offset). This converts non-deforming joints into either:

- same name, world position and orientation as the joint,
- kept in a MECH group beside the skeleton, so the exported skeleton only has deforming joints,
- following the joint's parent as before (parent + scale constraint, with offset),
- constraints that used the joint as a target are reconnected to the new node.

A joint that deforms nothing but has deforming joints under it stays: removing it would cut the
skeleton. Joints driven by a constraint are left alone too; both are listed in a warning.
"""
from maya import cmds

from . import rest

LOCATOR, GROUP = "locator", "group"
CONTAINER_NAME = "MECH"
# Connections to these node types belong to the joint's own skeleton bookkeeping, not to the rig.
SKIPPED_DESTINATIONS = ("dagPose", "skinCluster", "joint")


def is_deforming(joint):
    return bool(cmds.listConnections(joint + ".worldMatrix", type="skinCluster"))


def mechanism_joints(joints):
    """Non-deforming joints in the skeletons of the given joints (or of the given groups)."""
    return [j for j in rest.skeleton(joints) if not is_deforming(j)]


def select_mechanisms():
    """Select every non-deforming joint in the selected rig (switching to pose mode, where joints are selectable)."""
    from . import modes
    found = mechanism_joints(modes.rig_joints())
    if modes.current_mode() != modes.POSE:
        modes.go(modes.POSE)
    cmds.select(found, replace=True)
    cmds.headsUpMessage("{} mechanism joints (non-deforming)".format(len(found)), time=2.0)
    return found


def convert(joints, kind=LOCATOR):
    """Replace non-deforming joints by locators or groups. Returns the new nodes."""
    from . import modes
    if modes.is_editing():
        cmds.warning("Leave Edit Mode first (Tab): converting deletes joints that edit mode is holding.")
        return []
    joints = cmds.ls(joints, type="joint", long=True)
    convertible, skipped = [], []
    for joint in joints:
        reason = _blocker(joint)
        if reason:
            skipped.append("{} ({})".format(_short(joint), reason))
        else:
            convertible.append(joint)
    if skipped:
        cmds.warning("Mechanisms left as joints: " + "; ".join(skipped))
    if not convertible:
        return []

    cmds.undoInfo(openChunk=True, chunkName="convert_mechanisms")
    try:
        created = _convert(convertible, kind)
    finally:
        cmds.undoInfo(closeChunk=True)
    cmds.select(created, replace=True)
    return created


def _blocker(joint):
    if is_deforming(joint):
        return "deforms the mesh"
    descendants = cmds.listRelatives(joint, allDescendents=True, type="joint", fullPath=True) or []
    if any(is_deforming(d) for d in descendants):
        return "deforming joints below it"
    for axis in ("tx", "ty", "tz", "rx", "ry", "rz"):
        if cmds.listConnections("{}.{}".format(joint, axis), source=True, destination=False, type="constraint"):
            return "driven by a constraint"
    return None


def _convert(joints, kind):
    selected = set(joints)
    # Whole subtrees go together: a non-deforming joint's non-deforming children convert with it.
    for joint in list(joints):
        for child in cmds.listRelatives(joint, allDescendents=True, type="joint", fullPath=True) or []:
            selected.add(child)
    ordered = sorted(selected, key=lambda j: j.count("|"))
    mapping = {}
    for joint in ordered:
        node = _create(kind, joint)
        cmds.xform(node, worldSpace=True, matrix=cmds.xform(joint, query=True, worldSpace=True, matrix=True))
        parent = cmds.listRelatives(joint, parent=True, fullPath=True)
        parent = parent[0] if parent else None
        if parent in mapping:
            node = cmds.parent(node, mapping[parent])[0]
        else:
            node = cmds.parent(node, _container(joint))[0]
            if parent:
                # Keep following the bone it hung from in Blender.
                cmds.parentConstraint(parent, node, maintainOffset=True)
                cmds.scaleConstraint(parent, node, maintainOffset=True)
        mapping[joint] = cmds.ls(node, long=True)[0]

    for joint, node in mapping.items():
        _retarget(joint, node)

    names = {joint: _short(joint) for joint in mapping}
    top_level = [j for j in ordered if not any(j.startswith(other + "|") for other in selected if other != j)]
    uuids = {joint: cmds.ls(node, uuid=True)[0] for joint, node in mapping.items()}
    cmds.delete(top_level)
    created = []
    for joint, uid in uuids.items():
        node = cmds.ls(uid, long=True)[0]
        created.append(cmds.ls(cmds.rename(node, names[joint]), long=True)[0])
    return created


def _create(kind, joint):
    if kind == GROUP:
        return cmds.group(empty=True, world=True, name="mblMechanism#")
    from . import custom_shapes
    locator = cmds.spaceLocator(name="mblMechanism#")[0]
    size = custom_shapes.bone_length(joint) * 0.25
    shape = cmds.listRelatives(locator, shapes=True, fullPath=True)[0]
    cmds.setAttr(shape + ".localScale", size, size, size)
    return locator


def _container(joint):
    """RIG|MECH beside the skeleton when the skeleton lives in a group, MECH at the root otherwise."""
    root = rest.roots([joint])[0]
    top = "|" + root.split("|")[1]
    parent = top if top != root else None
    path = (parent or "") + "|" + CONTAINER_NAME
    if cmds.objExists(path):
        return path
    group = cmds.group(empty=True, name=CONTAINER_NAME, parent=parent) if parent else \
        cmds.group(empty=True, name=CONTAINER_NAME, world=True)
    return cmds.ls(group, long=True)[0]


def _retarget(joint, node):
    """Move the joint's outgoing rig connections (constraint targets, utility nodes) to the new node."""
    pairs = cmds.listConnections(joint, source=False, destination=True, plugs=True, connections=True) or []
    for source, destination in zip(pairs[0::2], pairs[1::2]):
        if cmds.nodeType(destination.split(".")[0]) in SKIPPED_DESTINATIONS:
            continue
        attribute = source.split(".", 1)[1]
        base = attribute.split("[")[0].split(".")[-1]
        if cmds.attributeQuery(base, node=node, exists=True):
            cmds.connectAttr("{}.{}".format(node, attribute), destination, force=True)
        else:
            # Joint-only inputs (jointOrient): the new node carries that rotation in rotate, so feed zero.
            cmds.disconnectAttr(source, destination)
            try:
                cmds.setAttr(destination, 0)
            except RuntimeError:
                pass


def _short(node):
    return node.rsplit("|", 1)[-1]
