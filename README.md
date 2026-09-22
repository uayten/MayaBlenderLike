# MayaBlenderLike

Makes Autodesk Maya feel like Blender, installed in one step and restored in one step after reinstalling Maya:

- **Viewport navigation without Alt**: middle mouse orbits, Shift + middle pans, Ctrl + middle dollies
- **Blender hotkeys**: G / R / S to move, rotate, scale, Tab for components, A to select all, Shift+D to duplicate, Ctrl+P to parent, and more
- **A usable grid**: 10 m wide with 1 m major lines, instead of Maya's 24 cm default
- **Nothing hard-coded into Maya**: everything lives in this folder as a Maya module and can be switched off in one file

## Contents

- [Install](#install)
- [Uninstall](#uninstall)
- [Hotkeys](#hotkeys)
- [Viewport navigation](#viewport-navigation)
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

## Viewport navigation

| Blender gesture | Maya camera command | Result |
|---|---|---|
| Middle mouse | tumble | Orbit |
| Shift + middle mouse | track | Pan |
| Ctrl + middle mouse | dolly | Dolly (drag up to zoom in) |
| Mouse wheel | unchanged | Zoom |

Alt + mouse keeps working as in stock Maya. Speeds and dolly direction are set in the configuration file. Maya's own middle-drag, which moves the selected object from anywhere in the viewport, isn't available while this feature is on.

## Grid

The viewport grid spans 10 m (−5 m to +5 m), with a major line every 1 m and a minor line every 10 cm. The module applies it at startup and again after **File → New** and **File → Open**.

Because the module sets the grid every time, changes made in **Display → Grid** don't survive a restart. Change the grid in the configuration file instead.

## Configuration

Edit `scripts/maya_blender_like/config.py` and restart Maya:

```python
ENABLE_HOTKEYS = True
HOTKEY_SET_NAME = "Blender_Style"

ENABLE_NAVIGATION = True

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
- Viewport navigation is a Qt event filter that catches middle-mouse drags over model panels and moves the panel camera with Maya's `tumble`, `track` and `dolly` commands.

## Compatibility

Written for Maya 2026 on Windows. The navigation filter supports both PySide6 (Maya 2025 and later) and PySide2 (Maya 2024 and earlier), but only Maya 2026 is the target.
