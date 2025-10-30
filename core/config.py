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

SPECIAL_FEATURES = ["star_system", "nebula", "asteroid_field", "black_hole", "empty"]

# Define IDs for features and planet types for serialization
FEATURE_IDS = {
    "star_system": 0,
    "nebula": 1,
    "asteroid_field": 2,
    "black_hole": 3,
    "empty":4
}

PLANET_TYPE_IDS = {
    "barren": 1,
    "terrestrial": 2,
    "volcanic": 3,
    "hydrogen_giant": 4,
    "ionized_giant": 5,
    "quantum_giant":6,
    "oceanic":7,
    "jungle":8,
    "symbiotic":9
}

# Reverse lookup for client
FEATURE_NAMES = {v: k for k, v in FEATURE_IDS.items()}
PLANET_TYPE_NAMES = {v: k for k, v in PLANET_TYPE_IDS.items()}

PLANET_RARITY_BONUS = {
    "volcanic": 2,        # +100% max bonus
    "quantum_giant": 3.0,   # +200% max bonus
    "barren": 2,
    "hydrogen_giant": 2,
    "ionized_giant": 1.5,
    "oceanic": 1.5,
    "jungle": 1.3,
    "symbiotic": 1.4
}


PLANET_TYPE_ALLOWED = {
    "volcanic": ["metal_bars", "alloy", "quantum_alloy"],#"star_alloy"
    "quantum_giant": ["quantum_plasma", "plasma"],
    "barren": ["basaltic_ore"],
    "hydrogen_giant": ["hydrogen_gas"],
    "ionized_giant": ["fuel", "plasma"],
    "oceanic": ["water_ice"],
    "jungle": ["wetware", "genetic_gel"],
    "symbiotic": ["genetic_gel", "neural_symbionts"]  
}

SPECIAL_FEATURES = ["star_system", "nebula", "asteroid_field", "black_hole", "empty"]

DEFENSE_MODIFIER = {
    "mountainous": 1.3,  # +30% defense (hard terrain)
    "volcanic": 1.2,     # +20% due to dense crust
    "swamp": 0.8,        # -20% defense (hard to fortify)
    "oceanic": 0.9,      # slightly harder to defend
}

CLIMATE_EFFECTS = {
    "sandstorm": {"resource_yield": 0.85, "refining_speed": 1.0, "defense": 1.1},
    "drought": {"resource_yield": 0.8, "refining_speed": 1.0, "defense": 1.0},
    "dry_winds": {"resource_yield": 0.9, "defense": 1.05},

    "temperate": {"resource_yield": 1.0, "refining_speed": 1.0, "defense": 1.0},
    "seasonal_storms": {"resource_yield": 0.95, "defense": 1.1},
    "dry_spell": {"resource_yield": 0.9},

    "lava_rain": {"resource_yield": 0.9, "defense": 1.3},
    "toxic_fumes": {"refining_speed": 0.9},
    "acid_storms": {"resource_yield": 0.85, "defense": 1.2},

    "megastorms": {"resource_yield": 0.9, "defense": 1.1},
    "ion_winds": {"refining_speed": 1.1},
    "gas_turbulence": {"resource_yield": 0.8},

    "plasma_storms": {"defense": 1.3},
    "magnetic_turbulence": {"refining_speed": 0.9},

    "quantum_flux": {"resource_yield": 1.2, "refining_speed": 0.8},
    "reality_distortion": {"defense": 1.5, "resource_yield": 0.9},

    "monsoon": {"resource_yield": 1.1, "defense": 0.9},
    "hurricane_season": {"resource_yield": 0.8, "defense": 1.2},
    "calm_currents": {"resource_yield": 1.05},

    "humid": {"resource_yield": 1.1},
    "dense_fog": {"defense": 1.15, "refining_speed": 0.95},

    "biospheric_balance": {"resource_yield": 1.2, "defense": 1.0},
    "mutual_growth": {"resource_yield": 1.15},
    "spore_clouds": {"refining_speed": 0.9, "defense": 1.1},
}

REFINEMENT_YIELD_MULTIPLIERS = {
    "raw": 1.0,
    "processed": 1.25,
    "advanced": 1.5
}
