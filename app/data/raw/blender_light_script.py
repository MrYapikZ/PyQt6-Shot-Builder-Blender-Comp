import bpy
import re
import mathutils
import os
import json

JSON_PRESET_FILEPATH = "$JSON_PRESETS_FILEPATH"
BLEND_PRESETS_FILEPATH = "$BLEND_PRESETS_FILEPATH"
CHARACTER_COLLECTION = "$CHARACTER_COLLECTION"
LIGHTING_PROPS_KEY = "$LIGHTING_PROPS_KEY"

# Open master file
bpy.ops.wm.open_mainfile(filepath="$FILEPATH")


# Utility functions for collection management
def _unlink_collection_from(parent, target):
    for child in list(parent.children):
        if child == target:
            parent.children.unlink(child)
        else:
            _unlink_collection_from(child, target)


def _force_remove_collection(name: str):
    coll = bpy.data.collections.get(name)
    if not coll:
        return
    for scene in bpy.data.scenes:
        _unlink_collection_from(scene.collection, coll)
    try:
        bpy.data.collections.remove(coll)
        print(f"Removed existing collection: {name}")
    except RuntimeError as e:
        print(f"[WARNING] Could not remove '{name}': {e}")


def ensure_parent_in_scene(name: str) -> bpy.types.Collection:
    if name != "$CAMERA_COLLECTION":
        _force_remove_collection(name)
        parent = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(parent)
        print(f"Created and linked parent collection: {name}")
        return parent


def get_empty_groups_from_collection(collection_name: str):
    coll = bpy.data.collections.get(collection_name)
    if not coll:
        raise ValueError(f"Collection '{collection_name}' not found.")

    result = []

    def recurse(c: bpy.types.Collection):
        for obj in c.objects:
            if obj.type == 'EMPTY' and obj.name.endswith("_grp"):
                result.append(obj.name)
        for child in c.children:
            recurse(child)

    recurse(coll)
    return result


# Main Fucntion
def link_animation():
    # Link the animation file
    print("Animation file:", "$ANIMATION_FILE")
    parents = {}
    for name, prefix in $COLLECTION_LIST:
        if name == "$CAMERA_COLLECTION":
            _force_remove_collection("$CAMERA_COLLECTION")
            continue
        parents[name] = ensure_parent_in_scene(name)

    desired = {}

    with bpy.data.libraries.load("$ANIMATION_FILE", link=True) as (data_from, data_to):
        for parent_name, prefix in $COLLECTION_LIST:
            if prefix is None:
                if "$CAMERA_COLLECTION" in data_from.collections:
                    desired[parent_name] = ["$CAMERA_COLLECTION"]
                else:
                    desired[parent_name] = []
                    print("[WARNING] '$CAMERA_COLLECTION' not found in library")
            else:
                names = [n for n in data_from.collections if n.startswith(prefix)]
                desired[parent_name] = names

    to_link = []
    for parent_name, names in desired.items():
        if parent_name == "$CAMERA_COLLECTION":
            continue
        to_link.extend(names)

    to_link = [n for n in to_link if n not in bpy.data.collections]

    if to_link:
        with bpy.data.libraries.load("$ANIMATION_FILE", link=True) as (data_from, data_to):
            data_to.collections = [n for n in to_link if n in data_from.collections]

    for parent_name, child_names in desired.items():
        if parent_name == "$CAMERA_COLLECTION":
            continue
        parent = parents[parent_name]
        for cname in child_names:
            col = bpy.data.collections.get(cname)
            if not col:
                print(f"[WARNING] Expected linked collection missing: {cname}")
                continue

            if not (col.library and bpy.path.abspath(col.library.filepath) == bpy.path.abspath("$ANIMATION_FILE")):
                col = next((c for c in bpy.data.collections
                            if c.name == cname and c.library and
                            bpy.path.abspath(c.library.filepath) == bpy.path.abspath("$ANIMATION_FILE")), None)
                if not col:
                    print(f"[WARNING] No valid linked collection found for: {cname}")
                    continue

            if cname not in parent.children.keys():
                parent.children.link(col)
                print(f"Linked '{cname}' under '{parent_name}'")
            else:
                pass

    link_mode = bool($METHOD)
    cam_names = desired.get("$CAMERA_COLLECTION", [])
    if cam_names:
        cam_name = cam_names[0]

        for c in [c for c in list(bpy.data.collections) if c.name == cam_name or c.name.startswith(cam_name + ".")]:
            for scene in bpy.data.scenes:
                _unlink_collection_from(scene.collection, c)
            try:
                bpy.data.collections.remove(c)
            except RuntimeError:
                pass

        try:
            bpy.data.orphans_purge(do_recursive=True)
        except Exception:
            pass

        with bpy.data.libraries.load("$ANIMATION_FILE", link=link_mode) as (data_from, data_to):
            if cam_name in data_from.collections:
                data_to.collections = [cam_name]
            else:
                print(f"[WARNING] '{cam_name}' missing in library during {'link' if link_mode else 'append'}")
                return

        found = next((c for c in bpy.data.collections
                      if (c.name == cam_name or c.name.startswith(cam_name + "."))
                      and ((link_mode and c.library) or (not link_mode and not c.library))), None)

        if not found:
            print(f"[WARNING] Failed to {'link' if link_mode else 'append'} '{cam_name}'")
            return

        if not link_mode:
            other = bpy.data.collections.get(cam_name)
            if other and other is not found:
                try:
                    bpy.data.collections.remove(other)
                except RuntimeError:
                    pass
            if found.name != cam_name:
                try:
                    found.name = cam_name
                except Exception:
                    pass

        if found.name not in bpy.context.scene.collection.children.keys():
            bpy.context.scene.collection.children.link(found)

        print(f"[CAM] {'Linked' if link_mode else 'Appended'} '{cam_name}' as "
              f"{'library' if link_mode else 'local'} collection '{found.name}'")


