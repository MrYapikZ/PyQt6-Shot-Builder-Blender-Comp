import bpy
import json
import os

JSON_PRESET_FILEPATH = $PRESETS_FILEPATH_JSON


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


import_lighting_preset(JSON_PRESET_FILEPATH)