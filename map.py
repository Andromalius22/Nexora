import math
import pygame
import config
import random
import json
from pygame.math import Vector2
from world import *
from defense import *
from registry import *
from config import *

from logger_setup import *

log = get_logger("Map")

RESOURCE_TYPES = ["ore", "gas", "liquid", "organics"]
SPECIAL_FEATURES = ["star_system", "nebula", "asteroid_field", "black_hole", "empty"]

# Helper: Load resource names by type
with open("resources.json") as f:
    RESOURCES_DATA = json.load(f)
RESOURCE_NAMES_BY_TYPE = {t: [name for name, data in RESOURCES_DATA.items() if data["resource_type"] == t] for t in RESOURCE_TYPES}

def random_resource():
    t = random.choice(RESOURCE_TYPES)
    return t, random.choice(RESOURCE_NAMES_BY_TYPE[t])

class Slot:
    def __init__(self, slot_type="empty", building=None):
        """
        :param slot_type: "farm", "mine", "refine", "industry", "energy" or "empty"
        :param building: Building object currently in the slot (under construction or completed)
        """
        self.type = slot_type
        self.building = building  # None if empty
        self.status = "empty" if building is None else ("under_construction" if building.under_construction else "built")
        self.active = True     # new flag for active/inactive

    def start_building(self, building, planet_industry_points):
        """
        Assign a building to this slot and start construction.
        """
        if self.building is not None:
            raise ValueError("Slot already has a building.")
        self.building = building
        building.start_construction(planet_industry_points)
        self.type = building.slot_type
        self.status = "under_construction"

    def progress_construction(self, planet_industry_points):
        """
        Progress the building construction. Returns True if finished this turn.
        """
        if self.building and self.building.under_construction:
            finished = self.building.progress_construction(planet_industry_points)
            if finished:
                self.status = "built"
            return finished
        return False

    def is_empty(self):
        return self.building is None
    
    def clear(self):
        """Reset this slot to empty state."""
        self.building = None
        self.type = "empty"
        self.status = "empty"


    def __repr__(self):
        return f"Slot type={self.type} status={self.status} building={self.building}"

