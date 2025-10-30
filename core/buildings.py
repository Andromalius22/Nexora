from webbrowser import get
from core.logger_setup import get_logger
from core.registry import REGISTRY

log = get_logger("Buildings")

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