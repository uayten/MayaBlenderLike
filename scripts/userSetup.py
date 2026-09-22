# Maya runs every userSetup.py found on sys.path at startup; this one comes from the MayaBlenderLike module.
import maya.utils

# Deferred so the UI (viewports, hotkey system) exists when the settings are applied.
maya.utils.executeDeferred("import maya_blender_like; maya_blender_like.startup()")
