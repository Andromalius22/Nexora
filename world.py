import json
import uuid
import random
import os
import time
from collections import deque
from logger_setup import get_logger
from registry import REGISTRY

log = get_logger("World")

class SpaceStructure:
    def __init__(self, id, name, hp, build_cost_credits, build_cost_resources, special_ability, description):
        self.id = id
        self.name = name
        self.hp = hp
        self.build_cost_credits = build_cost_credits
        self.build_cost_resources = build_cost_resources or {}
        self.special_ability = special_ability
        self.description = description

    @classmethod
    def from_dict(cls, data):
        return cls(
            data.get('id'),
            data.get('name'),
            data.get('hp'),
            data.get('build_cost_credits'),
            data.get('build_cost_resources'),
            data.get('special_ability'),
            data.get('description')
        )


def load_space_structures(filepath="data/space_structures.json"):
    with open(filepath, "r") as f:
        data = json.load(f)
    return [SpaceStructure.from_dict(entry) for entry in data]

##############################################################################################################################

class Patent:
    def __init__(self, name, target_building_type, resource_type=None, resource_tier=None, bonus_percent=0, tier="common", discoverer=None, description=""):
        """
        :param name: Name of the patent
        :param target_building_type: Building type it affects ("mine", "industry", "refine", "farm")
        :param resource_type: Optional specific resource this patent affects (e.g., "ore", "gas", etc)
        :param resource_tier: Optional specific tier this patent affects (e.g., 1, 2, 3)
        :param bonus_percent: Percentage bonus (e.g., 580 for +580%)
        :param tier: Rarity tier
        :param discoverer: Empire/player that researched/discovered the patent
        :param description: Flavor text / tooltip
        """
        self.id = str(uuid.uuid4())
        self.name = name
        self.target_building_type = target_building_type
        self.resource_type = resource_type
        self.resource_tier = resource_tier
        self.bonus_percent = bonus_percent
        self.tier = tier
        self.discoverer = discoverer  # Only discoverer can sell
        self.owners = set()           # Empires currently "using" the patent
        self.description = description
        self.tradable = True          # Can be sold, but rules enforced in transfer

        if discoverer:
            self.grant_to(discoverer)

    # --- Apply bonus ---
    def apply_bonus(self, base_output, resource_type=None, resource_tier=None):
        """
        Apply the patent bonus only if the resource type and tier match.
        """
        if self.resource_type and self.resource_type != resource_type:
            return base_output
        if self.resource_tier and self.resource_tier != resource_tier:
            return base_output
        return base_output * (1 + self.bonus_percent / 100)

    # --- Grant usage to an empire ---
    def grant_to(self, empire):
        self.owners.add(empire)

    # --- Transfer ownership (sale) ---
    def sell_to(self, seller, buyer):
        """
        Sell the patent to buyer. Only the discoverer can sell.
        Buyer can use the patent but cannot sell it.
        """
        if seller != self.discoverer:
            raise ValueError(f"Only the discoverer ({self.discoverer}) can sell this patent.")
        self.grant_to(buyer)
        print(f"{seller} sold {self.name} to {buyer} (buyer cannot resell).")

    def is_usable_by(self, empire):
        return empire in self.owners or empire == self.discoverer

    def __repr__(self):
        return f"<Patent {self.name} ({self.target_building_type}) +{self.bonus_percent}% [{self.tier}]>"
    
    @staticmethod
    def generate_random(target_building_type, discoverer=None, resource_type=None, resource_tier=None):
        tiers = ["common", "uncommon", "rare", "legendary"]
        tier_weights = [0.5, 0.3, 0.15, 0.05]

        tier = random.choices(tiers, weights=tier_weights, k=1)[0]
        bonus_ranges = {
            "common": (10, 50),
            "uncommon": (50, 150),
            "rare": (150, 350),
            "legendary": (350, 800)
        }
        bonus = random.randint(*bonus_ranges[tier])
        name = f"{tier.title()} {target_building_type.title()} Patent"
        description = f"Increases {target_building_type} output by {bonus}%"
        return Patent(name=name, target_building_type=target_building_type,
                      resource_type=resource_type, resource_tier=resource_tier,
                      bonus_percent=bonus, tier=tier, discoverer=discoverer,
                      description=description)
    
    def __repr__(self):
        resource_str = ""
        if self.resource_type:
            resource_str = f" ({self.resource_type}"
            if self.resource_tier:
                resource_str += f" T{self.resource_tier}"
            resource_str += ")"
        return f"<Patent {self.name}{resource_str} +{self.bonus_percent}% [{self.tier}]>"

