from core.logger_setup import get_logger

log = get_logger("BuildQueue")

class BuildOrder:
    def __init__(self, item_name, build_time, cost, category, data, slot=None):
        self.item_name = item_name
        self.build_time = build_time
        self.cost = cost
        self.category = category  # "building" or "defense"
        self.data = data  # raw registry entry
        self.progress = 0
        self.completed = False
        self.slot = slot #Only used for category building

    def update(self, delta_time):
        self.progress += delta_time
        if self.progress >= self.build_time:
            self.completed = True
            return True
        return False


class BuildQueue:
    def __init__(self):
        self.queue = []

    def add_order(self, order: BuildOrder):
        self.queue.append(order)

    def update(self, delta_time):
        """Advance the build queue and return completed item if any."""
        if not self.queue:
            return None

        current = self.queue[0]
        if current.update(delta_time):
            self.queue.pop(0)
            return current
        return None

    def get_all_orders(self):
        return self.queue