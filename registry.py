import json
from logger_setup import *

log = get_logger("Registry")

# Global registries
REGISTRY = {
    "planets": {},
    "buildings": {},
    "defense_units": {},
    "planet_features": {},
    "all": {}
}

def load_registry():
    load_from_file("data/buildings.json", "buildings")
    load_from_file("data/defense_units.json", "defense_units")
    load_from_file("data/planet_types.json", "planets")
    load_from_file("data/planet_features.json", "planet_features")

def load_from_file(filename, category):
    with open(filename) as f:
        data = json.load(f)
        for item in data:
            REGISTRY[category][item["id"]] = item
            REGISTRY["all"][item["id"]] = item
            log.info(f"[Registry] Loaded {item["id"]} into category {category}.")
