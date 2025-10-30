import json
from enum import Enum
from collections import defaultdict

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
    def __init__(self, name, layer, defense_value, upkeep, power_use=0, industry_cost=100, credit_cost=100):
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
        self.units[unit.layer].append(unit)

    def get_total_defense_value(self, layer=None):
        if layer:
            return sum(u.defense_value for u in self.units[layer])
        return sum(u.defense_value for layer_units in self.units.values() for u in layer_units)

    def get_unit_counts(self):
        """Returns a dict: {layer_name: count}"""
        return {layer.name: len(units) for layer, units in self.units.items()}

    def __repr__(self):
        return f"<PlanetDefense {self.get_unit_counts()}>"
