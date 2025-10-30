import json
from enum import Enum
from collections import defaultdict
from core.registry import REGISTRY
from core.logger_setup import get_logger

log = get_logger("Defense")

DEFENSE_REGISTRY = {}  # name -> dict

# Layer enum
class DefenseLayer(Enum):
    DEEP_SPACE = 1
    ORBITAL = 2
    HIGH_ALTITUDE = 3
    LOW_ALTITUDE = 4
    GROUND = 5

# Base class
class DefenseUnit:
    def __init__(self, id, name, layer, defense_value, upkeep, power_use=0, industry_cost=100, credit_cost=100):
        self.id=id
        self.name = name
        self.layer = layer
        self.defense_value = defense_value
        self.upkeep = upkeep
        self.power_use = power_use
        self.industry_cost=industry_cost
        self.credit_cost=credit_cost

# Loader function
def load_defense_units(json_file="data/defense_units.json"):
    units = []
    with open(json_file, "r") as f:
        data = json.load(f)
        for unit in data:
            layer = DefenseLayer[unit["layer"]]
            DEFENSE_REGISTRY[unit["name"]] = unit  # keep raw data for lookup
            units.append(
                DefenseUnit(
                    name=unit["name"],
                    layer=layer,
                    defense_value=unit["defense_value"],
                    upkeep=unit["upkeep"],
                    power_use=unit.get("power_use", 0),
                    industry_cost=unit.get("industry_cost", 100),
                    credit_cost=unit.get("credit_cost", 100)
                )
            )
    return units

class PlanetDefense:
    def __init__(self):
        # Dict[layer -> list of DefenseUnit]
        self.units = defaultdict(list)

    def add_unit(self, unit: DefenseUnit):
        # store ID for serialization
        self.units[unit.layer].append(unit.name)  # or unit.id if you have it
    
    def remove_unit(self, unit_id):
        for layer, unit_ids in self.units.items():
            if unit_id in unit_ids:
                unit_ids.remove(unit_id)
                return


    def get_total_defense_value(self, layer=None):
        if layer:
            return sum(REGISTRY["defense_units"][uid]["defense_value"] for uid in self.units[layer])
        return sum(
            REGISTRY["defense_units"][uid]["defense_value"]
            for unit_ids in self.units.values() for uid in unit_ids
        )

    def get_unit_counts(self):
        return {layer.name: len(ids) for layer, ids in self.units.items()}

    def to_dict(self):
        return {
            "units": {
                layer.name: [u.id if isinstance(u, DefenseUnit) else u for u in units]
                for layer, units in self.units.items()
            }
        }


    @classmethod
    def from_dict(cls, data):
        pd = cls()
        for layer_name, unit_ids in data.get("units", {}).items():
            layer = DefenseLayer[layer_name]
            for uid in unit_ids:
                unit_data = REGISTRY[uid]
                pd.units[layer].append(
                    DefenseUnit(
                        id=uid,
                        name=unit_data["name"],
                        layer=layer,
                        defense_value=unit_data["defense_value"],
                        upkeep=unit_data["upkeep"],
                        power_use=unit_data.get("power_use", 0)
                    )
                )
        return pd
