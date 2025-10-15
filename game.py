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

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        self.ui_manager = pygame_gui.UIManager((SCREEN_WIDTH, SCREEN_HEIGHT), 'theme.json') #480, 800 for more mobile-like
        pygame.display.set_caption("Nexora")
        self.running = True
        self.clock = pygame.time.Clock()
        self.redraw_tiles = True
        self.frame_count = 0
        self.player = Player()
        self.map = GalaxyMap(MAP_WIDTH, HEIGHT)
        self.camera = Camera(screen_width=MAP_WIDTH, screen_height=SCREEN_HEIGHT, world_width=self.map.width, world_height=self.map.height)
        with open("resources.json") as f:
            resource_data = json.load(f)
        self.assets = AssetsManager()
        self.assets.load_resource_icons(resource_data)
        with open("refined.json") as f:
            refined_data = json.load(f)
        self.assets.load_resource_icons(refined_data)
        
        # Load planet type icons
        with open("planet_types.json") as f:
            planet_types_data = json.load(f)
        self.assets.load_planets_icons(planet_types_data)
        self.tile_layer_surface = pygame.Surface((WIDTH, HEIGHT))
        self.state = 'MAIN_MENU'
        self.tile_info_panel = TileInfoPanel(self.ui_manager, self.assets, pygame.Rect(SCREEN_WIDTH-300, 10, 300, 400))

        # Main menu background image (safe fallback)
        self.menu_bg = None
        try:
            bg_surface = pygame.image.load("assets/images/nebulae_01.jpg").convert()
            self.menu_bg = pygame.transform.scale(bg_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
        except Exception as e:
            print(f"[Game] Menu background not found or failed to load: {e}")

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
        
            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.button_new_game:
                    self.state = 'IN_GAME'
                    self.main_menu_panel.hide()
            #--- HEX TILE CLICK DETECTION
            if self.state == 'IN_GAME' and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = pygame.mouse.get_pos()
                center = (WIDTH // 2, HEIGHT // 2)
                cam_offset = self.camera.get_offset() if self.camera else (0,0)
                found = None
                for h in self.map.all_hexes():
                    if h.contains_point(mouse_pos, center, pixel_offset=cam_offset):
                        found = h
                        break
                if found:
                    self.tile_info_panel.show(found)
                else:
                    self.tile_info_panel.hide()
        keys = pygame.key.get_pressed()
        if self.camera.move(keys):
            self.redraw_tiles = True
        if keys[pygame.K_ESCAPE]:
            self.running = False

    def update(self, time_delta):
        # Always update the UI manager each frame (mandatory)
        self.ui_manager.update(time_delta)
        
        # Update tooltips if in game
        if self.state == 'IN_GAME':
            mouse_pos = pygame.mouse.get_pos()
            self.tile_info_panel.update_tooltips(mouse_pos)

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
        
        # Draw tooltips after UI
        if self.state == 'IN_GAME':
            self.tile_info_panel.draw_tooltips(self.screen)
        
        pygame.display.flip()
    
    def draw_tile_layer(self):
        if self.redraw_tiles:
            # Clear the surface with background color
            self.tile_layer_surface.fill((10, 10, 30))  # Your background color (space blue)

            # Draw your tile map onto the cached surface
            center = (WIDTH // 2, HEIGHT // 2)
            self.map.draw(self.tile_layer_surface, center, self.assets, self.frame_count, self.player, self.camera)

            self.redraw_tiles = False  # Only redraw when something changes