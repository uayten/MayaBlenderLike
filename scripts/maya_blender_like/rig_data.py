"""Apply the rig data Blender's MayaBlenderLike exporter writes (blender/mayablenderlike_rig_export.py).

FBX brings the skeleton and skin; the JSON brings the rest of the Blender rig, applied to the
controls of a converted rig (mechanisms.py), matched by bone name:

- channel locks: locked and hidden in the Channel Box, as Maya riggers deliver controls
- rotation mode: rotate order (Blender's XYZ Euler is Maya's xyz; quaternion stays xyz, with a note)
- bone collections: selection sets (bone_collections.py), hidden collections hidden
- custom shapes: the shape's wire as curves on the control, in the bone color
- constraints: the stack types, limits and IK, with the Blender settings that have a Maya match
"""
import json
import math
import re

from maya import cmds
import maya.api.OpenMaya as om

from . import bone_collections, controls, custom_shapes, owner_constraints, rest, stack

ROTATE_ORDERS = {"XYZ": 0, "YZX": 1, "ZXY": 2, "XZY": 3, "YXZ": 4, "ZYX": 5}
STACK_TYPES = {"COPY_LOCATION", "COPY_ROTATION", "COPY_SCALE", "COPY_TRANSFORMS", "CHILD_OF",
               "DAMPED_TRACK", "TRACK_TO", "LOCKED_TRACK", "STRETCH_TO"}
LIMIT_TYPES = {"LIMIT_LOCATION", "LIMIT_ROTATION", "LIMIT_SCALE"}
CM_PER_BLENDER_UNIT = 100.0


def apply_from_dialog():
    """Menu entry: pick the JSON, apply it to the selected converted rig."""
    from . import modes
    joints = modes.rig_joints()
    if not joints:
        cmds.warning("Apply Blender Rig Data: select the converted rig first.")
        return None
    paths = cmds.fileDialog2(fileMode=1, fileFilter="Rig data (*.json)", caption="Blender rig data")
    if not paths:
        return None
    return apply(paths[0], "|" + cmds.ls(joints[0], long=True)[0].split("|")[1])


def apply(path, top):
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    cmds.undoInfo(openChunk=True, chunkName="apply_rig_data")
    try:
        notes = _apply(data, top)
    finally:
        cmds.undoInfo(closeChunk=True)
    for note in notes:
        cmds.warning("Rig data: " + note)
    message = "Rig data applied to {} ({} notes in the Script Editor)".format(top.lstrip("|"), len(notes))
    cmds.headsUpMessage(message, time=3.0)
    print("MayaBlenderLike: " + message)
    return notes


def _apply(data, top):
    notes = []
    rig = _Rig(top, data)
    bones = []
    for bone in data["bones"]:
        if rig.control(bone["name"]):
            bones.append(bone)
        else:
            notes.append("{}: no control or joint of that name in {}".format(bone["name"], top.lstrip("|")))
    for bone in bones:
        control = rig.control(bone["name"])
        _rotation_mode(control, bone, notes)
        _locks(control, bone)
        if bone.get("custom_shape"):
            _custom_shape(control, bone, rig, notes)
    _collections(data, bones, rig)
    for bone in bones:
        _constraints(rig.control(bone["name"]), bone, rig, notes)
    return notes


class _Rig(object):
    """Finds the Maya node for a Blender bone or object name in one converted rig."""

    def __init__(self, top, data):
        self.top = top
        self.armature = data["armature"]
        self.scale = data.get("armature_scale", 1.0)
        joints = rest.skeleton(cmds.listRelatives(top, allDescendents=True, type="joint", fullPath=True) or [])
        self.nodes = {}
        for joint in joints:
            self.nodes.setdefault(_short(joint), joint)
        for control in controls.in_rig(top):
            self.nodes[_short(control)] = control

    def control(self, bone):
        """The control of a bone (<bone>_ctrl), else the joint of that name. FBX turns '-' and '.' into '_'."""
        name = _maya_name(bone)
        return self.nodes.get(name + "_ctrl") or self.nodes.get(name)

    def target(self, obj, subtarget):
        if obj == self.armature and subtarget:
            return self.control(subtarget)
        if obj:
            found = cmds.ls(_maya_name(obj), long=True)
            return found[0] if found else None
        return None

    def units(self, control):
        """Control-space units per Blender unit (m to cm, times armature scale, over the control's own scale)."""
        world = om.MMatrix(cmds.getAttr(control + ".worldMatrix"))
        own = om.MVector(world.getElement(1, 0), world.getElement(1, 1), world.getElement(1, 2)).length() or 1.0
        return self.scale * CM_PER_BLENDER_UNIT / own


def _rotation_mode(control, bone, notes):
    mode = bone["rotation_mode"]
    if mode in ROTATE_ORDERS:
        cmds.setAttr(control + ".rotateOrder", ROTATE_ORDERS[mode])
    else:
        notes.append("{}: {} rotation has no Maya match, left as XYZ Euler".format(bone["name"], mode))


def _locks(control, bone):
    for channel, key in (("translate", "lock_location"), ("rotate", "lock_rotation"), ("scale", "lock_scale")):
        for axis, locked in zip("XYZ", bone[key]):
            if locked:
                cmds.setAttr("{}.{}{}".format(control, channel, axis), lock=True, keyable=False, channelBox=False)


