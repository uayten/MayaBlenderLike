# MayaBlenderLike

Makes Autodesk Maya feel like Blender, installed in one step and restored in one step after reinstalling Maya:

- **Viewport navigation without Alt**: middle mouse orbits, Shift + middle pans, Ctrl + middle dollies
- **Numpad views**: 1 / 3 / 7 for front, right and top in orthographic, Ctrl for the opposite side, 5 to toggle orthographic and perspective, `.` to frame the selection, / for local view
- **Edit mode and pose mode for skeletons**: Tab on joints edits the rest with the mesh standing still, then rebinds the skin; Alt+G / Alt+R / Alt+S return to that rest
- **Custom shapes for joints and controls**: bone, circle, square, cube, sphere, diamond, arrow or any curve of yours, scaled by bone length, bone hidden; plain Maya data that works for anyone who opens the file
- **Convert a Blender skeleton into a Maya rig**: one click gives every bone a control that reads 0 / 0 / 1 at rest, like a Blender pose bone, with display layers and IK on controls; a Blender add-on brings the locks, bone collections (M), custom shapes and constraints that FBX drops
- **Armature In Front**: see the rig through meshes
- **3D cursor**: Shift + right click places it, Shift+S snaps to and from it, Shift+A adds there
- **Constraints panel with Blender's stack**: Blender constraint names, top-to-bottom order, influence, Apply, built from standard Maya nodes
- **Modal transforms**: G / R / S follow the mouse, X / Y / Z lock an axis, type a value, click to confirm, right-click to cancel; E extrudes joints like bones
- **Blender hotkeys and menus**: Shift+A add, Ctrl+A apply, X delete, H / Shift+H / Alt+H hide and reveal, Alt+G / Alt+R / Alt+S clear transforms, Tab for components, A to select all, Shift+D to duplicate, Ctrl+P to parent, N for the sidebar, and more
- **Blender look**: Outliner on the right above the Channel Box, gray viewport, orange active selection
- **A usable grid**: 10 m wide with 1 m major lines, instead of Maya's 24 cm default
- **Nothing hard-coded into Maya**: everything lives in this folder as a Maya module and can be switched off in one file

## Contents

