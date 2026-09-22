"""User settings. Edit this file to turn features on or off, then restart Maya."""

# Hotkeys: G/R/S transforms, Tab, A/Alt+A, Shift+D, Ctrl+P/Alt+P, I, Shift+R, Home.
ENABLE_HOTKEYS = True
HOTKEY_SET_NAME = "Blender_Style"

# Viewport navigation: middle mouse orbits, Shift+middle pans, Ctrl+middle dollies, no Alt needed.
ENABLE_NAVIGATION = True
NAVIGATION_ORBIT_DEGREES_PER_PIXEL = 0.4
NAVIGATION_DOLLY_SPEED = 0.005     # zoom per pixel of vertical drag
NAVIGATION_INVERT_DOLLY = False    # False: drag up zooms in

# Viewport grid, in centimeters (Maya's default working unit).
ENABLE_GRID = True
GRID_HALF_SIZE_CM = 500   # grid spans -5 m to +5 m
GRID_SPACING_CM = 100     # major line every 1 m
GRID_DIVISIONS = 10       # minor line every 10 cm