class Planet:
    def __init__(self, name=None, star_system=None, population=None):
        self.name = name or self.generate_name()
        self.star_system = star_system

        # --- Planet type ---
        self.planet_type_id = self.generate_planet_type()
        self.planet_type = REGISTRY["planets"][self.planet_type_id]

        self.bonuses = self.planet_type.get("bonuses", {})
        self.resource_bonus = self.bonuses.get("resource", {})
        self.refine_bonus = self.bonuses.get("refining", {})
        self.defense_bonus = self.bonuses.get("defense", {})
        self.name_display = self.planet_type.get("name", self.planet_type_id.title())
        self.description = self.planet_type.get("description", "")
        self.rarity = self.planet_type.get("rarity", "common")
        self.colonization_cost = self.planet_type.get("colonization_cost", {"credits": 100, "resources": {}})
        self.habitability = self.planet_type.get("habitability", 0.5)

        # --- Colonization / Resources ---
        self.current_resource_type = None
        self.current_resource = None
        self.mode = None  # "mine" or "refine"
        self.can_refine = False
        self.is_colonized = False

        # --- Population / Slots ---
        self.population_max = population or random.randint(1, 20)
        self.slots = [Slot() for _ in range(self.population_max)]

        # --- Industry / Defense ---
        self.industry_points = 1000
        self.defense = PlanetDefense()
        self.defense_value = 0

        # --- Construction / Patents placeholders ---
        self.resource_mined = None
        self.resource_refined = None

        # --- Build Queue ---
        self.build_queue = BuildQueue()

        # --- Statistics ---
        self.statistics = {
            "mine": 0.0,
            "refine": 0.0,
            "farm": 0.0,
            "industry": 0.0,
            "energy": 0.0
        }
        self._last_cache_signature = None  # for detecting slot/mode changes
        self._resource_cache = {
            "main": 0.0,
            "farm": 0.0,
            "total": 0.0,
        }

        self._cache_signatures = {
            "main": None,
            "farm": None,
        }



    # ---------------- Name / Type ----------------
    def generate_name(self):
        return f"Planet-{random.randint(1000, 9999)}"

    def generate_planet_type(self):
        planets = REGISTRY.get("planets", {})
        # Safety: make sure registry actually has entries
        if not planets:
            log.error("[Planet] No planet types loaded in REGISTRY['planets']!")
            # fallback to a generic terrestrial world
            return "terrestrial"

        weights = {}
        weights_map = {
            "common": 0.25,
            "uncommon": 0.15,
            "rare": 0.05,
            "very_rare": 0.02
        }

        for planet_type_id, data in planets.items():
            rarity = data.get("rarity", "common").lower()
            weights[planet_type_id] = weights_map.get(rarity, 0.1)

        # Safety: filter out any invalid or zero weights
        valid_items = [(pid, w) for pid, w in weights.items() if w > 0]

        if not valid_items:
            log.error("[Planet] No valid planet type weights found — using fallback.")
            return "terrestrial"

        # Unzip into two lists for random.choices
        planet_ids, probs = zip(*valid_items)
        return random.choices(planet_ids, weights=probs, k=1)[0]
    
    # ---------------- Feature Helpers ----------------
    def get_features_for_type(self):
        return [
            f for f in REGISTRY["planet_features"].values()
            if f["planet_type"] == self.planet_type_id
        ]

    def assign_features(self, min_features=1, max_features=3, allow_negative=True):
        available_features = self.get_features_for_type()
        if not available_features:
            return
        if not allow_negative:
            available_features = [
                f for f in available_features
                if not any(k.endswith("_penalty") for k in f.get("effects", {}))
            ]

        feature_count = random.randint(min_features, max_features)
        self.features = random.sample(available_features, k=min(feature_count, len(available_features)))

    def apply_feature_effects(self):
        for f in self.features:
            for stat, value in f.get("effects", {}).items():
                if hasattr(self, stat):
                    setattr(self, stat, getattr(self, stat) + value)
                else:
                    self.dynamic_effects[stat] = self.dynamic_effects.get(stat, 0) + value

    # ---------------- Debug ----------------
    def describe(self):
        print(f"Planet type: {self.name_display}")
        for f in self.features:
            print(f"- {f['name']}: {f['description']}")

    # ---------------- Colonization ----------------
    def colonize(self, resource_type, resource_name, mode="mine"):
        self.current_resource_type = resource_type
        self.current_resource = resource_name
        self.mode = mode
        self.can_refine = mode == "refine"
        self.is_colonized = True

    # ---------------- Slots ----------------
    def get_available_slots(self):
        """
        Returns a list of free slots ready for construction.
        """
        available = []
        for slot in self.slots:
                # Skip occupied or under-construction slots
                if not slot.is_empty() or slot.status in ("under_construction", "built"):
                    continue
                available.append(slot)
        return available

    def get_used_slots(self):
        return [s for s in self.slots if not s.is_empty()]
    
    def remove_building_from_slot(self, building_type=None):
        """
        Removes one building (the first found) of the given type and frees its slot.
        If no type is given, removes the first non-empty slot.
        Returns a status message.
        """
        for slot in self.slots:
            # Skip empty slots
            if slot.is_empty():
                continue
            
            # Check if we match the desired building type (if specified)
            if building_type is None or slot.type == building_type:
                removed_building_name = getattr(slot.building, "name", slot.type)
                slot.clear()  # Or slot.free(), depending on your Slot API
                return f"Removed {removed_building_name} and freed one {slot.type} slot."
        
        # Nothing to remove
        if building_type:
            return f"No {building_type} building found to remove."
        else:
            return "No building found to remove."


    def get_active_buildings_by_type(self, building_type):
        return [s.building for s in self.slots if s.type == building_type and s.status == "built"]

    def get_total_industry_points(self):
        total = self.industry_points
        total += sum(100 for s in self.slots if s.type == "industry" and s.status == "built")
        return total
    
    def get_active_buildings_by_type(self, building_type):
        return [
            s.building for s in self.slots
            if s.type == building_type and s.status == "built" and s.active
        ]

    # ---------------- Resource Extraction ----------------
    def extract_resources(self, force_recompute=False):
        if not self.is_colonized or not self.star_system:
            return 0, 0

        owner = getattr(self.star_system.hextile, "owner", None)
        if not owner:
            return 0, 0
        
        # Ensure resource structures exist
        self._resource_cache = getattr(self, "_resource_cache", {"main": 0.0, "farm": 0.0, "total": 0.0})
        self._cache_signatures = getattr(self, "_cache_signatures", {"main": None, "farm": None})
        self.statistics = getattr(self, "statistics", {"mine": 0.0, "refine": 0.0, "farm": 0.0})
        
        tech_level = 1.0
        owner_patents = getattr(owner, "patents", [])
        total_yield_main = 0.0
        total_yield_farm = 0.0

        base_yield = next((s.building.base_yield for s in self.slots if s.type == "mine"), 0)
        tier_multiplier = TIER_YIELD_MULTIPLIERS.get(RESOURCES_DATA.get(self.current_resource, {}).get("tier", 1), 1.0)

        #we compute farm output first
        # -----------------------------------------------
        # 1. FARMING — always active but cached separately
        # ----------------------------------------------- 
        farm_signature = self._get_farm_signature()
        if not force_recompute and farm_signature == self._cache_signatures["farm"]:
            total_yield_farm = self._resource_cache["farm"]
        else :
            farm_count = len([s for s in self.slots if s.type == "farm" and s.status == "built" and s.active])
            if farm_count > 0:

                # Base yield per farm slot (you can define this elsewhere)
                base_yield = next((s.building.base_yield for s in self.slots if s.type == "farm"), 1)
                total_yield_farm = farm_count * base_yield * tech_level
                total_yield_farm = self.apply_patents(total_yield_farm, owner_patents, target_type="organics")

                #later add farm tier ?

                #basic funtion for now
                farm_resource = "Organifera"
                owner.resources[farm_resource] = owner.resources.get(farm_resource, 0) + total_yield_farm
                self.resource_farmed = farm_resource
                self.statistics["farm"] = total_yield_farm
            else :
                #No farms active
                total_yield_farm = 0
                self.statistics["farm"] = total_yield_farm
            self._resource_cache["farm"] = total_yield_farm
            self._cache_signatures["farm"] = farm_signature
        # ---------------------------
        # 2. MAIN MODE (mine/refine)
        # ---------------------------
        main_signature = self._get_main_signature()
        if not force_recompute and main_signature == self._cache_signatures["main"]:
            total_yield_main = self._resource_cache["main"]
        else :
            if self.mode == "mine":
                mine_count = len([s for s in self.slots if s.type == "mine" and s.status == "built"])
                if mine_count > 0:
                    total_yield_main = mine_count * tech_level * self.get_resource_yield_bonus() * base_yield * tier_multiplier
                    total_yield_main = self.apply_patents(total_yield_main, owner_patents, target_type="mine")

                    owner.resources[self.current_resource] = owner.resources.get(self.current_resource, 0) + total_yield_main
                    self.resource_mined = self.current_resource
                    # Cache and record statistics
                    self.statistics["mine"] = total_yield_main
                    #return total_yield

            # Refining Mode
            elif self.mode == "refine":
                refine_count = len([s for s in self.slots if s.type == "refine" and s.status == "built"])
                if refine_count > 0:
                    total_yield_main = refine_count * tech_level * self.get_refine_bonus()
                    total_yield_main = self.apply_patents(total_yield_main, owner_patents, target_type="refine")

                    # Consume resources and produce refined output
                    with open("refined.json") as f:
                        REFINED_DATA = json.load(f)
                    refined_info = REFINED_DATA.get(self.current_resource)
                    if not refined_info:
                        log.warning(f"{self.current_resource} not found in refined data.")
                    
                    else :

                        input_resources = refined_info.get("resources_needed", [])
                        if isinstance(input_resources, list):
                            input_resources = {res: 1 for res in input_resources}

                        for res_name, ratio in input_resources.items():
                            required = total_yield_main * ratio
                            if owner.resources.get(res_name, 0) < required:
                                total_yield_main = 0 
                                log.info(f"Not enough {res_name} to refine {self.current_resource}")
                                break

                        for res_name, ratio in input_resources.items():
                            owner.resources[res_name] -= total_yield_main * ratio

                        owner.resources[self.current_resource] = owner.resources.get(self.current_resource, 0) + total_yield_main
                        self.resource_refined = self.current_resource
                        self.statistics["refine"] = total_yield_main
            self._resource_cache["main"] = total_yield_main
            self._cache_signatures["main"] = main_signature


        #  ------------------------------------------
        # Combine both
        # ------------------------------------------
        total_yield = total_yield_main + total_yield_farm
        self._resource_cache["total"] = total_yield
        return total_yield_main, total_yield_farm

    def apply_patents(self, yield_amount, patents, target_type, resource_name=None):
        """
        Applies patent bonuses to a given yield amount.

        Args:
            yield_amount (float): base yield before patents
            patents (list): list of Patent objects
            target_type (str): e.g. "mine", "refine", "organics"
            resource_name (str, optional): overrides self.current_resource for special cases (e.g., farms)
        """
        # Use explicit resource if provided, otherwise fallback to planet’s current one
        res_name = resource_name or getattr(self, "current_resource", None)
        if not res_name or res_name not in RESOURCES_DATA:
            log.warning(f"apply_patents: unknown resource '{res_name}'")
            return yield_amount

        res_data = RESOURCES_DATA[res_name]
        resource_type = res_data.get("resource_type", "generic")
        resource_tier = res_data.get("tier", 1)

        for patent in patents:
            if (
                patent.is_usable_by(self.star_system.hextile.owner)
                and patent.target_building_type == target_type
            ):
                yield_amount = patent.apply_bonus(yield_amount, resource_type, resource_tier)

        return yield_amount
    
    # ---------------- Build Queue ----------------

    def start_build(self, item_id, building_manager=None):
        """Start building anything (building or defense) by ID."""
        categories_to_check = ["buildings", "defense_units"]

        data = None
        for cat in categories_to_check:
            if item_id in REGISTRY.get(cat, {}):
                data = REGISTRY[cat][item_id]
                break

        if not data:
            log.warning(f"[Planet] {self.name}: Unknown build item '{item_id}'")
            return "Unknown build item - see logs for more details"

        cost = data.get("cost", {})
        industry_cost=cost.get("industry", 1000)
        build_time=(industry_cost/self.get_total_industry_points())*60
        category = data.get("category", cat)

        log.info(f"[Planet] {self.name}: Started building {data['name']} ({category})")

        # ---------------- Buildings ----------------
        if category=="building":
            available_slots = self.get_available_slots()
            if not available_slots:
                return "No building slots available"
            # Pick the first free slot
            slot = available_slots[0]

            # Create a new building object in construction
            new_building = building_manager.create_building(data["id"])  # or key
            if new_building:
                new_building.status = "under_construction"

            # Assign to the slot
            slot.building = new_building
            slot.status = "under_construction"
            slot.type = slot.building.slot_type

            # Queue the construction
            order = BuildOrder(
                item_name=data['name'],
                build_time=build_time,
                cost=cost,
                category=category,
                data=data,
                slot=slot  # Store reference so we know where to finalize later
            )
            self.build_queue.add_order(order)
            return f"{self.name}: Queued {data['name']} for construction."
        # ---------------- Defense Units ----------------
        else :
            order = BuildOrder(
                item_name=data['name'],
                build_time=build_time,
                cost=cost,
                category=category,
                data=data
            )
            self.build_queue.add_order(order)
            return f"{self.name}: Queued {data['name']} (defense)"

    def update_build_queue(self, delta_time, notification_mgmt=None):
        completed = self.build_queue.update(delta_time)
        if completed:
            self.on_build_completed(completed, notification_mgmt)

    def on_build_completed(self, order, notification_mgmt=None):
        data = order.data

        if order.category == "defense":
            layer = DefenseLayer[data["layer"].upper()]
            new_unit = DefenseUnit(
                name=data["name"],
                layer=layer,
                defense_value=data["defense_value"],
                upkeep=data["upkeep"],
                power_use=data.get("power_use", 0)
            )
            self.defense.add_unit(new_unit)
            notification_mgmt.show(f"Added {new_unit.name} to {self.name}")
            log.info(f"[Defense] Added {new_unit.name} to {self.name}")

        elif order.category == "building":
            slot = getattr(order, "slot", None)
            if slot and slot.building:
                #slot.building.complete()
                slot.status = "built"
                
                notification_mgmt.show(f"{slot.building.name} completed on {self.name}")
                log.info(f"[Building] {slot.building.name} completed on {self.name}")
            else:
                log.warning(f"[Planet] {self.name}: Build completed but slot reference missing!")

    # ---------------- Bonuses ----------------
    def get_resource_yield_bonus(self):
        # Default: no bonus
        if not self.is_colonized or not self.current_resource_type:
            return 1.0

        # Get the whole resource bonuses block safely
        resource_bonuses = self.bonuses.get("resource", {})

        # Check for a bonus matching the current resource type (e.g., "ore", "gas", etc.)
        bonus_data = resource_bonuses.get(self.current_resource_type)
        if not bonus_data:
            return 1.0

        # Determine tier of the current resource
        resource_info = RESOURCES_DATA.get(self.current_resource)
        if not resource_info:
            return 1.0

        tier = resource_info.get("tier")
        # Apply multiplier if the tier matches
        return bonus_data["multiplier"] if tier in bonus_data.get("tiers", []) else 1.0

    def get_refine_bonus(self):
        # Default: no bonus if uncolonized or no active resource
        if not self.is_colonized or not self.current_resource_type:
            return 1.0

        # Access refining bonuses safely
        refining_bonuses = self.bonuses.get("refining", {})

        # Get bonus data for this resource type (e.g., "biomass", "ore", etc.)
        bonus_data = refining_bonuses.get(self.current_resource_type)
        if not bonus_data:
            return 1.0

        # Retrieve resource tier safely
        resource_info = RESOURCES_DATA.get(self.current_resource)
        if not resource_info:
            return 1.0

        tier = resource_info.get("tier")

        # Apply multiplier only if tier matches the list
        return bonus_data["multiplier"] if tier in bonus_data.get("tiers", []) else 1.0

    def get_defense_bonus(self):
        # Default multiplier: no bonus
        if not self.is_colonized:
            return 1.0

        # Access defense bonuses safely
        defense_bonus = self.bonuses.get("defense", {})

        # Return its multiplier if present, else 1.0
        return defense_bonus.get("multiplier", 1.0)
    
    # ---------------- Caching ----------------
    def _get_cache_signature(self):
        active_slots = [(s.type, s.status, s.active) for s in self.slots]
        return (self.mode, self.current_resource, tuple(active_slots))
    
    def _get_main_signature(self):
        """Cache key for mine/refine logic"""
        relevant_slots = [(s.type, s.status, s.active) for s in self.slots if s.type in ("mine", "refine")]
        return (self.mode, self.current_resource, tuple(relevant_slots))

    def _get_farm_signature(self):
        """Cache key for farming logic"""
        farm_slots = [(s.type, s.status, s.active) for s in self.slots if s.type == "farm"]
        return tuple(farm_slots)
    
    def on_slots_changed(self, slot_type=None, action=None):
        """
        Called whenever a slot is added, removed, activated, or deactivated.
        Automatically invalidates cache and optionally refreshes production stats.

        Args:
            slot_type (str): type of slot affected ('mine', 'refine', 'farm', etc.)
            action (str): optional, e.g. 'activate', 'deactivate', 'add', 'remove'
        """
        if not hasattr(self, "_resource_cache"):
            self._resource_cache = {"main": 0.0, "farm": 0.0, "total": 0.0}
        if not hasattr(self, "_cache_signatures"):
            self._cache_signatures = {"main": None, "farm": None}

        # ------------------------------------------
        # 1️⃣ Invalidate relevant cache section
        # ------------------------------------------
        if slot_type in ("mine", "refine"):
            # Invalidate main-mode cache
            self._cache_signatures["main"] = None
            self._resource_cache["main"] = 0.0
            log.debug(f"[Planet:{self.name}] Main cache invalidated due to {slot_type} {action}.")
        elif slot_type == "farm":
            # Invalidate farm cache
            self._cache_signatures["farm"] = None
            self._resource_cache["farm"] = 0.0
            log.debug(f"[Planet:{self.name}] Farm cache invalidated due to farm {action}.")
        else:
            # If slot_type not specified, clear everything
            self._cache_signatures = {"main": None, "farm": None}
            self._resource_cache = {"main": 0.0, "farm": 0.0, "total": 0.0}
            log.debug(f"[Planet:{self.name}] All caches invalidated (unknown slot type).")

    # ---------------- Statistics ----------------
    def get_statistics(self):
        return {
            "mined_total": round(self.statistics["mine"], 2),
            "refined_total": round(self.statistics["refine"], 2),
            "farmed_total": round(self.statistics["farm"], 2),
        }


    # ---------------- Representations ----------------
    def __repr__(self):
        used = len(self.get_used_slots())
        total = len(self.slots)
        if not self.is_colonized:
            return f"[{self.name_display} Uncolonized], Pop={self.population_max}B, Slots={used}/{total}"
        else:
            mode_str = "Refinery" if self.can_refine else "Mine"
            return f"[{self.name_display} {mode_str}: {self.current_resource}], Pop={self.population_max}B, Slots={used}/{total}"


