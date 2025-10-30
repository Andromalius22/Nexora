import random
from core.planet import Planet

class StarSystem:
    def __init__(self, hextile=None, name=None, planets=None):
        self.name = name or self.generate_name()
        self.hextile = hextile
        # Server generates planets if not provided
        if planets is None:
            self.planets = [Planet(star_system=self) for _ in range(random.randint(1,4))]
        else:
            self.planets = planets

    def generate_name(self):
        return "System-" + str(random.randint(100, 999))

    # Convert to dict for sending to client
    def to_dict(self):
        return {
            "name": self.name,
            "planets": [p.to_dict() for p in self.planets]
        }

    # Reconstruct from dict (client side)
    @classmethod
    def from_dict(cls, data):
        planets = [Planet.from_dict(pdata) for pdata in data.get("planets", [])]
        return cls(name=data.get("name"), planets=planets)
