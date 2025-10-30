import random
import math
from pygame.math import Vector2
from core.planet import Planet
from core.galaxy.star_system import StarSystem
from core.config import *
from server.hexcordencoder import *

class Hex:
    def __init__(self, q, r, s=None, weights=None, owner=0, reserved_id=0, feature=None, contents=None, protected=False):
        self.q = q
        self.r = r
        self.s = s if s is not None else -q - r
        self.owner_id = owner
        self.protected=protected
        self.reserved_id = reserved_id

        # Server generates feature
        if feature is None:
            self._feature_weights = weights
            self.feature, self.contents = self.generate_feature()
        # Client reconstructs from server data
        else:
            self.feature = feature
            self.contents = contents

    def generate_feature(self):
        weights = self._feature_weights or [0.3, 0.12, 0.14, 0.04, 0.1]
        feature = random.choices(SPECIAL_FEATURES, weights=weights)[0]

        if feature == "star_system":
            return feature, StarSystem(hextile=self)
        else:
            return feature, None

    def contains_point(self, point, origin, pixel_offset=(0, 0)):
        poly = [Vector2(c) for c in self.polygon(origin, HEX_SIZE, cam_offset=pixel_offset)]
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

    
    # Convert to dict for sending to client
    def to_dict(self):
        return {
            "q": self.q,
            "r": self.r,
            "s": self.s,
            "feature": FEATURE_IDS[self.feature],
            "owner_id": self.owner_id,
            "contents": self.contents.to_dict() if self.contents else None,
            "protected": self.protected,
            "reserved_id": self.reserved_id
        }
    
    def to_msgpack_dict(self):
        """
        Prepare hex data for MsgPack serialization.
        Coordinates are stored as a HexCoord object for ExtType encoding.
        """
        hex_coord = HexCoord(self.q, self.r, self.s)
        return {
            "coord": hex_coord,  # MsgPack will encode this using ext_encoder
            "feature": FEATURE_IDS[self.feature],
            "owner_id": self.owner.id if self.owner else 0,
            "contents": self.contents.to_dict() if self.contents else None,
            "protected": self.protected,
            "reserved_id": self.reserved_id
        }
    
    def from_msgpack_dict(data: dict):
        """
        Reconstruct a Hex object from MsgPack data.
        Assumes `coord` is a HexCoord object (decoded via ext_decoder).
        """
        hex_obj = Hex(
            q=data['coord'].q,
            r=data['coord'].r,
            s=data['coord'].s,
            feature=FEATURE_NAMES[data['feature']],
            owner=0,  # Your method to get player object by ID : get_player_by_id(data['owner'])
            contents=Contents.from_dict(data['contents']) if data['contents'] else None
        )
        return hex_obj


    @classmethod
    def from_dict(cls, data: dict):
        """
        Reconstruct Hex from MsgPack dictionary.
        Assumes:
        - data['q'], data['r'], data['s'] are ints
        - data['feature'] is an integer ID
        - data['owner'] is an integer ID
        - data['contents'] is a dict or None
        """
        #print(f"data: {data}")
        feature_name = FEATURE_NAMES.get(data.get("feature"), "unknown")
        owner_obj = None  # get_player_by_id(data["owner"]) if data["owner"] != 0 else None

        contents_obj = None
        owner_id=data["owner_id"]
        protected=data.get("protected", False) #we use get() to prevent keyerror if packet not contain them
        reserved_id=data.get("reserved_id")


        # 1️⃣ Handle star systems
        if feature_name == "star_system" and data.get("contents"):
            planets = []

            for planet_data in data["contents"]["planets"]:
                planet = Planet.from_dict(planet_data)
                planets.append(planet)

            # ✅ Corrected parameter name: `planets`, not `planest`
            contents_obj = StarSystem(
                hextile=None,
                name=data["contents"]["name"],
                planets=planets
            )

        # 2️⃣ Construct the Hex itself
        hex = cls(
            q=data["q"],
            r=data["r"],
            s=data["s"],
            feature=feature_name,
            owner=owner_id,
            contents=contents_obj,
            protected=protected,
            reserved_id=reserved_id
        )

        # 3️⃣ Link back the StarSystem to its hextile (optional but good)
        if hex.feature == "star_system" and hex.contents:
            hex.contents.hextile = hex
            for planet in hex.contents.planets:
                planet.star_system=contents_obj

        return hex


    # Hex <-> pixel functions for GUI
    def hex_to_pixel(self, center, size=HEX_SIZE, cam_offset=(0,0)):
        x = size * math.sqrt(3) * (self.q + self.r/2) + center[0] + cam_offset[0]
        y = size * 3/2 * self.r + center[1] + cam_offset[1]
        return (x, y)

    def polygon(self, center, size=HEX_SIZE, cam_offset=(0,0)):
        cx, cy = self.hex_to_pixel(center, size, cam_offset)
        points = []
        for i in range(6):
            angle = math.radians(60 * i - 30)
            px = cx + size * math.cos(angle)
            py = cy + size * math.sin(angle)
            points.append((px, py))
        return points
