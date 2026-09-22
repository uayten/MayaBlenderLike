"""Blender-style viewport navigation and numpad views.

Maya's camera tools only react to Alt + mouse button. This filter takes the
middle mouse button over viewports and drives the panel's camera directly with
Maya's camera commands:

    middle          -> orbit  (tumble)
    Shift + middle  -> pan    (track)
    Ctrl + middle   -> dolly

Numpad keys over a viewport work like Blender's:

    1 / 3 / 7         -> front / right / top, orthographic
    Ctrl + 1 / 3 / 7  -> back / left / bottom, orthographic
    5                 -> toggle orthographic / perspective
    . (numpad or row) -> frame selected

Maya's hotkeys can't tell the numpad from the number row, so the numpad is
handled here and the number row keeps its Maya hotkeys.

Alt + middle is left untouched, so Maya's own gestures keep working.
Mouse wheel zoom is Maya's own and also unchanged.
"""
import math

from maya import cmds, mel

try:
    from PySide6 import QtCore, QtWidgets
except ImportError:  # Maya 2024 and older ship PySide2
    from PySide2 import QtCore, QtWidgets

from . import config

Qt = QtCore.Qt

ORBIT, PAN, DOLLY = "orbit", "pan", "dolly"


def _key_value(key):
    # PySide6 may hand keys over as enums or as plain ints.
    return getattr(key, "value", key)


KEY_1, KEY_3, KEY_5, KEY_7 = (_key_value(k) for k in (Qt.Key_1, Qt.Key_3, Qt.Key_5, Qt.Key_7))
KEY_PERIOD = _key_value(Qt.Key_Period)

# With Num Lock off the numpad sends navigation keys instead of digits.
NUMLOCK_OFF_KEYS = {
    _key_value(Qt.Key_End): KEY_1,
    _key_value(Qt.Key_PageDown): KEY_3,
    _key_value(Qt.Key_Clear): KEY_5,
    _key_value(Qt.Key_Home): KEY_7,
    _key_value(Qt.Key_Delete): KEY_PERIOD,
}

# World rotation (degrees) that points the camera, which looks down its local -Z, at each view.
# Blender's front (-Y) arrives in Maya as +Z through the FBX axis conversion, so Blender front = Maya front.
VIEW_ROTATIONS = {
    (KEY_1, False): (0, 0, 0),     # front: from +Z
    (KEY_1, True): (0, 180, 0),    # back: from -Z
    (KEY_3, False): (0, 90, 0),    # right: from +X
    (KEY_3, True): (0, -90, 0),    # left: from -X
    (KEY_7, False): (-90, 0, 0),   # top: from +Y
    (KEY_7, True): (90, 0, 0),     # bottom: from -Y
}

TEXT_INPUT_WIDGETS = (QtWidgets.QLineEdit, QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit, QtWidgets.QAbstractSpinBox)

_filter = None

# Cameras that a numpad view switched to orthographic; orbiting returns them to perspective (Blender's Auto Perspective).
_auto_orthographic = set()


