"""Blender-style modal transforms.

G / R / S over a viewport start moving, rotating or scaling the selection with the mouse:

    X / Y / Z        constrain to a global axis; press again for local, again to clear
    digits . - Bksp  type an exact value (cm, degrees or factor)
    G / R / S        switch to another transform, keeping the selection
    click / Enter    confirm (one undo step)
    right / Esc      cancel

E on selected joints extrudes a child joint and starts moving it, like extruding a bone.
Works on objects, joints and mesh components.
"""
import math

from maya import cmds
import maya.api.OpenMaya as om
import maya.api.OpenMayaUI as omui

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from shiboken6 import wrapInstance
except ImportError:  # Maya 2024 and older ship PySide2
    from PySide2 import QtCore, QtGui, QtWidgets
    from shiboken2 import wrapInstance

Qt = QtCore.Qt

TRANSLATE, ROTATE, SCALE = "translate", "rotate", "scale"
MODE_KEYS = {Qt.Key_G: TRANSLATE, Qt.Key_R: ROTATE, Qt.Key_S: SCALE}
AXIS_KEYS = {Qt.Key_X: 0, Qt.Key_Y: 1, Qt.Key_Z: 2}
WORLD_AXES = (om.MVector(1, 0, 0), om.MVector(0, 1, 0), om.MVector(0, 0, 1))
TYPED_CHARACTERS = "0123456789.-"
MIN_SCALE = 1e-4


def _key(value):
    return getattr(value, "value", value)


MODE_KEYS = {_key(k): v for k, v in MODE_KEYS.items()}
AXIS_KEYS = {_key(k): v for k, v in AXIS_KEYS.items()}


