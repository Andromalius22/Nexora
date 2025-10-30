class Ship:
    def __init__(self, ship_id, name, capacity, speed, upkeep, role="transport"):
        self.ship_id = ship_id
        self.name = name
        self.capacity = capacity
        self.speed = speed
        self.upkeep = upkeep
        self.role = role
        self.route = None  # trade route ID or object
        self.status = "idle"

