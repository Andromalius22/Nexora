import pygame
import pygame_gui
import json
import os
from assetsmanager import AssetsManager

PLANET_ICON_PLACEHOLDER = "assets/resources/question.png"  # Placeholder for planet type icon
SLOTS_ICON_PLACEHOLDER = "assets/icons/star_empty.png"  # Placeholder for used slots icon
DEFENSE_ICON_PLACEHOLDER = "assets/icons/star_full.png"  # Placeholder for defense icon

class TileInfoPanel:
    def __init__(self, ui_manager, assets, rect):
        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=rect,
            starting_height=1,
            manager=ui_manager,
            visible=False
        )
        self.assets = assets
        self.ui_manager = ui_manager
        # These UI objects will be managed when showing panel
        self._objects = []
        # Preload default icons once using assetsmanager for performance
        self.planet_icon = pygame.image.load(PLANET_ICON_PLACEHOLDER).convert_alpha()
        self.slots_icon = pygame.image.load(SLOTS_ICON_PLACEHOLDER).convert_alpha()
        self.defense_icon = pygame.image.load(DEFENSE_ICON_PLACEHOLDER).convert_alpha()

    def show(self, hex_obj):
        self.clear()
        if not hex_obj or hex_obj.feature != "star_system":
            self.panel.hide()
            return
        ss = hex_obj.contents
        # Star system name
        y = 10
        name_lbl = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, y, 250, 30),
            text=f"System: {ss.name}",
            manager=self.ui_manager,
            container=self.panel,
        )
        y += 32
        star_type_lbl = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, y, 250, 22),
            text=f"Type: Star System",
            manager=self.ui_manager,
            container=self.panel,
        )
        y += 25
        planet_hdr = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, y, 250, 22),
            text=f"Planets:",
            manager=self.ui_manager,
            container=self.panel,
        )
        y += 30
        for planet in ss.planets:
            this_y = y
            # 1. Planet type icon (leftmost)
            planet_icon = pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect(10, this_y, 32, 32),
                image_surface=self.planet_icon,
                manager=self.ui_manager,
                container=self.panel
            )
            self._objects.append(planet_icon)
            # 2. Planet name, above and to right of resource icon
            planet_name = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(50, this_y, 100, 18),
                text=f"{planet.name}",
                manager=self.ui_manager,
                container=self.panel
            )
            self._objects.append(planet_name)
            # 3. Resource icon (below planet name, larger icon, no text)
            resource_icon = self.assets.get(f"resource_{planet.resource}")
            if resource_icon:
                resource_image = pygame_gui.elements.UIImage(
                    relative_rect=pygame.Rect(57, this_y+19, 38, 28),
                    image_surface=resource_icon,
                    manager=self.ui_manager,
                    container=self.panel
                )
                self._objects.append(resource_image)
            # 4. Slots icon and used/total (to right of resource icon)
            slots_image = pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect(105, this_y+19, 22, 22),
                image_surface=self.slots_icon,
                manager=self.ui_manager,
                container=self.panel
            )
            self._objects.append(slots_image)
            slots_text = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(130, this_y+19, 36, 20),
                text=f"0/{planet.slots}",  # Placeholder, you can use real used slots when available
                manager=self.ui_manager,
                container=self.panel
            )
            self._objects.append(slots_text)
            # 5. Defense icon and value (rightmost)
            defense_image = pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect(175, this_y+16, 26, 22),
                image_surface=self.defense_icon,
                manager=self.ui_manager,
                container=self.panel
            )
            self._objects.append(defense_image)
            # Placeholder logic for defense value. Replace with real intel/ownership detection
            defense_value = 0
            defense_text = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(204, this_y+16, 30, 20),
                text=f"{defense_value}",
                manager=self.ui_manager,
                container=self.panel,
                object_id='@left_label'
            )
            self._objects.append(defense_text)
            y += 40
        self.panel.show()
        self._objects.extend([name_lbl, star_type_lbl, planet_hdr])

    def clear(self):
        for obj in getattr(self, '_objects', []):
            obj.kill()
        self._objects = []
        self.panel.hide()

    def hide(self):
        self.clear()

# Example: you would create this panel with
# tile_info_panel = TileInfoPanel(ui_manager, assets, pygame.Rect(SCREEN_WIDTH-200, 0, 200, 400))
# and show it with tile_info_panel.show(selected_hex)
# and hide with tile_info_panel.hide()
# Integration is to be handled by main game loop/click logic