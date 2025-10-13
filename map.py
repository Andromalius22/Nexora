import math
import pygame
import config

class Hex:
    def __init__(self, q, r, s=None):
        self.q = q  # column (axial)
        self.r = r  # row (axial)
        self.s = s if s is not None else -q - r  # cube coords: q, r, s sum to 0

    def __repr__(self):
        return f"Hex(q={self.q}, r={self.r}, s={self.s})"

    def hex_to_pixel(self, center, size):
        x = size * math.sqrt(3) * (self.q + self.r/2) + center[0]
        y = size * 3/2 * self.r + center[1]
        return (x, y)

    def polygon(self, center, size):
        cx, cy = self.hex_to_pixel(center, size)
        points = []
        for i in range(6):
            angle = math.radians(60 * i - 30)
            px = cx + size * math.cos(angle)
            py = cy + size * math.sin(angle)
            points.append((px, py))
        return points

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
        # Draw borders for all hexes
        for hex in self.grid:
            points = hex.polygon(center, config.HEX_SIZE)
            pygame.draw.polygon(surface, config.LIGHT_GRAY, points, 1)

# Usage example:
# galaxy = GalaxyMap(width=10, height=10)
# print(galaxy.all_hexes())
