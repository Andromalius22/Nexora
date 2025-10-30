import math
import uuid
import os
import json
from core.galaxy.hex import Hex
from core.logger_setup import get_logger

log = get_logger("GalaxyMap")

class GalaxyMap:
    """
    Generates a 2D hex grid for a galaxy map using pointy-topped axial coordinates.
    """
    def __init__(self, width, height, star_density=50, nebula_density=20, authoritative=False, protected=False, owner=0, *args, **kwargs):
        self.width = width
        self.height = height
        self.star_density = star_density
        self.nebula_density = nebula_density
        self.protected=protected
        self.owner = owner
        self.global_id = str(uuid.uuid4())
        if owner:
            self.owner_id = owner.id
        else:
            self.owner_id = 0
        self.grid = self._generate_hexes(owner=self.owner_id, protected=self.protected)
        self.starting_hex = None
    
    # ----------------------------------------------
    # Class-level factory for player galaxies
    # ----------------------------------------------
    @classmethod
    def generate_for_player(cls, player, width=20, height=20, star_density=50, nebula_density=20, **kwargs):
        """
        Generate a galaxy for a player, assign ownership/reservations,
        and guarantee at least one valid star_system tile as a starting point.
        """
        start_hex = None
        attempt = 0

        while start_hex is None:
            attempt += 1
            galaxy = cls(width, height, star_density, nebula_density, **kwargs)
            log.info(f"[GalaxyGen] Attempt #{attempt}: Created new galaxy for player '{player.name}'")

            for hex in galaxy.grid:
                if hex.feature == "star_system":
                    start_hex = hex
                    break

            if start_hex is None:
                log.warning("[GalaxyGen] No suitable starting hex found; retrying...")

        # Assign ownership
        for hex in galaxy.grid:
            if hex is start_hex:
                hex.owner_id = player.id
                hex.reserved_id = player.id
                for planet in hex.contents.planets:
                    planet.is_colonized=True
            else:
                hex.owner_id = 0
                hex.reserved_id = player.id

        galaxy.starting_hex = (start_hex.q, start_hex.r)
        galaxy.owner_id = player.id

        log.info(
            f"[GalaxyGen] Assigned galaxy to player '{player.name}' "
            f"(start tile at {galaxy.starting_hex}) with {len(galaxy.grid)} hexes."
        )

        return galaxy
        

    def _feature_weights(self):
        base_star, base_nebula, base_asteroid, base_black_hole, base_empty = (
            0.30, 0.12, 0.14, 0.04, 0.10
        )
        star_scale = 0.2 + (self.star_density / 100.0)
        nebula_scale = 0.2 + (self.nebula_density / 100.0)
        w_star = base_star * star_scale
        w_nebula = base_nebula * nebula_scale
        density_factor = (self.star_density + self.nebula_density) / 200.0
        w_empty = max(0.02, base_empty * (1.0 - 0.4 * density_factor))
        return [w_star, w_nebula, base_asteroid, base_black_hole, w_empty]

    def _generate_hexes(self, owner=None, protected=False):
        grid = []
        weights = self._feature_weights()
        for q in range(self.width):
            q_offset = math.floor(q / 2)
            for r in range(-q_offset, self.height - q_offset):
                grid.append(Hex(q, r, weights=weights, owner=owner, protected=protected))
        return grid

    def all_hexes(self):
        return self.grid

    def to_dict(self):
        return {
            "width": self.width,
            "height": self.height,
            "grid": [h.to_dict() for h in self.grid],
            "owner": getattr(self.owner, "id", None),
            "protected": self.protected,
        }

    @classmethod
    def from_dict(cls, data):
        width = data.get("width", 0)
        height = data.get("height", 0)
        galaxy = cls(width=width, height=height)
        galaxy.owner = data.get("owner")
        galaxy.protected = data.get("protected", False)
        galaxy.grid = [Hex.from_dict(hd) for hd in data.get("grid", data)]
        return galaxy

    
    # ===============================
    # 📦 Save galaxy to disk
    # ===============================
    def save_to_file(self, path: str):
        """
        Serialize the galaxy to a JSON file.
        """
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            data = self.to_dict()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            log.debug(f"Galaxy saved to {path} ({len(self.grid)} hexes)")
        except Exception as e:
            log.exception(f"Failed to save galaxy to {path}: {e}")

    # ===============================
    # 📥 Load galaxy from disk
    # ===============================
    @classmethod
    def from_file(cls, path: str):
        """
        Deserialize a GalaxyMap from a JSON file.
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            galaxy = cls.from_dict(data)
            log.debug(f"Galaxy loaded from {path} ({len(galaxy.grid)} hexes)")
            return galaxy
        except FileNotFoundError:
            log.warning(f"Galaxy file not found: {path}")
            return None
        except Exception as e:
            log.exception(f"Failed to load galaxy from {path}: {e}")
            return None

    def __repr__(self):
        return f"<GalaxyMap {self.width}x{self.height} ({len(self.grid)} hexes)>"