def update_camera():
    # Update camera settings
    scene = bpy.data.scenes['Scene']

    cam_obj = next((obj for obj in scene.objects if obj.type == 'CAMERA'), None)

    if cam_obj:
        scene.camera = cam_obj
    else:
        print("cam not found")

    active_camera = bpy.context.scene.camera
    if active_camera:
        active_camera.data.clip_end = 1000
        active_camera.data.dof.use_dof = True
        active_camera.data.dof.driver_remove("aperture_fstop")
        active_camera.data.dof.driver_remove("focus_distance")
        print(f"Camera '{active_camera.name}' settings updated: DOF disabled, clip_end set to 1000")
    else:
        print("No active camera found in the scene.")


def set_duration():
    # Set the frame range based on the scene name
    scene_data = bpy.data.scenes.get("Scene")
    scene = bpy.context.scene
    scene.frame_start = $START_FRAME
    scene.frame_end = $END_FRAME
    print(f"Frame range set to: {$START_FRAME} - {$END_FRAME}")


def set_relative():
    # Make all file paths relative
    bpy.context.preferences.filepaths.use_relative_paths = True
    bpy.ops.file.make_paths_relative()


def update_node():
    empties = get_empty_groups_from_collection("$CHARACTER_COLLECTION")
    print(f"grp empties: {empties}")

    # Get the Cryptomatte node
    scene = bpy.data.scenes.get("$SCENE_NAME")
    if not scene:
        raise ValueError(f"Scene '$SCENE_NAME' not found.")
    nt = scene.node_tree
    cryp_node = nt.nodes.get("$CRYPTO_NODE")
    print(f"CRYPTO_NODE: {cryp_node.matte_id}")
    if not cryp_node:
        raise ValueError(f"Node '$CRYPTO_NODE' not found in scene '$SCENE_NAME' node tree.")

    # Replace to matte_id
    new_ids = []
    for e in empties:
        if e not in new_ids:
            new_ids.append(e)

    cryp_node.matte_id = str(",".join(sorted(set(empties))))

    for name, path, filename in $OUTPUT_NODES:
        output_node = nt.nodes.get(name)
        if not output_node:
            raise ValueError(f"Node '{name}' not found in scene 'Scene' node tree.")

        output_node.base_path = path

        if not getattr(output_node, "file_slots", None) or len(output_node.file_slots) == 0:
            raise ValueError(f"Node '{name}' has no file slots.")

        output_node.file_slots[0].path = filename


## APPEND LIGHT
def ensure_root_child(parent_coll: bpy.types.Collection, child_coll: bpy.types.Collection):
    if child_coll.name in parent_coll.children.keys():
        return
    parent_coll.children.link(child_coll)


def unique_collection_name(base: str) -> str | None:
    if bpy.data.collections.get(base) is None:
        return base
    print(f"[WARNING] Collection '{base}' already exists. Aborting to avoid conflict.")
    return None


def object_name_with_suffix(name: str, suffix: str) -> str:
    wanted_tail = f"_{suffix}"
    if name.endswith(wanted_tail) or re.search(rf"_{re.escape(suffix)}\.\d{{3}}$$", name):
        return name

    m = re.match(r"^(.*?)(\.\d{3})$$", name)
    if m:
        core, num = m.groups()
        return f"{core}{wanted_tail}{num}"
    return f"{name}{wanted_tail}"


