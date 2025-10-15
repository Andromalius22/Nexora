import pygame
import pygame_gui
import json
import os
from assetsmanager import AssetsManager


SLOTS_ICON_PLACEHOLDER = "assets/icons/star_empty.png"  # Placeholder for used slots icon
DEFENSE_ICON_PLACEHOLDER = "assets/icons/star_full.png"  # Placeholder for defense icon


##############################################################################################################################

class TooltipManager:
    def __init__(self, font, bg_color=(230, 230, 230), border_color=(100, 100, 100), text_color=(0, 0, 0)):
        self.font = font
        self.bg_color = bg_color
        self.border_color = border_color
        self.text_color = text_color
        self.tooltip_text = None
        self.rect = None

    def show_tooltip(self, text, rect):
        self.tooltip_text = text
        self.rect = rect

    def clear_tooltip(self):
        self.tooltip_text = None
        self.rect = None
    
    def set_tooltip(self, pos, text):
        self.tooltip_text = text
        self.tooltip_pos = pos


    def draw(self, surface):
        if self.tooltip_text and self.rect:
            mouse_pos = pygame.mouse.get_pos()
            screen_width = surface.get_width()
            screen_height = surface.get_height()

            # Split text into lines
            lines = self.tooltip_text.split('\n')
            line_surfaces = []
            max_width = 0
            
            for line in lines:
                line_surface = self.font.render(line, True, self.text_color)
                line_surfaces.append(line_surface)
                max_width = max(max_width, line_surface.get_width())
            
            # Calculate total tooltip size
            total_height = len(lines) * (self.font.get_height() + 2)
            total_width = max_width
            
            # Default position: right of mouse
            tooltip_x = mouse_pos[0] + 10
            tooltip_y = mouse_pos[1] + 10

            # Create background rect
            bg_rect = pygame.Rect(tooltip_x, tooltip_y, total_width + 10, total_height + 6)

            # Adjust position if going offscreen
            if bg_rect.right > screen_width:
                tooltip_x = mouse_pos[0] - bg_rect.width - 10
                bg_rect.x = tooltip_x
            
            if bg_rect.bottom > screen_height:
                tooltip_y = mouse_pos[1] - bg_rect.height - 10
                bg_rect.y = tooltip_y

            # Draw background and border
            pygame.draw.rect(surface, self.bg_color, bg_rect, border_radius=5)
            pygame.draw.rect(surface, self.border_color, bg_rect, 2, border_radius=5)
            
            # Draw text lines
            y_offset = tooltip_y + 3
            for line_surface in line_surfaces:
                surface.blit(line_surface, (tooltip_x + 5, y_offset))
                y_offset += self.font.get_height() + 2

##############################################################################################################################

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
        self.surface_for_tooltips = rect
        # These UI objects will be managed when showing panel
        self._objects = []
        self.font = pygame.font.SysFont("arial", 16)
        self.tooltip_manager = TooltipManager(self.font)
        # Preload default icons once using assetsmanager for performance
        self.slots_icon = pygame.image.load(SLOTS_ICON_PLACEHOLDER).convert_alpha()
        self.defense_icon = pygame.image.load(DEFENSE_ICON_PLACEHOLDER).convert_alpha()
        
        # Store planet icon rects for tooltip detection
        self.planet_icon_rects = []

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
        
        # Clear previous planet icon rects
        self.planet_icon_rects = []
        
        for planet in ss.planets:
            this_y = y
            # 1. Planet type icon (leftmost)
            planet_rect = pygame.Rect(10, this_y, 32, 32)
            
            # Load planet icon from assets or use fallback
            planet_icon_surface = self.assets.get(f"planet_{planet.planet_type}")
            if not planet_icon_surface:
                # Fallback to question mark if planet icon not found
                planet_icon_surface = pygame.image.load("assets/resources/question.png").convert_alpha()
            
            planet_icon = pygame_gui.elements.UIImage(
                relative_rect=planet_rect,
                image_surface=planet_icon_surface,
                manager=self.ui_manager,
                container=self.panel
            )
            
            # Store planet info for tooltip
            self.planet_icon_rects.append({
                'rect': planet_rect,
                'planet': planet
            })
            
            self._objects.append(planet_icon)
            # 2. Planet name and type, above and to right of resource icon
            planet_name = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(50, this_y, 200, 18),
                text=f"{planet.name}",
                manager=self.ui_manager,
                container=self.panel,
                object_id='@left_label'
            )
            self._objects.append(planet_name)
            # 3. Resource icon (below planet name, larger icon, no text)
            if planet.is_colonized and planet.current_resource:
                resource_icon = self.assets.get(f"resource_{planet.current_resource}")
                if resource_icon:
                    resource_image = pygame_gui.elements.UIImage(
                        relative_rect=pygame.Rect(57, this_y+19, 38, 28),
                        image_surface=resource_icon,
                        manager=self.ui_manager,
                        container=self.panel
                    )
                    self._objects.append(resource_image)
            else:
                # Show question mark for uncolonized planets
                question_icon = pygame.image.load("assets/resources/question.png").convert_alpha()
                resource_image = pygame_gui.elements.UIImage(
                    relative_rect=pygame.Rect(57, this_y+19, 38, 28),
                    image_surface=question_icon,
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
                text=f"{planet.used_slots}/{planet.slots}",
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

    def update_tooltips(self, mouse_pos):
        """Check if mouse is hovering over planet icons and show tooltips."""
        self.tooltip_manager.clear_tooltip()
        
        # Adjust mouse position relative to panel
        panel_rect = self.panel.rect
        relative_mouse_pos = (mouse_pos[0] - panel_rect.x, mouse_pos[1] - panel_rect.y)
        
        for icon_info in self.planet_icon_rects:
            if icon_info['rect'].collidepoint(relative_mouse_pos):
                planet = icon_info['planet']
                tooltip_text = f"{planet.name_display}\n{planet.description}\nRarity: {planet.rarity.title()}"
                self.tooltip_manager.show_tooltip(tooltip_text, icon_info['rect'])
                break
    
    def draw_tooltips(self, surface):
        """Draw tooltips on the given surface."""
        if self.panel.visible:
            self.tooltip_manager.draw(surface)

    def clear(self):
        for obj in getattr(self, '_objects', []):
            obj.kill()
        self._objects = []
        self.planet_icon_rects = []
        self.tooltip_manager.clear_tooltip()
        self.panel.hide()

    def hide(self):
        self.clear()
