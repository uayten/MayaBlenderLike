"""Constraints panel: Blender's Bone / Object Constraints tab for Maya.

Docked next to the Attribute Editor, it follows the active object (the last one selected),
lists its constraint stack top to bottom as cards, and adds constraints by their Blender names.
Adding with a second object selected uses it as the target, like Blender's
Add Constraint (with Targets). Target fields have a picker: click it, then click the target
in the viewport or Outliner.
"""
from maya import cmds
import maya.OpenMayaUI as omui

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from shiboken6 import wrapInstance
except ImportError:  # Maya 2024 and older ship PySide2
    from PySide2 import QtCore, QtGui, QtWidgets
    from shiboken2 import wrapInstance

from . import controls, custom_shapes, owner_constraints, stack

WORKSPACE_NAME = "MBL_ConstraintsPanel"
AXES = ["X", "Y", "Z", "-X", "-Y", "-Z"]
NOTE = ("Constraints run top to bottom, like Blender's stack. The stack is built from standard Maya "
        "nodes (group MBL_constraintStacks), so anyone can open and animate the rig without this tool. "
        "Game engines never receive constraints of any kind: bake the animation when exporting FBX.")


def show():
    """Open the panel, tabbed next to the Attribute Editor when possible."""
    if cmds.workspaceControl(WORKSPACE_NAME, exists=True):
        cmds.workspaceControl(WORKSPACE_NAME, edit=True, restore=True)
        cmds.workspaceControl(WORKSPACE_NAME, edit=True, visible=True)
        return
    ui_script = "import maya_blender_like.constraints_panel as p; p.build_ui()"
    try:
        cmds.workspaceControl(WORKSPACE_NAME, label="Bone & Constraints", retain=False,
                              tabToControl=("AttributeEditor", -1), uiScript=ui_script)
    except RuntimeError:
        cmds.workspaceControl(WORKSPACE_NAME, label="Bone & Constraints", retain=False,
                              floating=True, uiScript=ui_script)


def build_ui():
    """Called by the workspace control whenever Maya builds it."""
    host = wrapInstance(int(omui.MQtUtil.findControl(WORKSPACE_NAME)), QtWidgets.QWidget)
    host.layout().addWidget(ConstraintsPanel(host))


def add_constraint_menu():
    """Blender's Shift+Ctrl+C: Add Constraint (with Targets) for the active object, at the cursor."""
    owner, target = _active_and_target()
    if owner is None:
        return
    menu = QtWidgets.QMenu()
    _fill_add_menu(menu, lambda kind: _add(owner, kind, target))
    menu.exec_(QtGui.QCursor.pos())


def _active_and_target():
    selection = cmds.ls(selection=True, transforms=True, long=True) or []
    if not selection:
        return None, None
    owner = selection[-1]  # Blender's active object is the last one selected
    others = [s for s in selection if s != owner]
    return owner, (others[0] if others else None)


def _fill_add_menu(menu, callback):
    for group, kinds in stack.MENU:
        submenu = menu.addMenu(group)
        for kind in kinds:
            submenu.addAction(stack.LABELS[kind]).triggered.connect(lambda checked=False, k=kind: callback(k))


def _add(owner, kind, target):
    _guarded(lambda: _add_unguarded(owner, kind, target))


def _add_unguarded(owner, kind, target):
    if kind in owner_constraints.LIMIT_CHANNELS and owner_constraints.has_limits(owner, kind):
        stack.add(owner, kind)  # the owner's channels hold one limit per kind: a second one goes in the stack
    elif kind in owner_constraints.LIMIT_CHANNELS:
        owner_constraints.enable_limits(owner, kind)
    elif kind == "IK":
        if cmds.nodeType(owner) != "joint" and not controls.is_control(owner):
            cmds.warning("Inverse Kinematics needs a joint chain or a rig control: select the tip.")
            return
        owner_constraints.add_ik(owner, target)
    else:
        stack.add(owner, kind, target)


def _guarded(action):
    # Building a stack creates groups, and Maya selects each new group: give the selection back,
    # so the owner stays selected (and pose mode doesn't clear a group it can't select).
    selection = cmds.ls(selection=True, long=True) or []
    try:
        action()
    except Exception as error:  # show the problem in Maya instead of losing it in the Qt callback
        cmds.warning("MayaBlenderLike constraints: {}".format(error))
    finally:
        kept = [node for node in selection if cmds.objExists(node)]
        if kept != (cmds.ls(selection=True, long=True) or []):
            cmds.select(kept, replace=True) if kept else cmds.select(clear=True)


