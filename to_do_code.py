from collections import defaultdict
import logging

log = logging.getLogger(__name__)


class PlanetResourceManager:
    """
    Resource manager with automatic initialization, logging, and capacity limits.
    Supports add/remove/check operations and can handle overflow or caps.
    """

    def __init__(self, owner_name="Unknown"):
        self._resources = defaultdict(float)   # actual resource amounts
        self._caps = defaultdict(lambda: float("inf"))  # per-resource caps
        self.owner_name = owner_name

    # -------------------------------------------------------
    # Basic accessors
    # -------------------------------------------------------

    def get(self, resource_name):
        """Return current amount (0 if missing)."""
        return self._resources[resource_name]

    def set(self, resource_name, amount):
        """Force-set a resource amount (respecting cap)."""
        cap = self._caps[resource_name]
        old_value = self._resources[resource_name]
        new_value = min(float(amount), cap)
        self._resources[resource_name] = new_value

        log.debug(f"[{self.owner_name}] {resource_name}: {old_value:.2f} → {new_value:.2f} (cap={cap})")

    def add(self, resource_name, amount):
        """Add or subtract an amount from a resource (respecting cap)."""
        if amount == 0:
            return 0.0

        cap = self._caps[resource_name]
        before = self._resources[resource_name]
        after = before + float(amount)

        # Apply cap (storage limit)
        overflow = max(0.0, after - cap)
        if overflow > 0:
            after = cap

        # Avoid negative underflow
        if after < 0:
            overflow = -after  # underflow amount
            after = 0.0

        self._resources[resource_name] = after
        log.debug(
            f"[{self.owner_name}] {resource_name}: {before:.2f} → {after:.2f} "
            f"({'+' if amount >= 0 else ''}{amount:.2f}), cap={cap}"
        )

        return overflow  # Return overflow/underflow amount (useful for UI or loss tracking)

    def has_enough(self, resource_name, required_amount):
        """Check if we have at least required_amount of resource."""
        return self._resources[resource_name] >= required_amount

    # -------------------------------------------------------
    # Capacity management
    # -------------------------------------------------------

    def set_capacity(self, resource_name, capacity):
        """Set a storage cap for this resource."""
        if capacity <= 0:
            capacity = float("inf")

        old_cap = self._caps[resource_name]
        self._caps[resource_name] = float(capacity)

        # Enforce immediately
        if self._resources[resource_name] > capacity:
            self._resources[resource_name] = capacity
            log.info(f"[{self.owner_name}] {resource_name} reduced to cap {capacity}")

        log.debug(f"[{self.owner_name}] Capacity for {resource_name} set: {old_cap} → {capacity}")

    def get_capacity(self, resource_name):
        return self._caps[resource_name]

    def get_fill_ratio(self, resource_name):
        """Return fill ratio between 0 and 1."""
        cap = self._caps[resource_name]
        if cap == float("inf"):
            return 0.0
        return self._resources[resource_name] / cap

    # -------------------------------------------------------
    # Bulk operations
    # -------------------------------------------------------

    def consume(self, resources: dict):
        """Consume multiple resources if enough are available."""
        for name, amount in resources.items():
            if not self.has_enough(name, amount):
                log.info(f"[{self.owner_name}] Not enough {name} (need {amount}, have {self._resources[name]})")
                return False

        for name, amount in resources.items():
            self.add(name, -amount)

        return True

    def produce(self, resources: dict):
        """Produce multiple resources (respecting caps)."""
        overflow = {}
        for name, amount in resources.items():
            extra = self.add(name, amount)
            if extra > 0:
                overflow[name] = extra
        return overflow  # useful if you want to show “storage full” messages

    # -------------------------------------------------------
    # Utility and reporting
    # -------------------------------------------------------

    def as_dict(self):
        """Return a snapshot as a regular dict."""
        return dict(self._resources)

    def as_report(self):
        """Return dict with (amount, cap, ratio)."""
        return {
            name: {
                "amount": amt,
                "cap": self._caps[name],
                "ratio": self.get_fill_ratio(name)
            }
            for name, amt in self._resources.items()
        }

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        self.set(key, value)

    def __repr__(self):
        parts = []
        for k, v in self._resources.items():
            cap = self._caps[k]
            parts.append(f"{k}: {v:.2f}/{cap if cap != float('inf') else '∞'}")
        return f"<Resources({', '.join(parts)})>"


def __init__(self, owner_name="Unknown", default_cap=125_000):
    self._resources = defaultdict(float)
    self._caps = defaultdict(lambda: float(default_cap))
    self.owner_name = owner_name
    self.default_cap = default_cap

