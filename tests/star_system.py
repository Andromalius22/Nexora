from .planet import Planet

class StarSystem:
    def __init__(self, system_id, name, num_planets=3):
        self.id = system_id
        self.name = name
        self._planet_id_counter = 0
        self.planets = []
        for i in range(num_planets):
            self.add_planet()
    
    def add_planet(self):
        planet = Planet()
        planet.id = self._planet_id_counter
        self._planet_id_counter += 1
        planet.star_system = self
        self.planets.append(planet)

    def to_dict(self):
        return {"id": self.id, "name": self.name,
                "planets": [p.to_dict() for p in self.planets]}