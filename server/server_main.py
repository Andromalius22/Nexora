import asyncio
import msgpack
import uuid
import time
from server.logging_setup_server import get_logger
from core.registry import *
from core.galaxy.galaxy_map import GalaxyMap
from core.buildings import BuildingManager
from server.player_manager import PlayerManager

log = get_logger("GameServer")

class GameServer:
    def __init__(self):
        self.clients = []
        self.client_locks = {}
        self.client_for_player = {}  # maps player.id → writer
        self.galaxy = None
        self.building_manager = BuildingManager()
        

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info("peername")
        log.info(f"New client connection from {addr}")

        # Wait for login packet
        raw_len = await reader.readexactly(4)
        msg_len = int.from_bytes(raw_len, "big")
        login_data = await reader.readexactly(msg_len)
        login_packet = msgpack.unpackb(login_data, raw=False)

        token = login_packet.get("token")
        name = login_packet.get("name")

        # Find or create player
        player = self.player_manager.get_or_create_player(token=token, name=name)

        # Send login confirmation
        ack_packet = {
            "type": "login_ack",
            "player_id": player.id,
            "token": player.token,
            "home_system_id": player.home_system_id,
        }
        packed_ack = msgpack.packb(ack_packet, use_bin_type=True)
        writer.write(len(packed_ack).to_bytes(4, "big") + packed_ack)
        await writer.drain()

        log.info(f"Player '{player.name}' logged in successfully.")

        # --- Associate player with this connection ---
        self.client_for_player[player.id] = writer
        self.clients.append(writer)
        self.client_locks[writer] = asyncio.Lock()

        #send registry first
        packet = {
            "type": "registry_sync",
            "registry": registry_to_dict()
        }
        # print("Server registry keys:", REGISTRY.keys())
        # print("Defense units:", list(REGISTRY["defense_units"].keys()))
        packed_registry = msgpack.packb(packet, use_bin_type=True)
        async with self.client_locks[writer]:
            writer.write(len(packed_registry).to_bytes(4, "big") + packed_registry)
            await writer.drain()
        log.debug("Sent registry data to new client")

        # Create minimal payload — later can expand to visible systems
        galaxy_data = {
            "type": "full_galaxy_sync",
            "galaxy": player.galaxy.to_dict()
        }
        packed_galaxy = msgpack.packb(galaxy_data, use_bin_type=True)
        async with self.client_locks[writer]:
            writer.write(len(packed_galaxy).to_bytes(4, "big") + packed_galaxy)
            await writer.drain()
        log.debug(f"Sent full galaxy to player '{player.name}'")

        # --------------------
        # 3️⃣ Receive loop
        # --------------------
        try:
            while True:
                raw_len = await reader.readexactly(4)
                msg_len = int.from_bytes(raw_len, "big")
                data = await reader.readexactly(msg_len)
                packet = msgpack.unpackb(data, raw=False)

                await self.handle_packet(packet, writer)
        except asyncio.IncompleteReadError:
            log.info(f"Client {addr} disconnected.")
        except Exception as e:
            log.exception(f"Error while handling client {addr}: {e}")
        finally:
            if writer in self.clients:
                self.clients.remove(writer)
            # also remove player mapping
            for pid, w in list(self.client_for_player.items()):
                if w is writer:
                    del self.client_for_player[pid]
            writer.close()
            await writer.wait_closed()
    
    # ===============================
    # Dispatcher
    # ===============================
    async def handle_packet(self, packet, writer):
        packet_type = packet.get("type")

        if packet_type == "planet_action":
            await self.handle_planet_action(packet, writer)
        else:
            log.warning(f"Unknown packet type: {packet_type}")

    # ===============================
    # Planet Action Handler
    # ===============================
    async def handle_planet_action(self, packet, writer):
        action = packet.get("action")
        planet_gloabl_id = packet.get("planet_global_id")
        data = packet.get("data")
        player_id = packet.get("player_id")

        log.info(f"Received planet action '{action}' for planet ID (gloabl ID {planet_gloabl_id}),  with data {data}.\n player_id : {player_id}")
        player = self.player_manager.get_player_by_id(player_id)
        if not player:
            log.warning(f"Player with ID {player_id} not found.")
            return
        planet = self.find_planet_by_global_id(planet_gloabl_id, player.galaxy)
        if not planet:
            log.warning(f"Planet with global ID {planet_gloabl_id} not found.")
            return

        # Apply the requested change
        # --- Dispatch the action ---
        try:
            self.handle_action(action, data, planet)
        except Exception as e:
            log.exception(f"Error while handling action '{action}' for planet {planet.name}: {e}")
            return

        # Optionally confirm to the client
        ack_packet = {
            "type": "planet_update",
            "planet_id": planet.id,
            "planet_global_id": planet.global_id,
            "action": action,
            "new_state": planet.to_dict(),
        }
        try:
            packed = msgpack.packb(ack_packet, use_bin_type=True)
            # TODO : only send to the relevant client
            async with self.client_locks[writer]:
                writer.write(len(packed).to_bytes(4, "big") + packed)
                await writer.drain()
            log.debug(f"✅ Sent planet_update ack for planet {planet.name}, global ID {planet.global_id}, local ID {planet.id}")
        except Exception as e:
            log.exception(f"Failed to send planet_update for {planet.id}: {e}")
            return

    def handle_action(self, action, data, planet):
        """
        Dynamically dispatches planet-related actions to corresponding methods.
        Example: action='set_mode' calls self.action_set_mode(planet, data)
        """
        method_name = f"action_{action}"
        method = getattr(self, method_name, None)

        if callable(method):
            method(planet, data)
        else:
            log.warning(f"[PlanetHandler] Unknown action '{action}' for planet '{planet.name}'")
    
    def action_set_mode(self, planet, data):
        planet.mode = data
        log.info(f"Planet {planet.name} mode changed to {data}")

    def action_apply_resource(self, planet, data):
        planet.set_resource(data)
        log.info(f"Planet {planet.name} current resource modified to {planet.current_resource}")

    def action_toggle_slot(self, planet, data):
        planet.data.active = not planet.data.active
        log.info(f"Planet {planet.name} slot {data} toggled to {planet.data.active}")

    def action_add_slot(self, planet, data):
        msg = planet.start_build(f"{data}", self.building_manager)
        planet.on_slots_changed(slot_type=data, action="add")
        log.info(f"Added slot '{data}' on planet {planet.name}")

    def action_remove_slot(self, planet, data):
        msg = planet.remove_building_from_slot(f"{data}")
        planet.on_slots_changed(slot_type=data, action="remove")
        log.info(f"Removed slot '{data}' on planet {planet.name}")

    def action_build_defense_unit(self, planet, data):
        msg = planet.start_build(data, self.building_manager)
        log.info(f"{planet.name} started building defense unit ID : {data}")

    # ===============================
    # Helper to locate planets
    # ===============================
    def find_planet_by_id(self, planet_id):
        for hex in self.galaxy.grid:
            if hex.feature == "star_system" and hex.contents:
                for planet in hex.contents.planets:
                    if getattr(planet, "id", None) == planet_id:
                        return planet
        return None
    
    def find_planet_by_global_id(self, global_id, galaxy):
        for hex in galaxy.grid:
            if hex.feature == "star_system" and hex.contents:
                for planet in hex.contents.planets:
                    if planet.global_id == global_id:
                        return planet
        return None

    # ===============================
    # Periodic updates
    # ===============================
    async def broadcast_deltas(self):
        while True:
            await asyncio.sleep(1)
            delta_packet = {"type": "delta", "slots": [], "resources": []}
            
            # Collect deltas from all colonized planets
            for hex in self.galaxy.grid:
                if hex.feature == "star_system":
                    system=hex.contents
                    for planet in system.planets:
                        if planet.is_colonized:
                            d = planet.compute_deltas()  # should return {"slots": [...], "resources": [...]}
                            # Make sure slots are converted to dicts if needed
                            delta_packet["slots"].extend(d.get("slots", []))
                            delta_packet["resources"].extend(d.get("resources", []))

            # Only send if there are actual changes
            if delta_packet["slots"] or delta_packet["resources"]:
                packed = msgpack.packb(delta_packet, use_bin_type=True) + b"\n"
                
                disconnected_clients = []
                for client in self.clients:
                    try:
                        client.write(packed)
                        await client.drain()
                    except (ConnectionResetError, BrokenPipeError):
                        # mark client as disconnected
                        disconnected_clients.append(client)
                
                # Remove disconnected clients safely
                for client in disconnected_clients:
                    self.clients.remove(client)
                #do this later :
                #async with self.client_locks[client]:
                #    client.write(len(packed).to_bytes(4, "big") + packed)
                #    await client.drain()
    
    async def update_builds(self):
        while True:
            await asyncio.sleep(1)
            for player in self.player_manager.all_players():
                for hex in player.galaxy.grid:
                    if hex.feature == "star_system" and hex.contents:
                        for planet in hex.contents.planets:
                            if planet.is_colonized:
                                planet.update_build_queue(1, server=self, player=player)

    async def update_production(self):
        while True:
            await asyncio.sleep(60)
            for player in self.player_manager.all_players():
                # TODO iterate through player owned tiles for less compute costs
                for hex in player.galaxy.grid:
                    if hex.feature == "star_system" and hex.contents:
                        for planet in hex.contents.planets:
                            if planet.is_colonized:
                                changed = planet.extract_resources(server=self, player=player)
    
    async def periodic_resource_sync(self):
        """
        Periodically checks all planets for resource changes and sends delta updates
        to the relevant player's client.
        """
        while True:
            await asyncio.sleep(60)  # 1-minute tick
            now = time.time()
            for player in self.player_manager.all_players():
                if not player.galaxy:
                    continue

                for hex in player.galaxy.grid:
                    if hex.feature != "star_system" or not hex.contents:
                        continue

                    for planet in hex.contents.planets:
                        if not planet.is_colonized:
                            continue

                        # Compute production
                        changed = planet.extract_resources(player=player)

                        # --- only send if resources changed significantly ---
                        if changed or now - planet._last_resource_sync > 600:  # fallback 10-min sync
                            await self.send_planet_resource_update(player, planet)
                            planet._last_sent_resources = dict(planet.resources)
                            planet._last_resource_sync = now

    async def periodic_save(self, interval=60):
        while True:
            await asyncio.sleep(interval)
            self.player_manager.save_players()
            log.debug("Periodic save of all players and galaxies completed.")


    # ===============================
    # Startup
    # ===============================

    async def start_server(self):
        log.debug("Loading registry")  
        try:      
            load_registry()
            log.debug("Registry loaded")
        except Exception as e:
            log.exception(f"Failed to load the registry, error : {e}")
            return
        log.debug("Instantiate player manager")
        self.player_manager = PlayerManager()
        server = await asyncio.start_server(self.handle_client, "0.0.0.0", 5000)
        print("Server listening on 0.0.0.0:5000")
        asyncio.create_task(self.periodic_save(60))  # save every 60s
        async with server:
            await asyncio.gather(
                server.serve_forever(),
                self.update_builds(),
                self.update_production()
            )

if __name__ == "__main__":
    gs = GameServer()
    asyncio.run(gs.start_server())