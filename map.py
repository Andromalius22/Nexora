import math
import pygame
import config
import random
import json
from pygame.math import Vector2
from world import *

RESOURCE_TYPES = ["ore", "gas", "liquid", "organics"]
SPECIAL_FEATURES = ["star_system", "nebula", "asteroid_field", "black_hole", "empty"]

# Load planet types from external file
with open("planet_types.json") as f:
    PLANET_TYPES = json.load(f)

# Helper: Load resource names by type
with open("resources.json") as f:
    RESOURCES_DATA = json.load(f)
RESOURCE_NAMES_BY_TYPE = {t: [name for name, data in RESOURCES_DATA.items() if data["resource_type"] == t] for t in RESOURCE_TYPES}

def random_resource():
    t = random.choice(RESOURCE_TYPES)
    return t, random.choice(RESOURCE_NAMES_BY_TYPE[t])

class Slot:
    def __init__(self, slot_type="empty", building=None):
        """
        :param slot_type: "farm", "mine", "refine", "industry" or "empty"
        :param building: Building object currently in the slot (under construction or completed)
        """
        self.type = slot_type
        self.building = building  # None if empty
        self.status = "empty" if building is None else ("under_construction" if building.under_construction else "built")

    def start_building(self, building, planet_industry_points):
        """
        Assign a building to this slot and start construction.
        """
        if self.building is not None:
            raise ValueError("Slot already has a building.")
        self.building = building
        building.start_construction(planet_industry_points)
        self.type = building.slot_type
        self.status = "under_construction"

    def progress_construction(self, planet_industry_points):
        """
        Progress the building construction. Returns True if finished this turn.
        """
        if self.building and self.building.under_construction:
            finished = self.building.progress_construction(planet_industry_points)
            if finished:
                self.status = "built"
            return finished
        return False

    def is_empty(self):
        return self.building is None

    def __repr__(self):
        return f"Slot type={self.type} status={self.status} building={self.building}"