##############################################################################################################################

class Building:
    def __init__(self, key, name, cost, description, type_, slot_type,
                 resource_bonus=None, maintenance_cost=None,
                 defense_bonus=0.0, production_points=0,
                 construction_priority=0, base_yield=1, max_per_planet=0, unique=False,
                 tags=[]):
        self.key = key  # internal identifier, e.g., "farm"
        self.name = name
        self.cost = cost
        self.description = description
        self.type = type_
        self.slot_type = slot_type
        self.resource_bonus = resource_bonus or {}
        self.maintenance_cost = maintenance_cost or {}
        self.defense_bonus = defense_bonus
        self.production_points = production_points
        self.construction_priority = construction_priority
        self.base_yield = base_yield
        self.max_per_planet = max_per_planet
        self.unique = unique
        self.tags = tags

        # Dynamic / runtime fields
        self.under_construction = False
        self.remaining_build_points = 0  # to calculate progress

    def start_construction(self, planet_industry_points):
        """
        Begin construction on a planet.
        :param planet_industry_points: number of industry points per turn available on the planet
        """
        if planet_industry_points <= 0:
            raise ValueError("Planet must have at least 1 industry point to build.")
        # Build time dynamically calculated as industry cost divided by planet industry points
        self.remaining_build_points = self.cost.get("industry", 0)
        self.under_construction = True

    def progress_construction(self, planet_industry_points):
        """
        Apply planet's industry points to construction.
        Returns True if construction finished this turn.
        """
        if not self.under_construction:
            return False
        self.remaining_build_points -= planet_industry_points
        if self.remaining_build_points <= 0:
            self.under_construction = False
            self.remaining_build_points = 0
            return True
        return False

    def __repr__(self):
        status = "Under Construction" if self.under_construction else "Completed"
        return f"<Building {self.name} ({self.slot_type}) - {status}>"

class BuildingManager:
    def __init__(self):
        # No need to load JSON; use the registry
        self.buildings_data = REGISTRY.get("buildings", {})

    def create_building(self, key):
        """
        Instantiate a Building object from the registry by key (id).
        """
        data = self.buildings_data.get(key)
        if not data:
            log.error(f"[BuildingManager] Building '{key}' not found in registry")
            return None

        return Building(
            key=key,
            name=data["name"],
            cost=data.get("cost", {}),
            description=data.get("description", ""),
            type_=data.get("type", ""),
            slot_type=data.get("slot_type", ""),
            resource_bonus=data.get("resource_bonus", {}),
            maintenance_cost=data.get("upkeep", {}),
            defense_bonus=data.get("defense_value", 0.0),
            production_points=data.get("production_points", 0),
            construction_priority=data.get("construction_priority", 0),
            base_yield=data.get("base_yield", 1),
            max_per_planet=data.get("max_per_planet", 0),
            unique=data.get("unique", False),
            tags=data.get("tags", [])
        )


    def list_buildings(self):
        """
        Return a list of all building keys available.
        """
        return list(self.buildings_data.keys())

    def create_all_buildings(self):
        """
        Instantiate all buildings in JSON.
        """
        return {key: self.create_building(key) for key in self.buildings_data.keys()}

##############################################################################################################################

class BuildOrder:
    def __init__(self, item_name, build_time, cost, category, data, slot=None):
        self.item_name = item_name
        self.build_time = build_time
        self.cost = cost
        self.category = category  # "building" or "defense"
        self.data = data  # raw registry entry
        self.progress = 0
        self.completed = False
        self.slot = slot #Only used for category building

    def update(self, delta_time):
        self.progress += delta_time
        if self.progress >= self.build_time:
            self.completed = True
            return True
        return False


class BuildQueue:
    def __init__(self):
        self.queue = []

    def add_order(self, order: BuildOrder):
        self.queue.append(order)

    def update(self, delta_time):
        """Advance the build queue and return completed item if any."""
        if not self.queue:
            return None

        current = self.queue[0]
        if current.update(delta_time):
            self.queue.pop(0)
            return current
        return None

    def get_all_orders(self):
        return self.queue