import uuid

class TradeRoute:
    def __init__(self, origin, destination, good, amount, route_type="commercial"):
        self.id = str(uuid.uuid4())
        self.origin = origin      # Planet
        self.destination = destination  # Planet
        self.good = good          # e.g. "food" or "consumer_goods"
        self.amount = amount      # units/turn
        self.route_type = route_type
        self.assigned_ships = []  # list of Ship
        self.efficiency = 1.0
        self.last_profit = 0.0
        self.distance = self._compute_distance()

    def _compute_distance(self):
        """Roughly calculate distance or use map distance."""
        if hasattr(self.origin, "pos") and hasattr(self.destination, "pos"):
            dx = self.origin.pos[0] - self.destination.pos[0]
            dy = self.origin.pos[1] - self.destination.pos[1]
            return (dx**2 + dy**2) ** 0.5
        return 1.0  # fallback

    def update_efficiency(self):
        """Compute efficiency based on ships, distance, and possible modifiers."""
        total_capacity = sum(ship.capacity for ship in self.assigned_ships)
        required_capacity = self.amount * self.distance * 0.1
        capacity_ratio = min(total_capacity / required_capacity, 1.0)
        distance_factor = max(0.1, 1.0 - (self.distance / 1000.0))
        self.efficiency = capacity_ratio * distance_factor

    def calculate_profit(self):
        """Estimate per-turn profit or value."""
        base_value = 10  # could depend on good type
        self.last_profit = base_value * self.amount * self.efficiency
        return self.last_profit

class TradeManager:
    def __init__(self):
        self.routes = {}  # id -> TradeRoute

    def add_route(self, route):
        self.routes[route.id] = route
        route.origin.trade_routes.append(route)
        route.destination.trade_routes.append(route)

    def remove_route(self, route_id):
        route = self.routes.pop(route_id, None)
        if not route:
            return
        if route in route.origin.trade_routes:
            route.origin.trade_routes.remove(route)
        if route in route.destination.trade_routes:
            route.destination.trade_routes.remove(route)

    def update_all_routes(self):
        """Called once per turn/tick."""
        for route in self.routes.values():
            route.update_efficiency()
            route.calculate_profit()