class BlenderNavigationFilter(QtCore.QObject):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mode = None
        self._camera = None
        self._viewport_width = 1
        self._viewport_height = 1
        self._last_pos = None

    def eventFilter(self, obj, event):
        # The same event reaches the viewport's QWindow first and its QWidget second;
        # consuming it at the first stop keeps Maya from also seeing it.
        event_type = event.type()

        if event_type in (QtCore.QEvent.ShortcutOverride, QtCore.QEvent.KeyPress, QtCore.QEvent.KeyRelease):
            if config.ENABLE_NUMPAD_VIEWS:
                return self._handle_numpad(event, event_type)
            return False

        if event_type == QtCore.QEvent.MouseButtonPress:
            if event.button() != Qt.MiddleButton or self._mode is not None:
                return False
            modifiers = event.modifiers()
            if modifiers & Qt.AltModifier:
                return False
            panel = _viewport_panel(obj)
            if panel is None:
                return False
            camera = _panel_camera(panel)
            if camera is None:
                return False
            if modifiers & Qt.ShiftModifier:
                self._mode = PAN
            elif modifiers & Qt.ControlModifier:
                self._mode = DOLLY
            else:
                self._mode = ORBIT
            self._camera = camera
            self._viewport_width = max(obj.width(), 1)
            self._viewport_height = max(obj.height(), 1)
            self._last_pos = _global_pos(event)
            return True

        if self._mode is None:
            return False

        if event_type == QtCore.QEvent.MouseMove:
            pos = _global_pos(event)
            dx = pos.x() - self._last_pos.x()
            dy = pos.y() - self._last_pos.y()
            self._last_pos = pos
            if dx or dy:
                _without_undo(lambda: self._move_camera(dx, dy))
            return True

        if event_type == QtCore.QEvent.MouseButtonRelease and event.button() == Qt.MiddleButton:
            self._mode = None
            self._camera = None
            return True

        return False

    def _handle_numpad(self, event, event_type):
        key = _key_value(event.key())
        if event.modifiers() & Qt.KeypadModifier:
            key = NUMLOCK_OFF_KEYS.get(key, key)
            if key not in (KEY_1, KEY_3, KEY_5, KEY_7, KEY_PERIOD):
                return False
        elif key != KEY_PERIOD:
            # The number row keeps its Maya hotkeys; only "." is shared with the numpad.
            return False
        panel = _numpad_panel()
        camera = _panel_camera(panel) if panel else None
        if camera is None:
            return False

        if event_type == QtCore.QEvent.ShortcutOverride:
            # Claim the key so no Maya hotkey fires for it.
            event.accept()
            return True
        if event_type == QtCore.QEvent.KeyPress and not event.isAutoRepeat():
            opposite = bool(event.modifiers() & Qt.ControlModifier)
            if key == KEY_PERIOD:
                _without_undo(lambda: frame_selected(panel))
            elif key == KEY_5:
                _without_undo(lambda: toggle_orthographic(camera))
            else:
                _without_undo(lambda: set_view(camera, VIEW_ROTATIONS[(key, opposite)]))
        return True

    def _move_camera(self, dx, dy):
        camera = self._camera
        orthographic = cmds.getAttr(camera + ".orthographic")

        if self._mode == ORBIT:
            if orthographic and camera in _auto_orthographic and config.NUMPAD_AUTO_PERSPECTIVE:
                set_orthographic(camera, False)
                orthographic = False
            speed = config.NAVIGATION_ORBIT_DEGREES_PER_PIXEL
            # Without pivotPoint, tumble orbits the camera's tumblePivot (the world origin), not the view center.
            cmds.tumble(camera, azimuthAngle=-dx * speed, elevationAngle=dy * speed, pivotPoint=_pivot(camera))

        elif self._mode == PAN:
            if orthographic:
                units = cmds.getAttr(camera + ".orthographicWidth") / self._viewport_width
            else:
                units = _visible_height(camera) / self._viewport_height
            _track(camera, dx * units, dy * units)

        elif self._mode == DOLLY:
            steps = -dy if config.NAVIGATION_INVERT_DOLLY else dy
            factor = math.exp(steps * config.NAVIGATION_DOLLY_SPEED)
            if orthographic:
                width = cmds.getAttr(camera + ".orthographicWidth")
                cmds.setAttr(camera + ".orthographicWidth", width * factor)
            else:
                # dolly moves the camera but leaves centerOfInterest behind; keep the pivot in place.
                coi = cmds.getAttr(camera + ".centerOfInterest")
                new_coi = max(coi * factor, 0.01)
                cmds.dolly(camera, distance=new_coi - coi)
                cmds.setAttr(camera + ".centerOfInterest", new_coi)


def set_view(camera, rotation):
    """Aim the camera along an axis, orbiting around its current pivot, like Blender's numpad views."""
    transform = _transform(camera)
    pivot = _pivot(camera)
    coi = cmds.getAttr(camera + ".centerOfInterest")
    cmds.xform(transform, worldSpace=True, rotation=rotation)
    forward = _forward(transform)
    cmds.xform(transform, worldSpace=True, translation=[pivot[i] - forward[i] * coi for i in range(3)])
    if config.NUMPAD_AUTO_PERSPECTIVE and not cmds.getAttr(camera + ".orthographic"):
        set_orthographic(camera, True)
        _auto_orthographic.add(camera)


def frame_selected(panel):
    """Frame the selection in the given viewport, the same way Maya's F does."""
    cmds.setFocus(panel)
    mel.eval("fitPanel -selectedNoChildren")


def toggle_orthographic(camera):
    set_orthographic(camera, not cmds.getAttr(camera + ".orthographic"))
    _auto_orthographic.discard(camera)