class StarSystem:
    def __init__(self, hextile=None):
        self.name = self.generate_name()
        self.hextile=hextile
        self.planets = [Planet(star_system=self) for _ in range(random.randint(1,4))] # 1-4 planets
    def generate_name(self):
        return "System-"+str(random.randint(100,999))
    def __repr__(self):
        return f"{self.name}: {self.planets}"

class Hex:
    def __init__(self, q, r, s=None, weights=None, owner=None):
        self.q = q  # column (axial)
        self.r = r  # row (axial)
        self.s = s if s is not None else -q - r  # cube coords: q, r, s sum to 0
        self._feature_weights = weights
        self.owner=owner #Empire class
        self.feature, self.contents = self.generate_feature()
    def generate_feature(self):
        if self._feature_weights is None:
            weights = [0.3, 0.12, 0.14, 0.04, 0.1] # 30% system, 12% nebula, etc.
        else:
            weights = self._feature_weights
        feature = random.choices(
            SPECIAL_FEATURES,
            weights=weights,
        )[0]
        if feature == "star_system":
            return feature, StarSystem(hextile=self)
        else:
            return feature, None  # Could make Nebula, AsteroidField, BlackHole classes later
    def __repr__(self):
        return f"Hex(q={self.q}, r={self.r}, feat={self.feature}, contents={self.contents})"
    def hex_to_pixel(self, center, size, cam_offset=(0,0)):
        x = size * math.sqrt(3) * (self.q + self.r/2) + center[0] + cam_offset[0]
        y = size * 3/2 * self.r + center[1] + cam_offset[1]
        return (x, y)

    def polygon(self, center, size, cam_offset=(0,0)):
        cx, cy = self.hex_to_pixel(center, size, cam_offset)
        points = []
        for i in range(6):
            angle = math.radians(60 * i - 30)
            px = cx + size * math.cos(angle)
            py = cy + size * math.sin(angle)
            points.append((px, py))
        return points

    def contains_point(self, point, origin, pixel_offset=(0, 0)):
        poly = [Vector2(c) for c in self.polygon(origin, config.HEX_SIZE, cam_offset=pixel_offset)]
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