class Planet:
    def __init__(self, name=None, star_system=None, population=None):
        self.name = name or self.generate_name()
        self.star_system = star_system

        # --- Planet type ---
        self.planet_type = self.generate_planet_type()
        planet_data = PLANET_TYPES[self.planet_type]

        self.resource_bonus = planet_data.get("resource_bonus", {})
        self.refine_bonus = planet_data.get("refine_bonus", {})
        self.name_display = planet_data.get("name", self.planet_type.title())
        self.description = planet_data.get("description", "")
        self.rarity = planet_data.get("rarity", "common")
        self.colonization_cost = planet_data.get("colonization_cost", {"credits": 100, "resources": {}})
        self.habitability = planet_data.get("habitability", 0.5)
        self.defense_bonus = planet_data.get("defense_bonus", 0.0)

        # --- Colonization / Resources ---
        self.current_resource_type = None
        self.current_resource = None
        self.mode = None  # "mine" or "refine"
        self.can_refine = False
        self.is_colonized = False

        # --- Population / Slots ---
        self.population_max = population or random.randint(1, 20)
        self.slots = [Slot() for _ in range(self.population_max)]

        # --- Industry / Defense ---
        self.industry_points = 10
        self.defense_value = 0

        # --- Construction / Patents placeholders ---
        self.resource_mined = None
        self.resource_refined = None

    # ---------------- Name / Type ----------------
    def generate_name(self):
        return f"Planet-{random.randint(1000, 9999)}"

    def generate_planet_type(self):
        weights = {}
        for planet_type, data in PLANET_TYPES.items():
            rarity = data.get("rarity", "common")
            weights_map = {"common": 0.25, "uncommon": 0.15, "rare": 0.05, "very_rare": 0.02}
            weights[planet_type] = weights_map.get(rarity, 0.1)
        return random.choices(list(weights.keys()), weights=list(weights.values()))[0]

    # ---------------- Colonization ----------------
    def colonize(self, resource_type, resource_name, mode="mine"):
        self.current_resource_type = resource_type
        self.current_resource = resource_name
        self.mode = mode
        self.can_refine = mode == "refine"
        self.is_colonized = True

    # ---------------- Slots ----------------
    def get_available_slots(self):
        return [s for s in self.slots if s.is_empty()]

    def get_used_slots(self):
        return [s for s in self.slots if not s.is_empty()]

    def start_building_in_slot(self, building_key, building_manager, planet_industry_points):
        for slot in self.get_available_slots():
            building = building_manager.create_building(building_key)
            slot.start_building(building, planet_industry_points)
            return f"Started construction: {building.name}"
        return f"No empty slot available to build {building_key.title()}"

    def progress_all_construction(self, planet_industry_points):
        finished_slots = []
        for slot in self.get_used_slots():
            if slot.progress_construction(planet_industry_points):
                finished_slots.append(slot)
        return finished_slots

    def get_active_buildings_by_type(self, building_type):
        return [s.building for s in self.slots if s.type == building_type and s.status == "built"]

    def get_total_industry_points(self):
        total = self.industry_points
        total += sum(100 for s in self.slots if s.type == "industry" and s.status == "built")
        return total

    # ---------------- Resource Extraction ----------------
    def extract_resources(self):
        if not self.is_colonized or not self.star_system:
            return 0

        owner = getattr(self.star_system.hextile, "owner", None)
        if not owner or not self.current_resource:
            return 0

        tech_level = 1.0
        total_yield = 0.0
        owner_patents = getattr(owner, "patents", [])

        # Mining Mode
        if self.mode == "mine":
            mine_count = len([s for s in self.slots if s.type == "mine" and s.status == "built"])
            if mine_count <= 0:
                return 0
            total_yield = mine_count * tech_level * self.get_resource_yield_bonus()
            total_yield = self.apply_patents(total_yield, owner_patents, target_type="mine")

            owner.resources[self.current_resource] = owner.resources.get(self.current_resource, 0) + total_yield
            self.resource_mined = self.current_resource
            return total_yield

        # Refining Mode
        elif self.mode == "refine":
            refine_count = len([s for s in self.slots if s.type == "refine" and s.status == "built"])
            if refine_count <= 0:
                return 0
            total_yield = refine_count * tech_level * self.get_refine_bonus()
            total_yield = self.apply_patents(total_yield, owner_patents, target_type="refine")

            # Consume resources and produce refined output
            with open("refined.json") as f:
                REFINED_DATA = json.load(f)
            refined_info = REFINED_DATA.get(self.current_resource)
            if not refined_info:
                print(f"[WARN] {self.current_resource} not found in refined data.")
                return 0

            input_resources = refined_info.get("resources_needed", [])
            if isinstance(input_resources, list):
                input_resources = {res: 1 for res in input_resources}

            for res_name, ratio in input_resources.items():
                required = total_yield * ratio
                if owner.resources.get(res_name, 0) < required:
                    print(f"[INFO] Not enough {res_name} to refine {self.current_resource}")
                    return 0

            for res_name, ratio in input_resources.items():
                owner.resources[res_name] -= total_yield * ratio

            owner.resources[self.current_resource] = owner.resources.get(self.current_resource, 0) + total_yield
            self.resource_refined = self.current_resource
            return total_yield

        return 0

    def apply_patents(self, yield_amount, patents, target_type):
        resource_type = RESOURCES_DATA[self.current_resource]["resource_type"]
        resource_tier = RESOURCES_DATA[self.current_resource]["tier"]
        for patent in patents:
            if patent.is_usable_by(self.star_system.hextile.owner) and patent.target_building_type == target_type:
                yield_amount = patent.apply_bonus(yield_amount, resource_type, resource_tier)
        return yield_amount

    # ---------------- Bonuses ----------------
    def get_resource_yield_bonus(self):
        if not self.is_colonized or not self.current_resource_type:
            return 1.0
        bonus_data = self.resource_bonus.get(self.current_resource_type)
        if not bonus_data:
            return 1.0
        tier = RESOURCES_DATA[self.current_resource]["tier"]
        return bonus_data["multiplier"] if tier in bonus_data["tiers"] else 1.0

    def get_refine_bonus(self):
        if not self.is_colonized or not self.current_resource_type:
            return 1.0
        bonus_data = self.refine_bonus.get(self.current_resource_type)
        if not bonus_data:
            return 1.0
        tier = RESOURCES_DATA[self.current_resource]["tier"]
        return bonus_data["multiplier"] if tier in bonus_data["tiers"] else 1.0

    # ---------------- Representations ----------------
    def __repr__(self):
        used = len(self.get_used_slots())
        total = len(self.slots)
        if not self.is_colonized:
            return f"[{self.name_display} Uncolonized], Pop={self.population_max}B, Slots={used}/{total}"
        else:
            mode_str = "Refinery" if self.can_refine else "Mine"
            return f"[{self.name_display} {mode_str}: {self.current_resource}], Pop={self.population_max}B, Slots={used}/{total}"


class StarSystem:
    def __init__(self, hextile=None):
        self.name = self.generate_name()
        self.hextile=hextile
        self.planets = [Planet(star_system=self) for _ in range(random.randint(1,4))] # 1-4 planets
    def generate_name(self):
        return "System-"+str(random.randint(100,999))
    def __repr__(self):
        return f"{self.name}: {self.planets}"

