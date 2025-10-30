import pygame
import pygame_gui
from core.config import *
from client.camera import *
from client.ui import *
from client.notification_panel import NotificationPanel
from client.assetsmanager import AssetsManager

class GameGUI:
    def __init__(self, game):
        self.game = game
        pygame.init()
        pygame.display.set_caption("Nexora Client")

        # --- Setup display ---
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.ui_manager = pygame_gui.UIManager((SCREEN_WIDTH, SCREEN_HEIGHT), 'client/theme.json')
        self.clock = pygame.time.Clock()
        self.running = True
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT) #dummy placeholder for now
        self.notification_panel = NotificationPanel(self.ui_manager, pygame.Rect(10, 10, 300, 200))
        self.notifications = self.game.notifications
        self.assets = AssetsManager(online_mode=True)
        self.assets.load_all_icons()
        self.font = pygame.font.SysFont("arial", 16)
        self.planet_tooltip = PlanetTooltip(self.font, self.assets)
        
        # --- Panels ---
        self.tile_info_panel = TileInfoPanel(
            self.ui_manager, 
            self.assets, pygame.Rect(SCREEN_WIDTH-300, 60, 300, 500), 
            callback_on_planet_click=self.game.on_planet_click,
            planet_tooltip=self.planet_tooltip
        )
        self.planet_mgmt_panel = PlanetManagement(
            self.ui_manager, 
            self.assets, 
            pygame.Rect(10, 60, 280, 560), #building_mgmt=self.building_manager,
            notifications_manager=self.notifications,
            on_action=self.game.on_planet_action
        )
        self.planet_mgmt_tab_row = PlanetManagementButtonsCategory(
            self.ui_manager, 
            pygame.Rect(290, 60, 600, 60),
            self.assets,
            on_action=self.game.on_planet_action
        )
        # self.planet_slots_mgmt_panel = SlotsManagement(
        #     self.ui_manager, 
        #     self.assets, 
        #     pygame.Rect(290, 120, 280, 400), #notifications_manager=self.notifications, building_mgmt=self.building_manager
        #     on_action=self.game.on_planet_action
        # )
        # self.planet_defense_mgmt_panel = PlanetaryDefenseManagement(
        #     self.ui_manager, 
        #     self.assets, 
        #     pygame.Rect(570, 60, 330, 300), #notifications_manager=self.notifications
        # )
        self.redraw_tiles = True

    def render(self, dt):
        """Draw the full game scene."""
        self.screen.fill((20, 20, 30))
        self.draw_galaxy(center=(500, 300), hex_size=HEX_SIZE)
        #draw order is important ! we draw the galaxy as background, then the pygame_gui panels, then optional, pygame elements on top of it   
        self.ui_manager.draw_ui(self.screen)
        if self.planet_mgmt_panel.panel.visible:
            self.planet_mgmt_panel.draw_overlays(self.screen)
        # Draw tooltip LAST (on top)
        self.planet_tooltip.draw(self.screen, dt)
        pygame.display.update()
    
    def draw_galaxy(self, center=(500, 300), hex_size=HEX_SIZE, current_empire=None):
            cam_offset = self.camera.offset            
            if self.game.player_id:
                current_empire=self.game.player_id
            for hex in self.game.galaxy:
                # print(f"self.game.player_id: {current_empire}")
                # print(f"hex.owner_id: {hex.owner_id}")
                # print(f"hex.reserved_id: {hex.reserved_id}")
                points = hex.polygon(center, hex_size, cam_offset)

                # Draw the hex border
                color = (100, 100, 100)
                # --- Draw fill based on feature ---
                if hex.owner_id == current_empire:
                    if hex.feature == "star_system":
                        pygame.draw.polygon(self.screen, (255, 255, 0), points)
                        hx, hy = hex.hex_to_pixel(center, hex_size, cam_offset)
                        pygame.draw.circle(self.screen, (255, 255, 255), (int(hx), int(hy)), 6)
                    elif hex.feature == "nebula":
                        pygame.draw.polygon(self.screen, (100, 150, 255), points)
                    elif hex.feature == "asteroid_field":
                        pygame.draw.polygon(self.screen, (120, 120, 120), points)
                    elif hex.feature == "black_hole":
                        pygame.draw.polygon(self.screen, (0, 0, 0), points)
                    else:
                        pygame.draw.polygon(self.screen, (30, 30, 40), points)
                else :
                    pygame.draw.polygon(self.screen, (10, 10, 15), points)
                # Border
                pygame.draw.polygon(self.screen, (60, 60, 80), points, 1)
    
    # def show_planet_panel(self, planet):
    #     self.planet_mgmt_panel.show(planet, self.resource_data)
    #     self.planet_slots_mgmt_panel.show(planet)
    #     self.planet_defense_mgmt_panel.show(planet)

    def update(self, dt):
        """Update UI and animations."""
        self.ui_manager.update(dt)
    
    def close_window(self):
        if self.tile_info_panel.visible:
            self.tile_info_panel.hide()
            self.tile_info_panel.visible=False
        if self.planet_mgmt_panel.panel.visible:
            self.planet_mgmt_panel.panel.visible=False
            self.planet_mgmt_panel.hide()
        # if self.planet_slots_mgmt_panel.panel.visible:
        #     self.planet_slots_mgmt_panel.panel.visible=False
        #     self.planet_slots_mgmt_panel.hide()
        # if self.planet_defense_mgmt_panel.panel.visible:
        #     self.planet_defense_mgmt_panel.panel.visible=False
        #     self.planet_defense_mgmt_panel.hide()

    def dispatch_event_to_active_panel(self, event):
        active_panel = next(
            (p for p in self.planet_mgmt_tab_row.panels.values() if getattr(p, "visible", False)),
            None
        )
        if not active_panel:
            print("no active panel")
            return
        if hasattr(active_panel, "process_event"):  # pygame_gui panel
            active_panel.process_event(event)
        elif hasattr(active_panel, "handle_events"):  # raw pygame panel
            active_panel.handle_events(event)