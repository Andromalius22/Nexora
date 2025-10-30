from core.logger_setup import get_logger

log = get_logger("Slot")

class Slot:
    def __init__(self, slot_type="empty", building=None):
        """
        :param slot_type: "farm", "mine", "refine", "industry", "energy", "science" or "empty"
        :param building: Building object currently in the slot (under construction or completed)
        """
        self.type = slot_type
        self.building = building  # None if empty
        self.status = "empty" if building is None else ("under_construction" if building.under_construction else "built")
        self.active = True     # new flag for active/inactive
    
    # --- Helpers ---
    def is_empty(self):
        return self.building is None
    
    def clear(self):
        """Reset this slot to empty state."""
        log.info(f"[Slot] Clearing slot ({self.type}).")
        self.building = None
        self.type = "empty"
        self.status = "empty"
        self.active = True
    
    def toggle_active(self):
        """Toggle slot active/inactive."""
        self.active = not self.active
        log.debug(f"[Slot] Slot ({self.type}) active={self.active}")

    # --- Serialization for client sync ---
    def to_dict(self):
        """
        Serialize slot state for sending to client.
        Only include minimal info needed for GUI.
        """
        return {
            "type": self.type,
            "status": self.status,
            "active": self.active,
            "has_building": self.building is not None,
            "building_name": getattr(self.building, "name", None)
        }

    @classmethod
    def from_dict(cls, data, building_lookup=None):
        """
        Deserialize slot from dict (optional building_lookup for reconstruction).
        """
        building = None
        if building_lookup and data.get("building_name"):
            building = building_lookup.get(data["building_name"])
        slot = cls(slot_type=data.get("type", "empty"), building=building)
        slot.status = data.get("status", "empty")
        slot.active = data.get("active", True)
        return slot

    def __repr__(self):
        return f"Slot(type={self.type}, status={self.status}, active={self.active}, building={self.building})"