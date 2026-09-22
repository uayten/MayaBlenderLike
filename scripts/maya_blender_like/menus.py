"""Blender-style popup menus at the mouse cursor: Shift+A (Add), Ctrl+A (Apply), X (Delete)."""
from maya import cmds, mel

try:
    from PySide6 import QtGui, QtWidgets
    from shiboken6 import wrapInstance
except ImportError:  # Maya 2024 and older ship PySide2
    from PySide2 import QtGui, QtWidgets
    from shiboken2 import wrapInstance

import maya.OpenMayaUI as omui

# Blender's default bone is 1 m long; Maya works in centimeters.
BONE_LENGTH_CM = 100.0


def _main_window():
    return wrapInstance(int(omui.MQtUtil.mainWindow()), QtWidgets.QWidget)


def popup(title, entries, undo=True):
    """Show a menu at the cursor. entries: list of (label, callable), (label, [submenu entries]) or None for a separator.

    With undo, each chosen action is one undo step.
    """
    menu = QtWidgets.QMenu(_main_window())
    menu.setTitle(title)
    header = menu.addAction(title)
    header.setEnabled(False)
    menu.addSeparator()
    _fill(menu, entries, undo)
    menu.exec_(QtGui.QCursor.pos())


def _fill(menu, entries, undo=True):
    for entry in entries:
        if entry is None:
            menu.addSeparator()
            continue
        label, target = entry
        if isinstance(target, list):
            _fill(menu.addMenu(label), target, undo)
        else:
            run = _run if undo else (lambda action: action())
            menu.addAction(label).triggered.connect(lambda checked=False, action=target, run=run: run(action))


def _run(action):
    cmds.undoInfo(openChunk=True)
    try:
        action()
    finally:
        cmds.undoInfo(closeChunk=True)


# --- Shift+A: Add ---

def _add(create):
    # New objects must not be parented under the selection (cmds.joint parents to a selected joint).
    cmds.select(clear=True)
    create()


def _add_bone():
    cmds.select(clear=True)
    head = cmds.joint(position=(0, 0, 0))
    cmds.joint(position=(0, BONE_LENGTH_CM, 0))
    cmds.select(head)


def add_menu():
    popup("Add", [
        ("Mesh", [
            ("Plane", lambda: _add(lambda: cmds.polyPlane(width=200, height=200))),
            ("Cube", lambda: _add(lambda: cmds.polyCube(width=200, height=200, depth=200))),
            ("Circle", lambda: _add(lambda: cmds.polyDisc(sides=32, radius=100))),
            ("UV Sphere", lambda: _add(lambda: cmds.polySphere(radius=100))),
            ("Cylinder", lambda: _add(lambda: cmds.polyCylinder(radius=100, height=200))),
            ("Cone", lambda: _add(lambda: cmds.polyCone(radius=100, height=200))),
            ("Torus", lambda: _add(lambda: cmds.polyTorus(radius=100, sectionRadius=25))),
        ]),
        ("Curve", [
            ("Circle", lambda: _add(lambda: cmds.circle(normal=(0, 1, 0), radius=100))),
            ("Square", lambda: _add(lambda: cmds.curve(degree=1, point=[(-100, 0, -100), (100, 0, -100), (100, 0, 100), (-100, 0, 100), (-100, 0, -100)]))),
            ("Draw CV Curve", lambda: mel.eval("CVCurveTool")),
        ]),
        None,
        ("Empty", [
            ("Plain Axes (Locator)", lambda: _add(lambda: cmds.spaceLocator())),
            ("Group (Null)", lambda: _add(lambda: cmds.group(empty=True))),
        ]),
        ("Armature", [
            ("Single Bone", _add_bone),
            ("Joint", lambda: _add(lambda: cmds.joint(position=(0, 0, 0)))),
            ("Joint Tool (click to draw)", lambda: mel.eval("JointTool")),
        ]),
        None,
        ("Camera", lambda: _add(lambda: cmds.camera())),
        ("Light", [
            ("Point", lambda: _add(lambda: cmds.pointLight())),
            ("Sun (Directional)", lambda: _add(lambda: cmds.directionalLight())),
            ("Spot", lambda: _add(lambda: cmds.spotLight())),
            ("Area", lambda: _add(lambda: mel.eval("CreateAreaLight"))),
        ]),
    ])


# --- Ctrl+A: Apply ---

def _freeze(translate=False, rotate=False, scale=False):
    nodes = cmds.ls(selection=True, transforms=True)
    if nodes:
        cmds.makeIdentity(nodes, apply=True, translate=translate, rotate=rotate, scale=scale)


def _pose_as_rest():
    from . import modes
    joints = cmds.ls(selection=True, type="joint", long=True)
    if joints:
        modes.apply_pose_as_rest(joints)


def apply_menu():
    popup("Apply", [
        ("Location", lambda: _freeze(translate=True)),
        ("Rotation", lambda: _freeze(rotate=True)),
        ("Scale", lambda: _freeze(scale=True)),
        ("All Transforms", lambda: _freeze(translate=True, rotate=True, scale=True)),
        ("Rotation & Scale", lambda: _freeze(rotate=True, scale=True)),
        None,
        ("Pose as Rest Pose (joints)", _pose_as_rest),
        None,
        ("Origin to Geometry (Center Pivot)", lambda: mel.eval("CenterPivot")),
        ("Reset Transforms (Maya)", lambda: mel.eval("ResetTransformations")),
        ("Delete History (Maya)", lambda: mel.eval("DeleteHistory")),
    ])


# --- X: Delete ---

def delete_menu():
    if not cmds.ls(selection=True):
        return
    popup("Delete", [
        ("Delete", lambda: cmds.delete()),
    ])
