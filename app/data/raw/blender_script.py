import bpy

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

        with bpy.data.libraries.load("$ANIMATION_FILE", link=False) as (data_from, data_to):
            if cam_name in data_from.collections:
                data_to.collections = [cam_name]
            else:
                print(f"[WARNING] '{cam_name}' missing in library during append")
                return

        appended = next((c for c in bpy.data.collections if
                         not c.library and (c.name == cam_name or c.name.startswith(cam_name + "."))), None)
        if not appended:
            print(f"[WARNING] Failed to append '{cam_name}'")
            return

        other = bpy.data.collections.get(cam_name)
        if other and other is not appended:
            try:
                bpy.data.collections.remove(other)
            except RuntimeError:
                pass
        if appended.name != cam_name:
            try:
                appended.name = cam_name
            except Exception:
                pass

        if appended.name not in bpy.context.scene.collection.children.keys():
            bpy.context.scene.collection.children.link(appended)

        print(f"[CAM] Appended '{cam_name}' as local '{appended.name}' to scene root")


def update_camera():
    # Update camera settings
    active_camera = bpy.data.cameras["Dolly_Camera"]
    if active_camera:
        active_camera.clip_end = 1000
        active_camera.dof.use_dof = True
        active_camera.dof.driver_remove("aperture_fstop")
        active_camera.dof.driver_remove("focus_distance")
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


# Execute functions
link_animation()
update_camera()
set_duration()
set_relative()
update_node()
print("All operations completed successfully.")

# Save the modified Blender file
bpy.ops.wm.save_as_mainfile(filepath="$OUTPUT_PATH")
bpy.ops.wm.save_as_mainfile(filepath="$OUTPUT_PATH_PROGRESS")
print("File saved as: $OUTPUT_PATH and $OUTPUT_PATH_PROGRESS")

# Quit Blender
bpy.ops.wm.quit_blender()
