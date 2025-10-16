import math
import pygame
import config
import random
import json
from pygame.math import Vector2

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

class Planet:
    def __init__(self, name=None, star_system=None):
        self.name = name or self.generate_name()
        self.star_system=None
        # Assign planet type based on weighted probabilities
        self.planet_type = self.generate_planet_type()
        planet_data = PLANET_TYPES[self.planet_type]
        
        # Initialize planet bonuses and properties
        self.resource_bonus = planet_data.get("resource_bonus", {})
        self.refine_bonus = planet_data.get("refine_bonus", {})
        self.name_display = planet_data.get("name", self.planet_type.title())
        self.description = planet_data.get("description", "")
        self.rarity = planet_data.get("rarity", "common")
        self.icon_path = planet_data.get("icon", "assets/resources/question.png")
        self.colonization_cost = planet_data.get("colonization_cost", {"credits": 100, "resources": {}})
        self.habitability = planet_data.get("habitability", 0.5)
        self.defense_bonus = planet_data.get("defense_bonus", 0.0)
        
        # Planet starts uncolonized - no resource assigned yet
        self.current_resource_type = None
        self.current_resource = None
        self.mode = None  # "mine" or "refine"
        self.can_refine = False
        self.is_colonized = False       
        
        self.population = random.randint(1,20) # 1-20 billion for slot count and scale
        self.slots = self.population # For now, same as population
        self.used_slots=0
        # Basic planet management fields
        self.buildings = {"farm": 0, "mine": 0, "industry": 0, "forge": 0}
        self.defense_value = 0

    def generate_name(self):
        # Very simple placeholder name gen
        return "Planet-" + str(random.randint(1000,9999))
    
    def generate_planet_type(self):
        """Generate planet type with weighted probabilities based on rarity."""
        weights = {}
        for planet_type, data in PLANET_TYPES.items():
            rarity = data.get("rarity", "common")
            if rarity == "common":
                weights[planet_type] = 0.25
            elif rarity == "uncommon":
                weights[planet_type] = 0.15
            elif rarity == "rare":
                weights[planet_type] = 0.05
            elif rarity == "very_rare":
                weights[planet_type] = 0.02
            else:
                weights[planet_type] = 0.1  # Default
        
        return random.choices(list(weights.keys()), weights=list(weights.values()))[0]
    
    def colonize(self, resource_type, resource_name, mode="mine"):
        """Colonize the planet and assign it to mine/refine a specific resource."""
        self.current_resource_type = resource_type
        self.current_resource = resource_name
        self.mode = mode
        self.can_refine = (mode == "refine")
        self.is_colonized = True
    
    def get_preferred_resources(self):
        """Get the list of resources this planet type is optimized for."""
        preferred_resources = []
        if self.resource_bonus:
            for resource_type, bonus_data in self.resource_bonus.items():
                preferred_tiers = bonus_data["tiers"]
                tier_resources = [name for name, data in RESOURCES_DATA.items() 
                                if data["resource_type"] == resource_type and data["tier"] in preferred_tiers]
                preferred_resources.extend(tier_resources)
        return preferred_resources
    
    def get_resource_yield_bonus(self):
        """Get the resource yield bonus for this planet's current resource type and tier."""
        if not self.is_colonized or not self.current_resource_type:
            return 1.0
            
        if self.current_resource_type in self.resource_bonus:
            bonus_data = self.resource_bonus[self.current_resource_type]
            resource_tier = RESOURCES_DATA[self.current_resource]["tier"]
            if resource_tier in bonus_data["tiers"]:
                return bonus_data["multiplier"]
        return 1.0
    
    def get_refine_bonus(self):
        """Get the refining bonus for this planet's current resource type and tier."""
        if not self.is_colonized or not self.current_resource_type:
            return 1.0
            
        if self.current_resource_type in self.refine_bonus:
            bonus_data = self.refine_bonus[self.current_resource_type]
            resource_tier = RESOURCES_DATA[self.current_resource]["tier"]
            if resource_tier in bonus_data["tiers"]:
                return bonus_data["multiplier"]
        return 1.0

    def add_used_slot(self):
        """Add a used slot if there's space available. Returns True if successful, False otherwise."""
        if self.used_slots < self.slots:
            self.used_slots += 1
            return True
        return False
    
    def remove_used_slot(self):
        """Remove a used slot if there are any. Returns True if successful, False otherwise."""
        if self.used_slots > 0:
            self.used_slots -= 1
            return True
        return False
    
    def get_available_slots(self):
        """Return the number of available slots."""
        return self.slots - self.used_slots

    def __repr__(self):
        if not self.is_colonized:
            return f"[{self.name_display} Uncolonized], Pop={self.population}B, Slots={self.used_slots}/{self.slots}"
        else:
            mode_str = "Refinery" if self.can_refine else "Mine"
            return f"[{self.name_display} {mode_str}: {self.current_resource}], Pop={self.population}B, Slots={self.used_slots}/{self.slots}"

    def extract_resources(self):
        """Extract or refine resources depending on planet mode."""
        with open("refined.json") as f:
            REFINED_DATA = json.load(f)
        if not self.is_colonized or not self.star_system:
            return 0

        owner = getattr(self.star_system.hextile, "owner", None)
        if not owner:
            return 0

        tech_level = 1.0  # For future scaling
        total_yield = 0.0

        # --- MINING MODE ---
        if self.mode == "mine" and self.current_resource:
            mine_count = self.buildings.get("mine", 0)
            if mine_count <= 0:
                return 0

            base_yield = mine_count * tech_level
            bonus = self.get_resource_yield_bonus()
            total_yield = base_yield * bonus

            owner.resources[self.current_resource] = (
                owner.resources.get(self.current_resource, 0) + total_yield
            )
            self.resource_mined = self.current_resource
            return total_yield

        # --- REFINING MODE ---
        elif self.mode == "refine" and self.current_resource:
            industry_count = self.buildings.get("industry", 0)
            if industry_count <= 0:
                return 0

            base_yield = industry_count * tech_level
            bonus = self.get_refine_bonus()
            total_yield = base_yield * bonus

            # Fetch refined material data
            refined_info = REFINED_DATA.get(self.current_resource)
            if not refined_info:
                print(f"[WARN] {self.current_resource} not found in refined data.")
                return 0

            # Check if required input resources exist and are available
            input_resources = refined_info.get("resources_needed", [])
            can_refine = True
            for res in input_resources:
                if owner.resources.get(res, 0) < total_yield:
                    can_refine = False
                    break

            if not can_refine:
                print(f"[INFO] Not enough input materials to refine {self.current_resource}.")
                return 0

            # Consume input resources
            for res in input_resources:
                owner.resources[res] -= total_yield

            # Add refined product
            owner.resources[self.current_resource] = (
                owner.resources.get(self.current_resource, 0) + total_yield
            )

            self.resource_refined = self.current_resource
            return total_yield

        return 0

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

    def draw(self, surface, center, assets, frame_count, player, camera):
        cam_offset = camera.get_offset() if camera else (0,0)
        print(f"[MAP] cam_offset {cam_offset}")
        # Draw borders for all hexes
        for hex in self.grid:
            points = hex.polygon(center, config.HEX_SIZE, cam_offset)
            pygame.draw.polygon(surface, config.LIGHT_GRAY, points, 1)
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
