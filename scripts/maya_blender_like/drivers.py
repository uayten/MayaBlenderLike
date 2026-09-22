"""Find the controls that drive a node through constraints.

In a Maya rig a joint usually follows a control through a constraint, so its translate and
rotate are outputs that can't be set. Blender-style actions on such a joint (G/R/S, Alt+G/R/S)
are sent to the controls that drive it instead, which is what moves the bone.
"""
from maya import cmds

CONSTRAINT_QUERIES = {
    "parentConstraint": cmds.parentConstraint,
    "pointConstraint": cmds.pointConstraint,
    "orientConstraint": cmds.orientConstraint,
    "scaleConstraint": cmds.scaleConstraint,
    "aimConstraint": cmds.aimConstraint,
}
STACK_ROOT = "MBL_constraintStacks"


def controls(node):
    """Transforms driving the node's translate / rotate / scale through constraints.

    Targets inside a constraint stack (MBL_constraintStacks) are plumbing, not controls, and are skipped.
    """
    found = []
    for channel in ("translate", "rotate", "scale"):
        for axis in "XYZ":
            plug = "{}.{}{}".format(node, channel, axis)
            for source in cmds.listConnections(plug, source=True, destination=False, skipConversionNodes=True) or []:
                query = CONSTRAINT_QUERIES.get(cmds.nodeType(source))
                if query is None:
                    continue
                for target in cmds.ls(query(source, query=True, targetList=True) or [], long=True):
                    if not target.startswith("|" + STACK_ROOT) and target not in found:
                        found.append(target)
    return found


def redirect(nodes):
    """Replace constrained nodes by their controls. Returns (nodes, note for the viewport or None)."""
    result, notes = [], []
    for node in nodes:
        drivers = controls(node)
        if drivers:
            notes.append("{} follows {}".format(_short(node), ", ".join(_short(d) for d in drivers)))
            result.extend(d for d in drivers if d not in result)
        elif node not in result:
            result.append(node)
    return result, ("; ".join(notes) + ": acting on the control" if notes else None)


def _short(node):
    return node.rsplit("|", 1)[-1]
