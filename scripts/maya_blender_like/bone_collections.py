"""Blender's bone collections as Maya selection sets.

A collection is an objectSet tagged mblBoneCollection (holding the Blender name), so it shows
in Maya's own Edit > Quick Select Sets and in the Outliner, and works without this module.
M over the viewport opens Blender's menu: move the selected bones (their controls) to a
collection, or a new one; select a collection's bones; show or hide them.
"""
import re

from maya import cmds

from . import controls

TAG = "mblBoneCollection"


def all_collections():
    """(set, Blender name) for every collection in the scene, sorted by name."""
    found = [(s, cmds.getAttr(s + "." + TAG)) for s in cmds.ls(type="objectSet") or []
             if cmds.attributeQuery(TAG, node=s, exists=True)]
    return sorted(found, key=lambda item: item[1].lower())


def create(name, rig=None, members=None):
    """A new collection; rig (the rig's top group name) keeps same-named collections of two rigs apart."""
    set_name = re.sub(r"\W", "_", "{}_{}".format(rig, name) if rig else name) + "_collection"
    collection = cmds.sets(members or [], name=set_name) if members else cmds.sets(empty=True, name=set_name)
    cmds.addAttr(collection, longName=TAG, dataType="string")
    cmds.setAttr(collection + "." + TAG, name, type="string")
    return collection


def members(collection):
    return cmds.ls(cmds.sets(collection, query=True) or [], long=True)


def assign(collection, nodes):
    if nodes:
        cmds.sets(nodes, addElement=collection)


def move(collection, nodes):
    """Blender's Move to Collection: the bones leave every other collection."""
    for other, _ in all_collections():
        if other != collection:
            present = [n for n in nodes if cmds.sets(n, isMember=other)]
            if present:
                cmds.sets(present, remove=other)
    assign(collection, nodes)


def set_visible(collection, visible):
    for node in members(collection):
        if cmds.getAttr(node + ".visibility", settable=True):
            cmds.setAttr(node + ".visibility", visible)


def is_visible(collection):
    return any(cmds.getAttr(n + ".visibility") for n in members(collection))


def selected_bones():
    """Selected controls, with joints standing for the control that drives them."""
    result = []
    for node in cmds.ls(selection=True, transforms=True, long=True) or []:
        if cmds.nodeType(node) == "joint":
            node = controls.control_of(node) or node
        if node not in result:
            result.append(node)
    return result


def menu():
    """Blender's M: move to a collection, plus selecting and showing collections."""
    from . import menus
    bones = selected_bones()
    existing = all_collections()
    entries = [("Move to  " + label, lambda c=collection: move(c, bones)) for collection, label in existing]
    entries.append(("+  New Collection...", lambda: _new_from_selection(bones)))
    if existing:
        entries += [None,
                    ("Select", [(label, lambda c=collection: cmds.select(members(c), replace=True))
                                for collection, label in existing]),
                    ("Show / Hide", [(("●  " if is_visible(collection) else "○  ") + label,
                                      lambda c=collection: set_visible(c, not is_visible(c)))
                                     for collection, label in existing])]
    menus.popup("Bone Collections", entries)


def _new_from_selection(bones):
    answer = cmds.promptDialog(title="New Bone Collection", message="Name:", text="Bones",
                               button=["OK", "Cancel"], defaultButton="OK", cancelButton="Cancel")
    name = cmds.promptDialog(query=True, text=True).strip()
    if answer != "OK" or not name:
        return
    rig = "|" + bones[0].split("|")[1] if bones else None
    collection = create(name, rig.lstrip("|") if rig else None)
    move(collection, bones)