class ModalTransform(object):
    """One interactive transform. Feed it Qt events with handle() until finished is True."""

    def __init__(self, mode, panel):
        self.finished = False
        self.panel = panel
        self.view = omui.M3dView.getM3dViewFromModelPanel(panel)
        self.targets, self.components = _selection_targets()
        if not self.targets:
            self.finished = True
            return
        self.pivot = _pivot(self.targets, self.components)
        self.view_forward = _camera_forward(self.view)
        self.axis = None           # 0, 1, 2 or None
        self.local = False
        self.typed = ""
        self.applied = None        # value currently applied to the scene, reverted on cancel or change
        cmds.undoInfo(stateWithoutFlush=False)
        self._start(mode)

    # --- event handling ---

    def handle(self, event):
        """Process one event. Returns True, since every input belongs to the modal while it runs."""
        try:
            self._handle(event)
        except Exception:
            self._finish(confirm=False)
            raise
        return True

    def _handle(self, event):
        event_type = event.type()
        if event_type == QtCore.QEvent.ShortcutOverride:
            event.accept()
        elif event_type == QtCore.QEvent.KeyPress:
            self._key_press(event)
        elif event_type == QtCore.QEvent.MouseMove:
            if not self.typed:
                self._update()
        elif event_type == QtCore.QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                self._finish(confirm=True)
            elif event.button() == Qt.RightButton:
                self._finish(confirm=False)

    def _key_press(self, event):
        key = _key(event.key())
        text = event.text()
        if key in (_key(Qt.Key_Return), _key(Qt.Key_Enter)):
            self._finish(confirm=True)
        elif key == _key(Qt.Key_Escape):
            self._finish(confirm=False)
        elif key in AXIS_KEYS:
            self._cycle_axis(AXIS_KEYS[key])
        elif key in MODE_KEYS and MODE_KEYS[key] != self.mode:
            self._revert()
            self._start(MODE_KEYS[key])
        elif key == _key(Qt.Key_Backspace):
            self.typed = self.typed[:-1]
            self._update()
        elif text and text in TYPED_CHARACTERS:
            self.typed += text
            self._update()

    def _cycle_axis(self, axis):
        # Blender: first press global axis, second press local axis, third press free.
        if self.axis != axis:
            self.axis, self.local = axis, False
        elif not self.local:
            self.local = True
        else:
            self.axis, self.local = None, False
        self._revert()
        self._update()

    # --- transform ---

    def _start(self, mode):
        self.mode = mode
        self.typed = ""
        self.start_mouse = self._mouse()
        self.pivot_screen = self._to_screen(self.pivot)
        self.last_angle = self._screen_angle(self.start_mouse)
        self.turned = 0.0
        self.start_ray = self._plane_point(self.start_mouse)
        self._update()

    def _update(self):
        value = self._typed_value() if self.typed else self._mouse_value()
        self._revert()
        self._apply(value)
        self.applied = value
        cmds.headsUpMessage(self._status(value), time=60.0)

    def _mouse_value(self):
        mouse = self._mouse()
        if self.mode == TRANSLATE:
            delta = self._plane_point(mouse) - self.start_ray
            axis = self._axis_vector()
            if axis is not None:
                delta = axis * (delta * axis)
            return delta
        if self.mode == ROTATE:
            angle = self._screen_angle(mouse)
            step = angle - self.last_angle
            step = (step + 180.0) % 360.0 - 180.0   # unwrap across the +-180 seam
            self.turned += step
            self.last_angle = angle
            return self.turned
        start = _distance(self.start_mouse, self.pivot_screen) or 1.0
        return max(_distance(mouse, self.pivot_screen) / start, MIN_SCALE)

    def _typed_value(self):
        try:
            number = float(self.typed)
        except ValueError:
            number = 0.0 if self.mode != SCALE else 1.0
        if self.mode == TRANSLATE:
            axis = self._axis_vector() or WORLD_AXES[0]
            return axis * number
        if self.mode == SCALE and abs(number) < MIN_SCALE:
            number = MIN_SCALE
        return number

    def _apply(self, value, invert=False):
        targets = self.targets
        if self.mode == TRANSLATE:
            vector = -value if invert else value
            _safely(cmds.move, vector.x, vector.y, vector.z, targets, relative=True, worldSpace=True)
        elif self.mode == ROTATE:
            angle = -value if invert else value
            rotation = om.MQuaternion(math.radians(angle), self._rotation_axis()).asEulerRotation()
            _safely(cmds.rotate, math.degrees(rotation.x), math.degrees(rotation.y), math.degrees(rotation.z),
                    targets, relative=True, worldSpace=True, pivot=list(self.pivot)[:3])
        else:
            factor = 1.0 / value if invert else value
            scale = [factor] * 3
            if self.axis is not None:
                scale = [1.0, 1.0, 1.0]
                scale[self.axis] = factor
            _safely(cmds.scale, scale[0], scale[1], scale[2], targets, relative=True, pivot=list(self.pivot)[:3])

    def _revert(self):
        if self.applied is not None:
            self._apply(self.applied, invert=True)
            self.applied = None

    def _finish(self, confirm):
        if self.finished:
            return
        self.finished = True
        value = self.applied
        self._revert()
        cmds.undoInfo(stateWithoutFlush=True)
        cmds.headsUpMessage("", time=0.01)
        if confirm and value is not None:
            # Replay the final value with undo on, so the whole drag is one undo step.
            cmds.undoInfo(openChunk=True, chunkName="modal_" + self.mode)
            try:
                self._apply(value)
            finally:
                cmds.undoInfo(closeChunk=True)

    # --- geometry helpers ---

    def _axis_vector(self):
        if self.axis is None:
            return None
        if not self.local:
            return WORLD_AXES[self.axis]
        matrix = om.MMatrix(cmds.xform(_owner(self.targets[-1]), query=True, worldSpace=True, matrix=True))
        row = om.MVector(matrix.getElement(self.axis, 0), matrix.getElement(self.axis, 1), matrix.getElement(self.axis, 2))
        return row.normal()

    def _rotation_axis(self):
        # Free rotation turns around the view axis; the sign keeps screen and object turning the same way.
        toward_viewer = -self.view_forward
        axis = self._axis_vector()
        if axis is None:
            return toward_viewer
        return axis if axis * toward_viewer >= 0 else -axis

    def _mouse(self):
        """Cursor in M3dView port coordinates (pixels, origin bottom-left)."""
        widget = wrapInstance(int(self.view.widget()), QtWidgets.QWidget)
        local = widget.mapFromGlobal(QtGui.QCursor.pos())
        ratio = self.view.portWidth() / float(max(widget.width(), 1))
        return (local.x() * ratio, self.view.portHeight() - local.y() * ratio)

    def _to_screen(self, point):
        result = self.view.worldToView(om.MPoint(point))
        return (result[0], result[1])

    def _screen_angle(self, mouse):
        return math.degrees(math.atan2(mouse[1] - self.pivot_screen[1], mouse[0] - self.pivot_screen[0]))

    def _plane_point(self, mouse):
        """Where the mouse ray hits the plane through the pivot facing the camera."""
        near, direction = _view_ray(self.view, mouse)
        normal = self.view_forward
        denominator = direction * normal
        if abs(denominator) < 1e-9:
            return om.MVector(self.pivot)
        t = (om.MVector(self.pivot) - om.MVector(near)) * normal / denominator
        return om.MVector(near) + direction * t

    def _status(self, value):
        axis = ""
        if self.axis is not None:
            axis = " along {} {}".format("local" if self.local else "global", "XYZ"[self.axis])
        typed = " [{}]".format(self.typed) if self.typed else ""
        if self.mode == TRANSLATE:
            text = "Move: D {:.3f} {:.3f} {:.3f} cm".format(value.x, value.y, value.z)
        elif self.mode == ROTATE:
            text = "Rotate: {:.2f} deg".format(value)
        else:
            text = "Scale: {:.4f}".format(value)
        return text + axis + typed + "    (click/Enter confirm, right/Esc cancel, X Y Z axis)"