def unique_object_name(desired: str) -> str | None:
    if bpy.data.objects.get(desired) is None:
        return desired
    print(f"[WARNING] Object '{desired}' already exists. Aborting to avoid conflict.")
    return None


def add_suffix_to_objects_in_collection(coll: bpy.types.Collection, suffix: str, key: str) -> int:
    renamed = 0
    objs = getattr(coll, "all_objects", coll.objects)
    for obj in objs:
        old = obj.name
        wanted = object_name_with_suffix(old, suffix)
        if wanted != old:
            new_name = unique_object_name(wanted)
            if new_name is None:
                continue
            try:
                obj.name = new_name
                obj[key] = obj.name
                renamed += 1
            except Exception:
                pass
    return renamed


def _all_objects_in_collection(coll: bpy.types.Collection):
    return getattr(coll, "all_objects", coll.objects)


def _score_rig_candidate(obj: bpy.types.Object) -> int:
    score = 0
    name_l = obj.name.lower()
    if "rig" in name_l or name_l.startswith("rg") or name_l.endswith("_rig"):
        score += 2
    if obj.type == 'ARMATURE' and obj.data and len(getattr(obj.data, "bones", [])) > 0:
        score += 1
    if len(obj.keys()) > 0:
        score += 1
    return score


def find_rigs_in_collection(coll: bpy.types.Collection) -> list[bpy.types.Object]:
    return [o for o in _all_objects_in_collection(coll) if o.type == 'ARMATURE']


def pick_preferred_rig(rigs: list[bpy.types.Object]) -> bpy.types.Object | None:
    if not rigs:
        return None
    if len(rigs) == 1:
        return rigs[0]
    scored = sorted(rigs, key=_score_rig_candidate, reverse=True)
    return scored[0]


def all_objects_in_collection(coll: bpy.types.Collection):
    return getattr(coll, "all_objects", coll.objects)


def find_object_in_collection(coll: bpy.types.Collection, name: str):
    for o in all_objects_in_collection(coll):
        if o.name == name:
            return o
    return None


def find_light_root_candidate(coll: bpy.types.Collection, suffix: str):
    exact = f"light_root_{suffix}"
    obj = find_object_in_collection(coll, exact)
    if obj:
        return obj
    cands = [o for o in all_objects_in_collection(coll) if o.name.lower().startswith("light_root")]
    if len(cands) == 1:
        return cands[0]
    return None


def ensure_child_of_to_c_traj(root_obj: bpy.types.Object, rig: bpy.types.Object) -> bool:
    if rig is None or rig.type != 'ARMATURE':
        print("[WARNING] No valid rig (Armature) to constrain to.")
        return False

    pb = rig.pose.bones.get("c_traj") if rig.pose else None
    if pb is None:
        print("[WARNING] Rig has no pose bone named 'c_traj'.")
        return False

    con = None
    for c in root_obj.constraints:
        if c.type == 'CHILD_OF' and c.target == rig and c.subtarget == "c_traj":
            con = c
            break
    if con is None:
        con = root_obj.constraints.new(type='CHILD_OF')
        con.target = rig
        con.subtarget = "c_traj"

    con.inverse_matrix = mathutils.Matrix.Identity(4)
    con.influence = 1.0
    con.use_location_x = con.use_location_y = con.use_location_z = True
    con.use_rotation_x = con.use_rotation_y = con.use_rotation_z = True
    con.use_scale_x = con.use_scale_y = con.use_scale_z = True
    return True


def find_named_light(coll: bpy.types.Collection, base: str, suffix: str):
    exact = f"{base}_{suffix}"
    for o in all_objects_in_collection(coll):
        if o.type == 'LIGHT' and o.name == exact:
            return o
    cands = [o for o in all_objects_in_collection(coll)
             if o.type == 'LIGHT' and o.name.lower().startswith(base.lower())]
    return cands[0] if len(cands) == 1 else None


def ensure_shared_receiver_collection(rcv_name: str) -> bpy.types.Collection:
    rcv = bpy.data.collections.get(rcv_name) or bpy.data.collections.new(rcv_name)
    return rcv


def assign_receiver_collection_to_light(light: bpy.types.Object, rcv: bpy.types.Collection) -> bool:
    if not hasattr(light, "light_linking"):
        return False
    try:
        light.light_linking.receiver_collection = rcv
        return True
    except Exception:
        return False


def add_active_collection_to_receiver(rcv: bpy.types.Collection, active_coll: bpy.types.Collection) -> bool:
    if active_coll.name not in rcv.children.keys():
        rcv.children.link(active_coll)
        return True
    return False


