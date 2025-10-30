import pygame
import pygame_gui
import sys
from config import *
from camera import *
from player import *
from map import *
from assetsmanager import *
from world import *
from ui import *
from registry import *

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, 600))
        self.ui_manager = pygame_gui.UIManager((SCREEN_WIDTH, SCREEN_HEIGHT), 'theme.json') #480, 800 for more mobile-like
        pygame.display.set_caption("Nexora")
        self.running = True
        self.clock = pygame.time.Clock()
        self.redraw_tiles = True
        self.frame_count = 0
        load_registry()
        self.map = GalaxyMap(MAP_WIDTH, HEIGHT)
        self.camera = Camera(screen_width=MAP_WIDTH, screen_height=SCREEN_HEIGHT, world_width=self.map.width, world_height=self.map.height)
        with open("resources.json") as f:
            self.resource_data = json.load(f)
        self.assets = AssetsManager()
        self.assets.load_resource_icons(self.resource_data)
        with open("refined.json") as f:
            refined_data = json.load(f)
        self.assets.load_resource_icons(refined_data)
        self.assets.load_unit_icons()
        #load icons manually
        self.assets.load_image("mine_icon", "assets/icons/mine_cart.png")
        self.assets.load_image("farm_icon", "assets/icons/farm.png")
        self.assets.load_image("industry_icon", "assets/icons/industry.jpg")
        self.assets.load_image("refine_icon", "assets/icons/steell_mill_02.png")
        self.assets.load_image("energy_icon", "assets/icons/energy.png")
        self.assets.load_image("ore_icon", "assets/icons/ore.png", size=(32, 32))
        self.assets.load_image("gas_icon", "assets/icons/gas.png", size=(32, 32))
        self.assets.load_image("organics_icon", "assets/icons/organics.png", size=(32, 32)) #used for organics resource category and farm buildings
        self.assets.load_image("liquid_icon", "assets/icons/liquid.png", size=(32, 32))
        self.assets.load_image("plus_icon", "assets/icons/plus-box.png", size=(18, 18))
        self.assets.load_image("plus_02_icon", "assets/icons/plus_02.png", size=(18, 18))
        self.assets.load_image("moins_icon", "assets/icons/moins.png", size=(18, 18))
        self.assets.load_image("hammer_icon", "assets/icons/hammer.png", size=(10, 10))
        self.assets.load_image("credit_icon", "assets/icons/coin.png")
        self.assets.load_image("defense_icon", "assets/icons/phased_shield.png")

        # Load planet type icons
        self.assets.load_planets_icons()
        self.tile_layer_surface = pygame.Surface((WIDTH, HEIGHT))
        self.notifications = NotificationManager(self.ui_manager, self.screen.get_rect())
        self.building_manager = BuildingManager()
        self.tile_info_panel = TileInfoPanel(self.ui_manager, self.assets, pygame.Rect(SCREEN_WIDTH-300, 60, 300, 500), callback_on_planet_click=self.show_planet_panel)
        # Planet management panel on the left
        self.planet_mgmt_panel = PlanetManagement(self.ui_manager, self.assets, pygame.Rect(10, 60, 280, 480), building_mgmt=self.building_manager, notifications_manager=self.notifications)
        self.planet_slots_mgmt_panel = SlotsManagement(self.ui_manager, self.assets, pygame.Rect(290, 60, 280, 400), notifications_manager=self.notifications, building_mgmt=self.building_manager)
        self.planet_defense_mgmt_panel = PlanetaryDefenseManagement(self.ui_manager, self.assets, pygame.Rect(570, 60, 330, 300), notifications_manager=self.notifications)
        
        self.state = 'MAIN_MENU'
        

        # Main menu background image (safe fallback)
        self.menu_bg = None
        try:
            bg_surface = pygame.image.load("assets/images/nebulae_01.jpg").convert()
            self.menu_bg = pygame.transform.scale(bg_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
        except Exception as e:
            print(f"[Game] Menu background not found or failed to load: {e}")
        
        self.time_since_last_second = 0.0

        #UI
        # Container for main menu buttons
        self.main_menu_panel = pygame_gui.elements.UIPanel(relative_rect=pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT),
                                                          starting_height=1,
                                                          manager=self.ui_manager)

        self.setup_ui()

    def setup_ui(self):

         # Create buttons
        self.button_tutoriel = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((SCREEN_WIDTH//2 - 100, 150), (200, 50)),
                                                           text='Tutoriel',
                                                           manager=self.ui_manager,
                                                           container=self.main_menu_panel
                                                           )
        self.button_new_game = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((SCREEN_WIDTH//2 - 100, 220), (200, 50)),
                                                           text='New Game',
                                                           manager=self.ui_manager,
                                                           container=self.main_menu_panel
                                                           )
        self.button_load_game = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((SCREEN_WIDTH//2 - 100, 290), (200, 50)),
                                                           text='Load Game',
                                                           manager=self.ui_manager,
                                                           container=self.main_menu_panel
                                                           )
        self.button_multiplayers = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((SCREEN_WIDTH//2 - 100, 360), (200, 50)),
                                                               text='Multiplayers',
                                                               manager=self.ui_manager,
                                                               container=self.main_menu_panel
                                                               )

        # Parameters menu (hidden by default)
        self.params_panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect((SCREEN_WIDTH//2 - 220, SCREEN_HEIGHT//2 - 160), (440, 320)),
            starting_height=2,
            manager=self.ui_manager,
            visible=False
        )
        # Title
        self.params_title = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(0, 10, 440, 30),
            text='New Game Parameters',
            manager=self.ui_manager,
            container=self.params_panel
        )
        # Galaxy size
        self.label_galaxy_size = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(20, 60, 140, 24),
            text='Galaxy Size',
            manager=self.ui_manager,
            container=self.params_panel
        )
        self.dropdown_galaxy_size = pygame_gui.elements.UIDropDownMenu(
            options_list=['Small','Medium','Large'],
            starting_option='Medium',
            relative_rect=pygame.Rect(180, 60, 200, 28),
            manager=self.ui_manager,
            container=self.params_panel
        )
        # Star density
        self.label_star_density = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(20, 110, 140, 24),
            text='Star Density',
            manager=self.ui_manager,
            container=self.params_panel
        )
        self.slider_star_density = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=pygame.Rect(180, 110, 200, 24),
            start_value=50,
            value_range=(0,100),
            manager=self.ui_manager,
            container=self.params_panel
        )
        self.value_star_density = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(390, 110, 40, 24),
            text='50',
            manager=self.ui_manager,
            container=self.params_panel
        )
        # Nebula density (example extra)
        self.label_nebula_density = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(20, 150, 140, 24),
            text='Nebula Density',
            manager=self.ui_manager,
            container=self.params_panel
        )
        self.slider_nebula_density = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=pygame.Rect(180, 150, 200, 24),
            start_value=20,
            value_range=(0,100),
            manager=self.ui_manager,
            container=self.params_panel
        )
        self.value_nebula_density = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(390, 150, 40, 24),
            text='20',
            manager=self.ui_manager,
            container=self.params_panel
        )
        # --- Label ---
        self.empire_name_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(20, 180, 150, 30),
            text="Empire Name:",
            manager=self.ui_manager,
            container=self.params_panel
        )

        # --- Text Entry Field ---
        self.empire_name_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(170, 180, 200, 30),
            manager=self.ui_manager,
            container=self.params_panel
        )
        #self.empire_name_entry.set_text(self.empire_name)
        # Buttons
        self.button_params_start = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(240, 260, 180, 36),
            text='Start',
            manager=self.ui_manager,
            container=self.params_panel
        )
        self.button_params_back = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(20, 260, 180, 36),
            text='Back',
            manager=self.ui_manager,
            container=self.params_panel
        )

    def show_planet_panel(self, planet):
        self.planet_mgmt_panel.show(planet, self.resource_data)
        self.planet_slots_mgmt_panel.show(planet)
        self.planet_defense_mgmt_panel.show(planet)

    def run(self):
        while self.running:
            time_delta = self.clock.tick(60) / 1000.0  # seconds passed since last frame
            self.handle_events()
            self.update(time_delta)
            self.draw()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            self.ui_manager.process_events(event)
            
            if event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
                if event.ui_element == self.slider_star_density:
                    self.value_star_density.set_text(str(int(self.slider_star_density.get_current_value())))
                elif event.ui_element == self.slider_nebula_density:
                    self.value_nebula_density.set_text(str(int(self.slider_nebula_density.get_current_value())))
            
            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.button_new_game:
                    # Show parameters menu instead of starting immediately
                    self.main_menu_panel.hide()
                    self.params_panel.show()
                elif event.ui_element == self.button_params_back:
                    # Go back to main menu
                    self.params_panel.hide()
                    self.main_menu_panel.show()
                elif event.ui_element == self.button_params_start:
                    # Read parameters and start game
                    size_option = self.dropdown_galaxy_size.selected_option
                    star_density = int(self.slider_star_density.get_current_value())
                    nebula_density = int(self.slider_nebula_density.get_current_value())
                    empire_name = self.empire_name_entry.get_text().strip()
                    if not empire_name:
                        empire_name = "Unnamed Empire"  # Fallback
                    # Map size mapping
                    if size_option == 'Small':
                        map_width, map_height = 24, 18
                    elif size_option == 'Large':
                        map_width, map_height = 56, 42
                    else:  # Medium
                        map_width, map_height = 36, 27
                    # Create new galaxy map with parameters
                    self.map = GalaxyMap(map_width, map_height, star_density=star_density, nebula_density=nebula_density)
                    # Reset camera to new map bounds
                    self.camera = Camera(screen_width=MAP_WIDTH, screen_height=SCREEN_HEIGHT, world_width=self.map.width, world_height=self.map.height)
                    # Force redraw of tile layer
                    self.redraw_tiles = True
                    # Store settings for later use
                    self.new_game_settings = {
                        'galaxy_size': size_option,
                        'star_density': star_density,
                        'nebula_density': nebula_density,
                        'map_width': map_width,
                        'map_height': map_height
                    }
                    self.params_panel.hide()
                    #setting up empires and players seetings
                    player = Player()
                    self.player=player #change this in the future
                    empire=Empire(player, name=empire_name, color=(255,255,0))
                    self.empires=[empire]
                    def get_random_start_tile():
                        """Return a random valid tile for an empire start."""
                        valid_tiles = [
                            h for h in self.map.all_hexes()
                            if h.feature == "star_system"  # or h.feature in ['star_system', 'habitable'] depending on your logic
                            and h.owner is None
                        ]

                        if not valid_tiles:  # fallback if no star systems; later create an UI window : go back (to map settings), other options...
                            valid_tiles = [
                                h for h in self.map.all_hexes()
                                if h.feature not in ("nebula", "void")
                                and h.owner is None
                            ]

                        return random.choice(valid_tiles) if valid_tiles else None
                    
                    start_tile = get_random_start_tile()
                    if start_tile:
                        start_tile.owner = empire
                        empire.home_tile = start_tile
                        empire.tiles_owned.add(start_tile)
                        print(f"[GAME - Empire Start] {empire.name} starts at {start_tile.q}, {start_tile.r}")
                        for planet in start_tile.contents.planets:
                            planet.is_colonized=True

                        # Optionally mark the tile visually
                        start_tile.highlight_color = (255, 255, 0)
                    else:
                        print(f"[GAME - Warning] No valid start tile found for empire {empire.name} !")

                    self.current_empire=empire
                    self.state = 'IN_GAME'
            
            if self.state == 'IN_GAME':

                self.ui_manager.process_events(event)

                # Pass all events to active UI panels first
                if self.tile_info_panel.visible:
                    self.tile_info_panel.handle_events(event)
                if self.planet_mgmt_panel.panel.visible:
                    self.planet_mgmt_panel.process_event(event, self.tile_info_panel.selected_planet)
                if self.planet_slots_mgmt_panel.panel.visible:
                    self.planet_slots_mgmt_panel.process_events(event)
                if self.planet_defense_mgmt_panel.panel.visible:
                    self.planet_defense_mgmt_panel.process_event(event)
                
                # Determine if any panel is currently visible
                any_panel_visible = (
                    self.tile_info_panel.visible or
                    self.planet_mgmt_panel.panel.visible or
                    self.planet_slots_mgmt_panel.panel.visible or
                    self.planet_defense_mgmt_panel.panel.visible
                )
            
                # Map click logic (only if mouse not over UI)
                if not any_panel_visible and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mouse_pos = pygame.mouse.get_pos()

                    # # Skip map clicks if mouse over any UI element
                    # if self.ui_manager.get_hovering_any_element():
                    #     continue  # Let pygame_gui handle it

                    # Otherwise, process map click
                    center = (WIDTH // 2, HEIGHT // 2)
                    cam_offset = self.camera.get_offset() if self.camera else (0, 0)
                    found = None
                    for h in self.map.all_hexes():
                        if h.contains_point(mouse_pos, center, pixel_offset=cam_offset):
                            found = h
                            break

                    if found:
                        self.tile_info_panel.show_info(found)
                        if self.tile_info_panel.selected_planet:
                            print("test if")
                            self.planet_mgmt_panel.show(self.tile_info_panel.selected_planet, self.resource_data)
                            self.planet_slots_mgmt_panel.show(self.tile_info_panel.selected_planet)
                            
                    else:
                        self.tile_info_panel.hide()
                        self.planet_mgmt_panel.hide()
                
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                    if self.tile_info_panel.visible:
                        self.tile_info_panel.hide()
                        self.tile_info_panel.visible=False
                    if self.planet_mgmt_panel.panel.visible:
                        self.planet_mgmt_panel.panel.visible=False
                        self.planet_mgmt_panel.hide()
                    if self.planet_slots_mgmt_panel.panel.visible:
                        self.planet_slots_mgmt_panel.panel.visible=False
                        self.planet_slots_mgmt_panel.hide()
                    if self.planet_defense_mgmt_panel.panel.visible:
                        self.planet_defense_mgmt_panel.panel.visible=False
                        self.planet_defense_mgmt_panel.hide()

        keys = pygame.key.get_pressed()
        if self.camera.move(keys):
            self.redraw_tiles = True
        if keys[pygame.K_ESCAPE]:
            self.running = False

    def update(self, time_delta):
        # Always update the UI manager each frame (mandatory)
        self.ui_manager.update(time_delta)

        self.time_since_last_second += time_delta
        
        # Update tooltips if in game
        if self.state == 'IN_GAME':
            mouse_pos = pygame.mouse.get_pos()
            self.tile_info_panel.update_tooltips(mouse_pos)
            self.planet_mgmt_panel.update_tooltips(mouse_pos)
            self.planet_slots_mgmt_panel.update_tooltips(mouse_pos)
            self.planet_defense_mgmt_panel.update_tooltips(mouse_pos)
            if self.time_since_last_second >= 1.0:  # one second passed
                self.notifications.update()
                for empire in self.empires:
                    for tile in empire.tiles_owned:
                        if tile.feature=='star_system':
                            for p in tile.contents.planets:
                                p.update_build_queue(time_delta * p.industry_points, self.notifications)
                                p.extract_resources()
                self.time_since_last_second -= 1.0  # reset counter but keep any leftover


    def draw(self):
        if self.state == 'MAIN_MENU':
            if self.menu_bg:
                self.screen.blit(self.menu_bg, (0, 0))
            else:
                self.screen.fill((255, 255, 255))  # white background for menu
        elif self.state == 'IN_GAME' or self.state == 'TUTORIAL' :
            center = (WIDTH // 2,
                HEIGHT // 2)
            
            self.screen.fill((10, 10, 30))  # Or whatever background you want

            # Re-render tiles to the cache only if needed
            self.draw_tile_layer()
            # Always blit the cached tile layer
            self.screen.blit(self.tile_layer_surface, (0, 0))   # Will only redraw tiles when necessary
        self.ui_manager.draw_ui(self.screen)
        self.planet_mgmt_panel.draw_overlays(self.screen)
        
        # Draw tooltips after UI
        if self.state == 'IN_GAME':
            self.tile_info_panel.draw_tooltips(self.screen)
            self.planet_mgmt_panel.draw_tooltips(self.screen)
            self.planet_slots_mgmt_panel.draw_tooltips(self.screen)
            self.planet_defense_mgmt_panel.draw_tooltips(self.screen)
        
        pygame.display.flip()
    
    def draw_tile_layer(self):
        if self.redraw_tiles:
            # Clear the surface with background color
            self.tile_layer_surface.fill((10, 10, 30))  # Your background color (space blue)

            # Draw your tile map onto the cached surface
            center = (WIDTH // 2, HEIGHT // 2)
            self.map.draw(self.tile_layer_surface, center, self.assets, self.frame_count, self.player, self.camera, self.current_empire)

            self.redraw_tiles = False  # Only redraw when something changes