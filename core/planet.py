import asyncio
from pickle import NONE
import random
import json
import glob
import os
import msgpack
import time
from collections import defaultdict
from core.logger_setup import get_logger
from core.slot import Slot
from core.registry import REGISTRY
from core.defense import *
from core.buildqueue import *
from core.config import *

log = get_logger("Planet")

def build_resource_helpers_dynamic():
    """
    Dynamically build helper dictionaries from REGISTRY["resources"].
    
    Returns:
        RESOURCE_NAMES_BY_TYPE: dict[str, list[str]]  # resource IDs grouped by type
        RESOURCES_DATA: dict[str, dict]               # raw resource data by ID
        RESOURCE_TYPES: list[str]                     # all resource types found
    """
    RESOURCES_DATA = REGISTRY.get("resources", {})
    
    # Detect all resource types dynamically
    RESOURCE_TYPES = sorted({res.get("resource_type") for res in RESOURCES_DATA.values() if "resource_type" in res})
    
    RESOURCE_NAMES_BY_TYPE = {rtype: [] for rtype in RESOURCE_TYPES}
    for res_id, res_data in RESOURCES_DATA.items():
        rtype = res_data.get("resource_type")
        if rtype in RESOURCE_TYPES:
            RESOURCE_NAMES_BY_TYPE[rtype].append(res_id)
        else:
            log.warning(f"[Registry] Resource '{res_id}' has unknown type '{rtype}'")
    
    log.info(f"[Registry] Detected resource types: {RESOURCE_TYPES}")
    return RESOURCE_NAMES_BY_TYPE, RESOURCES_DATA, RESOURCE_TYPES

# Usage after loading registry
RESOURCE_NAMES_BY_TYPE, RESOURCES_DATA, RESOURCE_TYPES = build_resource_helpers_dynamic()


