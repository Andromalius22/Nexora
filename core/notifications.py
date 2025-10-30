import time

class NotificationManager:
    def __init__(self):
        self.queue = []

    def add(self, message, level="info", duration=3.0):
        self.queue.append({
            "message": message,
            "level": level,
            "timestamp": time.time(),
            "duration": duration
        })

    def get_visible(self):
        """Return active (non-expired) messages."""
        now = time.time()
        self.queue = [n for n in self.queue if now - n["timestamp"] < n["duration"]]
        return self.queue