- [Install](#install)
- [Uninstall](#uninstall)
- [Hotkeys](#hotkeys)
- [Modal transforms](#modal-transforms)
- [Edit mode and pose mode](#edit-mode-and-pose-mode)
- [Blender rig data](#blender-rig-data)
- [Bone collections](#bone-collections)
- [Constraints panel](#constraints-panel)
- [Custom shapes](#custom-shapes)
- [In Front](#in-front)
- [Convert to a MayaBlenderLike rig](#convert-to-a-mayablenderlike-rig)
- [Viewport navigation](#viewport-navigation)
- [Numpad views](#numpad-views)
- [3D cursor](#3d-cursor)
- [Layout and colors](#layout-and-colors)
- [Grid](#grid)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [How it works](#how-it-works)
- [Compatibility](#compatibility)

## Install

1. Clone or download this repository to a permanent location. Maya loads it from there, so don't delete or move the folder afterwards.
   ```
   git clone https://github.com/uayten/MayaBlenderLike.git
   ```
2. Double-click `install.bat`.
3. Restart Maya.

The installer writes one file, `Documents\maya\modules\MayaBlenderLike.mod`, which points Maya to this folder. It applies to every Maya version installed on the machine.

On first launch Maya may ask whether to run `userSetup.py` from this module. Allow it.

If you move the folder, run `install.bat` again.

## Uninstall

Double-click `uninstall.bat` and restart Maya.

The `Blender_Style` hotkey set stays in Maya's preferences. To go back to Maya's hotkeys, open **Windows → Settings/Preferences → Hotkey Editor** and pick **Maya_Default** in the set menu at the top.

## Hotkeys

The hotkeys live in their own hotkey set, `Blender_Style`, copied from `Maya_Default`. Maya's default set is never modified.

| Key | Action | Maya default it replaces |
|---|---|---|
| G / R / S | Modal move / rotate / scale over a viewport ([details](#modal-transforms)); Maya's tools outside viewports; nothing with nothing selected | Repeat last (moved to Shift+R), scale tool, set key (moved to I) |
| E | Extrude selected joints ([details](#modal-transforms)); Maya's rotate tool otherwise | |
| Alt+G / Alt+R / Alt+S | Clear location / rotation / scale | HumanIK full body key (Alt+S) |
| Shift+A | Add menu at the 3D cursor: mesh, curve, empty, armature, camera, light | Frame all in all views |
| Ctrl+A | Apply menu: freeze location / rotation / scale, center pivot, delete history | Attribute Editor (moved to Shift+N) |
| X | Delete menu (Delete deletes directly) | Hold for grid snap (now Shift+Tab) |
| H | Hide selected | Toggle visibility |
| Shift+H | Hide unselected | Show last hidden |
| Alt+H | Reveal all | Hide unselected |
| N | Toggle Channel Box (Blender's sidebar) | |
| Shift+N | Toggle Attribute Editor (Blender's Properties) | |
| Shift+Tab | Toggle grid snap (over a viewport) | |
| I | Set key | Insert key modifier |
| Shift+R | Repeat last command | |
| Tab | Over a viewport: edit mode on a selected rig, back to object mode from edit or pose mode ([details](#edit-mode-and-pose-mode)); object / component toggle on a mesh | F8 (cleared) |
| Ctrl+Tab | Over a viewport: mode menu (Object, Edit, Pose) | |
| Shift+Ctrl+C | Add Constraint (with Targets) menu ([details](#constraints-panel)) | Create camera from view |
| M | Bone collections menu: move to, select, show / hide ([details](#bone-collections)) | |
| Shift+S | Snap menu: selection and [3D cursor](#3d-cursor) | Keyframe tangent marking menu |
| Shift + right click | Place the [3D cursor](#3d-cursor) (over a viewport) | Maya's Shift + right click marking menu |
| Numpad / | Local view (Isolate Select), over a viewport | |
| A | Select all: every bone of the armature in pose or edit mode, everything in object mode | Frame all (moved to Home) |
| Alt+A | Select none | Cycle display mode |
| Home | Frame all | |
| Shift+D | Duplicate | Duplicate with transform |
| Ctrl+P | Parent (select child first, parent last) | |
| Alt+P | Unparent | Camera mode toggle |

W keeps Maya's move manipulator for when you want to drag handles. E is extrude on joints and Maya's rotate tool otherwise.

Maya's own keys for actions these keys already cover are cleared in this set, so each action has one key: Ctrl+D (use Shift+D), P and Shift+P (use Ctrl+P and Alt+P), Ctrl+H (use H), Alt+D (use Alt+A), Ctrl+Shift+A (use A), F8 (use Tab) and F (use `.`). Editor-specific keys, like F in the Graph Editor, stay. Shift+A adds objects at the [3D cursor](#3d-cursor), sized in centimeters like Blender's defaults in meters (a 1 m bone is 100 cm).

Alt+G / Alt+R / Alt+S skip locked and driven channels and can be undone in one step. When every channel is locked or driven they say so and add nothing to the undo queue.

**Joints that follow a control.** In a Maya rig a joint usually follows a control through a constraint (for example `root` constrained to `CTRL_main`), so its channels are outputs and can't be set. G / R / S and Alt+G / Alt+R / Alt+S on such a joint act on the control that drives it, and the viewport says so (`root follows CTRL_main: acting on the control`). Constraint-stack plumbing from the Bone & Constraints panel is not treated as a control.

 Objects and controls go to 0 (1 for scale). A joint's translate and rotate hold its rest position in Maya, so zeroing them would collapse the joint. Joints go back to their rest instead, like a Blender bone: the rest recorded by [edit mode](#edit-mode-and-pose-mode), or the skin's bind pose before the first edit. Joints with neither are skipped with a warning. Put controls inside offset groups and Alt+G / Alt+R / Alt+S work on them exactly as in Blender.

## Modal transforms

With the mouse over a viewport and something selected, G, R and S work as in Blender:

| Input | Effect |
|---|---|
| Move the mouse | Move in the view plane, rotate around the view axis, or scale from the pivot |
| X / Y / Z | Lock to the global axis; press again for the local axis (of the active object), again to unlock. Global axes are Blender's: **Z is up** and Y runs back to front (Maya's Y and -Z, as FBX converts them), so G Z moves up in a Y-up Maya; `BLENDER_AXES = False` in config.py uses Maya's names. Local axes are the object's or bone's own, the same as in Blender. A line through the pivot, in Maya's color for the axis it runs along, shows the locked axis. Switching axis discards what the previous axis did |
| Digits, `.`, `-`, Backspace | Type an exact value: cm for move (X when no axis is locked), degrees for rotate, factor for scale |
| G / R / S | Switch to another transform without confirming |
| Left click / Enter | Confirm, as one undo step |
| Right click / Esc | Cancel |

The pivot is the median of the selected origins, or of the selected components in component mode. Rotating and scaling several objects swings them around that point, like Blender's Median Point pivot, while each one turns and grows around its own origin. A child whose parent is also selected moves once, as in Blender. Locked or driven channels are skipped with a warning. The current value shows in the viewport while you drag.

E on selected joints adds a child joint at each one and starts moving it, like extruding a bone. The extrusion and the move are two undo steps.

## Edit mode and pose mode

Maya has no armature modes: a joint's translate and rotate hold both its rest placement and its pose. The module adds Blender's three modes on top of standard joints:

| Mode | For | What changes |
|---|---|---|
| **Object Mode** | Working on the scene | Maya as usual, except for bones: clicking any joint, or any control of its rig (a curve in the same top group), selects its **armature**, and the whole bone hierarchy highlights. Curves outside a rig select normally. The default |
| **Pose Mode** | Animating | Only entered with an armature selected (or from its edit mode). Only that armature's joints and its rig's controls (curves) can be selected; on a [converted rig](#convert-to-a-mayablenderlike-rig) a joint selects its control, and A selects every control. Only the selected joint highlights, not its whole hierarchy. Alt+G / Alt+R / Alt+S return joints to rest. Stays on with nothing selected |
| **Edit Mode** | Editing the rig | Only the joints of the rig being edited can be selected. See below |

| Key (over a viewport) | Effect |
|---|---|
| Tab | In object mode with a rig selected (a joint, a group with joints under it, or a control of the rig), enter edit mode. In edit or pose mode, back to object mode. With a mesh selected, Maya's object / component toggle (Blender's mesh edit mode) |
| Ctrl+Tab | Menu at the cursor to pick Object, Edit or Pose Mode; the current one is marked |

**The armature.** Blender separates the armature object from the bones inside it. In Maya the armature is the group holding the skeleton (`SKEL` in a `RIG|SKEL|root` rig), or the top joint when the skeleton isn't in a group. Moving it in object mode moves the whole rig, like moving an armature object. Select it, then Tab for edit mode or Ctrl+Tab → Pose Mode.

The rules hold everywhere: the viewport's selection masks stop the click, and the selection is checked after every change, so picks from the Outliner or scripts are corrected too. Anything a mode forbids is dropped from the selection with a note in the viewport, and the correction adds no undo step.

The same three modes are in the **Blender Like** menu. A label in the top-left corner of the viewport always shows the mode (Object Mode, Pose Mode, Edit Mode - Rig, Edit Mode - Mesh), with the active object's name under it (`Bone: root` for a joint, `Active: CTRL_main` otherwise, plus how many others are selected), while the viewport's Heads Up Display is on (**Display → Heads Up Display**).

Tab, Ctrl+Tab and Shift+Tab act over a viewport: Qt uses Tab to move keyboard focus between widgets before Maya's hotkeys see it, so the module reads these keys in its viewport event filter. Set `ENABLE_ARMATURE_MODES = False` to skip pose mode's selection changes.

**Edit mode** (for the whole skeleton of the selected rig):

- Joints go to their rest pose and are drawn light blue; the label shows **Edit Mode - Rig**.
- The skin is paused, so the mesh stays still while you move joints, like Blender's edit bones.
- Moving, rotating or scaling a joint leaves its children in place, with the modal G / R / S and with Maya's own tools.
- E extrudes new joints.

**Leaving edit mode** (Tab back to object mode, or Ctrl+Tab to pick pose mode):

- The new placement becomes the rest. Rotation goes into jointOrient, so joints at rest read rotate 0, as Maya riggers expect.
- The skin is rebound at the new rest: the mesh keeps its shape instead of jumping.
- The pose you had before comes back on top of the new rest.

**Pose mode** is Maya's normal state. Alt+G / Alt+R / Alt+S return joints to the rest recorded by edit mode (or to the skin's bind pose before the first edit). **Ctrl+A → Pose as Rest Pose** makes the current pose the rest, like Blender's Apply menu.

The rest is stored as three hidden attributes on each joint (`mblRestTranslate`, `mblRestRotate`, `mblRestScale`). The skeleton stays made of standard joints, so other animators, Maya tools and FBX exports to game engines see a normal skeleton.

Limitations:

- Keyframes on joints are absolute in Maya: editing the rest doesn't shift existing keys the way Blender's relative pose channels do. Edit the rest before animating.
- Undoing across a mode change restores the scene but not the mode display. Press Tab to resync.

An experimental alternative, keeping the rest inside the joint (`offsetParentMatrix`) so channels read 0 at rest exactly like Blender, is planned for testing. It stays out of the default because its compatibility with FBX export and other riggers still has to be verified.

## Blender rig data

FBX carries the skeleton and the skin, not the rig. The Blender add-on in this repository, [`blender/mayablenderlike_rig_export.py`](blender/mayablenderlike_rig_export.py), writes the rest to a JSON file, and Maya puts it on the controls of the [converted rig](#convert-to-a-mayablenderlike-rig):

1. In Blender: **Edit → Preferences → Add-ons → Install from Disk**, pick the file (or open it in the Text Editor and Run Script). Select the armature, then **File → Export → MayaBlenderLike Rig Data (.json)**.
2. In Maya: import the FBX, **Convert to MayaBlenderLike Rig**, then with the rig selected **Blender Like → Apply Blender Rig Data (.json)...**.

| Blender | Maya |
|---|---|
| Lock location / rotation / scale | Channels locked and hidden in the Channel Box. Constraints still move them, as in Blender |
| Rotation mode | Rotate order (XYZ Euler = xyz). Quaternion and Axis Angle stay XYZ, with a note |
| Bone collections | Selection sets, see [Bone collections](#bone-collections); hidden collections hidden |
| Custom shape (with its translation, rotation, scale and Scale to Bone Length) | The shape's wire as curves on the control, in the bone color |
| Copy Location / Rotation / Scale / Transforms, Child Of, Damped Track, Track To, Locked Track, Stretch To | The same constraint in the control's [stack](#the-stack), in Blender's order, with influence, mute, axes, offset and track / lock / up axes |
| Limit Location / Rotation / Scale | Below every other constraint: Maya transform limits on the control. Higher up, muted or with influence below 1: a layer in the stack, in Blender's order |
| Inverse Kinematics | [IK on the control](#convert-to-a-mayablenderlike-rig), with target, pole and chain length |

Bones are matched by name (`MCH-arm.L` in Blender is `MCH_arm_L` after FBX). Anything without a Maya match is listed as a warning in the Script Editor: other constraint types, non-World spaces, Head/Tail, pole angle, inverted axes.

## Bone collections

Blender's bone collections are Maya **selection sets** tagged as collections, so they also show in Maya's **Edit → Quick Select Sets** and in the Outliner, and work without this module. **M** over the viewport opens Blender's menu for the selected bones (a joint counts as its control):

- **Move to** a collection (the bones leave the others), or **New Collection...**
- **Select** a collection's bones
- **Show / Hide** a collection

## Constraints panel

**Blender Like → Bone & Constraints Panel** docks a panel next to the Attribute Editor, like Blender's Bone and Constraints tabs. It follows the active object (the last one selected).

- **Add Object Constraint** lists Blender's constraints by name: Copy Location, Copy Rotation, Copy Scale, Copy Transforms, Limit Location, Limit Rotation, Limit Scale, Damped Track, Inverse Kinematics, Locked Track, Stretch To, Track To, Child Of.
- With a second object selected, it becomes the target, like Blender's Add Constraint (with Targets). Shift+Ctrl+C opens the same menu at the cursor.
- Each constraint is a card: enable checkbox, move up / down, Apply, delete, target field with a picker (click Pick, then the target in the viewport or Outliner), axes, offset, track and up axes, and influence with a key button.

Maya equivalents under the hood:

| Blender | Maya |
|---|---|
| Copy Location / Rotation / Scale | Point / Orient / Scale Constraint |
| Copy Transforms | Parent + Scale Constraint |
| Child Of (with Set Inverse) | Parent + Scale Constraint with offset |
| Damped Track | Aim Constraint without up vector |
| Track To | Aim Constraint with scene up (Blender's Z up is Maya's Y up) |
| Locked Track | Aim Constraint with an object-rotation up vector |
| Stretch To | Aim Constraint plus scale by distance (no volume preservation) |
| Limit Location / Rotation / Scale | At the bottom: Maya transform limits on the owner's own channels. Moved up: a stack layer that clamps the owner's local values at that point |
| Inverse Kinematics | ikHandle (Rotate-Plane solver) with point and pole vector constraints |

### The stack

Blender evaluates constraints top to bottom, each blending into the previous result by its influence. Maya constraints have no order, and two on the same channel fight. The panel rebuilds Blender's stack as a chain of plain transforms in a hidden group, `MBL_constraintStacks`, outside the owner's hierarchy. The owner then follows the end of the chain.

- **Other animators**: the stack is built only from standard Maya nodes (groups, constraints, utility nodes). Anyone can open and animate the rig without this module. Influence and enable are keyable attributes on the layer nodes.
- **Game engines**: nothing changes. No constraint, from Blender or Maya, ever reaches a game engine: bake the animation when exporting FBX. The skeleton hierarchy is untouched, since the chain lives outside it.
- **Limits** at the bottom are Maya's own transform limits ("own channels"): they clamp after the whole stack, and the animator feels them in the channel box. Move a limit up and it becomes a stack layer that clamps at that point, like Blender's Copy Location → Limit Location → Copy Rotation; move it back down past the last constraint and it returns to the owner's channels. A second limit of a kind the channels already hold is added to the stack.
- **IK** acts on the owner itself and doesn't take part in the order, shown at the bottom as "own chain".
- **The stack is Blender's model, not Maya's.** A Maya rigger opening the file sees the chain of groups, not a constraint stack. The note at the bottom of the panel says so.

Differences from Blender:

- A constrained owner's channels become outputs of its stack, as with any Maya constraint. Animate a control and constrain the joint to it, which is standard Maya practice, instead of animating the constrained node directly.
- Constraint spaces are world space. Blender's local and custom spaces aren't offered.

## Custom shapes

Blender's Bone → Viewport Display → Custom Shape, for Maya joints.

- In the **Bone & Constraints** panel, a joint or control shows a **Custom Shape** card: shape (Bone, Circle, Square, Cube, Sphere, Diamond, Arrow, Line, or **From Selected Curve** to copy any curve of yours), scale, color, and **Hide bone** to show only the shape.
- On a [converted rig](#convert-to-a-mayablenderlike-rig) the shape goes on the bone's control. Setting it to None there brings back the Bone shape, since a control needs one.
- **Blender Like → Custom Shape (selected joints)** applies a shape to several joints at once, or removes it.
- Shapes are built in bone space: Y runs along the bone, toward the first child joint, and the size follows the bone length, like Blender's Scale to Bone Length. A copied curve keeps its own size, times the scale.
- Clicking the shape selects the joint.

**Working for anyone who opens the file.** The shape is a curve parented under the joint itself, Maya's native technique. The scene needs nothing but Maya: tested by saving the file and reopening it without this module, the shapes are there and the file only requires Maya.

**FBX.** Tested: FBX export writes the joints as plain bones and leaves the curves out, so game engines get a clean skeleton.

## In Front

Blender's Armature → Viewport Display → In Front: see the rig through the mesh. Tick **In Front** in the Viewport Display card of the Bone & Constraints panel, or use **Blender Like → Armature In Front: On / Off** with the rig selected.

- Joints: Maya can only x-ray joints per viewport (**Joint X-Ray**), not per skeleton, so while any armature in the scene has In Front on, every viewport x-rays joints.
- Curves: the custom shapes and controls in the rig's top group get **Always Draw On Top** each.
- The setting is saved on the skeleton's top joint, and viewports pick it up again when the scene opens, once Maya has restored the panel settings stored in the file. With the armature selected, the Bone & Constraints panel shows an **Armature** card with the same checkbox.

## Convert to a MayaBlenderLike rig

In Blender you pose the bones themselves, and their channels read 0 at rest. A Maya joint can't do that: its translate holds where the bone sits in its parent. Maya rigs pose **controls** instead. A control's rest is stored in its offset parent matrix, so its channels read 0 / 0 / 1 at rest, and it drives the joint. **Blender Like → Convert to MayaBlenderLike Rig**, with the armature (or any of its joints) selected, builds that layout from a skeleton imported from Blender.

**Export from Blender with these FBX options** (Armature section):

| Option | Value | Why |
|---|---|---|
| Primary Bone Axis | **Y** (default) | Keeps Blender's bone space in the joints: the bone runs along Y, so controls point where the bones pointed and constraint axes (Track Y, rotate Y) mean the same as in Blender. With X, every bone looks turned 90° |
| Secondary Bone Axis | **X** (default) | Same reason |
| Add Leaf Bones | **On** | FBX has no bone tails; the `*_end` leaf bones carry where each last bone ends, so it keeps its direction and length |

Converting warns when the leaf bones show the bones running along X.

Each joint is sorted by the skin weights actually painted on the mesh. A joint that is a skin influence but has no weight counts as non-deforming.

| Joint | Becomes |
|---|---|
| Deforming, or with deforming joints below it (a root, say) | Stays a joint, in the skeleton that FBX exports. Gets a control that drives it (parent + scale constraint), shaped like a Blender bone, or with its custom shape moved over |
| Non-deforming, no joints below (IK target, pole, pivot) | Replaced by a control; constraints that used the joint as a target now use the control |
| Non-deforming, with joints below (IK / FK mechanism chain) | Stays a joint chain, so an ikHandle can use it, moved into a **MECH** group and following the bone it hung from |
| Leaf bone from Blender's FBX export (`*_end`, "Add Leaf Bones") | Gives its parent bone its length, then is deleted |

The result, inside the rig's top group (a skeleton at the world root gets a `<root>_rig` group):

```
Armature
  root ...            the skeleton: joints only, bones hidden (the controls draw them)
  CTRL
    root_ctrl         one control per bone, parented like the bones
      spine_ctrl
  MECH
    mch_a ...         mechanism chains
```

After converting:

- **Pose Mode** poses the controls. The Channel Box reads 0 / 0 / 1 at rest, Alt+G / Alt+R / Alt+S clear to it, and keys are relative to the rest, as in Blender.
- **Edit Mode** edits the joints: the controls hide, the bones show, and on leaving, each control takes its joint's new rest while keeping its pose. Controls that replaced joints keep their place, like Blender's child bones.
- **Object Mode**: clicking a control or a joint selects the whole rig.
- **Display layers**, the Maya way to show only what the animator needs (Layer Editor, under the Channel Box): `<rig>_GEO` holds the skinned meshes as Reference (visible, not clickable), `<rig>_JNT` holds the skeleton and MECH, hidden, and `<rig>_CTRL` the controls. Edit Mode shows the JNT layer while editing.
- **Inverse Kinematics** on a control (Add Object Constraint → Inverse Kinematics, with the target selected first): Maya's ikHandle only solves joints, so the control gets its own joint chain in MECH, from the chain's top control to the owner bone's tail, solved toward the target and pole; the controls of the chain turn with it. Chain Length 0 takes every control above, as in Blender. The chain, like the constraint stacks, is rebuilt when Edit Mode changes the rest.
- Add constraints to the **controls** in the Bone & Constraints panel. The panel's Custom Shape card works on controls too.
- FBX: export the skeleton (the joints). Controls and MECH stay in Maya. Bake the animation, since game engines never get constraints.

The conversion is done at the rest pose and is one undo step. A rig that is already converted is left alone.

Limitations:

- IK has no influence slider yet: the chain's controls follow the IK fully, and removing the IK returns their rotation to rest.
- Keys on the joints from before the conversion are overridden by the controls.
- Controls are never scaled at rest, even when the FBX brings the joints at 100x: their translate reads centimeters.
- FBX doesn't keep the length of a bone that has children. The control takes the distance to a child lying on the bone's line, or 10 cm; adjust it with Scale in the Custom Shape card.
- Ctrl+A → Pose as Rest Pose is refused on a converted rig; edit the rest in Edit Mode.

## Viewport navigation

| Blender gesture | Maya camera command | Result |
|---|---|---|
| Middle mouse | tumble | Orbit |
| Shift + middle mouse | track | Pan |
| Ctrl + middle mouse | dolly | Dolly (drag up to zoom in) |
| Mouse wheel | unchanged | Zoom |

Alt + mouse keeps working as in stock Maya. Speeds and dolly direction are set in the configuration file. Maya's own middle-drag, which moves the selected object from anywhere in the viewport, isn't available while this feature is on.

## Numpad views

Press the keys with the mouse over a viewport, as in Blender.

| Key | View |
|---|---|
| Numpad 1 | Front (orthographic) |
| Ctrl + Numpad 1 | Back |
| Numpad 3 | Right |
| Ctrl + Numpad 3 | Left |
| Numpad 7 | Top |
| Ctrl + Numpad 7 | Bottom |
| Numpad 5 | Toggle orthographic / perspective, keeping the framing |
| `.` (numpad or main keyboard) | Frame selected, same as Maya's F |
| Numpad / | Local view: only the selection in this viewport, framed (Maya's Isolate Select); again to show everything |

Like Blender's Auto Perspective, a view that went orthographic through 1, 3 or 7 returns to perspective when you orbit. A view made orthographic with 5 stays orthographic while orbiting.

The views move the viewport's own camera around the current view center. Maya's front, side and top cameras are untouched. Views follow Blender's axes after an FBX export: Blender's front arrives in Maya facing +Z, which is Maya's front.

Maya's hotkeys can't tell the numpad from the number row, so the numpad is handled by the navigation filter. The number row keeps its Maya hotkeys (1 / 2 / 3 smoothness, 4 / 5 / 6 / 7 display modes). The numpad works with Num Lock on or off, and it's ignored while typing in a text field.

## 3D cursor

Blender's 3D cursor: a point in the scene where Shift+A adds objects and that Shift+S snaps to and from. It's drawn as a red ring with a white cross, always on top, and can't be clicked.

| Input | Effect |
|---|---|
| Shift + right click in a viewport | Place the cursor on the mesh surface under the mouse, or at its current depth when there is none |
| Shift+S | Snap menu: Selection to Cursor, Selection to Cursor (Keep Offset), Selection to Active, Selection to Grid, Cursor to Selected, Cursor to Active, Cursor to World Origin, Cursor to Grid |
| Shift+A | Adds at the cursor |

Selection to Cursor puts each object's pivot on the cursor, or each selected vertex. Selection to Grid uses the grid's minor spacing (10 cm by default). Joints that follow a control move the control, as with G.

The cursor's position is saved in the scene and comes back when it opens. The marker itself is never saved (Maya's doNotWrite) and is hidden from the Outliner, so the file stays clean for anyone without this module. Moving the cursor isn't an undo step, as in Blender. The cursor has no rotation yet.

## Layout and colors

A **Blender Like** menu in Maya's main menu bar opens the Constraints panel, toggles edit mode, applies Pose as Rest Pose and links to this page.

The module makes **Blender Like** the current workspace, with the Outliner docked on the right above the Channel Box and Attribute Editor, like Blender's Outliner above Properties.

The workspace travels with this repository, in `workspaces/Blender_Like.json`:

- On a machine where Maya doesn't have it yet (a fresh install), the module installs the repository's copy.
- Rearrange panels as you like and pick **Blender Like → Save Workspace to GitHub**. It saves the layout, copies it into the repository, commits and pushes. Maya's own Save Workspace keeps the change on this machine only.
- Maya's local copy always wins at startup, so the module never overwrites a layout you saved in Maya.

The viewport gets Blender's flat gray background and orange active-object highlight.

## Grid

The viewport grid spans 10 m (−5 m to +5 m), with a major line every 1 m and a minor line every 10 cm. The module applies it at startup and again after **File → New** and **File → Open**.

Because the module sets the grid every time, changes made in **Display → Grid** don't survive a restart. Change the grid in the configuration file instead.

## Configuration

Edit `scripts/maya_blender_like/config.py` and restart Maya:

```python
ENABLE_HOTKEYS = True
HOTKEY_SET_NAME = "Blender_Style"

ENABLE_NAVIGATION = True
NAVIGATION_ORBIT_DEGREES_PER_PIXEL = 0.4
NAVIGATION_DOLLY_SPEED = 0.005
NAVIGATION_INVERT_DOLLY = False

ENABLE_NUMPAD_VIEWS = True
NUMPAD_AUTO_PERSPECTIVE = True

ENABLE_MODAL_TRANSFORMS = True
BLENDER_AXES = True        # G / R / S: Z is up, as in Blender
ENABLE_MODE_INDICATOR = True
ENABLE_ARMATURE_MODES = True
ENABLE_LAYOUT = True
ENABLE_COLORS = True

ENABLE_GRID = True
GRID_HALF_SIZE_CM = 500
GRID_SPACING_CM = 100
GRID_DIVISIONS = 10
```

To add or change a hotkey, edit the `BINDINGS` list in `scripts/maya_blender_like/hotkeys.py`. Command names are in Maya's `scripts/startup/hotkeySetup.mel`, inside the Maya install folder.

## Troubleshooting

**Startup order.** Hotkeys, menus, grid and the mode label load with Maya's window. The viewport event filter (middle-mouse navigation, modal G / R / S, Tab and numpad keys) waits until Maya has nothing left to load: Bifrost, USD, Arnold and other plugins keep loading after the window appears. Until the viewport shows **MayaBlenderLike ready**, the viewport behaves like stock Maya and G / R / S pick Maya's tools. Plugins you never use can be switched off in **Windows → Settings/Preferences → Plug-in Manager** (untick **Auto load**) for a faster start.

At startup the Script Editor shows one line per feature, `MayaBlenderLike: <feature> applied` or `MayaBlenderLike: <feature> failed: ...`. A failed hotkey lists each binding that didn't take; the others still work.

If hotkeys don't respond, check which hotkey set is active and what each key is bound to. Paste this in the Script Editor's Python tab:

```python
import maya_blender_like.hotkeys as h; h.report()
```

Every line should end in `OK`, including the cleared Maya duplicates at the end, and the set should be `Blender_Style`. If another set is current (picked in the Hotkey Editor, or created by another script), restart Maya or pick `Blender_Style` in **Windows → Settings/Preferences → Hotkey Editor**.

Maya saves hotkeys and preferences only when it closes normally. After a crash the saved hotkey file stays old, but the module applies its hotkeys again at every start, so that doesn't matter.

To rule the module out when Maya misbehaves, turn features off one at a time in `config.py` (for example `ENABLE_NAVIGATION` and `ENABLE_MODAL_TRANSFORMS`) and restart.

## How it works

- `install.bat` registers the folder as a Maya module (a `.mod` file), which adds `scripts/` to Maya's Python path.
- Maya runs every `userSetup.py` found on its Python path at startup. The module's `scripts/userSetup.py` calls `maya_blender_like.startup()` once the UI is ready.
- Each feature is applied on its own. If one fails, the others still load, and the failure shows as a warning in the Script Editor.
- Custom commands are Maya runtime commands, listed in the Hotkey Editor under **Custom Scripts → MayaBlenderLike**, so they can be rebound there.
- G / R / S / E are hotkeys that start the modal transform; the event filter then feeds it the mouse and keyboard until you confirm or cancel.
- Viewport navigation is a Qt event filter that catches middle-mouse drags over model panels and moves the panel camera with Maya's `tumble`, `track` and `dolly` commands. The same filter catches numpad keys over viewports.

## Compatibility

Written for Maya 2026 on Windows. The navigation filter supports both PySide6 (Maya 2025 and later) and PySide2 (Maya 2024 and earlier), but only Maya 2026 is the target.
