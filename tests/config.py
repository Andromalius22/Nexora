# Screen setup
WIDTH, HEIGHT = 1200, 600
GRID_RADIUS=24
HEX_SIZE=24
UI_WIDTH = 200
SCREEN_WIDTH = 1200 #in pixels
SCREEN_HEIGHT = 700 #in pixels
MAP_WIDTH = SCREEN_WIDTH - UI_WIDTH
TILE_SIZE = 8
REGION_GRID_WIDTH = MAP_WIDTH // TILE_SIZE  # 100 in tiles
REGION_GRID_HEIGHT = SCREEN_HEIGHT // TILE_SIZE  # 75
MINIMAP_WIDTH = 200
MINIMAP_HEIGHT = 200
MINIMAP_PADDING = 10

# Colors
WHITE = (255, 255, 255)
GRAY = (200, 200, 200)
DARK_GRAY = (100, 100, 100)
LIGHT_GRAY = (230, 230, 230)
BLACK = (0, 0, 0)
LIGHT_DARK = (30, 30, 30)
RED = (255, 100, 100)
BLUE = (100, 100, 255)
LIGHT_BLUE = (160, 200, 255)
GREEN = (100, 255, 100)
YELLOW = (255, 255, 0)

terrain_color = {
    "grass": (80, 200, 120),
    "forest": (34, 139, 34),
    "mountain": (120, 120, 120),
    "water": (50, 100, 255),
    "desert": (210, 180, 140),
    "snow": (240, 240, 255)
}

FOG_COLOR = (20, 20, 30)

RARITY_PROBABILITY = {
    "common": 0.15,
    "uncommon": 0.08,
    "rare": 0.03,
    "very_rare": 0.01
}

RARITY_MULTIPLIERS = {
    "common": 1.0,
    "uncommon": 0.7,
    "rare": 0.4,
    "very_rare": 0.25
}

TIER_YIELD_MULTIPLIERS = {
    1: 1.0,   # T1 → full yield
    2: 0.9,   # T2 → slightly less
    3: 0.7,   # T3 → reduced yield
    4: 0.5    # T4 → rare and slow to extract
}