class ConstraintsPanel(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(ConstraintsPanel, self).__init__(parent)
        self.owner = None
        self._pick_callback = None

        layout = QtWidgets.QVBoxLayout(self)
        header = QtWidgets.QHBoxLayout()
        self.owner_label = QtWidgets.QLabel()
        self.owner_label.setStyleSheet("font-weight: bold;")
        self.pin = QtWidgets.QToolButton()
        self.pin.setText("Pin")
        self.pin.setCheckable(True)
        self.pin.setToolTip("Keep showing this object while selecting others")
        header.addWidget(self.owner_label, 1)
        header.addWidget(self.pin)
        layout.addLayout(header)

        self.add_button = QtWidgets.QPushButton("Add Object Constraint")
        add_menu = QtWidgets.QMenu(self.add_button)
        _fill_add_menu(add_menu, self._add)
        self.add_button.setMenu(add_menu)
        layout.addWidget(self.add_button)

        self.hint = QtWidgets.QLabel()
        self.hint.setStyleSheet("color: #e8a33d;")
        self.hint.hide()
        layout.addWidget(self.hint)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        cards_host = QtWidgets.QWidget()
        self.cards = QtWidgets.QVBoxLayout(cards_host)
        self.cards.setContentsMargins(0, 0, 0, 0)
        self.cards.addStretch(1)
        scroll.setWidget(cards_host)
        layout.addWidget(scroll, 1)

        note = QtWidgets.QLabel(NOTE)
        note.setWordWrap(True)
        note.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(note)

        # Jobs die with the panel: parented to its workspace control, or killed when the widget goes away.
        docked = cmds.workspaceControl(WORKSPACE_NAME, exists=True)
        jobs = []
        for event in ("SelectionChanged", "Undo", "Redo", "SceneOpened", "NewSceneOpened"):
            options = {"parent": WORKSPACE_NAME} if docked else {}
            jobs.append(cmds.scriptJob(event=[event, self._on_scene_event], **options))
        if not docked:
            self.destroyed.connect(lambda *args: [cmds.scriptJob(kill=j, force=True) for j in jobs if cmds.scriptJob(exists=j)])
        self._on_scene_event()

    # --- selection and picking ---

    def start_pick(self, callback, what="target"):
        self._pick_callback = callback
        self.hint.setText("Click the {} in the viewport or Outliner".format(what))
        self.hint.show()

    def _on_scene_event(self):
        if self._pick_callback is not None:
            picked = [s for s in cmds.ls(selection=True, transforms=True, long=True) or [] if s != self.owner]
            if not picked:
                return
            callback, self._pick_callback = self._pick_callback, None
            self.hint.hide()
            _guarded(lambda: callback(picked[-1]))
            if self.owner and cmds.objExists(self.owner):
                cmds.select(self.owner, replace=True)
            self.refresh()
            return
        if not self.pin.isChecked() or not (self.owner and cmds.objExists(self.owner)):
            owner, _ = _active_and_target()
            self.owner = owner
        self.refresh()

    def _add(self, kind):
        if self.owner is None:
            return
        _, target = _active_and_target()
        _add(self.owner, kind, target)
        self.refresh()

    # --- cards ---

    def refresh(self):
        while self.cards.count() > 1:
            item = self.cards.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        owner = self.owner if self.owner and cmds.objExists(self.owner) else None
        self.add_button.setEnabled(owner is not None)
        if owner is None:
            self.owner_label.setText("Select an object or joint")
            return
        self.owner_label.setText(owner.rsplit("|", 1)[-1])
        cards = [CustomShapeCard(self, owner)] if custom_shapes.accepts(owner) else []
        armature_joints = cmds.listRelatives(owner, allDescendents=True, type="joint", fullPath=True) or []
        if cmds.nodeType(owner) != "joint" and armature_joints:
            cards.append(ArmatureCard(self, owner, armature_joints))
        cards += [StackCard(self, owner, spec) for spec in stack.specs(owner)]
        cards += [LimitCard(self, owner, kind) for kind in owner_constraints.LIMIT_CHANNELS
                  if owner_constraints.has_limits(owner, kind)]
        if owner_constraints.ik_handle(owner):
            cards.append(IkCard(self, owner))
        for index, card in enumerate(cards):
            self.cards.insertWidget(index, card)

    def run(self, action):
        """Run an edit and rebuild the cards, since a stack edit rebuilds the Maya nodes."""
        _guarded(action)
        QtCore.QTimer.singleShot(0, self.refresh)


class Card(QtWidgets.QFrame):

    def __init__(self, panel, owner, title):
        super(Card, self).__init__()
        self.panel, self.owner = panel, owner
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.body = QtWidgets.QFormLayout()
        outer = QtWidgets.QVBoxLayout(self)
        self.title_row = QtWidgets.QHBoxLayout()
        self.title = QtWidgets.QLabel(title)
        self.title.setStyleSheet("font-weight: bold;")
        self.title_row.addWidget(self.title, 1)
        outer.addLayout(self.title_row)
        outer.addLayout(self.body)

    def button(self, text, tooltip, action):
        widget = QtWidgets.QToolButton()
        widget.setText(text)
        widget.setToolTip(tooltip)
        widget.clicked.connect(lambda: self.panel.run(action))
        self.title_row.addWidget(widget)
        return widget

    def object_field(self, label, value, on_pick, what="target"):
        row = QtWidgets.QHBoxLayout()
        field = QtWidgets.QLineEdit(value.rsplit("|", 1)[-1] if value else "")
        field.setReadOnly(True)
        if not value:
            field.setPlaceholderText("none")
            field.setStyleSheet("background: #6b2b2b;")  # Blender marks a constraint without target in red
        pick = QtWidgets.QToolButton()
        pick.setText("Pick")
        pick.setToolTip("Click, then click the {} in the viewport or Outliner".format(what))
        pick.clicked.connect(lambda: self.panel.start_pick(on_pick, what))
        row.addWidget(field, 1)
        row.addWidget(pick)
        self.body.addRow(label, row)

    def combo(self, label, options, current, on_change):
        widget = QtWidgets.QComboBox()
        widget.addItems(options)
        widget.setCurrentText(current)
        widget.currentTextChanged.connect(lambda text: self.panel.run(lambda: on_change(text)))
        self.body.addRow(label, widget)


class StackCard(Card):

    def __init__(self, panel, owner, spec):
        super(StackCard, self).__init__(panel, owner, stack.LABELS[spec["type"]])
        self.spec = spec
        spec_id = spec["id"]
        self.layer = stack.layer(owner, spec_id)

        enabled = QtWidgets.QCheckBox()
        enabled.setToolTip("Enable / disable (keyable on the layer node)")
        enabled.setChecked(bool(cmds.getAttr(self.layer + ".enabled")) if self.layer else spec["enabled"])
        enabled.toggled.connect(self._set_enabled)
        self.title_row.insertWidget(0, enabled)
        kind = spec["type"]
        self.button("^", "Move up", lambda: stack.move(owner, spec_id, -1))
        # A limit at the bottom moves down out of the stack, onto the owner's own channels.
        leaves = kind in stack.LIMIT_CHANNELS and stack.specs(owner)[-1]["id"] == spec_id
        if leaves:
            down = self.button("v", "Move down to the owner's own channels (Maya transform limits, after the whole stack)",
                               lambda: owner_constraints.limit_out_of_stack(owner, spec_id))
            if not owner_constraints.can_limit_leave_stack(owner, spec):
                down.setEnabled(False)
                down.setToolTip("The owner's own channels already have a " + stack.LABELS[kind])
        else:
            self.button("v", "Move down", lambda: stack.move(owner, spec_id, 1))
        self.button("Apply", "Keep the current result and remove this constraint", lambda: stack.apply(owner, spec_id))
        self.button("X", "Delete", lambda: stack.remove(owner, spec_id))

        if kind in stack.LIMIT_CHANNELS:
            _limit_rows(self, spec["limits"], self._set_limit)
        else:
            self.object_field("Target", stack.target_name(spec), lambda node: stack.update(owner, spec_id, target=node))
        if kind in ("COPY_LOCATION", "COPY_ROTATION", "COPY_SCALE"):
            axes = QtWidgets.QHBoxLayout()
            for index, name in enumerate("XYZ"):
                box = QtWidgets.QCheckBox(name)
                box.setChecked(spec["axes"][index])
                box.toggled.connect(lambda checked, i=index: self._set_axis(i, checked))
                axes.addWidget(box)
            offset = QtWidgets.QCheckBox("Offset")
            offset.setChecked(spec["offset"])
            offset.toggled.connect(lambda checked: self.panel.run(lambda: stack.update(owner, spec_id, offset=checked)))
            axes.addWidget(offset)
            self.body.addRow("Axis", axes)
        if kind in ("DAMPED_TRACK", "TRACK_TO", "LOCKED_TRACK", "STRETCH_TO"):
            self.combo("Track Axis", AXES, spec["track_axis"], lambda text: stack.update(owner, spec_id, track_axis=text))
        if kind == "TRACK_TO":
            self.combo("Up", AXES, spec["up_axis"], lambda text: stack.update(owner, spec_id, up_axis=text))
        if kind == "LOCKED_TRACK":
            self.combo("Lock", AXES, spec["lock_axis"], lambda text: stack.update(owner, spec_id, lock_axis=text))
        self._influence_row()

    def _influence_row(self):
        row = QtWidgets.QHBoxLayout()
        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setRange(0, 1000)
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(0.0, 1.0)
        spin.setSingleStep(0.05)
        spin.setDecimals(3)
        value = cmds.getAttr(self.layer + ".influence") if self.layer else self.spec["influence"]
        slider.setValue(int(value * 1000))
        spin.setValue(value)
        slider.valueChanged.connect(lambda v: spin.setValue(v / 1000.0))
        spin.valueChanged.connect(lambda v: (slider.blockSignals(True), slider.setValue(int(v * 1000)),
                                             slider.blockSignals(False), self._set_influence(v)))
        key = QtWidgets.QToolButton()
        key.setText("Key")
        key.setToolTip("Set a key on the influence (Blender: I over the field)")
        key.clicked.connect(lambda: self.layer and cmds.setKeyframe(self.layer, attribute="influence"))
        row.addWidget(slider, 1)
        row.addWidget(spin)
        row.addWidget(key)
        self.body.addRow("Influence", row)

    def _set_influence(self, value):
        if self.layer:
            cmds.setAttr(self.layer + ".influence", value)

    def _set_enabled(self, checked):
        if self.layer:
            cmds.setAttr(self.layer + ".enabled", checked)

    def _set_axis(self, index, checked):
        axes = list(self.spec["axes"])
        axes[index] = checked
        self.panel.run(lambda: stack.update(self.owner, self.spec["id"], axes=axes))

    def _set_limit(self, index, values):
        limits = [list(axis) for axis in self.spec["limits"]]
        limits[index] = list(values)
        self.panel.run(lambda: stack.update(self.owner, self.spec["id"], limits=limits))


class LimitCard(Card):

    def __init__(self, panel, owner, kind):
        super(LimitCard, self).__init__(panel, owner, stack.LABELS[kind] + "  (own channels)")
        self.kind = kind
        up = self.button("^", "Move up into the stack, above its last constraint",
                         lambda: owner_constraints.limit_into_stack(owner, kind))
        if not stack.specs(owner):
            up.setEnabled(False)
            up.setToolTip("Nothing above to move past")
        self.button("X", "Delete", lambda: owner_constraints.clear_limits(owner, kind))
        _limit_rows(self, owner_constraints.limits(owner, kind), self._commit)

    def _commit(self, index, values):
        _guarded(lambda: owner_constraints.set_limit(self.owner, self.kind, index, *values))


def _limit_rows(card, limits, on_commit):
    """One Min / Max row per axis; on_commit(axis_index, (use_min, min, use_max, max))."""
    for index, (use_min, minimum, use_max, maximum) in enumerate(limits):
        row = QtWidgets.QHBoxLayout()
        widgets = []
        for label, used, value in (("Min", use_min, minimum), ("Max", use_max, maximum)):
            box = QtWidgets.QCheckBox(label)
            box.setChecked(used)
            spin = QtWidgets.QDoubleSpinBox()
            spin.setRange(-100000.0, 100000.0)
            spin.setDecimals(3)
            spin.setValue(value)
            row.addWidget(box)
            row.addWidget(spin, 1)
            widgets.extend([box, spin])
        for widget in widgets:
            signal = widget.toggled if isinstance(widget, QtWidgets.QCheckBox) else widget.editingFinished
            # *_ swallows toggled's checked argument, which would otherwise land in i and pick the wrong axis.
            signal.connect(lambda *_, i=index, w=widgets: on_commit(
                i, (w[0].isChecked(), w[1].value(), w[2].isChecked(), w[3].value())))
        card.body.addRow("XYZ"[index], row)


class ArmatureCard(Card):
    """Blender's Armature > Viewport Display, for the armature (the group holding a skeleton)."""

    def __init__(self, panel, owner, joints):
        super(ArmatureCard, self).__init__(panel, owner, "Armature  ({} joints)".format(len(joints)))
        in_front = QtWidgets.QCheckBox("In Front (see the armature through meshes)")
        in_front.setChecked(custom_shapes.in_front(joints[0]))
        in_front.toggled.connect(lambda checked: self.panel.run(lambda: custom_shapes.set_in_front(joints, checked)))
        self.body.addRow("", in_front)


class CustomShapeCard(Card):
    """Blender's Bone > Viewport Display > Custom Shape."""

    NONE, FROM_CURVE = "None", "From Selected Curve..."

    def __init__(self, panel, owner):
        super(CustomShapeCard, self).__init__(panel, owner, "Viewport Display")
        in_front = QtWidgets.QCheckBox("In Front (whole armature: see it through meshes)")
        bone = custom_shapes.armature_joint(owner)
        in_front.setEnabled(bone is not None)
        in_front.setChecked(bool(bone) and custom_shapes.in_front(bone))
        in_front.toggled.connect(lambda checked: self.panel.run(lambda: custom_shapes.set_in_front([bone], checked)))
        self.body.addRow("", in_front)
        current = custom_shapes.settings(owner) or {"shape": self.NONE, "size": 1.0,
                                                    "color": custom_shapes.COLORS["Yellow"], "hide_bone": True}
        self.shape = QtWidgets.QComboBox()
        self.shape.addItems([self.NONE] + list(custom_shapes.SHAPES) + [self.FROM_CURVE])
        if current["shape"] == "Custom":
            self.shape.insertItem(1, "Custom")
        self.shape.setCurrentText(current["shape"])
        self.size = QtWidgets.QDoubleSpinBox()
        self.size.setRange(0.01, 100.0)
        self.size.setSingleStep(0.1)
        self.size.setValue(current["size"])
        self.size.setToolTip("Scale, relative to the bone length (Blender's Scale to Bone Length)")
        self.color = QtWidgets.QComboBox()
        self.color.addItems(list(custom_shapes.COLORS))
        names = {v: k for k, v in custom_shapes.COLORS.items()}
        self.color.setCurrentText(names.get(current["color"], "Yellow"))
        self.hide_bone = QtWidgets.QCheckBox("Hide bone (wireframe shape only)")
        self.hide_bone.setChecked(current["hide_bone"])

        self.body.addRow("Custom Shape", self.shape)
        self.body.addRow("Scale", self.size)
        self.body.addRow("Color", self.color)
        self.body.addRow("", self.hide_bone)
        note = QtWidgets.QLabel("Plain Maya curves under the joint: anyone opening the file sees them, no tool needed.")
        note.setWordWrap(True)
        note.setStyleSheet("color: gray; font-size: 10px;")
        self.body.addRow(note)

        self.shape.currentTextChanged.connect(lambda _: self._apply())
        self.size.editingFinished.connect(self._apply)
        self.color.currentTextChanged.connect(lambda _: self._apply())
        self.hide_bone.toggled.connect(lambda _: self._apply())

    def _apply(self):
        shape = self.shape.currentText()
        owner = self.owner
        if shape == self.NONE:
            self.panel.run(lambda: custom_shapes.remove([owner]))
            return
        options = dict(size=self.size.value(), color=custom_shapes.COLORS[self.color.currentText()],
                       hide_bone=self.hide_bone.isChecked())
        if shape == self.FROM_CURVE:
            self.panel.start_pick(lambda node: custom_shapes.assign([owner], source=node, **options), "curve")
        elif shape == "Custom":
            self.panel.run(lambda: _restyle_custom(owner, options))
        else:
            self.panel.run(lambda: custom_shapes.assign([owner], shape, **options))


class IkCard(Card):

    def __init__(self, panel, owner):
        super(IkCard, self).__init__(panel, owner, "Inverse Kinematics  (own chain)")
        settings = owner_constraints.ik_settings(owner)
        self.button("X", "Delete", lambda: owner_constraints.remove_ik(owner))
        self.object_field("Target", settings["target"], lambda node: owner_constraints.set_ik(owner, target=node))
        self.object_field("Pole Target", settings["pole"], lambda node: owner_constraints.set_ik(owner, pole=node), "pole target")
        chain = QtWidgets.QSpinBox()
        chain.setRange(1, 64)
        chain.setValue(settings["chain_count"])
        chain.editingFinished.connect(lambda: self.panel.run(lambda: owner_constraints.set_ik(owner, chain_count=chain.value())))
        self.body.addRow("Chain Length", chain)


def _restyle_custom(owner, options):
    """Recolor / re-hide a copied curve in place; its geometry stays as it was."""
    for curve_shape in custom_shapes.shapes(owner):
        cmds.setAttr(curve_shape + ".overrideColor", options["color"])
    if cmds.nodeType(owner) == "joint":
        cmds.setAttr(owner + ".drawStyle", 2 if options["hide_bone"] else 0)