class Hex:
    def __init__(self, q, r, s=None, weights=None, owner=None):
        self.q = q  # column (axial)
        self.r = r  # row (axial)
        self.s = s if s is not None else -q - r  # cube coords: q, r, s sum to 0
        self._feature_weights = weights
        self.owner=owner #Empire class
        self.feature, self.contents = self.generate_feature()
    def generate_feature(self):
        if self._feature_weights is None:
            weights = [0.3, 0.12, 0.14, 0.04, 0.1] # 30% system, 12% nebula, etc.
        else:
            weights = self._feature_weights
        feature = random.choices(
            SPECIAL_FEATURES,
            weights=weights,
        )[0]
        if feature == "star_system":
            return feature, StarSystem(hextile=self)
        else:
            return feature, None  # Could make Nebula, AsteroidField, BlackHole classes later
    def __repr__(self):
        return f"Hex(q={self.q}, r={self.r}, feat={self.feature}, contents={self.contents})"
    def hex_to_pixel(self, center, size, cam_offset=(0,0)):
        x = size * math.sqrt(3) * (self.q + self.r/2) + center[0] + cam_offset[0]
        y = size * 3/2 * self.r + center[1] + cam_offset[1]
        return (x, y)

    def polygon(self, center, size, cam_offset=(0,0)):
        cx, cy = self.hex_to_pixel(center, size, cam_offset)
        points = []
        for i in range(6):
            angle = math.radians(60 * i - 30)
            px = cx + size * math.cos(angle)
            py = cy + size * math.sin(angle)
            points.append((px, py))
        return points

    def contains_point(self, point, origin, pixel_offset=(0, 0)):
        poly = [Vector2(c) for c in self.polygon(origin, config.HEX_SIZE, cam_offset=pixel_offset)]
        p = Vector2(point)

        # Use ray casting algorithm
        inside = False
        j = len(poly) - 1
        for i in range(len(poly)):
            if ((poly[i].y > p.y) != (poly[j].y > p.y)) and \
            (p.x < (poly[j].x - poly[i].x) * (p.y - poly[i].y) / (poly[j].y - poly[i].y) + poly[i].x):
                inside = not inside
            j = i
        return inside

class GalaxyMap:
    """
    Generates a 2D hex grid for a galaxy map using pointy-topped axial coordinates.
    """
    def __init__(self, width, height, star_density=50, nebula_density=20):
        self.width = width  # columns (q)
        self.height = height  # rows (r)
        self.star_density = star_density  # 0-100
        self.nebula_density = nebula_density  # 0-100
        self.grid = self._generate_hexes()

    def _feature_weights(self):
        # Base weights order aligned with SPECIAL_FEATURES
        base_star = 0.30
        base_nebula = 0.12
        base_asteroid = 0.14
        base_black_hole = 0.04
        base_empty = 0.10
        # Scale star and nebula by density factors (0.2x .. 1.2x)
        star_scale = 0.2 + (self.star_density / 100.0)
        nebula_scale = 0.2 + (self.nebula_density / 100.0)
        w_star = base_star * star_scale
        w_nebula = base_nebula * nebula_scale
        # Keep others constant but lightly reduce empty as density goes up
        density_factor = (self.star_density + self.nebula_density) / 200.0  # 0..1
        w_empty = max(0.02, base_empty * (1.0 - 0.4 * density_factor))
        return [w_star, w_nebula, base_asteroid, base_black_hole, w_empty]

    def _generate_hexes(self):
        grid = []
        weights = self._feature_weights()
        for q in range(self.width):
            q_offset = math.floor(q / 2)  # even-q vertical layout
            for r in range(-q_offset, self.height - q_offset):
                grid.append(Hex(q, r, weights=weights))
        return grid

    def get_hex(self, q, r):
        for hex in self.grid:
            if hex.q == q and hex.r == r:
                return hex
        return None

    def all_hexes(self):
        return self.grid

    def draw(self, surface, center, assets, frame_count, player, camera, current_empire):
        cam_offset = camera.get_offset() if camera else (0,0)
        print(f"[MAP] cam_offset {cam_offset}")
        # Draw borders for all hexes
        for hex in self.grid:
            points = hex.polygon(center, config.HEX_SIZE, cam_offset)
            if hex.owner == current_empire:
                # Optional: Draw a dot or color for star system centers
                if hex.feature == 'star_system':
                    star_x, star_y = hex.hex_to_pixel(center, config.HEX_SIZE, cam_offset)
                    pygame.draw.circle(surface, config.YELLOW, (int(star_x), int(star_y)), 4)
                elif hex.feature == 'nebula':
                    cx, cy = hex.hex_to_pixel(center, config.HEX_SIZE, cam_offset)
                    pygame.draw.circle(surface, config.LIGHT_BLUE, (int(cx), int(cy)), 4)
                elif hex.feature == 'asteroid_field':
                    cx, cy = hex.hex_to_pixel(center, config.HEX_SIZE, cam_offset)
                    pygame.draw.circle(surface, config.GRAY, (int(cx), int(cy)), 4)
                elif hex.feature == 'black_hole':
                    cx, cy = hex.hex_to_pixel(center, config.HEX_SIZE, cam_offset)
                    pygame.draw.circle(surface, config.BLACK, (int(cx), int(cy)), 4)
                pygame.draw.polygon(surface, current_empire.color, points, 1)
            else :
                pygame.draw.polygon(surface, config.FOG_COLOR, points)
                pygame.draw.polygon(surface, config.LIGHT_GRAY, points, 1)
        
        for hex in self.grid:
            points = hex.polygon(center, config.HEX_SIZE, cam_offset)
            if hex.owner == current_empire:
                pygame.draw.polygon(surface, current_empire.color, points, 1)
            