def append_lighting_setup(presets_path: str, character_collection: str, key: str = "blp"):
    context = bpy.context

    if not presets_path or not presets_path.endswith(".blend"):
        print("[ERROR] Invalid presets file path.")
        return

    selected_collection = bpy.data.collections.get(character_collection)
    if not selected_collection:
        print(f"[ERROR] No collection named '{character_collection}' found.")
        return

    print(f"[INFO] Processing children of '{selected_collection.name}':")
    for child in selected_collection.children:
        print("  -", child.name)

        active_coll = child
        sel_name = active_coll.name

        rigs = find_rigs_in_collection(active_coll)
        rig = pick_preferred_rig(rigs)

        if rig is None:
            print(f"[WARNING] No rig (Armature) found under collection '{sel_name}'. Skipping.")
            continue
        else:
            try:
                bpy.ops.object.select_all(action='DESELECT')
            except Exception:
                pass
            try:
                rig.select_set(True)
                context.view_layer.objects.active = rig
            except Exception:
                pass
            print(f"[INFO] Detected rig: {rig.name} in collection '{sel_name}'.")
        rig.data.pose_position = 'REST'

        if sel_name.lower().startswith("c-"):
            suffix = sel_name[2:] or sel_name  # handle 'c-' edge-case
        else:
            print(f"[WARNING] Collection '{sel_name}' doesn't start with 'c-'. Skipping.")
            continue

        rimfill = bpy.data.collections.get("RIMFILL")
        if rimfill is None:
            rimfill = bpy.data.collections.new("RIMFILL")
            context.scene.collection.children.link(rimfill)
            print("[INFO] Created 'RIMFILL' collection.")

        try:
            with bpy.data.libraries.load(presets_path, link=False) as (data_from, data_to):
                if 'LightingSetup' in data_from.collections:
                    data_to.collections = ['LightingSetup']
                else:
                    print("[ERROR] No 'LightingSetup' collection found in the blend file.")
                    continue
        except Exception as e:
            print(f"[ERROR] Failed to load library: {e}")
            continue

        renamed_any = False
        for coll in getattr(data_to, "collections", []):
            if coll is None:
                continue

            ensure_root_child(rimfill, coll)

            target_name = unique_collection_name(f"rf-{suffix}")
            if target_name is not None:
                try:
                    coll.name = target_name
                    renamed_any = True
                    print(f"[INFO] Renamed appended collection to '{coll.name}'.")
                except Exception as e:
                    print(f"[WARNING] Could not rename appended collection: {e}")
            else:
                print("[WARNING] Skipped renaming appended collection due to name conflict.")

            # Rename all objects inside to include _<suffix>
            renamed_count = add_suffix_to_objects_in_collection(coll, suffix, key)
            if renamed_count:
                print(f"[INFO] Renamed {renamed_count} object(s) to include _{suffix}.")
            else:
                print(f"[INFO] No object names needed _{suffix} (already suffixed or none found).")

            # Constrain light_root to rig.c_traj
            light_root = find_light_root_candidate(coll, suffix)
            if light_root and rig:
                if ensure_child_of_to_c_traj(light_root, rig):
                    print(f"[INFO] Added Child Of (target: {rig.name}, bone: c_traj) to '{light_root.name}'.")
                else:
                    print(f"[WARNING] Could not complete Child Of setup for '{light_root.name}'.")
            else:
                if not light_root:
                    print(f"[WARNING] No root light found in '{coll.name}'. Expected 'light_root_{suffix}'.")
                if not rig:
                    print(f"[WARNING] No rig detected under active collection '{sel_name}'.")

            fill_light = find_named_light(coll, "l-fill", suffix)
            rim_light = find_named_light(coll, "l-rim", suffix)

            shared_rcv = ensure_shared_receiver_collection(f"LL_{suffix}")
            if not shared_rcv:
                print("[WARNING] Light Linking API not available; skipped receiver collection setup.")
            else:
                ok_fill = ok_rim = False
                if fill_light:
                    ok_fill = assign_receiver_collection_to_light(fill_light, shared_rcv)
                    print(f"[{'INFO' if ok_fill else 'WARNING'}] "
                          f"Receiver -> '{fill_light.name}' {'set' if ok_fill else 'failed'} to '{shared_rcv.name}'.")
                else:
                    print("[WARNING] Fill light not found.")

                if rim_light:
                    ok_rim = assign_receiver_collection_to_light(rim_light, shared_rcv)
                    print(f"[{'INFO' if ok_rim else 'WARNING'}] "
                          f"Receiver -> '{rim_light.name}' {'set' if ok_rim else 'failed'} to '{shared_rcv.name}'.")
                else:
                    print("[WARNING] Rim light not found.")

                if add_active_collection_to_receiver(shared_rcv, active_coll):
                    print(f"[INFO] Added '{sel_name}' to shared receiver '{shared_rcv.name}'.")
                else:
                    print(f"[INFO] '{sel_name}' already present in shared receiver '{shared_rcv.name}'.")

        if not renamed_any:
            print("[WARNING] Lighting setup appended but renaming may have failed.")

        rig.data.pose_position = 'POSE'
        print(f"[INFO] Lighting setup appended into 'RIMFILL' as 'rf-{suffix}'.")

    print("[DONE] Append/Setup pass finished.")


