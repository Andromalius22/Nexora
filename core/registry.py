import json
import os
from core.logger_setup import get_logger

log = get_logger("Registry")

# --------------------------------------------------------------------
# Global registry container
# --------------------------------------------------------------------
REGISTRY = {
    "planets": {},
    "buildings": {},
    "defense_units": {},
    "planet_features": {},
    "resources": {},
    "offense_units": {},
    "ships": {},
    "all": {}
}

# --------------------------------------------------------------------
# Loading functions
# --------------------------------------------------------------------
def load_registry(folder_path="data/"):
    """Load all registry categories from JSON files in a folder."""
    files = {
        "buildings.json": "buildings",
        "defense_units.json": "defense_units",
        "planet_types.json": "planets",
        "planet_features.json": "planet_features",
        "resources.json": "resources",
        "offense_units.json":"offense_units",
        "ships.json":"ships"
    }

    REGISTRY["all"].clear()

    for filename, category in files.items():
        path = os.path.join(folder_path, filename)
        if not os.path.exists(path):
            log.warning(f"[Registry] Missing file: {filename}")
            continue

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError(f"{filename} must contain a list of entries, not a dict")

        for item in data:
            if "id" not in item:
                raise ValueError(f"[Registry] Entry missing 'id' in {filename}: {item}")
            REGISTRY[category][item["id"]] = item
            REGISTRY["all"][item["id"]] = item

            log.debug(f"[Registry] Loaded {item['id']} → {category}")

    validate_registry()
    log.info(f"[Registry] Loaded registry with {len(REGISTRY['all'])} total entries.")


def validate_registry():
    """Basic validation for duplicates and missing fields."""
    seen = set()
    for cat, items in REGISTRY.items():
        if cat == "all":
            continue
        for id_, entry in items.items():
            if id_ in seen:
                log.warning(f"[Registry] Duplicate ID '{id_}' across categories.")
            seen.add(id_)
            if "name" not in entry:
                log.warning(f"[Registry] {cat}:{id_} missing 'name' field.")
    log.debug("[Registry] Validation complete.")


# --------------------------------------------------------------------
# Save / export functions
# --------------------------------------------------------------------
def save_registry(folder_path="data/"):
    """Save all registry categories to JSON files."""
    os.makedirs(folder_path, exist_ok=True)

    for cat_name, table in REGISTRY.items():
        if cat_name == "all":
            continue
        file_path = os.path.join(folder_path, f"{cat_name}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(list(table.values()), f, indent=2, ensure_ascii=False)
        log.info(f"[Registry] Saved {len(table)} items to {file_path}.")


# --------------------------------------------------------------------
# Serialization helpers for network or offline sync
# --------------------------------------------------------------------
def registry_to_dict():
    """Convert global registry to a serializable dict (for network)."""
    return {
        key: table for key, table in REGISTRY.items() if key != "all"
    }


def registry_from_dict(data: dict):
    """Rebuild global REGISTRY from dict (e.g., from MsgPack or save)."""
    for key, table in data.items():
        if key not in REGISTRY:
            REGISTRY[key] = {}
        else:
            REGISTRY[key].clear()
        REGISTRY[key].update(table)

        if key != "all":  # rebuild "all" separately
            for id_, item in table.items():
                REGISTRY["all"][id_] = item
    log.info(f"[Registry] Rehydrated from network with {len(REGISTRY['all'])} entries.")


# --------------------------------------------------------------------
# Optional: Merge registry (for mods / DLC)
# --------------------------------------------------------------------
def merge_registry(extra_registry: dict):
    """Merge another registry (modded or downloaded) into the main one."""
    for cat, items in extra_registry.items():
        if cat not in REGISTRY:
            REGISTRY[cat] = {}
        for id_, entry in items.items():
            REGISTRY[cat][id_] = entry
            REGISTRY["all"][id_] = entry
    log.info("[Registry] Merged external registry data.")
