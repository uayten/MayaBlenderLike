"""Convert a skeleton imported from Blender into the MayaBlenderLike rig layout.

Blender poses bones directly; a Maya rig poses controls whose channels read 0 / 0 / 1 at rest,
and they drive the joints. Converting the selected rig sorts every joint by what it does, judged
by the skin weights actually painted on the mesh:

- Deforming joints (and joints with deforming joints below, such as a root) stay joints, the
  skeleton that FBX exports. Each gets a control shaped like a Blender bone (or its custom
  shape, moved over) that drives it.
- Loose non-deforming joints (no joints below: IK targets, poles, pivots) are replaced by a
  control only, since nothing needs a joint there.
- Non-deforming chains (a non-deforming joint with joints below, typical of IK / FK mechanism
  chains) stay joints, so an ikHandle can use them, but leave the skeleton for a MECH group,
  following the bone they hung from.
- Leaf bones added by Blender's FBX export ("Add Leaf Bones", named *_end) only mark where the
  last bones end: they give those bones their length, then are deleted.

Controls go in a CTRL group in the rig's top group, parented like the bones they stand for.
Display layers split the rig the Maya way: <rig>_GEO (the skinned meshes, visible but not
clickable), <rig>_JNT (skeleton and MECH, hidden) and <rig>_CTRL (the controls).
The conversion is done at the rest pose and is one undo step.
"""
from maya import cmds

from . import controls, custom_shapes, rest

CONTAINER_NAME = "MECH"
LEAF_SUFFIX = custom_shapes.LEAF_SUFFIX
CONTROL_SUFFIX = "_ctrl"
LAYER_REFERENCE = 2   # displayLayer.displayType: drawn normally, but can't be clicked
# Connections to these node types belong to the joint's own skeleton bookkeeping, not to the rig.
SKIPPED_DESTINATIONS = ("dagPose", "skinCluster", "joint")


def convert_selected_rig():
    """Menu entry: convert the rig of the selection (a joint, control or the armature group)."""
    from . import modes
    if modes.is_editing():
        cmds.warning("Leave Edit Mode first (Tab).")
        return None
    joints = modes.rig_joints()
    if not joints:
        cmds.warning("Convert Rig: select the armature (or any of its joints) first.")
        return None
    skeleton = rest.skeleton(joints)
    if any(controls.control_of(j) for j in skeleton):
        cmds.warning("Convert Rig: this rig is already converted.")
        return None
    cmds.undoInfo(openChunk=True, chunkName="convert_rig")
    try:
        report = convert(skeleton)
    finally:
        cmds.undoInfo(closeChunk=True)
    cmds.select(report["top"], replace=True)
    message = "Rig converted: {} controls driving joints, {} controls replacing joints, {} mechanism chains".format(
        len(report["linked"]), len(report["loose"]), len(report["chains"]))
    cmds.headsUpMessage(message, time=3.0)
    print("MayaBlenderLike: " + message)
    if report["along_x"]:
        cmds.warning("Convert Rig: the bones run along the joints' X axis (FBX exported with Primary Bone Axis X). "
                     "Controls follow the joints' axes, so Blender axis names (Track Y, rotate Y) won't match: "
                     "re-export from Blender with Primary Bone Axis Y and Secondary X, the defaults.")
    return report


def convert(skeleton):
    """Convert these joints (whole skeletons). Returns what became of them."""
    uuids = cmds.ls(cmds.ls(skeleton, type="joint"), uuid=True)
    top = rig_group(skeleton)   # may reparent the skeleton: read the paths after it
    skeleton = cmds.ls(uuids, long=True)
    weighted = deforming_joints(skeleton)
    leaves = [j for j in skeleton if _is_leaf_marker(j, weighted)]
    along_x = _leaves_along_x(leaves)
    kept = [j for j in skeleton if j in weighted or any(d in weighted for d in _joint_descendants(j))]
    loose, chains = [], []
    for joint in skeleton:
        parent = _parent_joint(joint)
        if joint in kept or joint in leaves or (parent is not None and parent not in kept):
            continue   # only the topmost joint of each non-deforming branch decides the branch
        if any(c not in leaves for c in _joint_children(joint)):
            chains.append(joint)
        else:
            loose.append(joint)

    rest.ensure(skeleton)
    rest.restore(kept)
    ctrl_group = controls.container(top)

    # Controls, parents first, each under the control of the nearest bone above it.
    mapping = {}
    for joint in sorted(kept + loose, key=lambda j: j.count("|")):
        parent = _nearest(joint, mapping) or ctrl_group
        control = controls.create(joint, parent, _short(joint) + CONTROL_SUFFIX)
        _give_shape(joint, control)
        mapping[joint] = control
    for joint in kept:
        controls.link(mapping[joint], joint)
        cmds.setAttr(joint + ".drawStyle", 2)   # the control draws the bone now

    chain_nodes = [_move_chain(joint, top) for joint in chains]

    for joint in loose:
        _retarget(joint, mapping[joint])
    # Leaves inside chains moved with them; leaves under loose joints go with their parent.
    doomed = loose + [j for j in leaves if not any(j.startswith(n + "|") for n in chains + loose)]
    uuids = {j: cmds.ls(mapping[j], uuid=True)[0] for j in mapping}
    if doomed:
        cmds.delete(doomed)
    current = {j: cmds.ls(uid, long=True)[0] for j, uid in uuids.items()}
    _display_layers(top, kept)
    return {"top": top,
            "linked": [current[j] for j in kept],
            "loose": [current[j] for j in loose],
            "chains": chain_nodes,
            "along_x": along_x}


