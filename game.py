import pygame
import sys
from config import *
from camera import *
from player import *
from map import *
from assetsmanager import *

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Nexora")
        self.running = True
        self.clock = pygame.time.Clock()
        self.redraw_tiles = True
        self.frame_count = 0
        self.player = Player()
        self.map = GalaxyMap(MAP_WIDTH, HEIGHT)
        self.camera = Camera(screen_width=MAP_WIDTH, screen_height=SCREEN_HEIGHT, world_width=self.map.width, world_height=self.map.height)
        self.assets = AssetsManager()
        self.tile_layer_surface = pygame.Surface((WIDTH, HEIGHT))
        self.state = 'MAIN_MENU'

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
        
        keys = pygame.key.get_pressed()
        if self.camera.move(keys):
            self.redraw_tiles = True
        if keys[pygame.K_ESCAPE]:
            self.running = False

    def update(self, time_delta):
        pass

    def draw(self):
        if self.state == 'MAIN_MENU':
            self.screen.fill((255, 255, 255))  # white background for menu
        elif self.state == 'IN_GAME' or self.state == 'TUTORIAL' :
            center = (WIDTH // 2,
                HEIGHT // 2)
            
            self.screen.fill((10, 10, 30))  # Or whatever background you want

            # Re-render tiles to the cache only if needed
            self.draw_tile_layer()
            # Always blit the cached tile layer
            self.screen.blit(self.tile_layer_surface, (0, 0))   # Will only redraw tiles when necessary
            pygame.display.flip()
    
    def draw_tile_layer(self):
        if self.redraw_tiles:
            # Clear the surface with background color
            self.tile_layer_surface.fill((10, 10, 30))  # Your background color (space blue)

            # Draw your tile map onto the cached surface
            center = (WIDTH // 2, HEIGHT // 2)
            self.map.draw(self.tile_layer_surface, center, self.assets, self.frame_count, self.player, self.camera)

            self.redraw_tiles = False  # Only redraw when something changes