def apply_decay(self, delta_hours=1.0):
    """
    Applies resource decay over time.
    delta_hours: simulated game hours passed (float).
    """
    DECAY_RATES = {
        "Organifera": 0.02,  # 2% per hour
        "Biomass": 0.015,
    }

    for name, rate in DECAY_RATES.items():
        if self._resources[name] <= 0:
            continue

        decay_factor = (1.0 - rate) ** delta_hours  # exponential decay
        before = self._resources[name]
        after = before * decay_factor

        self._resources[name] = after
        lost = before - after

        if lost > 0.01:
            log.debug(f"[{self.owner_name}] {name} decayed by {lost:.2f} units ({rate*100:.1f}%/h)")

def update_storage_capacities(self, buildings):
    """Recompute storage caps from buildings."""
    base_cap = self.default_cap
    total_energy_upkeep = 0

    for b in buildings:
        if b.type == "warehouse":
            cap_bonus = b.capacity_bonus  # e.g., 10_000
            base_cap += cap_bonus
            total_energy_upkeep += cap_bonus / 1000 * 1.5  # 1.5 energy per 1k capacity

    self.set_capacity("Organifera", base_cap)
    return total_energy_upkeep

def apply_decay(self, delta_hours=1.0, refrigeration_bonus=0.0):
    """
    Apply food decay; refrigeration_bonus reduces decay rate (0 = none, 1 = no decay)
    """
    DECAY_RATES = {
        "Organifera": 0.02,  # 2%/hr
        "Biomass": 0.015,
    }

    for name, rate in DECAY_RATES.items():
        if self._resources[name] <= 0:
            continue

        effective_rate = rate * (1.0 - refrigeration_bonus)
        decay_factor = (1.0 - effective_rate) ** delta_hours
        before = self._resources[name]
        after = before * decay_factor
        lost = before - after

        if lost > 0.01:
            log.debug(f"[{self.owner_name}] {name} decayed by {lost:.2f} units ({effective_rate*100:.1f}%/h)")

        self._resources[name] = after

refrigeration_bonus = 0.5  # e.g., 50% less decay if you researched "Refrigeration"
planet.resources.apply_decay(delta_hours=1/60, refrigeration_bonus=refrigeration_bonus)

class SimulationManager:
    def __init__(self):
        self.planets = []
        self.tick_index = 0

    async def run(self):
        while True:
            self.tick_some_planets()
            await asyncio.sleep(0.1)

    def tick_some_planets(self):
        BATCH_SIZE = 50
        end = self.tick_index + BATCH_SIZE
        for planet in self.planets[self.tick_index:end]:
            planet.resource_manager.apply_decay(delta_hours=1/60)
            planet.resource_manager.extract_resources()
        self.tick_index = end % len(self.planets)

# simulation.py
import asyncio
import multiprocessing as mp
import signal
import time
from typing import List, Dict, Any

# -------------------------
# Config
# -------------------------
TICK_INTERVAL = 0.1        # seconds (scheduler loop cadence)
BATCH_SIZE = 50            # planets updated per loop
PERSIST_INTERVAL = 5.0     # seconds: flush changed planets to DB
PLANET_TICK_HOURS_PER_CALL = 1.0 / 60.0  # simulate 1 in-game minute per tick call

# -------------------------
# Minimal Planet stub (replace with your real Planet class)
# -------------------------
class Planet:
    def __init__(self, planet_id: int, name: str):
        self.id = planet_id
        self.name = name
        self.last_update = 0.0
        self.dirty = False  # set True when state changed (slots toggled / built / removed)
        # insert your resource_manager, slots, etc:
        # self.resources = PlanetResourceManager(owner_name=name)
        # self.resource_cache, etc.

    async def tick(self, delta_hours: float):
        """
        Called by the simulation loop to advance planet simulation.
        Keep this method non-blocking or use only async-friendly I/O.
        """
        # Example pseudo-actions:
        #  - apply decay
        #  - extract resources (maybe cached)
        #  - update building progress
        #  - mark dirty if persistent state changed
        # For production use, call your resource_manager methods here.
        # Simulate some CPU work (for demo):
        await asyncio.sleep(0)  # yield control
        # pretend some change happened
        # self.resource_manager.apply_decay(delta_hours)
        # main, farm = self.extract_resources()
        # if main or farm: self.dirty = True
        return

    def snapshot(self) -> Dict[str, Any]:
        """
        Return JSON-serializable snapshot for persistence.
        """
        # Replace with a full planet state serialization
        return {"id": self.id, "name": self.name, "timestamp": time.time()}