def _display_layers(top, joints):
    """GEO (reference), JNT (hidden) and CTRL layers for the rig, named after its top group."""
    rig = _short(top)
    meshes = set()
    for cluster in rest.skin_clusters(joints):
        for shape in cmds.skinCluster(cluster, query=True, geometry=True) or []:
            meshes.update(cmds.listRelatives(shape, parent=True, fullPath=True) or [])
    skeleton = rest.roots(joints) + [top + "|" + CONTAINER_NAME]
    for suffix, members, visible, display in (("_GEO", sorted(meshes), True, LAYER_REFERENCE),
                                               ("_JNT", skeleton, False, 0),
                                               ("_CTRL", [top + "|" + controls.CONTAINER_NAME], True, 0)):
        members = [m for m in members if cmds.objExists(m)]
        if not members:
            continue
        layer = cmds.createDisplayLayer(name=rig + suffix, empty=True)
        cmds.editDisplayLayerMembers(layer, members, noRecurse=True)
        cmds.setAttr(layer + ".visibility", visible)
        cmds.setAttr(layer + ".displayType", display)


def deforming_joints(joints):
    """Joints with weight painted on some vertex (being a skin influence with zero weight doesn't count)."""
    found = set()
    for cluster in rest.skin_clusters(joints):
        for influence in cmds.skinCluster(cluster, query=True, weightedInfluence=True) or []:
            found.update(cmds.ls(influence, long=True))
    return found


def rig_group(skeleton):
    """The rig's top group; a skeleton at the world root gets one (<root>_rig) so its controls have a home."""
    root = rest.roots(skeleton)[0]
    top = "|" + root.split("|")[1]
    if top != root:
        return top
    group = cmds.group(empty=True, world=True, name=_short(root) + "_rig")
    for other in rest.roots(skeleton):
        cmds.parent(other, group)
    return cmds.ls(group, long=True)[0]


def _leaves_along_x(leaves):
    """True when most leaf bones sit on their parent's X axis instead of Y (Blender's bone axis)."""
    votes = 0
    for leaf in leaves:
        offset = cmds.getAttr(leaf + ".translate")[0]
        votes += 1 if abs(offset[0]) > abs(offset[1]) else -1
    return votes > 0


def _is_leaf_marker(joint, weighted):
    return (_short(joint).endswith(LEAF_SUFFIX) and joint not in weighted
            and not _joint_children(joint) and _parent_joint(joint) is not None)


def _give_shape(joint, control):
    """The joint's custom shape moves to the control; without one, the control is drawn as a Blender bone."""
    existing = [s for s in cmds.listRelatives(joint, shapes=True, fullPath=True, type="nurbsCurve") or []
                if cmds.attributeQuery(custom_shapes.TAG, node=s, exists=True)]
    if not existing:
        custom_shapes.build(control, "Bone")
        return
    scale = controls.world_scale(joint)
    for curve_shape in existing:
        # Same place and axes as the joint, but the control is unscaled: bring the points to its units.
        moved = cmds.parent(curve_shape, control, relative=True, shape=True)[0]
        for index, point in enumerate(cmds.getAttr(moved + ".cv[*]")):
            cmds.setAttr("{}.cv[{}]".format(moved, index), *[v * scale for v in point])
    cmds.setAttr(joint + ".drawStyle", 0)


def _move_chain(joint, top):
    """A non-deforming chain leaves the skeleton for MECH, following the bone it hung from."""
    parent = _parent_joint(joint)
    moved = cmds.ls(cmds.parent(joint, mech_group(top))[0], long=True)[0]
    if parent:
        cmds.parentConstraint(parent, moved, maintainOffset=True)
        cmds.scaleConstraint(parent, moved, maintainOffset=True)
    return moved


def mech_group(top):
    """The rig's MECH group, created on first use."""
    path = top + "|" + CONTAINER_NAME
    if cmds.objExists(path):
        return path
    return cmds.ls(cmds.group(empty=True, name=CONTAINER_NAME, parent=top), long=True)[0]


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


def _nearest(joint, mapping):
    """Control of the closest joint above this one that has a control."""
    parent = _parent_joint(joint)
    while parent is not None:
        if parent in mapping:
            return mapping[parent]
        parent = _parent_joint(parent)
    return None


def _parent_joint(joint):
    node = joint
    while True:
        parent = cmds.listRelatives(node, parent=True, fullPath=True)
        if not parent:
            return None
        if cmds.nodeType(parent[0]) == "joint":
            return parent[0]
        node = parent[0]


def _joint_children(joint):
    return cmds.listRelatives(joint, children=True, type="joint", fullPath=True) or []


def _joint_descendants(joint):
    return cmds.listRelatives(joint, allDescendents=True, type="joint", fullPath=True) or []


def _short(node):
    return node.rsplit("|", 1)[-1]