## APPLY PRESET
def _all_objects_in_collection(coll: bpy.types.Collection):
    return getattr(coll, "all_objects", coll.objects)


def _json_load(filepath: str):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load preset from {filepath}: {e}")
        return None


def _coerce_color(value, default=(1.0, 1.0, 1.0)):
    try:
        c = tuple(float(x) for x in value)
        return c[:3] if len(c) >= 3 else default
    except Exception:
        return default


def _coerce_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _apply_light_item_to_object(light_obj: bpy.types.Object, item: dict):
    light_data = getattr(light_obj, "data", None)
    if not light_data:
        return False

    color = _coerce_color(item.get("color", (1.0, 1.0, 1.0)))
    energy = _coerce_float(item.get("energy", 10.0))

    try:
        light_data.color = color
    except Exception as e:
        print(f"[WARNING] Could not set color for '{light_obj.name}': {e}")

    try:
        light_data.energy = energy
    except Exception as e:
        print(f"[WARNING] Could not set energy for '{light_obj.name}': {e}")

    if hasattr(light_data, "exposure"):
        try:
            light_data.exposure = _coerce_float(item.get("exposure", 0.0))
        except Exception as e:
            print(f"[WARNING] Could not set exposure for '{light_obj.name}': {e}")

    if hasattr(light_data, "shadow_jitter_overblur"):
        try:
            light_data.shadow_jitter_overblur = _coerce_float(item.get("shadow_jitter_overblur", 0.0))
        except Exception as e:
            print(f"[WARNING] Could not set shadow_jitter_overblur for '{light_obj.name}': {e}")

    return True


def import_lighting_preset(filepath: str | None = None):
    path = filepath or JSON_PRESET_FILEPATH
    if not path:
        print("[ERROR] No filepath provided for importing preset.")
        return
    else:
        path = bpy.path.abspath(path)

    print(f"[INFO] Importing lighting preset from: {path}")
    if not os.path.exists(path):
        print(f"[ERROR] File does not exist: {path}")
        return

    data = _json_load(path)
    if data is None:
        print(f"[ERROR] Failed to load preset from {path}")
        return

    applied = 0
    skipped = 0

    for entry in data:
        collection_name = entry.get("collection", "")
        preset_items = entry.get("preset", [])
        if not collection_name or not preset_items:
            continue

        collection = bpy.data.collections.get(collection_name)
        if not collection:
            print(f"[WARNING] Collection '{collection_name}' not found; skipping {len(preset_items)} item(s).")
            skipped += len(preset_items)
            continue

        for item in preset_items:
            light_name = item.get("name", "")
            if not light_name:
                skipped += 1
                continue

            light_obj = collection.objects.get(light_name)
            if not light_obj:
                light_obj = next((o for o in _all_objects_in_collection(collection) if o.name == light_name), None)

            if not light_obj or light_obj.type != 'LIGHT' or getattr(light_obj, "data", None) is None:
                skipped += 1
                continue

            if _apply_light_item_to_object(light_obj, item):
                applied += 1
            else:
                skipped += 1

    print(f"[DONE] Applied: {applied}  |  Skipped: {skipped}")


# Execute functions
link_animation()
update_camera()
set_duration()
set_relative()
update_node()

append_lighting_setup(BLEND_PRESETS_FILEPATH, CHARACTER_COLLECTION, LIGHTING_PROPS_KEY)
import_lighting_preset(JSON_PRESET_FILEPATH)
print("All operations completed successfully.")

# Save the modified Blender file
bpy.ops.wm.save_as_mainfile(filepath="$OUTPUT_PATH")
bpy.ops.wm.save_as_mainfile(filepath="$OUTPUT_PATH_PROGRESS")
print("File saved as: $OUTPUT_PATH and $OUTPUT_PATH_PROGRESS")

# Quit Blender
bpy.ops.wm.quit_blender()
