import asyncio
from core.config import *
from core.buildings import BuildingManager
from client.camera import Camera
from core.notifications import NotificationManager
from client.assetsmanager import AssetsManager
from core.logger_setup import get_logger

log = get_logger("GameClient")

class Game:
    def __init__(self, galaxy, network=None, online=False):
        self.galaxy = galaxy  # list of Hexes
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.selected_hex = None
        self.building_manager = BuildingManager()
        self.notifications = NotificationManager()
        self.selected_planet = None
        self.gui = None #set later to prevent circular references
        self.online=online
        self.network=network # instance of NetworkClient if online
        if network:
            self.player_id=network.player_id

    def update(self, dt):
        """Advance game logic each frame (non-UI)."""
        # e.g., animations, resource ticking, etc.
        self.gui.notification_panel.update(self.notifications.get_visible())
        #self.gui.tile_info_panel.update_tooltips(mouse_pos)

    def select_hex(self, hex):
        self.selected_hex = hex
        print(f"Selected {hex.feature} at ({hex.q}, {hex.r})")
    
    def on_planet_click(self, planet):
        """Called by UI when player clicks a planet."""
        self.selected_planet = planet
        #print(f"Planet clicked: {planet.name}")
        self.gui.planet_mgmt_panel.show(planet)
        #self.gui.planet_slots_mgmt_panel.show(planet)
        self.gui.planet_mgmt_tab_row.show(planet)
    
    def on_planet_action(self, action, planet, data=None):
        """Called by the UI when the player interacts with a planet."""
        print(f"[Game] UI requested action {action} for {planet.name}, with data: {data}")

        if self.online:
            # Schedule async send (don't block main loop)
            asyncio.create_task(self.send_planet_action_to_server(action, planet, data))
        else:
            # Handle locally
            self.handle_planet_action_local(action, planet, data)
    
    def handle_planet_action_local(self, action, planet, data=None):
        """Offline mode: apply changes directly."""
        if action == "apply_resource":
            planet.set_resource(data)
        elif action == "set_mode":
            planet.mode = data
        elif action == "toggle_slot":
            #Here data is a slot
            if data in planet.slots:
                data.active = not data.active
        
        elif action == "add_slot":
            #Here data is slot_type
            msg = planet.start_build(f"{data}", self.building_manager)
            planet.on_slots_changed(slot_type=data, action="add")
            #self.show_info(self.selected_planet)  # refresh UI
            #self.notifications.show(msg)
        elif action == "remove_slot":
            msg = planet.remove_building_from_slot(f"{data}")
            planet.on_slots_changed(slot_type=data, action="remove")
        else:
            print(f"[Game] Unknown local action: {action}")
    
    async def send_planet_action_to_server(self, action, planet, data=None, resource=None):
        """Online mode: send planet action request to server."""
        if not self.network or not self.network.connected:
            print("[Game] Warning: network client not connected!")
            return

        packet = {
            "type": "planet_action",
            "action": action,
            "planet_global_id": planet.global_id,
            "planet_id": planet.id,
            "data": data,
            "resource": resource,
            "player_id":self.player_id
        }

        # Use the network client's dedicated method
        await self.network.send_packet(packet)
        log.debug(f"[Game] Sent planet action '{action}' for {planet.name} to server.")    

