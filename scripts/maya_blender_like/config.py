"""User settings. Edit this file to turn features on or off, then restart Maya."""

# Hotkeys and popup menus: Shift+A add, Ctrl+A apply, X delete, H hide, N / Shift+N panels, Shift+Tab snap, and more.
ENABLE_HOTKEYS = True
HOTKEY_SET_NAME = "Blender_Style"

# Viewport navigation: middle mouse orbits, Shift+middle pans, Ctrl+middle dollies, no Alt needed.
ENABLE_NAVIGATION = True
NAVIGATION_ORBIT_DEGREES_PER_PIXEL = 0.4
NAVIGATION_DOLLY_SPEED = 0.005     # zoom per pixel of vertical drag
NAVIGATION_INVERT_DOLLY = False    # False: drag up zooms in

# Numpad views over a viewport: 1/3/7 front/right/top, Ctrl for the opposite side, 5 toggles orthographic.
ENABLE_NUMPAD_VIEWS = True
NUMPAD_AUTO_PERSPECTIVE = True     # like Blender: numpad views go orthographic, orbiting goes back to perspective

# Modal G / R / S over a viewport (X/Y/Z axis, typed values, click to confirm) and E to extrude joints.
# Off: G / R / S just pick Maya's move, rotate and scale tools.
ENABLE_MODAL_TRANSFORMS = True
# X / Y / Z in G / R / S name Blender's global axes: Z is up, Y is back to front (Maya's Y and -Z,
# through the FBX axis conversion). False: Maya's own axes (Y up). Local axes are the same either way.
BLENDER_AXES = True

# Label in the viewport's top-left corner: Object Mode, Pose Mode, Edit Mode - Armature / Mesh.
ENABLE_MODE_INDICATOR = True

# Object mode (clicking a joint selects its whole skeleton) and pose mode (one joint at a time,
# only it highlights), switched with Ctrl+Tab. Off: joints select one by one, as in stock Maya.
ENABLE_ARMATURE_MODES = True

# Viewport grid, in centimeters (Maya's default working unit).
ENABLE_GRID = True
GRID_HALF_SIZE_CM = 500   # grid spans -5 m to +5 m
GRID_SPACING_CM = 100     # major line every 1 m
GRID_DIVISIONS = 10       # minor line every 10 cm

# Workspace "Blender Like": Outliner on the right above the Channel Box. Created once, then yours to change and save.
ENABLE_LAYOUT = True

# Blender's gray viewport background and orange active selection.
ENABLE_COLORS = True
