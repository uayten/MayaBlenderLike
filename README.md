# MayaBlenderLike

Makes Autodesk Maya feel like Blender, installed in one step and restored in one step after reinstalling Maya:

- **Viewport navigation without Alt**: middle mouse orbits, Shift + middle pans, Ctrl + middle dollies
- **Numpad views**: 1 / 3 / 7 for front, right and top in orthographic, Ctrl for the opposite side, 5 to toggle orthographic and perspective, `.` to frame the selection
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
- [Viewport navigation](#viewport-navigation)
- [Numpad views](#numpad-views)
- [Layout and colors](#layout-and-colors)
- [Grid](#grid)
- [Configuration](#configuration)
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
| G / R / S | Modal move / rotate / scale over a viewport ([details](#modal-transforms)); Maya's tools elsewhere or with nothing selected | Repeat last (moved to Shift+R), scale tool, set key (moved to I) |
| E | Extrude selected joints ([details](#modal-transforms)); Maya's rotate tool otherwise | |
| Alt+G / Alt+R / Alt+S | Clear location / rotation / scale | HumanIK full body key (Alt+S) |
| Shift+A | Add menu: mesh, curve, empty, armature, camera, light | Frame all in all views |
| Ctrl+A | Apply menu: freeze location / rotation / scale, center pivot, delete history | Attribute Editor (moved to Shift+N) |
| X | Delete menu (Delete deletes directly) | Hold for grid snap (now Shift+Tab) |
| H | Hide selected | Toggle visibility |
| Shift+H | Hide unselected | Show last hidden |
| Alt+H | Reveal all | Hide unselected |
| N | Toggle Channel Box (Blender's sidebar) | |
| Shift+N | Toggle Attribute Editor (Blender's Properties) | |
| Shift+Tab | Toggle grid snap | |
| I | Set key | Insert key modifier |
| Shift+R | Repeat last command | |
| Tab | Toggle object / component mode (F8 still works) | |
| A | Select all | Frame all (moved to Home) |
| Alt+A | Select none | Cycle display mode |
| Home | Frame all | |
| Shift+D | Duplicate | Duplicate with transform |
| Ctrl+P | Parent (select child first, parent last) | |
| Alt+P | Unparent | Camera mode toggle |

W and E keep Maya's manipulator tools when you need them, so Maya tutorials still apply. F still frames the selection. Shift+A adds objects at the origin, sized in centimeters like Blender's defaults in meters (a 1 m bone is 100 cm).

Alt+G / Alt+R / Alt+S skip locked and driven channels and can be undone in one step. Objects and controls go to 0 (1 for scale). A joint's translate and rotate hold its rest position in Maya, so zeroing them would collapse the joint. Joints go back to their bind pose instead, like a Blender bone to rest. Joints without a bind pose (not skinned) are skipped with a warning. Put controls inside offset groups and Alt+G / Alt+R / Alt+S work on them exactly as in Blender.

## Modal transforms

With the mouse over a viewport and something selected, G, R and S work as in Blender:

| Input | Effect |
|---|---|
| Move the mouse | Move in the view plane, rotate around the view axis, or scale from the pivot |
| X / Y / Z | Lock to the global axis; press again for the local axis (of the active object), again to unlock |
| Digits, `.`, `-`, Backspace | Type an exact value: cm for move (X when no axis is locked), degrees for rotate, factor for scale |
| G / R / S | Switch to another transform without confirming |
| Left click / Enter | Confirm, as one undo step |
| Right click / Esc | Cancel |

The pivot is the median of the selected origins, or of the selected components in component mode. A child whose parent is also selected moves once, as in Blender. Locked or driven channels are skipped with a warning. The current value shows in the viewport while you drag.

E on selected joints adds a child joint at each one and starts moving it, like extruding a bone. The extrusion and the move are two undo steps.

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

Like Blender's Auto Perspective, a view that went orthographic through 1, 3 or 7 returns to perspective when you orbit. A view made orthographic with 5 stays orthographic while orbiting.

The views move the viewport's own camera around the current view center. Maya's front, side and top cameras are untouched. Views follow Blender's axes after an FBX export: Blender's front arrives in Maya facing +Z, which is Maya's front.

Maya's hotkeys can't tell the numpad from the number row, so the numpad is handled by the navigation filter. The number row keeps its Maya hotkeys (1 / 2 / 3 smoothness, 4 / 5 / 6 / 7 display modes). The numpad works with Num Lock on or off, and it's ignored while typing in a text field.

## Layout and colors

The first start creates a workspace named **Blender Like**, with the Outliner docked on the right above the Channel Box and Attribute Editor, like Blender's Outliner above Properties. After that the workspace is yours: rearrange it and save it from the workspace menu at the top right of Maya, and the module won't overwrite it. To rebuild it, delete the workspace in Maya and restart.

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
ENABLE_LAYOUT = True
ENABLE_COLORS = True

ENABLE_GRID = True
GRID_HALF_SIZE_CM = 500
GRID_SPACING_CM = 100
GRID_DIVISIONS = 10
```

To add or change a hotkey, edit the `BINDINGS` list in `scripts/maya_blender_like/hotkeys.py`. Command names are in Maya's `scripts/startup/hotkeySetup.mel`, inside the Maya install folder.

## How it works

- `install.bat` registers the folder as a Maya module (a `.mod` file), which adds `scripts/` to Maya's Python path.
- Maya runs every `userSetup.py` found on its Python path at startup. The module's `scripts/userSetup.py` calls `maya_blender_like.startup()` once the UI is ready.
- Each feature is applied on its own. If one fails, the others still load, and the failure shows as a warning in the Script Editor.
- Viewport navigation is a Qt event filter that catches middle-mouse drags over model panels and moves the panel camera with Maya's `tumble`, `track` and `dolly` commands. The same filter catches numpad keys over viewports.

## Compatibility

Written for Maya 2026 on Windows. The navigation filter supports both PySide6 (Maya 2025 and later) and PySide2 (Maya 2024 and earlier), but only Maya 2026 is the target.
