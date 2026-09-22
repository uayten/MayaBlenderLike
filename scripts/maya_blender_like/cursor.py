"""Blender's 3D cursor for Maya: a point new objects are added at, and snapping to and from it.

- Shift + right click in a viewport places it on the mesh surface under the mouse, or at its
  current depth when there is no surface there.
- Shift+S opens Blender's Snap menu: selection to cursor / active / grid, cursor to selected /
  active / world origin / grid.
- Shift+A adds new objects at the cursor.

The cursor's position is saved in the scene (fileInfo mblCursor3D). The marker drawn for it is
not: it is left out of saved files (doNotWrite), hidden from the Outliner and can't be clicked.
"""
import math

from maya import cmds
import maya.api.OpenMaya as om

from . import config

NODE = "MBL_cursor3D"
FILE_INFO = "mblCursor3D"
SIZE_CM = 5.0
RING_RGB = (1.0, 0.15, 0.15)
CROSS_RGB = (1.0, 1.0, 1.0)


# --- position ---

def position():
    stored = cmds.fileInfo(FILE_INFO, query=True)
    if stored:
        try:
            return tuple(float(v) for v in stored[0].split())
        except ValueError:
            pass
    return (0.0, 0.0, 0.0)


def set_position(point):
    """Move the cursor. Like Blender, moving the cursor is not an undo step."""
    point = tuple(float(v) for v in point)[:3]
    cmds.undoInfo(stateWithoutFlush=False)
    try:
        cmds.fileInfo(FILE_INFO, "{:.6f} {:.6f} {:.6f}".format(*point))
        cmds.xform(_marker(), worldSpace=True, translation=point)
    finally:
        cmds.undoInfo(stateWithoutFlush=True)


def show():
    """Draw the marker where the scene's cursor is (after opening a scene)."""
    set_position(position())


def install():
    for event in ("SceneOpened", "NewSceneOpened"):
        cmds.scriptJob(event=[event, show])
    show()


def _marker():
    if cmds.objExists(NODE):
        return NODE
    # Built through the API: cmds.curve would select each new curve and lose the user's selection.
    marker = cmds.createNode("transform", name=NODE, skipSelect=True)
    ring = [(SIZE_CM * math.cos(a), SIZE_CM * math.sin(a), 0) for a in (2 * math.pi * i / 16 for i in range(17))]
    ticks = ([[(0, SIZE_CM * sign * 0.4, 0), (0, SIZE_CM * sign * 1.6, 0)] for sign in (1, -1)]
             + [[(SIZE_CM * sign * 0.4, 0, 0), (SIZE_CM * sign * 1.6, 0, 0)] for sign in (1, -1)])
    parent = _mobject(marker)
    om.MFnDependencyNode(parent).setDoNotWrite(True)
    for points, rgb in [(ring, RING_RGB)] + [(t, CROSS_RGB) for t in ticks]:
        shape_object = om.MFnNurbsCurve().create([om.MPoint(p) for p in points], list(range(len(points))), 1,
                                                 om.MFnNurbsCurve.kOpen, False, False, parent)
        om.MFnDependencyNode(shape_object).setDoNotWrite(True)
        shape = om.MFnDagNode(shape_object).fullPathName()
        cmds.setAttr(shape + ".overrideEnabled", True)
        cmds.setAttr(shape + ".overrideDisplayType", 2)   # reference: drawn, never clicked
        cmds.setAttr(shape + ".overrideRGBColors", True)
        cmds.setAttr(shape + ".overrideColorRGB", *rgb)
        cmds.setAttr(shape + ".alwaysDrawOnTop", True)
    cmds.setAttr(marker + ".hiddenInOutliner", True)
    return marker


# --- snapping (Shift+S) ---

def snap_menu():
    from . import menus
    menus.popup("Snap", [
        ("Selection to Cursor", lambda: selection_to(position(), keep_offset=False)),
        ("Selection to Cursor (Keep Offset)", lambda: selection_to(position(), keep_offset=True)),
        ("Selection to Active", selection_to_active),
        ("Selection to Grid", selection_to_grid),
        None,
        ("Cursor to Selected", cursor_to_selected),
        ("Cursor to Active", cursor_to_active),
        ("Cursor to World Origin", lambda: set_position((0, 0, 0))),
        ("Cursor to Grid", lambda: set_position(_to_grid(position()))),
    ])