# -------------------------
# Persistence hook (replace with DB code)
# -------------------------
async def persist_planet_snapshot(snapshot: Dict[str, Any]):
    """
    Persist snapshot to database or caching store.
    Replace with actual async DB calls (asyncpg/aiomysql/aioredis).
    Keep this function async so worker doesn't block.
    """
    # Example placeholder: replace with await db.execute(...)
    await asyncio.sleep(0)  # yield — put your DB write here
    # e.g. await db.execute("UPDATE planets SET data = $1 WHERE id = $2", json.dumps(snapshot), snapshot['id'])
    return

# -------------------------
# Worker: runs galaxy shard
# -------------------------
class SimulationWorker:
    def __init__(self, galaxy_id: str, planets: List[Planet]):
        self.galaxy_id = galaxy_id
        self.planets = planets  # list of Planet objects owned by this galaxy
        self._stop = False
        self._last_persist = time.time()
        # We keep a rotating index to pick batches
        self._index = 0

    def stop(self):
        self._stop = True

    async def _tick_planet_batch(self):
        """
        Tick a batch of planets. Advances _index circularly.
        """
        n = len(self.planets)
        if n == 0:
            await asyncio.sleep(TICK_INTERVAL)
            return

        start = self._index
        end = start + BATCH_SIZE
        # Circular slice
        batch = [self.planets[i % n] for i in range(start, end)]
        self._index = end % n

        # Schedule ticks in parallel (bounded concurrency if necessary)
        tasks = [p.tick(PLANET_TICK_HOURS_PER_CALL) for p in batch]
        # run them concurrently; they should be mostly CPU-light or async
        await asyncio.gather(*tasks)

        # check if we should persist dirty planets
        now = time.time()
        if now - self._last_persist >= PERSIST_INTERVAL:
            await self._persist_dirty_planets()
            self._last_persist = now

    async def _persist_dirty_planets(self):
        """
        Persist snapshots for planets flagged dirty. Group writes if possible.
        """
        to_persist = [p for p in self.planets if getattr(p, "dirty", False)]
        if not to_persist:
            return

        # Option 1: persist sequentially but asynchronously (simple)
        # for planet in to_persist:
        #     await persist_planet_snapshot(planet.snapshot())
        #
        # Option 2: persist concurrently (parallel DB writes) - use with care
        tasks = [persist_planet_snapshot(p.snapshot()) for p in to_persist]
        await asyncio.gather(*tasks)

        # Reset dirty flags after successful persistence
        for p in to_persist:
            p.dirty = False

    async def run(self):
        """
        Main async worker loop. Respects self._stop for graceful shutdown.
        """
        try:
            while not self._stop:
                await self._tick_planet_batch()
                await asyncio.sleep(TICK_INTERVAL)
        except asyncio.CancelledError:
            pass
        finally:
            # On shutdown, persist everything quickly (best effort)
            await self._persist_dirty_planets()

# -------------------------
# Multiprocessing wrapper (one process per galaxy)
# -------------------------
def _worker_process_entry(galaxy_id: str, planet_data: List[Dict[str, Any]]):
    """
    Entry point for a child process. Recreate all planet objects here.
    planet_data is serializable representation of planets needed to bootstrap worker.
    """
    # Recreate Planet instances (or load from DB)
    planets = [Planet(pd["id"], pd["name"]) for pd in planet_data]

    worker = SimulationWorker(galaxy_id, planets)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Setup signal handling for graceful shutdown inside the process
    def _signal_handler(signum, frame):
        worker.stop()

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    try:
        loop.run_until_complete(worker.run())
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()

# -------------------------
# Master: spawn worker processes
# -------------------------
class MasterOrchestrator:
    def __init__(self):
        self.workers: Dict[str, mp.Process] = {}

    def start_worker_for_galaxy(self, galaxy_id: str, planet_data: List[Dict[str, Any]]):
        proc = mp.Process(target=_worker_process_entry, args=(galaxy_id, planet_data), daemon=True)
        proc.start()
        self.workers[galaxy_id] = proc
        print(f"Started worker for galaxy {galaxy_id} pid={proc.pid}")

    def stop_worker(self, galaxy_id: str):
        proc = self.workers.get(galaxy_id)
        if not proc:
            return
        proc.terminate()
        proc.join(timeout=10)
        if proc.is_alive():
            proc.kill()
        del self.workers[galaxy_id]

    def shutdown_all(self):
        for gid in list(self.workers.keys()):
            self.stop_worker(gid)
