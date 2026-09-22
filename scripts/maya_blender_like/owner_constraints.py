"""Blender constraints that act on the owner itself instead of joining the stack order.

- Limit Location / Rotation / Scale: Maya's transform limits on the owner's own channels,
  which is what Blender limits usually do on controls: keep the animator inside a range.
- Inverse Kinematics: a Maya ikHandle from the owner up its chain, following the target,
  with an optional pole target. On a control of a converted rig, see control_ik.py.
"""
import functools

from maya import cmds

from . import control_ik, controls


def _undoable(function):
    """One undo step per call, like any Blender operator."""
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        cmds.undoInfo(openChunk=True, chunkName=function.__name__)
        try:
            return function(*args, **kwargs)
        finally:
            cmds.undoInfo(closeChunk=True)
    return wrapper


LIMIT_CHANNELS = {"LIMIT_LOCATION": "translation", "LIMIT_ROTATION": "rotation", "LIMIT_SCALE": "scale"}
IK_OWNER_ATTRIBUTE = "mblIkOwner"


# --- limits ---

def limits(owner, kind):
    """Per axis: (use_min, min, use_max, max)."""
    channel = LIMIT_CHANNELS[kind]
    result = []
    for axis in "XYZ":
        values = cmds.transformLimits(owner, query=True, **{channel + axis: True})
        enabled = cmds.transformLimits(owner, query=True, **{"enable" + channel.capitalize() + axis: True})
        result.append((bool(enabled[0]), values[0], bool(enabled[1]), values[1]))
    return result


@_undoable
def set_limit(owner, kind, axis_index, use_min, minimum, use_max, maximum):
    channel = LIMIT_CHANNELS[kind]
    axis = "XYZ"[axis_index]
    cmds.transformLimits(owner, **{channel + axis: (minimum, maximum),
                                   "enable" + channel.capitalize() + axis: (use_min, use_max)})


def has_limits(owner, kind):
    return any(use_min or use_max for use_min, _, use_max, _ in limits(owner, kind))


@_undoable
def clear_limits(owner, kind):
    for index in range(3):
        _, minimum, _, maximum = limits(owner, kind)[index]
        set_limit(owner, kind, index, False, minimum, False, maximum)


@_undoable
def enable_limits(owner, kind):
    """Blender adds a limit with every axis off; Maya's panel shows it once any axis is on, so start with X."""
    _, minimum, _, maximum = limits(owner, kind)[0]
    set_limit(owner, kind, 0, True, minimum, True, maximum)


# --- inverse kinematics ---

def ik_handle(owner):
    for handle in cmds.ls(type="ikHandle", long=True) or []:
        if cmds.attributeQuery(IK_OWNER_ATTRIBUTE, node=handle, exists=True):
            source = cmds.listConnections(handle + "." + IK_OWNER_ATTRIBUTE, source=True, destination=False) or []
            if source and cmds.ls(source[0], long=True) == cmds.ls(owner, long=True):
                return handle
    return None


@_undoable
def add_ik(owner, target=None, pole=None, chain_count=2):
    """IK from the owner up chain_count joints (Blender's Chain Length), solved toward the target."""
    if controls.is_control(owner):
        return control_ik.add(owner, target, pole, chain_count)
    start = owner
    for _ in range(max(chain_count, 1) - 1):
        parent = cmds.listRelatives(start, parent=True, fullPath=True, type="joint")
        if not parent:
            break
        start = parent[0]
    handle = cmds.ikHandle(startJoint=start, endEffector=owner, solver="ikRPsolver",
                           name=owner.rsplit("|", 1)[-1] + "_ik")[0]
    handle = cmds.ls(handle, long=True)[0]
    cmds.addAttr(handle, longName=IK_OWNER_ATTRIBUTE, attributeType="message")
    cmds.connectAttr(owner + ".message", handle + "." + IK_OWNER_ATTRIBUTE)
    cmds.addAttr(handle, longName="mblChainCount", attributeType="long")
    cmds.setAttr(handle + ".mblChainCount", chain_count)
    if target:
        cmds.pointConstraint(target, handle, maintainOffset=False)
    if pole:
        cmds.poleVectorConstraint(pole, handle)
    return handle


def ik_settings(owner):
    handle = ik_handle(owner)
    if handle is None:
        return None
    point = cmds.listRelatives(handle, type="pointConstraint", fullPath=True) or []
    pole = cmds.listRelatives(handle, type="poleVectorConstraint", fullPath=True) or []
    target = cmds.pointConstraint(point[0], query=True, targetList=True)[0] if point else None
    pole_target = cmds.poleVectorConstraint(pole[0], query=True, targetList=True)[0] if pole else None
    return {"handle": handle, "target": target, "pole": pole_target,
            "chain_count": cmds.getAttr(handle + ".mblChainCount")}


@_undoable
def remove_ik(owner):
    handle = ik_handle(owner)
    if handle and control_ik.is_control_ik(handle):
        control_ik.remove(handle)
    elif handle:
        cmds.delete(handle)


@_undoable
def set_ik(owner, target=None, pole=None, chain_count=None):
    """Rebuild the IK with new settings, keeping the ones not given."""
    current = ik_settings(owner) or {"target": None, "pole": None, "chain_count": 2}
    remove_ik(owner)
    return add_ik(owner,
                  target if target is not None else current["target"],
                  pole if pole is not None else current["pole"],
                  chain_count if chain_count is not None else current["chain_count"])