def _view_ray(view, mouse):
    result = view.viewToWorld(int(mouse[0]), int(mouse[1]))
    near, second = result[0], result[1]
    if isinstance(second, om.MVector):
        return near, second.normal()
    return near, (om.MVector(second) - om.MVector(near)).normal()


def _camera_forward(view):
    camera = om.MFnCamera(view.getCamera())
    return om.MVector(camera.viewDirection(om.MSpace.kWorld)).normal()


def _selection_targets():
    """(targets, components?) — components when any are selected, otherwise transforms without selected ancestors."""
    selection = cmds.ls(selection=True, long=True) or []
    components = [s for s in selection if "." in s]
    if components:
        return components, True
    nodes = cmds.ls(selection=True, transforms=True, long=True) or []
    chosen = set(nodes)
    # Blender moves a child whose parent is also selected only once; Maya would move it twice.
    top = [n for n in nodes if not any(n.startswith(other + "|") for other in chosen if other != n)]
    return top, False


def _pivot(targets, components):
    if not targets:
        return om.MPoint()
    if components:
        vertices = cmds.polyListComponentConversion(targets, toVertex=True) or []
        positions = cmds.xform(vertices, query=True, worldSpace=True, translation=True) if vertices else []
        if positions:
            count = len(positions) // 3
            return om.MPoint(sum(positions[0::3]) / count, sum(positions[1::3]) / count, sum(positions[2::3]) / count)
        box = cmds.exactWorldBoundingBox(targets)
        return om.MPoint((box[0] + box[3]) / 2, (box[1] + box[4]) / 2, (box[2] + box[5]) / 2)
    points = [cmds.xform(n, query=True, worldSpace=True, rotatePivot=True) for n in targets]
    count = float(len(points))
    return om.MPoint(sum(p[0] for p in points) / count, sum(p[1] for p in points) / count, sum(p[2] for p in points) / count)


def _owner(target):
    """Transform that owns an object or component name."""
    node = target.split(".")[0]
    if cmds.objectType(node, isAType="shape"):
        node = cmds.listRelatives(node, parent=True, fullPath=True)[0]
    return node


def _distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _safely(command, *args, **kwargs):
    # Locked or driven channels make Maya raise; the rest of the selection should still move.
    try:
        command(*args, **kwargs)
    except RuntimeError as error:
        cmds.warning("MayaBlenderLike: {}".format(str(error).strip()))


def extrude_joints():
    """Blender's E on bones: add a child joint at each selected joint and select the new ones."""
    joints = cmds.ls(selection=True, type="joint", long=True) or []
    created = []
    for joint in joints:
        position = cmds.xform(joint, query=True, worldSpace=True, translation=True)
        cmds.select(joint, replace=True)
        created.append(cmds.joint(position=position))
    if created:
        cmds.select(created, replace=True)
    return created