def set_orthographic(camera, orthographic):
    """Switch projection keeping the same framing at the pivot distance."""
    if bool(cmds.getAttr(camera + ".orthographic")) == orthographic:
        return
    half_fov_tan = math.tan(math.radians(cmds.camera(camera, query=True, horizontalFieldOfView=True)) / 2.0)
    if orthographic:
        coi = cmds.getAttr(camera + ".centerOfInterest")
        cmds.setAttr(camera + ".orthographicWidth", 2.0 * coi * half_fov_tan)
        cmds.setAttr(camera + ".orthographic", True)
    else:
        # Back to perspective: place the camera at the distance that shows the same width.
        transform = _transform(camera)
        pivot = _pivot(camera)
        coi = max(cmds.getAttr(camera + ".orthographicWidth") / (2.0 * half_fov_tan), 0.01)
        forward = _forward(transform)
        cmds.setAttr(camera + ".orthographic", False)
        cmds.setAttr(camera + ".centerOfInterest", coi)
        cmds.xform(transform, worldSpace=True, translation=[pivot[i] - forward[i] * coi for i in range(3)])


def _track(camera, left, up):
    # track only takes positive lengths, one flag per direction.
    if left > 0:
        cmds.track(camera, left=left)
    elif left < 0:
        cmds.track(camera, right=-left)
    if up > 0:
        cmds.track(camera, up=up)
    elif up < 0:
        cmds.track(camera, down=-up)


def _visible_height(camera):
    """World-space height a perspective viewport shows at the camera's pivot distance."""
    coi = cmds.getAttr(camera + ".centerOfInterest")
    fov = math.radians(cmds.camera(camera, query=True, verticalFieldOfView=True))
    return 2.0 * coi * math.tan(fov / 2.0)


def _transform(camera):
    return cmds.listRelatives(camera, parent=True, fullPath=True)[0]


def _forward(transform):
    """Unit vector the camera looks along (its local -Z) in world space."""
    matrix = cmds.xform(transform, query=True, worldSpace=True, matrix=True)
    z_axis = matrix[8:11]
    length = math.sqrt(sum(v * v for v in z_axis)) or 1.0
    return [-v / length for v in z_axis]


def _pivot(camera):
    """Point the camera orbits around: centerOfInterest units in front of it."""
    transform = _transform(camera)
    position = cmds.xform(transform, query=True, worldSpace=True, translation=True)
    forward = _forward(transform)
    coi = cmds.getAttr(camera + ".centerOfInterest")
    return [position[i] + forward[i] * coi for i in range(3)]


def _without_undo(action):
    # Camera moves must not flood the undo queue.
    cmds.undoInfo(stateWithoutFlush=False)
    try:
        action()
    finally:
        cmds.undoInfo(stateWithoutFlush=True)


def _global_pos(event):
    if hasattr(event, "globalPosition"):  # Qt 6
        return event.globalPosition()
    return event.globalPos()


def _viewport_panel(obj):
    """Model panel (3D viewport) that contains the widget or window, or None."""
    panels = set(cmds.getPanel(type="modelPanel") or [])
    node = obj
    while node is not None:
        name = node.objectName()
        # Viewport QWindows are named after their panel plus a "Window" suffix.
        if name.endswith("Window"):
            name = name[:-len("Window")]
        if name in panels:
            return name
        node = node.parent()
    return None


def _numpad_panel():
    """Viewport under the mouse (or with focus), unless the user is typing in a field."""
    if isinstance(QtWidgets.QApplication.focusWidget(), TEXT_INPUT_WIDGETS):
        return None
    for panel in (cmds.getPanel(underPointer=True), cmds.getPanel(withFocus=True)):
        if panel and cmds.getPanel(typeOf=panel) == "modelPanel":
            return panel
    return None


def _panel_camera(panel):
    camera = cmds.modelPanel(panel, query=True, camera=True)
    if not camera:
        return None
    if cmds.nodeType(camera) != "camera":
        shapes = cmds.listRelatives(camera, shapes=True, type="camera", fullPath=True) or []
        if not shapes:
            return None
        camera = shapes[0]
    return camera


def install():
    global _filter
    if _filter is not None:
        return
    app = QtWidgets.QApplication.instance()
    _filter = BlenderNavigationFilter(app)
    app.installEventFilter(_filter)


def uninstall():
    global _filter
    if _filter is None:
        return
    QtWidgets.QApplication.instance().removeEventFilter(_filter)
    _filter = None