def _custom_shape(control, bone, rig, notes):
    shape = bone["custom_shape"]
    if shape.get("override_transform"):
        notes.append("{}: custom shape drawn at bone {} in Blender, here at its own bone".format(
            bone["name"], shape["override_transform"]))
    if not controls.is_control(control):
        notes.append("{}: custom shape skipped, the bone has no control".format(bone["name"]))
        return
    units = rig.units(control)
    curves = [[[v * units for v in point] for point in curve] for curve in shape["curves"]]
    custom_shapes.assign_curves(control, curves, bone.get("color"))


def _collections(data, bones, rig):
    rig_name = _short(rig.top)
    for entry in data["collections"]:
        members = [rig.control(b["name"]) for b in bones if entry["name"] in b["collections"]]
        if not members:
            continue
        collection = bone_collections.create(entry["name"], rig_name, members)
        if not entry["visible"]:
            bone_collections.set_visible(collection, False)


def _constraints(owner, bone, rig, notes):
    items = []
    for constraint in bone["constraints"]:
        kind = constraint["type"]
        label = "{}: {} '{}'".format(bone["name"], kind, constraint["name"])
        if kind in STACK_TYPES:
            spec = _stack_spec(constraint, rig, label, notes)
            if spec:
                items.append(spec)
        elif kind in LIMIT_TYPES:
            _limit(owner, constraint, rig, label, notes)
        elif kind == "IK":
            _ik(owner, constraint, rig, label, notes)
        else:
            notes.append(label + ": no Maya match yet, skipped")
    if items:
        stack.build(owner, stack.specs(owner) + items)


def _stack_spec(constraint, rig, label, notes):
    target = rig.target(constraint.get("target"), constraint.get("subtarget"))
    if target is None:
        notes.append(label + ": target not found, skipped")
        return None
    for key in ("owner_space", "target_space"):
        if constraint.get(key, "WORLD") != "WORLD":
            notes.append("{}: {} {} built as World Space".format(label, key, constraint[key]))
    if constraint.get("head_tail"):
        notes.append(label + ": Head/Tail ignored, uses the target bone's head")
    spec = stack.new_spec(constraint["type"], target)
    spec["influence"] = constraint.get("influence", 1.0)
    spec["enabled"] = not constraint.get("mute", False)
    if "use_x" in constraint:
        spec["axes"] = [constraint["use_x"], constraint["use_y"], constraint["use_z"]]
    spec["offset"] = bool(constraint.get("use_offset", False))
    if constraint.get("track_axis"):
        spec["track_axis"] = _axis(constraint["track_axis"])
    if constraint.get("lock_axis"):
        spec["lock_axis"] = _axis(constraint["lock_axis"])
    if constraint.get("up_axis"):
        spec["up_axis"] = _axis(constraint["up_axis"])
    if any(constraint.get("invert_" + a) for a in "xyz"):
        notes.append(label + ": Invert axes ignored")
    return spec


def _limit(owner, constraint, rig, label, notes):
    kind = constraint["type"]
    if constraint.get("owner_space", "LOCAL") != "LOCAL":
        notes.append("{}: owner space {} applied as Local".format(label, constraint["owner_space"]))
    for index, axis in enumerate("xyz"):
        if kind == "LIMIT_ROTATION":
            use = constraint.get("use_limit_" + axis, False)
            use_min = use_max = use
            low, high = (math.degrees(constraint["min_" + axis]), math.degrees(constraint["max_" + axis]))
        else:
            use_min, use_max = constraint.get("use_min_" + axis, False), constraint.get("use_max_" + axis, False)
            low, high = constraint["min_" + axis], constraint["max_" + axis]
            if kind == "LIMIT_LOCATION":
                units = rig.units(owner)
                low, high = low * units, high * units
        if use_min or use_max:
            owner_constraints.set_limit(owner, kind, index, use_min, low, use_max, high)


def _ik(owner, constraint, rig, label, notes):
    target = rig.target(constraint.get("target"), constraint.get("subtarget"))
    pole = rig.target(constraint.get("pole_target"), constraint.get("pole_subtarget"))
    if constraint.get("pole_target") and pole is None:
        notes.append(label + ": pole target not found, built without it")
    if pole and constraint.get("pole_angle"):
        notes.append("{}: pole angle {:.1f} deg ignored".format(label, math.degrees(constraint["pole_angle"])))
    if constraint.get("use_tail") is False:
        notes.append(label + ": Use Tail off not supported, the chain reaches with the tail")
    owner_constraints.add_ik(owner, target, pole, constraint.get("chain_count", 0))


def _axis(blender_value):
    """TRACK_NEGATIVE_Y -> -Y, LOCK_X -> X, UP_Z -> Z."""
    axis = blender_value.rsplit("_", 1)[-1]
    return "-" + axis if "NEGATIVE" in blender_value else axis


def _maya_name(name):
    return re.sub(r"[^A-Za-z0-9_]", "_", name)


def _short(node):
    return node.rsplit("|", 1)[-1]