def selection_to(point, keep_offset=False, targets=None):
    """Each selected object's pivot (or each vertex) to the point; keep_offset moves them together."""
    from . import modal
    targets, components = (targets, False) if targets is not None else modal._selection_targets()
    if not targets:
        return
    point = om.MVector(point)
    if keep_offset:
        _move_by(targets, components, point - om.MVector(modal._pivot(targets, components)))
    elif components:
        vertices = cmds.ls(cmds.polyListComponentConversion(targets, toVertex=True) or targets, flatten=True)
        for vertex in vertices:
            cmds.xform(vertex, worldSpace=True, translation=list(point))
    else:
        for target in targets:
            _move_by([target], False, point - _pivot_of(target))


def selection_to_active():
    selection = cmds.ls(selection=True, transforms=True, long=True) or []
    if len(selection) < 2:
        cmds.warning("Selection to Active: select the objects, then the active one last.")
        return
    selection_to(_pivot_of(selection[-1]), targets=selection[:-1])


def selection_to_grid():
    from . import modal
    targets, components = modal._selection_targets()
    if components:
        vertices = cmds.ls(cmds.polyListComponentConversion(targets, toVertex=True) or targets, flatten=True)
        for vertex in vertices:
            here = cmds.xform(vertex, query=True, worldSpace=True, translation=True)
            cmds.xform(vertex, worldSpace=True, translation=_to_grid(here))
        return
    for target in targets:
        here = _pivot_of(target)
        _move_by([target], False, om.MVector(_to_grid(here)) - here)


def cursor_to_selected():
    from . import modal
    targets, components = modal._selection_targets()
    if targets:
        pivot = modal._pivot(targets, components)
        set_position((pivot.x, pivot.y, pivot.z))


def cursor_to_active():
    selection = cmds.ls(selection=True, long=True) or []
    if selection:
        if "." in selection[-1]:
            from . import modal
            pivot = modal._pivot([selection[-1]], True)
            set_position((pivot.x, pivot.y, pivot.z))
        else:
            set_position(tuple(_pivot_of(selection[-1])))


# --- placing with the mouse (Shift + right click) ---

def place_at_mouse(panel):
    """Put the cursor on the surface under the mouse, or at its current depth facing the view."""
    from . import modal
    import maya.api.OpenMayaUI as omui
    view = omui.M3dView.getM3dViewFromModelPanel(panel)
    source, direction = modal._view_ray(view, modal.view_mouse(view))
    hit = _surface_hit(source, direction)
    if hit is None:
        forward = modal._camera_forward(view)
        depth = (om.MVector(position()) - om.MVector(source)) * forward
        denominator = direction * forward
        hit = om.MVector(source) + direction * (depth / denominator if abs(denominator) > 1e-9 else 0)
    set_position((hit.x, hit.y, hit.z))


def _surface_hit(source, direction):
    """Closest point where the ray meets a visible mesh, or None."""
    nearest, found = None, None
    ray_source, ray_direction = om.MFloatPoint(source.x, source.y, source.z), om.MFloatVector(direction)
    for mesh in cmds.ls(type="mesh", visible=True, noIntermediate=True, long=True) or []:
        path = om.MSelectionList().add(mesh).getDagPath(0)
        result = om.MFnMesh(path).closestIntersection(ray_source, ray_direction, om.MSpace.kWorld, 1e7, False)
        if result and (nearest is None or result[1] < nearest):
            nearest, found = result[1], om.MVector(result[0].x, result[0].y, result[0].z)
    return found


# --- helpers ---

def _move_by(targets, components, delta):
    if delta.length() < 1e-9:
        return
    cmds.move(delta.x, delta.y, delta.z, targets, relative=True, worldSpace=True)


def _pivot_of(node):
    return om.MVector(cmds.xform(node, query=True, worldSpace=True, rotatePivot=True))


def _to_grid(point):
    step = float(config.GRID_SPACING_CM) / max(config.GRID_DIVISIONS, 1)
    return tuple(round(v / step) * step for v in point)


def _mobject(node):
    return om.MSelectionList().add(node).getDependNode(0)
