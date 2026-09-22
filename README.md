# MayaBlenderLike

Makes Autodesk Maya feel like Blender, installed in one step and restored in one step after reinstalling Maya:

- **Viewport navigation without Alt**: middle mouse orbits, Shift + middle pans, Ctrl + middle dollies
- **Numpad views**: 1 / 3 / 7 for front, right and top in orthographic, Ctrl for the opposite side, 5 to toggle orthographic and perspective, `.` to frame the selection
- **Blender hotkeys**: G / R / S to move, rotate, scale, Alt+G / Alt+R / Alt+S to clear them, Tab for components, A to select all, Shift+D to duplicate, Ctrl+P to parent, and more
- **A usable grid**: 10 m wide with 1 m major lines, instead of Maya's 24 cm default
- **Nothing hard-coded into Maya**: everything lives in this folder as a Maya module and can be switched off in one file

## Contents

- [Install](#install)
- [Uninstall](#uninstall)
- [Hotkeys](#hotkeys)
- [Viewport navigation](#viewport-navigation)
- [Numpad views](#numpad-views)
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
| G | Move tool | Repeat last (moved to Shift+R) |
| R | Rotate tool | Scale tool (moved to S) |
| S | Scale tool | Set key (moved to I) |
| Alt+G / Alt+R / Alt+S | Clear location / rotation / scale | HumanIK full body key (Alt+S) |
| I | Set key | Insert key modifier |
| Shift+R | Repeat last command | |
| Tab | Toggle object / component mode (F8 still works) | |
| A | Select all | Frame all (moved to Home) |
| Alt+A | Select none | Cycle display mode |
| Home | Frame all | |
| Shift+D | Duplicate | Duplicate with transform |
| Ctrl+P | Parent (select child first, parent last) | |
| Alt+P | Unparent | Camera mode toggle |

W and E keep their Maya behavior (move and rotate), so Maya tutorials still apply. F still frames the selection, and H still hides and shows.

The transform tools aren't modal like Blender's: the key picks the tool and you drag the manipulator.

Alt+G / Alt+R / Alt+S skip locked and driven channels and can be undone in one step. Objects and controls go to 0 (1 for scale). A joint's translate and rotate hold its rest position in Maya, so zeroing them would collapse the joint. Joints go back to their bind pose instead, like a Blender bone to rest. Joints without a bind pose (not skinned) are skipped with a warning. Put controls inside offset groups and Alt+G / Alt+R / Alt+S work on them exactly as in Blender.

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
