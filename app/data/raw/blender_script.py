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

    with bpy.data.libraries.load("$ANIMATION_FILE", link=True) as (data_from, data_to):
        desired = {}
        for parent_name, prefix in $COLLECTION_LIST:
            if prefix is None:
                # Special case: CAM → link exact 'CAM' if present
                if "$CAMERA_COLLECTION" in data_from.collections:
                    desired[parent_name] = ["$CAMERA_COLLECTION"]
                    data_to.collections.append("$CAMERA_COLLECTION")
                else:
                    desired[parent_name] = []
                    print("[WARNING] '$CAMERA_COLLECTION' collection not found in library")
            else:
                # Prefix case
                names = [n for n in data_from.collections if n.startswith(prefix)]
                desired[parent_name] = names
                for n in names:
                    data_to.collections.append(n)

    for parent_name, child_names in desired.items():
        if parent_name == "$CAMERA_COLLECTION":
            # Just link CAM directly into the scene root
            for cname in child_names:
                coll = bpy.data.collections.get(cname)
                if coll and cname not in bpy.context.scene.collection.children.keys():
                    bpy.context.scene.collection.children.link(coll)
                    print(f"Linked '{cname}' directly into the scene")
        else:
            # Normal parent bucket case
            parent = parents[parent_name]

            for cname in child_names:
                # Try to find the collection by name
                col = bpy.data.collections.get(cname)
                if not col:
                    print(f"[WARNING] Expected linked collection missing: {cname}")
                    continue

                # Ensure it's from the right library
                if not (col.library and col.library.filepath == "$ANIMATION_FILE"):
                    col = next(
                        (c for c in bpy.data.collections
                         if c.name == cname and c.library and c.library.filepath == "$ANIMATION_FILE"),
                        None
                    )

                if not col:
                    print(f"[WARNING] No valid collection found for: {cname}")
                    continue

                print(f"CHILD: {col.library.filepath}")

                if cname not in parent.children.keys():
                    parent.children.link(col)
                    print(f"Added '{cname}' under '{parent_name}'")
                else:
                    print(f"'{cname}' already under '{parent_name}'")


def update_camera():
    # Update camera settings
    active_camera = bpy.context.scene.camera
    if active_camera:
        active_camera.data.dof.use_dof = False
        active_camera.data.clip_end = 1000
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

    output_node = nt.nodes.get("$OUTPUT_NODE")
    if not output_node:
        raise ValueError(f"Node '$OUTPUT_NODE' not found in scene '$SCENE_NAME' node tree.")
    output_node.base_path = "$OUTPUT_NODE_PATH"


# Execute functions
link_animation()
update_camera()
set_duration()
set_relative()
update_node()
print("All operations completed successfully.")

# Save the modified Blender file
bpy.ops.wm.save_as_mainfile(filepath="$OUTPUT_PATH")
print("File saved as: $OUTPUT_PATH")

# Quit Blender
bpy.ops.wm.quit_blender()