class GalaxyMap:
    """
    Generates a 2D hex grid for a galaxy map using pointy-topped axial coordinates.
    """
    def __init__(self, width, height, star_density=50, nebula_density=20):
        self.width = width  # columns (q)
        self.height = height  # rows (r)
        self.star_density = star_density  # 0-100
        self.nebula_density = nebula_density  # 0-100
        self.grid = self._generate_hexes()

    def _feature_weights(self):
        # Base weights order aligned with SPECIAL_FEATURES
        base_star = 0.30
        base_nebula = 0.12
        base_asteroid = 0.14
        base_black_hole = 0.04
        base_empty = 0.10
        # Scale star and nebula by density factors (0.2x .. 1.2x)
        star_scale = 0.2 + (self.star_density / 100.0)
        nebula_scale = 0.2 + (self.nebula_density / 100.0)
        w_star = base_star * star_scale
        w_nebula = base_nebula * nebula_scale
        # Keep others constant but lightly reduce empty as density goes up
        density_factor = (self.star_density + self.nebula_density) / 200.0  # 0..1
        w_empty = max(0.02, base_empty * (1.0 - 0.4 * density_factor))
        return [w_star, w_nebula, base_asteroid, base_black_hole, w_empty]

    def _generate_hexes(self):
        grid = []
        weights = self._feature_weights()
        for q in range(self.width):
            q_offset = math.floor(q / 2)  # even-q vertical layout
            for r in range(-q_offset, self.height - q_offset):
                grid.append(Hex(q, r, weights=weights))
        return grid

    def get_hex(self, q, r):
        for hex in self.grid:
            if hex.q == q and hex.r == r:
                return hex
        return None

    def all_hexes(self):
        return self.grid

    def draw(self, surface, center, assets, frame_count, player, camera, current_empire):
        cam_offset = camera.get_offset() if camera else (0,0)
        # Draw borders for all hexes
        for hex in self.grid:
            points = hex.polygon(center, config.HEX_SIZE, cam_offset)
            if hex.owner == current_empire:
                # Optional: Draw a dot or color for star system centers
                if hex.feature == 'star_system':
                    star_x, star_y = hex.hex_to_pixel(center, config.HEX_SIZE, cam_offset)
                    pygame.draw.circle(surface, config.YELLOW, (int(star_x), int(star_y)), 4)
                elif hex.feature == 'nebula':
                    cx, cy = hex.hex_to_pixel(center, config.HEX_SIZE, cam_offset)
                    pygame.draw.circle(surface, config.LIGHT_BLUE, (int(cx), int(cy)), 4)
                elif hex.feature == 'asteroid_field':
                    cx, cy = hex.hex_to_pixel(center, config.HEX_SIZE, cam_offset)
                    pygame.draw.circle(surface, config.GRAY, (int(cx), int(cy)), 4)
                elif hex.feature == 'black_hole':
                    cx, cy = hex.hex_to_pixel(center, config.HEX_SIZE, cam_offset)
                    pygame.draw.circle(surface, config.BLACK, (int(cx), int(cy)), 4)
                pygame.draw.polygon(surface, current_empire.color, points, 1)
            else :
                pygame.draw.polygon(surface, config.FOG_COLOR, points)
                pygame.draw.polygon(surface, config.LIGHT_GRAY, points, 1)
        
        for hex in self.grid:
            points = hex.polygon(center, config.HEX_SIZE, cam_offset)
            if hex.owner == current_empire:
                pygame.draw.polygon(surface, current_empire.color, points, 1)
            
