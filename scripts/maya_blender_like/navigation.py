"""Blender-style viewport navigation.

Maya's camera tools only react to Alt + mouse button. This filter watches the
middle mouse button over viewports and forwards it to Maya as the matching
Alt gesture:

    middle          -> Alt + left    (orbit)
    Shift + middle  -> Alt + middle  (pan)
    Ctrl + middle   -> Alt + right   (dolly)

Alt + middle is left untouched, so Maya's own gestures keep working.
"""
from maya import cmds

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:  # Maya 2024 and older ship PySide2
    from PySide2 import QtCore, QtGui, QtWidgets

Qt = QtCore.Qt

_filter = None


class BlenderNavigationFilter(QtCore.QObject):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._target_button = None  # Maya button being emulated during a drag
        self._forwarding = False

    def eventFilter(self, obj, event):
        if self._forwarding:
            return False

        event_type = event.type()

        if event_type == QtCore.QEvent.MouseButtonPress:
            if event.button() != Qt.MiddleButton or not _is_viewport(obj):
                return False
            modifiers = event.modifiers()
            if modifiers & Qt.AltModifier:
                return False
            if modifiers & Qt.ShiftModifier:
                self._target_button = Qt.MiddleButton
            elif modifiers & Qt.ControlModifier:
                self._target_button = Qt.RightButton
            else:
                self._target_button = Qt.LeftButton
            self._forward(obj, event, event_type, self._target_button, self._target_button)
            return True

        if self._target_button is None:
            return False

        if event_type == QtCore.QEvent.MouseMove:
            self._forward(obj, event, event_type, Qt.NoButton, self._target_button)
            return True

        if event_type == QtCore.QEvent.MouseButtonRelease and event.button() == Qt.MiddleButton:
            button = self._target_button
            self._target_button = None
            self._forward(obj, event, event_type, button, Qt.NoButton)
            return True

        return False

    def _forward(self, obj, event, event_type, button, buttons):
        if hasattr(event, "position"):  # Qt 6
            local_pos, global_pos = event.position(), event.globalPosition()
        else:  # Qt 5
            local_pos, global_pos = event.localPos(), event.screenPos()
        emulated = QtGui.QMouseEvent(event_type, local_pos, global_pos, button, buttons, Qt.AltModifier)
        self._forwarding = True
        try:
            QtWidgets.QApplication.sendEvent(obj, emulated)
        finally:
            self._forwarding = False


def _is_viewport(obj):
    """True if the widget sits inside a model panel (a 3D viewport)."""
    panels = set(cmds.getPanel(type="modelPanel") or [])
    widget = obj
    while widget is not None:
        if widget.objectName() in panels:
            return True
        widget = widget.parent()
    return False


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
