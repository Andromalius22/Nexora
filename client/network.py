import asyncio
from webbrowser import get
import msgpack
from core.galaxy.hex import Hex
from core.config import FEATURE_NAMES
from server.hexcordencoder import ext_decoder
from core.registry import registry_from_dict, REGISTRY
from client.assetsmanager import AssetsManager
from core.logger_setup import get_logger
from core.slot import Slot
from client.client_config import load_client_config, save_client_config

log = get_logger("NetworkClient")

class NetworkClient:
    def __init__(self, server_ip="192.168.0.40", server_port=5000):
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_galaxy = []   # replaces planets[]
        self.connected = False

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(
            self.server_ip, self.server_port
        )

        # Load saved token if available
        config = load_client_config()
        token = config.get("token")
        player_name = config.get("name", "Player1")

        # Send login packet
        login_packet = {
            "type": "login",
            "name": player_name,
            "token": token  # can be None if first time
        }
        packed = msgpack.packb(login_packet, use_bin_type=True)
        self.writer.write(len(packed).to_bytes(4, "big") + packed)
        await self.writer.drain()

        # Receive login_ack
        raw_len = await self.reader.readexactly(4)
        msg_len = int.from_bytes(raw_len, "big")
        data = await self.reader.readexactly(msg_len)
        ack = msgpack.unpackb(data, raw=False)

        if ack.get("type") == "login_ack":
            self.player_id = ack["player_id"]
            token = ack["token"]
            home_system_id = ack["home_system_id"]
            print(f"✅ Logged in as {player_name} (ID: {self.player_id})")
            print(f"Home system ID: {home_system_id}")

            # Save for next time
            config["token"] = token
            config["name"] = player_name
            save_client_config(config)

        else:
            print("⚠️ Unexpected login response:", ack)
            return


        self.connected = True
        log.debug(f"Connected to server {self.server_ip}:{self.server_port}")

        # --------------------------
        # 1️⃣ Receive the registry
        # --------------------------
        raw_len = await self.reader.readexactly(4)
        msg_len = int.from_bytes(raw_len, "big")
        data = await self.reader.readexactly(msg_len)

        packet = msgpack.unpackb(data, raw=False)
        if packet.get("type") != "registry_sync":
            raise RuntimeError(f"Expected registry_sync, got {packet.get('type')}")

        # Rebuild the global registry
        registry_from_dict(packet["registry"])
        log.debug(f"✅ Loaded registry with {len(REGISTRY['all'])} total entries.")


        # 1️⃣ Read message length and data
        raw_len = await self.reader.readexactly(4)
        msg_len = int.from_bytes(raw_len, "big")
        data = await self.reader.readexactly(msg_len)

        # 2️⃣ Unpack MsgPack with HexCoord decoding
        #full_sync = msgpack.unpackb(data, ext_hook=ext_decoder, raw=False)
        packet = msgpack.unpackb(data, ext_hook=ext_decoder, raw=False)
        if packet.get("type") != "full_galaxy_sync":
            raise RuntimeError(f"Expected full_galaxy_sync, got {packet.get('type')}")

        # 3️⃣ Extract hexes list
        hex_data_list = packet.get("galaxy", []).get("grid", [])
        #print(f"hex_data_list: {hex_data_list}")
        # Convert hexes to Hex objects
        self.client_galaxy = [Hex.from_dict(h) for h in hex_data_list]


        #if msg_type == "full_sync" and "hexes" in full_sync:
        #self.client_galaxy = [Hex.from_dict(h) for h in full_sync]
            #self.galaxy = [Hex.from_dict(h) for h in full_sync["galaxy"]]
        log.debug(f"[DEBUG] Received galaxy with {len(self.client_galaxy)} hexes")
        #else:
        #    print("[WARN] Unexpected packet type or missing galaxy data:", full_sync)

        # --- Start listening for deltas in background ---
        #asyncio.create_task(self.receive_deltas())

        # Step 3️⃣: Start listening for updates
        asyncio.create_task(self.listen())
    
    # =============================
    # Listen for incoming messages
    # =============================
    async def listen(self):
        """Continuously receive packets from the server."""
        try:
            while True:
                raw_len = await self.reader.readexactly(4)
                msg_len = int.from_bytes(raw_len, "big")
                data = await self.reader.readexactly(msg_len)
                packet = msgpack.unpackb(data, raw=False)

                await self.handle_packet(packet)

        except asyncio.IncompleteReadError:
            log.warning("Connection closed by server.")
            self.connected = False
        except Exception as e:
            log.exception(f"Error in network loop: {e}")
            self.connected = False
        finally:
            if self.writer:
                try:
                    self.writer.close()
                    await self.writer.wait_closed()
                except Exception:
                    pass
    
    # =============================
    # Packet dispatcher
    # =============================
    async def handle_packet(self, packet):
        ptype = packet.get("type")

        if ptype == "delta":
            self.apply_deltas(packet)
        elif ptype == "planet_update":
            log.debug("Received ack packet from server, update local planet...")
            self.update_local_planet(packet)
        elif ptype == "planet_resource_update":
            log.debug("Received planet resource update from server")
            self.update_local_planet_resource(packet)
        else:
            log.debug(f"Unhandled packet type: {ptype}")

    # =============================
    # Apply server-side deltas
    # =============================
    def apply_deltas(self, packet):
        slots = packet.get("slots", [])
        resources = packet.get("resources", [])

        if not (slots or resources):
            return

        log.debug(f"Applying {len(slots)} slot and {len(resources)} resource deltas.")

        # Example: if you store planets by ID, you can directly update them here
        for s in slots:
            pid = s.get("planet_id")
            planet = self.find_planet_by_id(pid)
            if planet:
                planet.apply_slot_delta(s)

        for r in resources:
            pid = r.get("planet_id")
            planet = self.find_planet_by_id(pid)
            if planet:
                planet.apply_resource_delta(r)

        if hasattr(self, "on_deltas_applied"):
            self.on_deltas_applied(slots, resources)

    # =============================
    # Handle planet updates
    # =============================
    def update_local_planet(self, packet):
        """Update local planet state after server-confirmed change."""
        planet_id = packet.get("planet_global_id")
        new_state = packet.get("new_state")

        if planet_id is None:
            log.warning(f"update_local_planet() called without planet_id.\n packet : {packet}")
            return
        if not self.client_galaxy:
            log.warning("No galaxy loaded yet when updating planet.")
            return

        planet = self.find_planet_by_global_id(planet_id)
        if not planet:
            log.warning(f"Planet with ID {planet_id} not found locally.")
            return

        try:
            self.apply_planet_state(planet, new_state)
            log.info(f"✅ Updated planet {planet.name} (ID={planet_id}) after server confirmation.")
        except Exception as e:
            log.exception(f"Error updating planet {planet_id}: {e}")
            return

        # Optional: refresh GUI elements if registered
        if hasattr(self, "on_planet_updated") and callable(self.on_planet_updated):
            self.on_planet_updated(planet)
        
    def apply_planet_state(self, planet, new_state):
        """
        Merge the new_state dict into an existing Planet instance.
        Only updates mutable fields, keeps references intact.
        """
        # Keep local star_system reference
        star_system = planet.star_system

        # Replace simple attributes
        planet.name = new_state.get("name", planet.name)
        planet.is_colonized = new_state.get("is_colonized", planet.is_colonized)
        planet.mode = new_state.get("mode", getattr(planet, "mode", None))
        planet.current_resource = new_state.get("current_resource", getattr(planet, "current_resource", None))
        planet.population_max = new_state.get("population_max", planet.population_max)

        # Update slots
        if "slots" in new_state:
            planet.slots = [Slot.from_dict(s) for s in new_state["slots"]]

        # Update resources
        if "resources" in new_state:
            planet.resources = new_state["resources"]

        # Reassign star_system to preserve local linkage
        planet.star_system = star_system

    def update_local_planet_resource(self, packet):
        pid = packet.get("planet_global_id")
        new_resources = packet.get("resources", {})
        planet = self.find_planet_by_global_id(pid)
        if not planet:
            log.warning(f"Planet {pid} not found for resource update.")
            return
        planet.resources = new_resources
        planet.statistics = packet.get("statistics", {})
        if hasattr(self, "on_resources_updated") and callable(self.on_resources_updated):
            self.on_resources_updated(planet)

    # =============================
    # Helpers
    # =============================
    def find_planet_by_id(self, planet_id):
        """Find a planet object in the current galaxy by ID."""
        for hex in self.client_galaxy:
            if hex.feature == "star_system" and hex.contents:
                for planet in hex.contents.planets:
                    if getattr(planet, "id", None) == planet_id:
                        return planet
        return None
    
    def find_planet_by_global_id(self, global_id):
        for hex in self.client_galaxy:
            if hex.feature == "star_system" and hex.contents:
                for planet in hex.contents.planets:
                    if planet.global_id == global_id:
                        return planet
        return None


    async def send_planet_action(self, action, planet_global_id, planet_id, data=None):
        """Send a planet action (e.g., set_mode, apply_resource) to the server."""

        packet = {
            "type": "planet_action",
            "action": action,
            "global_id": planet_global_id,
            "planet_id": planet_id,
            "data": data,
        }
        log.debug(f"Client sending planet_action '{action}' for planet {planet_id}.")
        await self.send_packet(packet)
        log.debug(f"Client finished sending, connection open: {self.connected}")
    
    async def send_packet(self, packet: dict):
        """Helper to send any MsgPack-framed packet."""
        if not self.connected:
            log.warning("Attempted to send while disconnected.")
            return
        packed = msgpack.packb(packet, use_bin_type=True)
        self.writer.write(len(packed).to_bytes(4, "big") + packed)
        await self.writer.drain()

    async def receive_deltas(self):
        while True:
            try:
                line = await self.reader.readline()
                if not line:
                    print("[DEBUG] Connection closed by server.")
                    break

                delta = msgpack.unpackb(line.rstrip(b"\n"), raw=False)
                self.handle_delta(delta)

            except Exception as e:
                print(f"[ERROR] Delta receive failed: {e}")
                break

    def handle_delta(self, delta):
        """
        Handle incremental updates sent by the server.
        Example: updating a planet or star system resource.
        """
        if delta.get("type") == "delta":
            # Update local structures
            print("[DEBUG] Received delta packet:", delta)
            # TODO: Apply changes to galaxy data structures here
