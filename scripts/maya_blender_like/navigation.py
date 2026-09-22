"""Blender-style viewport navigation.

Maya's camera tools only react to Alt + mouse button. This filter takes the
middle mouse button over viewports and drives the panel's camera directly with
Maya's camera commands:

    middle          -> orbit  (tumble)
    Shift + middle  -> pan    (track)
    Ctrl + middle   -> dolly

Alt + middle is left untouched, so Maya's own gestures keep working.
Mouse wheel zoom is Maya's own and also unchanged.
"""
import math

from maya import cmds

try:
    from PySide6 import QtCore, QtWidgets
except ImportError:  # Maya 2024 and older ship PySide2
    from PySide2 import QtCore, QtWidgets

from . import config

Qt = QtCore.Qt

ORBIT, PAN, DOLLY = "orbit", "pan", "dolly"

_filter = None


class BlenderNavigationFilter(QtCore.QObject):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mode = None
        self._camera = None
        self._viewport_height = 1
        self._last_pos = None

    def eventFilter(self, obj, event):
        # The same mouse event reaches the viewport's QWindow first and its QWidget second;
        # consuming it at the first stop keeps Maya from also seeing it.
        event_type = event.type()

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

    def _move_camera(self, dx, dy):
        camera = self._camera
        orthographic = cmds.getAttr(camera + ".orthographic")

        if self._mode == ORBIT:
            if orthographic:
                return
            speed = config.NAVIGATION_ORBIT_DEGREES_PER_PIXEL
            cmds.tumble(camera, azimuthAngle=-dx * speed, elevationAngle=dy * speed)

        elif self._mode == PAN:
            units = _visible_height(camera, orthographic) / self._viewport_height
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


def _visible_height(camera, orthographic):
    """World-space height the viewport shows at the camera's pivot distance."""
    if orthographic:
        return cmds.getAttr(camera + ".orthographicWidth")
    coi = cmds.getAttr(camera + ".centerOfInterest")
    fov = math.radians(cmds.camera(camera, query=True, verticalFieldOfView=True))
    return 2.0 * coi * math.tan(fov / 2.0)


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


def _panel_camera(panel):
    camera = cmds.modelPanel(panel, query=True, camera=True)
    if not camera:
        return None
    if cmds.nodeType(camera) != "camera":
        shapes = cmds.listRelatives(camera, shapes=True, type="camera") or []
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
