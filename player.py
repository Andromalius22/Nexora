from collections import defaultdict

class Player:
    """A player can mange multiples empires aka if he lost, he can restart with some tech learned, for instance"""
    def __init__(self):
        self.name = "Player"
        self.tech = []
        self.research = []
        self.victory_points = 0

class Empire:
    def __init__(self, player, name="Empire", color=(255, 255, 0)):
        self.player=player
        self.name = name
        self.color = color
        self.home_tile=None
        self.tiles_owned = set()
        self.army = []
        self.resources = defaultdict(float)