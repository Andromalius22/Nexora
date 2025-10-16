class Player:
    """A player can mange multiples empires aka if he lost, he can restart with some tech learned, for instance"""
    def __init__(self):
        self.name = "Player"
        self.tech = []
        self.research = []
        self.victory_points = 0

class Empire:
    def _init__(self):
        self.name = "Empire"
        self.color = (255, 255, 0)
        self.army = []
        self.resources = []
        self.units = []