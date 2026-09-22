"""MayaBlenderLike rig data export: what FBX leaves out of a Blender rig, as JSON for Maya.

FBX carries the skeleton and the skin, but not the rig: channel locks, rotation modes, bone
collections, bone colors, custom shapes and constraints. This add-on writes them for the active
armature (File > Export > MayaBlenderLike Rig Data), and Maya's Blender Like > Apply Blender Rig
Data puts them on the controls of the rig converted from the same FBX.

Install: Edit > Preferences > Add-ons > Install from Disk, pick this file. Or open it in the Text
Editor and press Run Script.
"""
import json

import bpy
from bpy.props import StringProperty
from bpy_extras.io_utils import ExportHelper
from mathutils import Euler, Matrix, Vector

bl_info = {
    "name": "MayaBlenderLike Rig Data Export",
    "author": "uayten",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "File > Export > MayaBlenderLike Rig Data (.json)",
    "description": "Exports locks, rotation modes, bone collections, colors, custom shapes and constraints for Maya",
    "category": "Import-Export",
}

FORMAT_VERSION = 1
SKIPPED_PROPERTIES = {"rna_type", "name", "type", "is_valid", "is_override_data_editable", "error_location",
                      "error_rotation", "active", "show_expanded"}


def export_rig(armature, path):
    """Write the rig data of an armature object to path. Returns the data."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    data = {
        "format": FORMAT_VERSION,
        "armature": armature.name,
        "armature_scale": armature.matrix_world.to_scale()[0],
        "collections": [{"name": c.name, "visible": c.is_visible} for c in _collections(armature.data)],
        "bones": [_bone(armature, pose_bone, depsgraph) for pose_bone in armature.pose.bones],
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=1)
    return data


def _collections(armature_data):
    # Blender 4.1+ lists nested collections in collections_all; 4.0 only has collections.
    return getattr(armature_data, "collections_all", None) or armature_data.collections


def _bone(armature, pose_bone, depsgraph):
    bone = pose_bone.bone
    return {
        "name": pose_bone.name,
        "parent": bone.parent.name if bone.parent else None,
        "head": list(bone.head_local),
        "tail": list(bone.tail_local),
        "length": bone.length,
        "rotation_mode": pose_bone.rotation_mode,
        "lock_location": list(pose_bone.lock_location),
        "lock_rotation": list(pose_bone.lock_rotation),
        "lock_rotation_w": pose_bone.lock_rotation_w,
        "lock_scale": list(pose_bone.lock_scale),
        "collections": [c.name for c in bone.collections],
        "color": _color(pose_bone) or _color(bone),
        "custom_shape": _custom_shape(pose_bone, depsgraph),
        "constraints": [_constraint(c) for c in pose_bone.constraints],
    }


def _color(owner):
    """RGB (0-1) of a bone color: its theme set, or its custom color. None for the default."""
    color = getattr(owner, "color", None)
    if color is None or color.palette == "DEFAULT":
        return None
    if color.palette == "CUSTOM":
        return list(color.custom.normal)
    index = int(color.palette[-2:]) - 1
    return list(bpy.context.preferences.themes[0].bone_color_sets[index].normal)


def _custom_shape(pose_bone, depsgraph):
    """The custom shape's wire as polylines, in bone space (Y along the bone), in Blender units."""
    shape = pose_bone.custom_shape
    if shape is None:
        return None
    evaluated = shape.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        scale = Vector(pose_bone.custom_shape_scale_xyz)
        if pose_bone.use_custom_shape_bone_size:
            scale *= pose_bone.bone.length
        placement = Matrix.LocRotScale(Vector(pose_bone.custom_shape_translation),
                                       Euler(pose_bone.custom_shape_rotation_euler), scale)
        points = [placement @ v.co for v in mesh.vertices]
        curves = [[list(points[i]) for i in path] for path in _polylines(mesh)]
    finally:
        evaluated.to_mesh_clear()
    return {"object": shape.name, "curves": curves,
            "override_transform": pose_bone.custom_shape_transform.name if pose_bone.custom_shape_transform else None}


def _polylines(mesh):
    """Mesh edges chained into as few open or closed paths as possible (vertex index lists)."""
    neighbours = {}
    for edge in mesh.edges:
        a, b = edge.vertices
        neighbours.setdefault(a, []).append(b)
        neighbours.setdefault(b, []).append(a)
    unused = {tuple(sorted(edge.vertices)) for edge in mesh.edges}
    paths = []
    # Open paths start at ends and branch points; what is left after them are closed loops.
    starts = [v for v, n in neighbours.items() if len(n) != 2] + list(neighbours)
    for start in starts:
        while True:
            path = [start]
            current = start
            while True:
                following = next((n for n in neighbours[current] if tuple(sorted((current, n))) in unused), None)
                if following is None:
                    break
                unused.discard(tuple(sorted((current, following))))
                path.append(following)
                current = following
            if len(path) < 2:
                break
            paths.append(path)
    return paths


def _constraint(constraint):
    """Every setting of a constraint, with object targets by name."""
    result = {"type": constraint.type, "name": constraint.name}
    for prop in constraint.bl_rna.properties:
        key = prop.identifier
        if key in SKIPPED_PROPERTIES:
            continue
        value = getattr(constraint, key)
        if prop.type == "POINTER":
            result[key] = getattr(value, "name", None) if value is not None else None
        elif prop.type == "COLLECTION":
            continue
        elif prop.type == "ENUM" and prop.is_enum_flag:
            result[key] = sorted(value)
        elif getattr(prop, "array_length", 0):
            result[key] = [list(row) if hasattr(row, "__len__") else row for row in value]
        else:
            result[key] = value
    return result


class EXPORT_OT_mayablenderlike_rig(bpy.types.Operator, ExportHelper):
    """Export the active armature's rig data (locks, collections, shapes, constraints) for MayaBlenderLike"""
    bl_idname = "export_scene.mayablenderlike_rig"
    bl_label = "Export MayaBlenderLike Rig Data"
    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == "ARMATURE"

    def execute(self, context):
        data = export_rig(context.active_object, self.filepath)
        self.report({"INFO"}, "Rig data: {} bones written".format(len(data["bones"])))
        return {"FINISHED"}


def _menu(self, context):
    self.layout.operator(EXPORT_OT_mayablenderlike_rig.bl_idname, text="MayaBlenderLike Rig Data (.json)")


def register():
    bpy.utils.register_class(EXPORT_OT_mayablenderlike_rig)
    bpy.types.TOPBAR_MT_file_export.append(_menu)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(_menu)
    bpy.utils.unregister_class(EXPORT_OT_mayablenderlike_rig)


if __name__ == "__main__":
    register()