class Planet:
    _next_global_id = 1
    def __init__(self, name=None, star_system=None, population=None):
        self.name = name or self.generate_name()
        self.global_id = Planet._next_global_id
        Planet._next_global_id += 1
        self.star_system = star_system
        self.id=0 # TODO : immediately modified when construct by star system, we can keep it for id inside a star system 

        # --- Planet type ---
        self.planet_type_id = self.generate_planet_type()
        self.planet_type = REGISTRY["planets"][self.planet_type_id]

        self.climate = self.assign_random_climate()
        #TODO refactoring climate in json to gather all attributes (and description)
        self.features=None #Prevent attribute error
        self.assign_features()

        #self.bonuses = self.planet_type.get("bonuses", {})
        bonuses = self.assign_planet_bonuses(
                planet_type=self.planet_type_id,
                all_resources=REGISTRY["resources"]
            )
        #print(f"[Planet__init__] self.bonuses: {self.bonuses}")
        self.resource_bonus = bonuses
        #print(f"[Planet__init__] self.resource_bonus: {self.resource_bonus}")
        self.defense_bonus = self.get_defense_bonus()
        self.bonuses = {
            "resources": self.resource_bonus,
            "defense":self.defense_bonus
        }
        self.name_display = self.planet_type.get("name", self.planet_type_id.title())
        self.description = self.planet_type.get("description", "")
        self.rarity = self.planet_type.get("rarity", "common")
        self.colonization_cost = self.planet_type.get("colonization_cost", {"credits": 100, "resources": {}})
        self.habitability = self.planet_type.get("habitability", 0.5)

        # --- Colonization / Resources ---
        self.current_resource_type = None
        self.current_resource = "basaltic_ore" #prevent attribute error
        self.mode = None  # "mine" or "refine"
        self.can_refine = False
        self.is_colonized = False

        # --- Population / Slots ---
        self.population_max = population or random.randint(1, 20)
        self.population= 0
        self.slots = [Slot() for _ in range(self.population_max)]
        #Trade
        self.trade_routes = []  # list[TradeRoute]
        self.trade_capacity = max(1, self.population_max// 4)

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
        #production
        self.statistics = {
            "mine": 0.0,
            "refine": 0.0,
            "farm": 0.0,
            "industry": 0.0,
            "energy": 0.0,
            "science": 0.0
        }
        #reserves
        self.resources = defaultdict(float)
        self._last_cache_signature = None  # for detecting slot/mode changes
        self._resource_cache = {
            "mine": 0.0,
            "refine": 0.0,
            "farm": 0.0
        }

        self._cache_signatures = {
            "mine": None,
            "refine": None,
            "farm": None
        }
        # ---Graphics---
        self.rotation_gif_path = None
        self.assign_planet_gif()
        self.animation = None

        # ---Updates---
        self._last_sent_resources = {}
        self._last_sync_time = time.time()


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

    def assign_planet_bonuses(self, planet_type, all_resources):
        """
        Assign both raw and refined resource bonuses for a planet.
        
        planet_type: string
        all_resources: list of dicts from resources.json
        Returns: dict with bonus multipliers
        """
        bonuses = {}

        # Determine eligible resources for this planet type
        eligible_ids = PLANET_TYPE_ALLOWED.get(planet_type, [])
        
        # Filter resources to planet-allowed only
        eligible_resources = [r for id, r in all_resources.items() if r["id"] in eligible_ids]
        
        # Apply rarity multiplier
        rarity_multiplier = PLANET_RARITY_BONUS.get(planet_type, 1.0)
        
        for res in eligible_resources:
            base_multiplier = random.uniform(1.1, 1.5)  # +10% to +50% base
            # Scale with rarity
            final_multiplier = base_multiplier * rarity_multiplier
            bonuses[res["id"]] = round(final_multiplier, 2)
            
        # Optional: assign a smaller bonus to raw extraction (tier 1 resources) if planet allows it
        for id, res in all_resources.items():
            if res["id"] in PLANET_TYPE_ALLOWED.get(planet_type, []):
                # Make raw bonuses smaller than refined
                raw_bonus = 1.05 * rarity_multiplier  # +5% base, scaled
                bonuses[res["id"]] = max(bonuses.get(res["id"], 1.0), round(raw_bonus, 2))
        
        return bonuses
    
    def assign_random_climate(self):
        """
        Assigns a random climate appropriate for this planet type.
        """
        type_data = self.planet_type if isinstance(self.planet_type, dict) else {}
        possible = type_data.get("possible_climates", [])

        if not possible:
            self.climate = "unknown"
        else:
            self.climate = random.choice(possible)
        
        return self.climate


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
    def extract_resources(self, force_recompute=False, player=None, server=None):
        if not self.is_colonized or not self.star_system:
            #changed, farm, mine, refine
            log.debug(f"function returned False. orgigin : {self.star_system}")
            return False
        
        if player is None:
            log.debug(f"function returned False. origin : player is None : {player}")
            return False
        # Ensure resource structures exist
        self._resource_cache = getattr(self, "_resource_cache", {"mine": 0.0, "farm": 0.0, "refine": 0.0})
        self._cache_signatures = getattr(self, "_cache_signatures", {"mine": None, "farm": None, "refine": None})
        self.statistics = getattr(self, "statistics", {"mine": 0.0, "refine": 0.0, "farm": 0.0})
        
        tech_level = 1.0
        owner_patents = getattr(player, "patents", [])
        total_yield_mine = 0.0
        total_yield_farm = 0.0
        total_yield_refine = 0.0


        changed = False
        #we compute farm output first
        # -----------------------------------------------
        # 1. FARMING — always active but cached separately
        # ----------------------------------------------- 
        farm_signature = self._get_farm_signature()
        if not force_recompute and farm_signature == self._cache_signatures["farm"]:
            log.debug("No recomputing farm for this turn")
            total_yield_farm = self._resource_cache["farm"]
        else :
            farm_count = len([s for s in self.slots if s.type == "farm" and s.status == "built" and s.active])
            if farm_count > 0:

                # Base yield per farm slot (you can define this elsewhere)
                base_yield = next((s.building.base_yield for s in self.slots if s.type == "farm"), 1)
                total_yield_farm = farm_count * base_yield * tech_level
                total_yield_farm = self.apply_patents(total_yield_farm, owner_patents, target_type="organics")

                # TODO later add farm tier ?
            changed = True
            self._resource_cache["farm"] = total_yield_farm
            self._cache_signatures["farm"] = farm_signature
        # Apply production (even if cached)
        if total_yield_farm > 0:
            #basic funtion for now
            farm_resource = "Organifera"
            self.resources[farm_resource] = self.resources.get(farm_resource, 0) + total_yield_farm
            self.statistics["farm"] = total_yield_farm
            self.resource_farmed = farm_resource

        # ---------------------------
        # 2. MINE/REFINE MODE
        # ---------------------------
        resource_info = RESOURCES_DATA.get(self.current_resource)
        if resource_info:
            if resource_info.get("inputs"):
                # This resource needs inputs -> it’s a refined product
                self.compute_refining(tech_level, owner_patents, force_recompute=force_recompute)
            else:
                # No inputs -> it’s a raw extractable resource
                self.compute_mining(tech_level, owner_patents, force_recompute=force_recompute)

        # --- Send packet to client ---
        if server and player and player.id in server.client_for_player:
            # assume planet has owner_id or player_id
            #owner_id = self.star_system.hextile.owner_id
                writer = server.client_for_player[player.id]
                packet = {
                    "type": "planet_resource_update",
                    "planet_global_id": self.global_id,
                    "resources": self.resources,
                    "statistics": self.statistics,
                }
                async def _send_update():
                    try:
                        packed = msgpack.packb(packet, use_bin_type=True)
                        async with server.client_locks[writer]:
                            writer.write(len(packed).to_bytes(4, "big") + packed)
                            await writer.drain()
                        log.debug(f"Sent resource_update packet for {self.name} to player {player.name}")
                    except Exception as e:
                        log.exception(f"Failed to send resource_update packet: {e}")
                asyncio.create_task(_send_update())

        return changed

    def apply_patents(self, yield_amount, patents, target_type, resource_name=None):
        """
        Applies patent bonuses to a given yield amount.

        Args:
            yield_amount (float): base yield before patents
            patents (list): list of Patent objects
            target_type (str): e.g. "mine", "refine", "organics"
            resource_name (str, optional): overrides self.current_resource for special cases
        """
        res_name = resource_name or getattr(self, "current_resource", None)
        if not res_name or res_name not in RESOURCES_DATA:
            log.warning(f"apply_patents: unknown resource '{res_name}'")
            return yield_amount

        res_data = RESOURCES_DATA[res_name]

        # --- Extract relevant fields ---
        resource_type = res_data.get("resource_type", "generic")  # e.g. "gas", "mineral", "biological"
        refinement_level = res_data.get("refinement_level", "raw")  # e.g. "raw", "processed", "advanced"
        tags = res_data.get("tags", []) or []

        # --- Apply matching patents ---
        for patent in patents:
            if not patent.is_usable_by(self.star_system.hextile.owner):
                continue

            # Basic match by building type (e.g. mine, refine, organics)
            if patent.target_building_type != target_type:
                continue

            # If patent has specialized conditions, match by resource_type or refinement_level
            if hasattr(patent, "applies_to_resource_type") and patent.applies_to_resource_type:
                if resource_type not in patent.applies_to_resource_type:
                    continue

            if hasattr(patent, "applies_to_refinement_level") and patent.applies_to_refinement_level:
                if refinement_level not in patent.applies_to_refinement_level:
                    continue

            # Optional: match by tag
            if hasattr(patent, "applies_to_tags") and patent.applies_to_tags:
                if not any(tag in tags for tag in patent.applies_to_tags):
                    continue

            # Finally, apply the bonus
            yield_amount = patent.apply_bonus(yield_amount, resource_type, refinement_level)

        return yield_amount

    
    def compute_mining(self, tech_level, owner_patents, force_recompute=False):
        """Compute mining yield for the current planet."""
        mine_signature = self._get_mine_signature()
        self._cache_signatures.setdefault("mine", None)
        self._resource_cache.setdefault("mine", 0.0)

        # --- Use cached value if signature didn't change ---
        if not force_recompute and mine_signature == self._cache_signatures.get("mine"):
            total_yield_mine = self._resource_cache["mine"]

        else:
            mine_count = len([s for s in self.slots if s.type == "mine" and s.status == "built"])
            total_yield_mine = 0.0  # default

            if mine_count > 0:
                # --- Get base yield from building or resource ---
                base_yield = next(
                    (s.building.base_yield for s in self.slots if s.type == "mine" and hasattr(s, "building")),
                    1.0
                )

                resource_data = RESOURCES_DATA.get(self.current_resource, {})
                if resource_data.get("refinement_level") != "raw":
                    log.warning(f"{self.name} is mining a non-raw resource ({self.current_resource})")
                refinement_level = resource_data.get("refinement_level", "raw")
                refine_multiplier = REFINEMENT_YIELD_MULTIPLIERS.get(refinement_level, 1.0)

                # Optional per-resource yield (from resource.json)
                resource_yield = resource_data.get("yield", 1.0)

                # --- Compute total yield ---
                total_yield_mine = (
                    mine_count
                    * tech_level
                    * self.get_resource_yield_bonus()
                    * base_yield
                    * refine_multiplier
                    * resource_yield
                )
                log.debug(f"mine_count :{mine_count}, yield_bonus : {self.get_resource_yield_bonus()}, refine_multiplier : {refine_multiplier}, resource_yield : {resource_yield}")

                # --- Apply patents ---
                total_yield_mine = self.apply_patents(
                    total_yield_mine,
                    owner_patents,
                    target_type="mine",
                    resource_name=self.current_resource,
                )

                # --- Update statistics ---
                self.statistics["mine"] = total_yield_mine
                self._resource_cache["mine"] = total_yield_mine
                self._cache_signatures["mine"] = mine_signature
                self.resource_mined = self.current_resource

            else:
                # No active mines
                self.statistics["mine"] = 0.0
                total_yield_mine = 0.0

            changed = True  # <- flag to trigger packet update

        # --- Apply to stored resources ---
        self.resources[self.current_resource] = (
            self.resources.get(self.current_resource, 0) + total_yield_mine
        )

        log.debug(f"[{self.name}] mined {total_yield_mine:.2f} units of {self.current_resource}")
        return total_yield_mine


    def compute_refining(self, tech_level, owner_patents, force_recompute=False):
        """Compute refined resource output based on available inputs and slots."""

        refine_signature = self._get_refine_signature()
        self._cache_signatures.setdefault("refine", None)
        self._resource_cache.setdefault("refine", 0.0)
        # Skip recomputation if nothing changed
        if not force_recompute and refine_signature == self._cache_signatures.get("refine"):
            return self._resource_cache["refine"]

        total_yield_refine = 0
        refine_count = len([s for s in self.slots if s.type == "refine" and s.status == "built"])

        if refine_count == 0:
            self.statistics["refine"] = 0
            return 0

        # --- Get refining resource info ---
        resource_info = RESOURCES_DATA.get(self.current_resource)
        if not resource_info:
            log.warning(f"{self.name}: current resource '{self.current_resource}' not found in RESOURCES_DATA.")
            self.statistics["refine"] = 0
            return 0

        inputs = resource_info.get("inputs", {})
        yield_factor = resource_info.get("yield", 1.0)

        # --- Check if this resource is actually refinable ---
        if not inputs:
            log.info(f"{self.name}: Resource '{self.current_resource}' has no inputs, cannot refine.")
            self.statistics["refine"] = 0
            return 0

        # --- Base yield before modifiers ---
        total_yield_refine = refine_count * tech_level * self.get_refine_bonus()
        total_yield_refine = self.apply_patents(total_yield_refine, owner_patents, target_type="refine")

        # --- Check if we have enough input materials ---
        for input_res, ratio in inputs.items():
            required = total_yield_refine * ratio
            available = self.resources.get(input_res, 0)
            if available < required:
                log.info(f"[{self.name}] Not enough {input_res} ({available}/{required}) to refine {self.current_resource}")
                self.statistics["refine"] = 0
                return 0

        # --- Consume inputs ---
        for input_res, ratio in inputs.items():
            consumed = total_yield_refine * ratio
            self.resources[input_res] -= consumed

        # --- Produce output ---
        refined_amount = total_yield_refine * yield_factor
        self.resources[self.current_resource] = self.resources.get(self.current_resource, 0) + refined_amount

        self.resource_refined = self.current_resource
        self.statistics["refine"] = round(refined_amount, 3)
        self._cache_signatures["refine"] = refine_signature
        self._resource_cache["refine"] = refined_amount

        log.debug(f"[{self.name}] Refined {self.current_resource}: +{refined_amount:.2f} (yield {yield_factor}, inputs {inputs})")
        return

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

    def update_build_queue(self, delta_time, notification_mgmt=None, server=None, player=None):
        completed = self.build_queue.update(delta_time)
        if completed:
            self.on_build_completed(completed, notification_mgmt, server, player)

    def on_build_completed(self, order, notification_mgmt=None, server=None, player=None):
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
            #notification_mgmt.show(f"Added {new_unit.name} to {self.name}")
            log.info(f"[Defense] Added {new_unit.name} to {self.name}")

        elif order.category == "building":
            slot = getattr(order, "slot", None)
            if slot and slot.building:
                #slot.building.complete()
                slot.status = "built"
                
                #notification_mgmt.show(f"{slot.building.name} completed on {self.name}")
                log.info(f"[Building] {slot.building.name} completed on {self.name}")
            else:
                log.warning(f"[Planet] {self.name}: Build completed but slot reference missing!")
        
        # --- Send packet to client ---
        if server and player and player.id in server.client_for_player:
            # assume planet has owner_id or player_id
            #owner_id = self.star_system.hextile.owner_id
                writer = server.client_for_player[player.id]
                packet = {
                    "type": "planet_update",
                    "planet_id": self.id,
                    "planet_global_id": self.global_id,
                    "action": "build_completed",
                    "new_state": self.to_dict(),
                }
                async def _send_update():
                    try:
                        packed = msgpack.packb(packet, use_bin_type=True)
                        async with server.client_locks[writer]:
                            writer.write(len(packed).to_bytes(4, "big") + packed)
                            await writer.drain()
                        log.debug(f"Sent build_completed packet for {self.name} to player {player.name}")
                    except Exception as e:
                        log.exception(f"Failed to send build_completed packet: {e}")
                asyncio.create_task(_send_update())

    def get_total_defense_points(self):
        total = 0
        for unit in self.defense:
            total +=unit.defense_value
        
        return total
    # ---------------- Bonuses ----------------
    def get_resource_yield_bonus(self):
        """
        Returns final resource extraction multiplier, combining:
        - base resource bonuses
        - climate modifiers
        """
        if not self.is_colonized or not self.current_resource_type:
            return 1.0

        res_id = self.current_resource_type
        base_mult = self.resource_bonus.get(res_id, 1.0)

        climate_mod = CLIMATE_EFFECTS.get(self.climate, {}).get("resource_yield", 1.0)


        return round(base_mult * climate_mod, 2)

    def get_refine_bonus(self):
        """
        Returns the refining bonus multiplier for the planet’s current resource.

        Uses the new flat resource bonus structure:
            self.resource_bonus = { resource_id: multiplier }
        """
        # No bonus if uncolonized or resource not selected
        if not self.is_colonized or not self.current_resource_type:
            return 1.0

        # Current resource ID being refined (e.g., "metal_bars")
        res_id = self.current_resource_type

        # Get multiplier from resource_bonus dict
        bonus_mult = self.resource_bonus.get(res_id, 1.0)

        #get climate modifier
        climate_mod = CLIMATE_EFFECTS.get(self.climate, {}).get("refining_speed", 1.0)

        return round(bonus_mult * climate_mod, 2)

    def get_defense_bonus(self):
        """
        initial defense bonus compute.
        defense bonus is affected by planet type and climate.
        """

        if isinstance(self.planet_type, dict):
            type_bonus = self.planet_type.get("defense_base_bonus", 1.0)

        #get climate modifier
        climate_mod = CLIMATE_EFFECTS.get(self.climate, {}).get("defense", 1.0)

        total = round(type_bonus * climate_mod, 2)

        # Return its multiplier if present, else 1.0
        return total
    
    # ---------------- Caching ----------------
    def _get_cache_signature(self):
        active_slots = [(s.type, s.status, s.active) for s in self.slots]
        return (self.mode, self.current_resource, tuple(active_slots))
    
    def _get_main_signature(self):
        """Cache key for mine/refine logic"""
        relevant_slots = [(s.type, s.status, s.active) for s in self.slots if s.type in ("mine", "refine")]
        return (self.mode, self.current_resource, tuple(relevant_slots))
    
    def _get_mine_signature(self):
        """Cache key for mine logic"""
        mine_slots = [(s.type, s.status, s.active) for s in self.slots if s.type == "mine"]
        return (self.mode, self.current_resource, tuple(mine_slots))
    
    def _get_refine_signature(self):
        """Cache key for refine logic"""
        refine_slots = [(s.type, s.status, s.active) for s in self.slots if s.type == "refine"]
        return (self.mode, self.current_resource, tuple(refine_slots))

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
            self._resource_cache = {"mine": 0.0, "farm": 0.0, "refine": 0.0}
        if not hasattr(self, "_cache_signatures"):
            self._cache_signatures = {"mine": None, "farm": None, "refine": None}

        # ------------------------------------------
        # 1️⃣ Invalidate relevant cache section
        # ------------------------------------------
        if slot_type in ("mine", "farm", "refine"):
            # Invalidate cache
            self._cache_signatures[f"{slot_type}"] = None
            self._resource_cache[f"{slot_type}"] = 0.0
            log.debug(f"[Planet:{self.name}] {slot_type} cache invalidated due to {slot_type} {action}.")
        # if slot_type == "mine":
        #     # Invalidate mine cache
        #     self._cache_signatures["mine"] = None
        #     self._resource_cache["mine"] = 0.0
        #     log.debug(f"[Planet:{self.name}] Mine cache invalidated due to mine {action}.")
        # elif slot_type == "farm":
        #     # Invalidate farm cache
        #     self._cache_signatures["farm"] = None
        #     self._resource_cache["farm"] = 0.0
        #     log.debug(f"[Planet:{self.name}] Farm cache invalidated due to farm {action}.")
        # elif slot_type == "refine":
        #     # Invalidate refine cache
        #     self._cache_signatures["refine"] = None
        #     self._resource_cache["refine"] = 0.0
        #     log.debug(f"[Planet:{self.name}] Refine cache invalidated due to refine {action}.")
        else:
            # If slot_type not specified, clear everything
            self._cache_signatures = {"mine": None, "farm": None, "refine": None}
            self._resource_cache = {"mine": 0.0, "farm": 0.0, "refine": 0.0}
            log.debug(f"[Planet:{self.name}] All caches invalidated (unknown slot type : {slot_type}).")

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

    def to_dict(self):
        #print(f"[Planet-to_dict]self.resource_bonus: {self.resource_bonus}")
        return {
            "global_id": self.global_id,
            "id": self.id,
            "name": self.name,
            "population_max": self.population_max,
            "population": self.population,
            "slots": [s.to_dict() for s in self.slots],
            "mode": self.mode,
            "resources": getattr(self, "resources", {}).copy(),
            "current_resource": self.current_resource,
            "planet_type": self.planet_type_id,
            "is_colonized": self.is_colonized,
            "bonuses": self.bonuses,
            "gif_path": self.rotation_gif_path,
            "statistics": self.statistics,
            "climate":self.climate,
            "features":self.features,
            "defense": self.defense.to_dict()
        }

    def compute_deltas(self):
        #deltas = {"slots": [], "resources": []}
        deltas = {"slots": []}

        # --- Slot delta tracking ---
        for i, slot in enumerate(self.slots):
            last_sent = getattr(slot, "_last_sent", None)
            if last_sent != slot.active:
                deltas["slots"].append({
                    "global_id": getattr(self, "global_id", None),
                    "planet_id": getattr(self, "id", None),
                    "slot_index": i,
                    "type": getattr(slot, "type", None),
                    "active": int(slot.active)
                })
                slot._last_sent = slot.active  # remember last sent state

        # --- Resource delta tracking ---
        # for rid, val in enumerate(self.resources):
        #     last_val = self._last_sent_resources[rid]
        #     if last_val != val:
        #         deltas["resources"].append({
        #             "planet_id": getattr(self, "id", None),
        #             "resource_id": rid,
        #             "amount": val
        #         })
        #         self._last_sent_resources[rid] = val

        return deltas
    
    #Hydration
    @classmethod
    def from_dict(cls, data: dict, star_system=None):
        """
        Rebuild a Planet instance from a serialized dictionary.
        Expected structure:
        {
            "id": 0,
            "name": "Planet-6695",
            "slots": [...],
            "resources": {...},
            "planet_type": "volcanic",
            "is_colonized": False
        }
        """
        # 1️⃣ Create a new Planet (but skip random generation)
        planet = cls.__new__(cls)

        # Basic attributes
        planet.global_id = data.get("global_id", 0)
        planet.id = data.get("id", 0)
        planet.name = data.get("name", f"Planet-{planet.id}")
        planet.star_system = star_system

        # 2️⃣ Planet type and metadata from registry
        planet.planet_type_id = data.get("planet_type", "terrestrial")
        planet.planet_type = REGISTRY["planets"].get(planet.planet_type_id, {})

        planet.bonuses = data.get("bonuses", {})
        planet.resource_bonus = planet.bonuses.get("resources", {})
        planet.defense_bonus = planet.bonuses.get("defense", 1.0)
        planet.name_display = planet.planet_type.get("name", planet.planet_type_id.title())
        planet.description = planet.planet_type.get("description", "")
        planet.rarity = planet.planet_type.get("rarity", "common")
        planet.colonization_cost = planet.planet_type.get(
            "colonization_cost", {"credits": 100, "resources": {}}
        )
        planet.habitability = planet.planet_type.get("habitability", 0.5)

        # 3️⃣ Colonization & resources
        planet.current_resource_type = data.get("current_resource_type")
        planet.current_resource = data.get("current_resource")
        planet.mode = data.get("mode", None)
        planet.can_refine = data.get("can_refine", False)
        planet.is_colonized = data.get("is_colonized", False)
        planet.resources = data.get("resources", {})

        planet.population_max = data.get("population_max", 1)
        planet.population = data.get("population", 0)

        # 4️⃣ Slots (simplify hydration)
        slot_data = data.get("slots", [])
        planet.slots = []
        for s in slot_data:
            slot = Slot(
                slot_type=s.get("type", "empty"),              
            )
            slot.active=s.get("active", True)
            #has_building=s.get("has_building", False),
            #building_name=s.get("building_name"),
            planet.slots.append(slot)

        # 5️⃣ Defaults for non-serialized components
        planet.industry_points = 1000
        planet.defense = PlanetDefense()
        planet.defense_value = data.get("defense_value", 0)

        planet.build_queue = BuildQueue()

        planet._last_cache_signature = None
        planet._resource_cache = {"main": 0.0, "farm": 0.0, "total": 0.0}
        planet._cache_signatures = {"main": None, "farm": None}

        planet.rotation_gif_path = data.get("gif_path", None)
        planet.animation = None

        planet.statistics = data.get("statistics", {})
        planet.climate = data.get("climate", None)
        planet.features = data.get("features", None)
        planet.defense = PlanetDefense.from_dict(data.get("defense", {}))

        return planet

    def set_resource(self, resource):
        self.current_resource=resource
    
    def assign_planet_gif(self, base_folder="assets/planets_rotation"):
        type_folder = os.path.join(base_folder, self.planet_type_id)
        gifs = glob.glob(os.path.join(type_folder, "*.gif"))
        # TODO even simplier, just planet.rotation_variant = 3
        # and then the client interpret f"assets/planet_rotation/{planet.planet_type_id}/volcanic_{planet.rotation_variant:02d}.gif"
        if gifs:
            chosen = random.choice(gifs)
            self.rotation_gif_path = chosen