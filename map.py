import math
import pygame
import config
import random
import json
from pygame.math import Vector2

RESOURCE_TYPES = ["ore", "gas", "liquid", "organics"]
SPECIAL_FEATURES = ["star_system", "nebula", "asteroid_field", "black_hole", "empty"]

# Helper: Load resource names by type
with open("resources.json") as f:
    RESOURCES_DATA = json.load(f)
RESOURCE_NAMES_BY_TYPE = {t: [name for name, data in RESOURCES_DATA.items() if data["resource_type"] == t] for t in RESOURCE_TYPES}

def random_resource():
    t = random.choice(RESOURCE_TYPES)
    return t, random.choice(RESOURCE_NAMES_BY_TYPE[t])

class Planet:
    def __init__(self, name=None):
        self.name = name or self.generate_name()
        # 50% chance to be a mining planet, 50% refining
        self.mode = random.choice(["mine", "refine"])
        if self.mode == "mine":
            self.resource_type, self.resource = random_resource()
            self.can_refine = False
        else:
            self.resource_type, self.resource = random_resource()
            self.can_refine = True
        self.population = random.randint(1,20) # 1-20 billion for slot count and scale
        self.slots = self.population # For now, same as population

    def generate_name(self):
        # Very simple placeholder name gen
        return "Planet-" + str(random.randint(1000,9999))

    def __repr__(self):
        if self.can_refine:
            return f"[Refinery: {self.resource}], Pop={self.population}B, Slots={self.slots}"
        else:
            return f"[Mine: {self.resource}], Pop={self.population}B, Slots={self.slots}"

class StarSystem:
    def __init__(self):
        self.name = self.generate_name()
        self.planets = [Planet() for _ in range(random.randint(1,4))] # 1-4 planets
    def generate_name(self):
        return "System-"+str(random.randint(100,999))
    def __repr__(self):
        return f"{self.name}: {self.planets}"

class Hex:
    def __init__(self, q, r, s=None):
        self.q = q  # column (axial)
        self.r = r  # row (axial)
        self.s = s if s is not None else -q - r  # cube coords: q, r, s sum to 0
        self.feature, self.contents = self.generate_feature()
    def generate_feature(self):
        feature = random.choices(
            SPECIAL_FEATURES,
            weights=[0.3, 0.12, 0.14, 0.04, 0.1], # 60% system, 12% nebula, etc.
        )[0]
        if feature == "star_system":
            return feature, StarSystem()
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
    def __init__(self, width, height):
        self.width = width  # columns (q)
        self.height = height  # rows (r)
        self.grid = self._generate_hexes()

    def _generate_hexes(self):
        grid = []
        for q in range(self.width):
            q_offset = math.floor(q / 2)  # even-q vertical layout
            for r in range(-q_offset, self.height - q_offset):
                grid.append(Hex(q, r))
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
