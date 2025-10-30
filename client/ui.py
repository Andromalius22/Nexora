import pygame
import pygame_gui
import json
import os
import math, time
#from assetsmanager import AssetsManager
from core.defense import *
from core.registry import REGISTRY
from client.assetsmanager import AnimatedAsset

from logger_setup import *
from tests.testgui import PAD_Y, ROW_HEIGHT, VISIBLE_ROWS

log = get_logger("UI")

SLOTS_ICON_PLACEHOLDER = "assets/icons/star_empty.png"  # Placeholder for used slots icon


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

class PlanetTooltip:
    def __init__(self, font, assets, image_size=(82, 82)):
        """
        font: pygame Font
        assets: dict of loaded icon surfaces, e.g. assets['icon_resource'], etc.
        """
        self.font = font
        self.image_size = image_size
        self.assets = assets
        self.bg_color = (10, 15, 15, 235)  # deep, slightly transparent sci-fi background
        self.text_color = (160, 255, 180)
        self.shadow_color = (0, 0, 0, 150)
        self.image = None
        self.text = None
        self.visible = False
        self.start_time = None
        self.theme_color = (80, 255, 100)
        self.cached_surface = None
        self.rect = None
        self.resource_bonus = {}

        # Planet-type specific theme colors (you can expand freely)
        self.PLANET_COLORS = {
            "icy": (120, 240, 255),
            "frozen": (100, 220, 255),
            "oceanic": (60, 160, 255),
            "jungle": (180, 255, 80),
            "volcanic": (255, 100, 40),
            "desert": (255, 200, 100),
            "barren": (200, 200, 200),
            "toxic": (140, 255, 160),
            "default": (80, 255, 100),
        }

    def show(self, text, planet_type=None, image_surface=None, planet=None):
        """Activate tooltip with text and optional image and planet type color."""
        self.text = text
        self.image = None
        self.animation = None
        self.visible = True
        self.start_time = time.time()
        self.resource_bonus = planet.resource_bonus

        # Pick color based on planet type
        self.theme_color = self.PLANET_COLORS.get(planet_type.lower(), self.PLANET_COLORS["default"]) if planet_type else self.PLANET_COLORS["default"]

        # Prefer animation if available
        if planet and getattr(planet, "animation", None):
            self.animation = planet.animation              # 👈 store the AnimatedAsset
        elif image_surface:
            self.image = pygame.transform.smoothscale(image_surface, self.image_size)
        
        self._render_cache()

    def hide(self):
        self.visible = False
        self.cached_surface = None
    
    def _wrap_text(self, text, max_width):
        """Split long lines into multiple shorter ones to fit max_width."""
        words = text.split(' ')
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + word + " "
            if self.font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                lines.append(current_line.strip())
                current_line = word + " "
        if current_line:
            lines.append(current_line.strip())
        return lines

    def _render_cache(self):
        """Pre-render text and layout (without glow)."""
        if not self.text:
            return

        padding = 12
        line_spacing = 2
        bonus_icon_size = 28
        bonus_gap_y = 60
        max_text_width = 500  # max width for text wrapping

        # --- 1️⃣ Wrap text lines ---
        raw_lines = self.text.split('\n')
        lines = []
        for line in raw_lines:
            lines.extend(self._wrap_text(line, max_text_width))
        line_surfaces = [self.font.render(line, True, self.text_color) for line in lines]

        total_text_height = sum(s.get_height() + line_spacing for s in line_surfaces)

        # --- 2️⃣ Compute image size ---
        img_w, img_h = (self.image_size if (self.image or self.animation) else (0, 0))

        # --- 3️⃣ Compute bonus section height ---
        bonus_count = sum(1 for b in self.resource_bonus.values() if b)
        bonus_section_height = bonus_count * bonus_gap_y if bonus_count > 0 else 0

        # --- 4️⃣ Compute final tooltip size ---
        width = img_w + max_text_width + 3 * padding
        height = max(img_h, total_text_height) + padding*2 + bonus_section_height

        # --- 5️⃣ Create surface and rect ---
        self.cached_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self.rect = self.cached_surface.get_rect()

        # --- 6️⃣ Draw shadow and background ---
        shadow = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(shadow, self.shadow_color, shadow.get_rect(), border_radius=8)
        self.cached_surface.blit(shadow, (3, 3))
        pygame.draw.rect(self.cached_surface, self.bg_color, (0, 0, width, height), border_radius=8)

        # --- 7️⃣ Draw image on left ---
        x_img, y_img = padding, padding
        if self.image:
            self.cached_surface.blit(self.image, (x_img, y_img))
        elif self.animation:
            # If using animated asset, draw first frame for cache
            self.cached_surface.blit(self.animation.get_frame(), (x_img, y_img))

        # --- 8️⃣ Draw text on right of image ---
        x_text = x_img + img_w + padding
        y_text = padding
        for line_surface in line_surfaces:
            self.cached_surface.blit(line_surface, (x_text, y_text))
            y_text += line_surface.get_height() + line_spacing

        # --- 9️⃣ Draw bonus icons and values below ---
        # y_bonuses = max(img_h, total_text_height) + padding
        # x_bonuses = x_img
        # text_gap = 6
        # for key, bonus_dict in self.resource_bonus.items():
        #     if not bonus_dict:
        #         continue
        #     icon_key = f"icon_{key}"
        #     icon_surf = self.assets.get(icon_key)
        #     if icon_surf:
        #         icon_scaled = pygame.transform.smoothscale(icon_surf, (bonus_icon_size, bonus_icon_size))
        #         self.cached_surface.blit(icon_scaled, (x_bonuses, y_bonuses))
        #         x_bonuses += bonus_icon_size + text_gap

        #     # Render bonus text
        #     bonus_text_raw = ", ".join(f"{k.title()} {v}" for k, v in bonus_dict.items())
        #     text_surface = self.font.render(bonus_text_raw, True, self.text_color)
        #     self.cached_surface.blit(text_surface, (x_bonuses, y_bonuses + 4))
        #     y_bonuses += bonus_gap_y
        #     x_bonuses = x_img  # reset x for next line

    def draw(self, surface, dt=0):
        """Draw the tooltip near the mouse cursor with animated glow and animated GIF support."""
        if not self.visible or not self.cached_surface:
            return

        mouse_x, mouse_y = pygame.mouse.get_pos()
        screen_w, screen_h = surface.get_size()
        tooltip_rect = self.cached_surface.get_rect(topleft=(mouse_x + 12, mouse_y + 12))

        # Prevent off-screen placement
        if tooltip_rect.right > screen_w:
            tooltip_rect.left = mouse_x - tooltip_rect.width - 12
        if tooltip_rect.bottom > screen_h:
            tooltip_rect.top = mouse_y - tooltip_rect.height - 12

        # Copy pre-rendered surface
        surface.blit(self.cached_surface, tooltip_rect)

        # --- Update animation if any ---
        #Render ON TOP of the tooltip
        if self.animation:
            self.animation.update(dt)
            current_frame = self.animation.get_frame()
            surface.blit(current_frame, (tooltip_rect.x +10 , tooltip_rect.y +10))

        # --- Animated neon border glow ---
        elapsed = time.time() - (self.start_time or 0)
        pulse = 0.5 + 0.5 * math.sin(elapsed * 3)  # smooth sine pulse (3 Hz)
        intensity = int(150 + pulse * 105)  # vary brightness

        glow_color = (
            min(255, int(self.theme_color[0] * (intensity / 255))),
            min(255, int(self.theme_color[1] * (intensity / 255))),
            min(255, int(self.theme_color[2] * (intensity / 255)))
        )

        # Outer and inner glow lines
        pygame.draw.rect(surface, glow_color, tooltip_rect, width=2, border_radius=8)
        inner_rect = tooltip_rect.inflate(-6, -6)
        pygame.draw.rect(surface, glow_color, inner_rect, width=1, border_radius=6)

##############################################################################################################################
     
class TileInfoPanel(pygame_gui.elements.UIWindow):
    def __init__(self, ui_manager, assets, rect, callback_on_planet_click=None, planet_tooltip=None):
        super().__init__(
            pygame.Rect(rect),
            manager=ui_manager,
            window_display_title="Star System Info",
            resizable=False,
            visible=False,
            object_id="#star_system_overview_window"
        )
        self.assets = assets
        self.ui_manager = ui_manager
        self.surface_for_tooltips = rect
        # These UI objects will be managed when showing panel
        self._objects = []
        self.font = pygame.font.SysFont("arial", 16)
        self.tooltip_manager = TooltipManager(self.font)
        self.planet_tooltip = planet_tooltip
        self.callback_on_planet_click = callback_on_planet_click
        self.planet_buttons = []
        # Preload default icons once using assetsmanager for performance
        self.slots_icon = pygame.image.load(SLOTS_ICON_PLACEHOLDER).convert_alpha()
        
        # Store planet icon rects for tooltip detection
        self.planet_icon_rects = []
        #same for slot tooltips
        self.slot_icon_rects = []

        # This container is now the main content area inside the window
        self.container = self.get_container()

        self.icon_size = 19
        self.icon_gap = 6

        self.selected_planet = None
        self.halo_image = pygame.image.load("assets/icons/disk-icon-size_32.png").convert_alpha()
        self.halo_ui = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(-100, -100, 48, 48),  # offscreen by default
            image_surface=self.halo_image,
            manager=self.ui_manager,
            container=self.container
        )
        self.halo_ui.hide()


    def show_info(self, hex_obj):
        self.clear()
        if not hex_obj or hex_obj.feature != "star_system":
            return
        for button, planet in self.planet_buttons:
            button.kill()
        self.planet_buttons.clear()
        self.slot_icon_rects.clear()
        ss = hex_obj.contents
        # Star system name
        y = 10
        name_lbl = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, y, 250, 30),
            text=f"System: {ss.name}",
            manager=self.ui_manager,
            container=self.container,
        )
        y += 32
        star_type_lbl = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, y, 250, 22),
            text=f"Type: Star System",
            manager=self.ui_manager,
            container=self.container,
        )
        y += 25
        planet_hdr = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, y, 250, 22),
            text=f"Planets:",
            manager=self.ui_manager,
            container=self.container,
        )
        y += 30
        
        # Clear previous planet icon rects
        self.planet_icon_rects = []
        self.planet_buttons = []  # <-- for event handling later
        
        for planet in ss.planets:
            this_y = y
            # 1. Planet type icon (leftmost)
            planet_rect = pygame.Rect(10, this_y, 32, 32)
            
            # Load planet icon from assets or use fallback
            planet_icon_surface = self.assets.get(f"planet_{planet.planet_type_id}")
            planet_icon_surface = pygame.transform.smoothscale(planet_icon_surface, (32, 32))
            if not planet_icon_surface:
                # Fallback to question mark if planet icon not found
                planet_icon_surface = pygame.image.load("assets/resources/question.png").convert_alpha()
            
            planet_image = pygame_gui.elements.UIImage(
                relative_rect=planet_rect,
                image_surface=planet_icon_surface,
                manager=self.ui_manager,
                container=self.container
            )
            self._objects.append(planet_image)
            # Create a button instead of plain image (so it's clickable)
            planet_icon_button = pygame_gui.elements.UIButton(
                relative_rect=planet_rect,
                text='',  # no text, purely image-based
                manager=self.ui_manager,
                container=self.container,
                object_id=pygame_gui.core.ObjectID(class_id='@planet_icon')
            )
            planet_icon_button.set_image(planet_icon_surface)

            # Store both for later (button + planet)
            # Store planet info for tooltip
            self.planet_icon_rects.append({'rect': planet_rect, 'planet': planet})
            self.planet_buttons.append((planet_icon_button, planet))  # shared handling with text buttons
            self._objects.append(planet_icon_button)

            # 2. Planet name and type, above and to right of resource icon
            planet_name = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(50, this_y, 200, 18),
                text=f"{planet.name}",
                manager=self.ui_manager,
                container=self.container,
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
                        container=self.container
                    )
                    self._objects.append(resource_image)
            else:
                # Show question mark for uncolonized planets
                question_icon = pygame.image.load("assets/resources/question.png").convert_alpha()
                resource_image = pygame_gui.elements.UIImage(
                    relative_rect=pygame.Rect(57, this_y+19, 38, 28),
                    image_surface=question_icon,
                    manager=self.ui_manager,
                    container=self.container
                )
                self._objects.append(resource_image)
            # 4. Slots icon and used/total (to right of resource icon)
            slots_image = pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect(105, this_y+19, 22, 22),
                image_surface=self.slots_icon,
                manager=self.ui_manager,
                container=self.container
            )
            self._objects.append(slots_image)
            slots_text = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(130, this_y+19, 36, 20),
                text=f"{len(planet.get_used_slots())}/{len(planet.slots)}",
                manager=self.ui_manager,
                container=self.container
            )
            self._objects.append(slots_text)
            # 5. Defense icon and value (rightmost)
            defense_image = pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect(175, this_y+16, 26, 22),
                image_surface=self.assets.get("icon_defense"),
                manager=self.ui_manager,
                container=self.container
            )
            self._objects.append(defense_image)
            # Placeholder logic for defense value. Replace with real intel/ownership detection
            defense_text = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(204, this_y+16, 30, 20),
                text=f"{planet.defense.get_total_defense_value()}",
                manager=self.ui_manager,
                container=self.container,
                object_id='@left_label'
            )
            self._objects.append(defense_text)
            y += 40
            max_per_row = 10
            slot_types_order = ["farm", "mine", "refine", "industry", "energy", "empty"]
            
            # Flatten slots grouped by type
            grouped_slots = []
            for t in slot_types_order:
                grouped_slots.extend([s for s in planet.slots if s.type == t])

            
            for i, slot in enumerate(grouped_slots):
                row = i // max_per_row
                col = i % max_per_row
                rect = pygame.Rect(
                    20 + col * (self.icon_size + self.icon_gap),
                    this_y + row * (self.icon_size + self.icon_gap) + 48,
                    self.icon_size,
                    self.icon_size
                )

                # Choose the correct icon
                if slot.status == "under_construction":
                    icon_surface = self.assets.get(f"{slot.type}_icon")  # e.g., mine_icon
                    icon_image = pygame_gui.elements.UIImage(
                        relative_rect=rect,
                        image_surface=icon_surface,
                        manager=self.ui_manager,
                        container=self.container
                    )
                    # Draw hammer in top-right corner
                    hammer_rect = pygame.Rect(
                        rect.right - 12, rect.top, 12, 12
                    )
                    hammer_image = pygame_gui.elements.UIImage(
                        relative_rect=hammer_rect,
                        image_surface=self.assets.get("hammer_icon"),
                        manager=self.ui_manager,
                        container=self.container
                    )
                    self._objects.append(hammer_image)
                else:
                    icon_surface = self.assets.get(f"icon_{slot.type}") if slot.type != "empty" else self.assets.get("icon_plus")
                    icon_image = pygame_gui.elements.UIImage(
                        relative_rect=rect,
                        image_surface=icon_surface,
                        manager=self.ui_manager,
                        container=self.container
                    )

                # Store for tooltips or click detection
                self.slot_icon_rects.append({'rect': rect, 'slot': slot})
                self._objects.append(icon_image)

            if len(planet.slots)>10:
                y +=30
            y += 30
            print(f"[UI]planet.industry_points : {planet.industry_points}")
        #self.panel.show()
        
        self._objects.extend([name_lbl, star_type_lbl, planet_hdr])
        self.show()

    def update_tooltips(self, mouse_pos):
        """Check if mouse is hovering over planet icons and show tooltips."""
        self.tooltip_manager.clear_tooltip()
        
        # Adjust mouse position relative to panel
        panel_rect = self.rect
        relative_mouse_pos = (mouse_pos[0] - panel_rect.x, mouse_pos[1] - panel_rect.y)
        
        for icon_info in self.planet_icon_rects:
            if icon_info['rect'].collidepoint(relative_mouse_pos):
                planet = icon_info['planet']
                #self.tooltip_manager.show_tooltip(tooltip_text, icon_info['rect'])
                break
        for icon_info in self.slot_icon_rects:
            if icon_info['rect'].collidepoint(relative_mouse_pos):
                slot = icon_info['slot']
                tooltip_text = f"{slot}"
                self.tooltip_manager.show_tooltip(tooltip_text, icon_info['rect'])
                break
    
    def draw_planet_tooltip(self, pos):
        panel_rect = self.rect
        relative_mouse_pos = (pos[0] - panel_rect.x, pos[1] - panel_rect.y)

        hovered = False  # track whether any planet is hovered

        for icon_info in self.planet_icon_rects:
            if icon_info['rect'].collidepoint(relative_mouse_pos):
                planet = icon_info['planet']
                self.planet_tooltip.show(
                    text=f"{planet.name_display}\n"
                        f"{planet.description}\n"
                        f"Rarity: {planet.rarity.title()}\n"
                        f"Population: {planet.population}/{planet.population_max}",
                    planet_type=planet.planet_type_id,
                    image_surface=self.assets.get(f"planet_{planet.planet_type_id}"),
                    planet=planet
                )
                hovered = True
                break  # ✅ stop looping once we found the hovered planet

        if not hovered:
            self.planet_tooltip.hide()

    
    def draw_tooltips(self, surface):
        """Draw tooltips on the given surface."""
        if self.visible:
            self.tooltip_manager.draw(surface)
    
    def handle_events(self, event):
        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            for button, planet in self.planet_buttons:
                if event.ui_element == button:
                    # 1️⃣ Set the visual selection (halo)
                    self.set_selected_planet(planet)
                    # 2️⃣ Trigger the callback to open the planet menu
                    if self.callback_on_planet_click:
                        self.callback_on_planet_click(planet)
                    # Stop looping after finding the clicked button
                    break
    
    def set_selected_planet(self, planet):
        """Visual-only selection feedback."""
        self.selected_planet = planet

        # Find its position in the list
        for (button, p) in self.planet_buttons:
            if p == planet:
                rect = button.relative_rect
                # Move halo just behind the icon
                self.halo_ui.set_relative_position((rect.x - 8, rect.y - 8))
                self.halo_ui.show()
                return

        # If not found, hide halo
        self.halo_ui.hide()

    def clear(self):
        for obj in getattr(self, '_objects', []):
            obj.kill()
        self._objects = []
        self.planet_icon_rects = []
        self.tooltip_manager.clear_tooltip()
        self.halo_ui.hide()
        self.selected_planet=None

    def hide(self):
        self.clear()


class PlanetManagement:
    def __init__(self, ui_manager, assets, rect,notifications_manager=None, on_action=None):        
        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=rect,
            starting_height=1,
            manager=ui_manager,
            visible=False,
            object_id='@planet_mgmt_panel'
        )
        self.rect_input=rect
        self.ui_manager = ui_manager
        self.assets = assets
        self.on_action = on_action  # <-- callback to game logic
        self._objects = []
        self.selected_planet = None
        self.font = pygame.font.SysFont("arial", 16)
        self.tooltip_manager = TooltipManager(self.font)
        #self.building_mgmt=building_mgmt
        self.notifications= notifications_manager
        self.mode_icons_rect = []
        self.resource_category_buttons = {}
        self.selected_category = None
        self.selected_tier = None
        self.selected_resource = None #the resource the panet will mine/refine
        self._objects = []

    def show_info(self, planet):
        for obj in getattr(self, '_objects', []):
            obj.kill()
        self._objects = []
        # Header
        self.header = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 10, self.rect_input.width - 20, 28),
            text='Planet Management',
            manager=self.ui_manager,
            container=self.panel
        )
        self._objects.append(self.header)
        # Planet name
        self.planet_name_lbl = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 40, self.rect_input.width - 20, 24),
            text='-'
            ,manager=self.ui_manager,
            container=self.panel
        )
        self._objects.append(self.planet_name_lbl)
        y=70
        # Mode selection
        self.mode_lbl = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, y, 100, 24),
            text='Mode : ',
            manager=self.ui_manager,
            container=self.panel,
            object_id='@left_label'
        )
        self._objects.append(self.mode_lbl)
        self.mode_icons = {
            'mine': pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect(80,y, 48, 48),
                image_surface=self.assets.get("icon_mine"),
                manager=self.ui_manager,
                container=self.panel
            ),
            'refine': pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect(148, y, 48, 48),
                image_surface=self.assets.get("icon_refine"),
                manager=self.ui_manager,
                container=self.panel
            ),
        }
        self._objects.append(self.mode_icons['mine'])
        self._objects.append(self.mode_icons['refine'])
        # Current selection state
        self.mode_selected = 'mine'
        # Store mode info for tooltip
        self.mode_icons_rect.append({
                    'rect': self.mode_icons['mine'].rect,
                    'mode': 'mine'
        })
        self.mode_icons_rect.append({
                    'rect': self.mode_icons['refine'].rect,
                    'mode': 'refine'
        })
        y+=50
        # Resource selection
        self.resource_lbl = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, y, 180, 24),
            text=f'Select resource to {planet.mode}',
            manager=self.ui_manager,
            container=self.panel,
            object_id='@left_label'
        )
        self._objects.append(self.resource_lbl)
        # Resource categories row
        x = 10
        size = 48
        spacing = 10
        y+=30

        for cat in ['ore', 'gas', 'liquid']:
            btn = pygame_gui.elements.UIImage( 
                relative_rect=pygame.Rect(x, y, size, size), 
                image_surface=self.assets.get(f"icon_{cat}"), 
                manager=self.ui_manager, 
                container=self.panel
            )

            self.resource_category_buttons[cat] = btn
            self._objects.append(btn)
            x += size + spacing
        y+=30
        #resources by caterories (see below)
        y+=70
        self.apply_resource_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(10, y, self.rect_input.width - 20, 28),
            text='Apply Extraction/Refining',
            manager=self.ui_manager,
            container=self.panel
        )
        self._objects.append(self.apply_resource_btn)
        y+=30
        # Status line
        self.status_lbl = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 338, self.rect_input.width - 20, 22),
            text='',
            manager=self.ui_manager,
            container=self.panel
        )
        self._objects.append(self.status_lbl)
        y+=30
        self.stats_lbl = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, y, 150, 20),
            text='Production stats',
            manager=self.ui_manager,
            container=self.panel
        )
        self._objects.append(self.stats_lbl)
        y+=30
        farm_image = pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect(10, y, 20, 20),
                image_surface=self.assets.get("farm_icon"),
                manager=self.ui_manager,
                container=self.panel
            )
        self._objects.append(farm_image)
        y+=30
        self.col_status_lbl = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, y, 180, 20),
            text=f'Colonization status :{planet.is_colonized}',
            manager=self.ui_manager,
            container=self.panel
        )
        self._objects.append(self.col_status_lbl)
        y+=30
        self.prod_res_status_lbl = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, y, 180, 20),
            text=f'Producing :{planet.current_resource}',
            manager=self.ui_manager,
            container=self.panel
        )
        self._objects.append(self.prod_res_status_lbl)

    def show(self, planet):
        self.selected_planet = planet
        self.panel.show()
        self.show_info(planet)
        self.planet_name_lbl.set_text(f"{planet.name}")
        print(f"planet.defense: {planet.defense}")

    def hide(self):
        self.panel.hide()
        for obj in getattr(self, '_objects', []):
            obj.kill()
        self._objects = []
        self.selected_planet = None
        self.tooltip_manager.clear_tooltip()
    
    def draw_overlays(self, surface):
        """Draw selection borders or other overlays."""
        if not self.panel.visible:
            return
        
        # Position of selected icon (relative to screen)
        selected_icon = self.mode_icons[self.mode_selected]
        pygame.draw.rect(surface, (255, 255, 0), selected_icon.rect, width=3)

        # Highlight selected category
        if self.selected_category:
            cat_img = self.resource_category_buttons[self.selected_category]
            pygame.draw.rect(surface, (255, 255, 0), cat_img.rect, width=3)

        # Highlight selected tier/resource
        if self.selected_resource and self.selected_resource in self.resource_icons:
            res_img = self.resource_icons[self.selected_resource]
            pygame.draw.rect(surface, (255, 255, 0), res_img.rect, width=3)

    
    def update_tooltips(self, mouse_pos):
        """Check if mouse is hovering over mode or resources icons and show tooltips."""
        self.tooltip_manager.clear_tooltip()
        
        # Adjust mouse position relative to panel
        panel_rect = self.panel.rect
        relative_mouse_pos = (mouse_pos[0] - panel_rect.x, mouse_pos[1] - panel_rect.y)
        
        for icon_info in self.mode_icons_rect:
            if icon_info['rect'].collidepoint(relative_mouse_pos):
                mode = icon_info['mode']
                tooltip_text = f"mode : {mode}\na planet can either mine or refine resource, not both"
                self.tooltip_manager.show_tooltip(tooltip_text, icon_info['rect'])
                break
    
    def draw_tooltips(self, surface):
        """Draw tooltips on the given surface."""
        if self.panel.visible:
            self.tooltip_manager.draw(surface)
    
    def show_resource_icons_for_category(self, category):
        """Display all resources of a given type (sorted by tier)."""

        self.resources_data = REGISTRY["resources"]
        # Remove previous resource icons if any
        for img in getattr(self, "resource_icons", {}).values():
            img.kill()
        self.resource_icons = {}

        # Filter
        resources_of_type = [
            data
            for res, data in self.resources_data.items()
            if data.get("resource_type") == category
        ]

        # Create icons
        x = 10
        y = 200
        size = 40
        spacing = 8

        for res in resources_of_type:
            resource_id = res["id"]  # unique key for assets dictionary
            icon_path = res.get("resource_icon")
            if not icon_path:
                continue

            # Get the preloaded surface from self.assets
            icon_surface = self.assets.get(f"resource_{resource_id}")

            # Create the UI element
            btn = pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect(x, y, size, size),
                image_surface=icon_surface,
                manager=self.ui_manager,
                container=self.panel
            )
            
            self.resource_icons[resource_id] = btn
            self._objects.append(btn)
            x += size + spacing


    def process_event(self, event, planet):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:

            if event.ui_element == self.apply_resource_btn:
                #the UI doesn't modify game state directly, using callback
                #self.selected_planet.current_resource = self.selected_resource
                if self.on_action:
                    self.on_action("apply_resource", self.selected_planet, self.selected_resource)
                return

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            # Convert mouse_pos relative to panel
            panel_rect = self.panel.rect
            rel = (mouse_pos[0] - panel_rect.x, mouse_pos[1] - panel_rect.y)

            # Detect click inside the icons
            if self.mode_icons['mine'].relative_rect.collidepoint(rel):
                self.mode_selected = 'mine'
                if self.on_action:
                    self.on_action("set_mode", self.selected_planet, "mine")
            elif self.mode_icons['refine'].relative_rect.collidepoint(rel):
                self.mode_selected = 'refine'
                if self.on_action:
                    self.on_action("set_mode", self.selected_planet, "refine")
            
            # pygame_gui rects are in global coordinates
            # Category click
            for cat, img in self.resource_category_buttons.items():
                if img.rect.collidepoint(mouse_pos):
                    self.selected_category = cat
                    self.selected_tier = None  # reset
                    self.selected_resource = None
                    self.show_resource_icons_for_category(cat)
                    return
            
            # Resource click (only if any are displayed)
            for name, img in getattr(self, "resource_icons", {}).items():
                if img.rect.collidepoint(mouse_pos):
                    self.selected_resource = name
                    # Optional: trigger something like self.show_resource_info
                    #self.selected_planet.current_resource=self.selected_resource
                    # if self.on_action:
                    #     self.on_action("select_resource", self.selected_planet, name)
                    return

class PlanetManagementButtonsCategory:
    def __init__(self, manager, rect, assets, on_action=None):
        self.manager = manager
        self.container = pygame_gui.elements.UIPanel(
            relative_rect=rect,
            manager=manager,
            starting_height=1,
            visible=False,
            object_id='@planet_mgmt_panel'
        )
        self.assets=assets
        self.selected_planet=None
        self.on_action=on_action

        # ---------------------------
        # ICON BAR CONFIG
        # ---------------------------
        self.icon_size = (32, 32)
        self.icon_defs = {
            "overview": {"icon": "planet_terrestrial", "tooltip": "General Overview"},
            "slots": {"icon": "icon_plus", "tooltip": "Slots Management"},
            "defense": {"icon": "icon_defense", "tooltip": "Defense"},
            "offense": {"icon": "icon_offense", "tooltip": "Offense"},
            "shipyard": {"icon": "icon_defense", "tooltip": "Shipyard"},
            "trade": {"icon": "icon_coin", "tooltip": "Trade"},
            "population": {"icon": "icon_populationSmall", "tooltip": "Population"},
            "special": {"icon": "icon_populationSmall", "tooltip": "Special Buildings"},
        }

        # ---------------------------
        # BUILD TOP ICON ROW
        # ---------------------------
        self.buttons = {}
        self.images = []
        self.active_tab = "overview"
        padding = 15
        x = 10
        y = 10

        

        for name, data in self.icon_defs.items():
            icon_rect=pygame.Rect(x, y, *self.icon_size)
            icon_img = self.assets.get(data["icon"])
            base_icon = pygame.transform.smoothscale(icon_img, self.icon_size)
            if not base_icon:
                # Fallback to question mark if planet icon not found
                base_icon = pygame.image.load("assets/resources/question.png").convert_alpha()

            icon_image = pygame_gui.elements.UIImage(
                relative_rect=icon_rect,
                image_surface=base_icon,
                manager=manager,
                container=self.container
            )
            self.images.append(icon_image)

            button = pygame_gui.elements.UIButton(
                relative_rect=icon_rect,
                text='',
                manager=manager,
                container=self.container,
                tool_tip_text=data["tooltip"],
                object_id='@planet_icon'
            )
            button.set_image(base_icon)
            button._base_icon = base_icon
            self.buttons[name] = button
            x+= 32 + padding

        # ---------------------------
        # CONTENT PANELS (hidden by default)
        # ---------------------------
        self.panels = {
            "overview": self._create_panel(pygame.Rect(290, 120, 600, 500), panel_class=PlanetOverviewPanel, ui_manager=self.manager, assets=self.assets),
            "slots": self._create_panel(pygame.Rect(290, 120, 280, 500), panel_class=SlotsManagement, ui_manager=self.manager, assets=self.assets, on_action=self.on_action),
            "defense": self._create_panel(pygame.Rect(290, 120, 600, 500), panel_class=PlanetaryDefenseManagement, ui_manager=self.manager, assets=self.assets, on_action=self.on_action),
            "offense": self._create_panel(pygame.Rect(290, 120, 600, 500), panel_class=PlanetaryOffenseMangement, ui_manager=self.manager, assets=self.assets, on_action=self.on_action),
            "shipyard": self._create_panel(pygame.Rect(290, 120, 600, 500), panel_class=PlanetShipyardManagement, ui_manager=self.manager, assets=self.assets, on_action=self.on_action),
            "trade": self._create_panel(pygame.Rect(290, 120, 600, 500), panel_class=TradeRoutePlanetaryManagement, ui_manager=self.manager, assets=self.assets, on_action=self.on_action),
            "population": self._create_panel((0, 50, rect.width, rect.height - 50), "Population Overview"),
            "special": self._create_panel((0, 50, rect.width, rect.height - 50), "Special Buildings"),
        }

        #self.switch_tab("overview")  # start on overview

    # ------------------------------------------
    # Helper: Create UIPanel with a placeholder
    # ------------------------------------------
    def _create_panel(self, rect, label=None,  panel_class=None, **kwargs):
        """
        rect: (x, y, w, h)
        label: optional string for simple panels
        panel_class: optional class derived from UIPanel for complex panels
        kwargs: passed to the panel_class
        """
        if panel_class is not None:
            # instantiate custom panel
            panel = panel_class(
                rect=rect,
                #container=self.container,
                **kwargs
            )
        else :
            # fallback to simple placeholder panel
            panel = pygame_gui.elements.UIPanel(
                relative_rect=pygame.Rect(rect),
                manager=self.manager,
                container=self.container,
                visible=False
            )
            if label:
                pygame_gui.elements.UILabel(
                    relative_rect=pygame.Rect(10, 10, rect[2]-20, 30),
                    text=label,
                    manager=self.manager,
                    container=panel
                )
        panel.hide()
        return panel

    # ------------------------------------------
    # Switch tab: hide others, show selected
    # ------------------------------------------
    def switch_tab(self, tab_name):
        for name, panel in self.panels.items():
            panel.hide()
        self.panels[tab_name].show()
        self.show_panel(tab_name)
        self.set_active_tab(tab_name)

    # ------------------------------------------
    # Handle hover / press events
    # ------------------------------------------
    def process_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_ON_HOVERED:
            for name, button in self.buttons.items():
                if event.ui_element == button:
                    self._tint_icon(button, 1.3)

        elif event.type == pygame_gui.UI_BUTTON_ON_UNHOVERED:
            for name, button in self.buttons.items():
                if event.ui_element == button:
                    self._tint_icon(button, 1.0)

        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            for name, button in self.buttons.items():
                if event.ui_element == button:
                    self.switch_tab(name)

    
    def _make_glow_image(self, base_img, glow_color=(120, 200, 255), glow_radius=6, glow_alpha=120):
        """
        Return a new Surface slightly larger than base_img with a colored "glow" behind it.
        This is a cheap, non-blurred glow: a filled rounded rect (or circle) behind the icon.
        """
        w, h = base_img.get_size()
        pad = glow_radius
        surf = pygame.Surface((w + pad*2, h + pad*2), pygame.SRCALPHA)

        # draw a simple glow blob (ellipse) behind the icon
        glow_surf = pygame.Surface((w + pad*2, h + pad*2), pygame.SRCALPHA)
        glow_col = (*glow_color, glow_alpha)
        pygame.draw.ellipse(glow_surf, glow_col, glow_surf.get_rect())
        # you can blur by scaling down/up, but that's expensive; this simple ellipse works well
        surf.blit(glow_surf, (0, 0))

        # blit the base icon centered
        surf.blit(base_img, (pad, pad))
        return surf

    def set_active_tab(self, tab_name):
        """Highlight active tab (glow) and reset others to their base icon/background."""
        # TODO rework this system so it render better
        for name, button in self.buttons.items():
            if name == tab_name:
                # create glow image if not cached
                if not hasattr(button, "_glow_icon"):
                    button._glow_icon = self._make_glow_image(button._base_icon)
                button.set_image(button._glow_icon)
                # slightly darker panel background to match glow
                #button.set_background_colour(pygame.Color(30, 50, 80))
                self.active_tab = tab_name
            else:
                # reset to base icon and neutral background
                button.set_image(getattr(button, "_base_icon"))
                #button.set_background_colour(pygame.Color(25, 25, 25))

    def _tint_icon(self, button, factor):
        """Modify icon brightness on hover. Uses button._base_icon as the source (not cumulative)."""
        if not hasattr(button, "_base_icon"):
            return

        base = button._base_icon
        # do nothing if factor == 1.0 (restore)
        if factor == 1.0:
            # if active and has glow, keep glow; otherwise keep base
            if getattr(button, "_glow_icon", None) and self.active_tab and self.buttons.get(self.active_tab) is button:
                button.set_image(button._glow_icon)
            else:
                button.set_image(base)
            return

        # produce brightened copy from base icon (do not alter base)
        bright = pygame.Surface(base.get_size(), pygame.SRCALPHA)
        # Additive brighten
        bright.fill((int(255 * (factor - 1)),) * 3 + (0,))
        icon_copy = base.copy()
        icon_copy.blit(bright, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        button.set_image(icon_copy)
    
    # ---------------------------------------------------
    # Show/hide logic
    # ---------------------------------------------------
    def hide_all_panels(self):
        for panel in self.panels.values():
            panel.hide()

    def show_panel(self, tab_name):
        """Show one panel and hide all others."""
        self.hide_all_panels()
        panel = self.panels.get(tab_name)
        if panel:
            panel.show()
            if hasattr(panel, "update_content") and callable(panel.update_content):
                if getattr(panel, "selected_planet", None) != self.selected_planet:
                    panel.update_content(self.selected_planet)

            self.active_tab = tab_name
            self.set_active_tab(tab_name)  # update icon glow
            # Optionally refresh the content
            self.refresh_panel_content(tab_name)

    def refresh_panel_content(self, tab_name):
        """Optional: refresh dynamic content when a panel is shown."""
        if tab_name == "general":
            # update labels or descriptions from the planet
            pass
        elif tab_name == "slots":
            # update slot visuals, etc.
            pass

    # ---------------------------------------------------
    # Public show/hide entry points for this UI
    # ---------------------------------------------------
    def show(self, planet):
        """Show the entire Planet Management UI."""
        self.selected_planet=planet
        self.container.visible=True
        for image in self.images:
            image.show()
        for button in self.buttons.values():
            button.show()
        if self.active_tab:
            self.show_panel(self.active_tab)

    def hide(self):
        """Hide everything."""
        self.container.visible=False
        for button in self.buttons.values():
            button.hide()
        self.hide_all_panels()

class PlanetOverviewPanel(pygame_gui.elements.UIPanel):
    def __init__(self, ui_manager, rect, assets, **kwargs):
        super().__init__(
            relative_rect=rect,
            starting_height=1,
            manager=ui_manager,
            visible=False,
            object_id='@planet_mgmt_panel',
            **kwargs
        )
        self.ui_manager = ui_manager
        self.assets = assets
        self.selected_planet = None

        self._objects = []

        # fonts
        self.font = pygame.font.SysFont("arial", 16)
        self.title_font = pygame.font.SysFont("arial", 20, bold=True)
        self.small_font = pygame.font.SysFont("arial", 16)
        
        # cache for static content
        self._cached_surface = None

        # animated GIF
        self.animated_gif: AnimatedAsset | None = None

    def show_info(self, planet):
        """Rebuild cached surface and setup GIF for the selected planet."""
        self.selected_planet = planet

        # --- Prepare animated GIF ---
        if planet.rotation_gif_path:
            frames = self.assets.load_gif_as_frames(
                key = f"planet_anim_{planet.planet_type_id}_{planet.global_id}",
                path=planet.rotation_gif_path,
                size=(128,128),
                frame_duration=0.167 #0.08
                )
            self.animated_gif = frames
            self.gif_image = pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect((430, 10), (128, 128)),
                image_surface=self.animated_gif.get_frame(),
                manager=self.ui_manager,
                container=self
            )
            self._objects.append(self.gif_image)
        else:
            self.animated_gif = None

        # Planet Name
        y_offset = 10
        planet_name_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, y_offset, 300, 20),
            text=f"{planet.name}",
            manager=self.ui_manager,
            container=self,
            object_id="@planet_name_label"
        )
        self._objects.append(planet_name_label)
        y_offset +=35

        # Climate placeholder
        climate_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, y_offset, 300, 20),
            text=f"Climate: {planet.climate or 'Unknown'}",
            manager=self.ui_manager,
            container=self,
            object_id="@planet_name_label_18"
        )
        self._objects.append(climate_label)

        y_offset +=25

        # Features placeholder
        planet_features_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, y_offset, 300, 20),
            text="Features: ",
            manager=self.ui_manager,
            container=self,
            object_id="@planet_name_label_18"
        )
        self._objects.append(planet_features_label)
        y_offset+=30
        y_offset = self.display_planet_features(planet, y_offset)
        # Resource bonus/malus\
        self.display_resource_bonuses(planet, y_offset=y_offset)

        #

        # Refine bonus/malus
        # refine_bonus = planet.refine_bonus
        # refine_text = self.small_font.render(f"Refine bonus: {refine_bonus:+}%", True, (200, 200, 100))
        # self._cached_surface.blit(refine_text, (10, 120))
    
    def display_resource_bonuses(self, planet, y_offset):
        """Display planet resource bonuses using pygame_gui elements."""
        resource_bonus = planet.resource_bonus
        x = 10
        y = y_offset
        icon_size = 24
        gap_y = 8

        planet_resources_bonus_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, y_offset, 300, 20),
            text="Production bonus :",
            manager=self.ui_manager,
            container=self,
            object_id="@planet_name_label_18"
        )
        self._objects.append(planet_resources_bonus_label)
        y+= 25

        if not resource_bonus:
            # Display "None" if there are no bonuses
            none_label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(x, y, 300, 20),
                text="None",
                manager=self.ui_manager,
                container=self,
                object_id="@default_label"
            )
            self._objects.append(none_label)
            return  # early exit

        for resource_type, multiplier in resource_bonus.items():
            # multiplier is now directly a float
            percent = int(round((multiplier - 1) * 100))

            # --- Pick theme based on sign ---
            if percent > 0:
                object_id = "@bonus_positive"
                sign = "+"
            elif percent < 0:
                object_id = "@bonus_negative"
                sign = "-"
            else:
                object_id = "@default_label"
                sign = ""

            # --- Icon ---
            icon_surface = self.assets.get(f"resource_{resource_type}")
            icon_surface = pygame.transform.smoothscale(icon_surface, (icon_size, icon_size))
            icon = pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect(x, y, icon_size, icon_size),
                image_surface=icon_surface,
                manager=self.ui_manager,
                container=self
            )
            self._objects.append(icon)

            # --- Label ---
            label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(x + icon_size + 8, y, 100, icon_size),
                text=f"{sign}{percent}%",
                manager=self.ui_manager,
                container=self,
                object_id=object_id
            )
            self._objects.append(label)

            # --- Optional Tooltip ---
            # TODO better tooltips
            description = f"{percent}% bonus to {resource_type}"  # fallback description
            label.set_tooltip(description, object_id="@tool_tip")

            y += icon_size + gap_y

    def display_planet_features(self, planet, y_offset):
        """
        Display planet features in pygame_gui.
        planet.features should be a list of dicts.
        Returns the new y_offset after rendering all features.
        """
        x = 10
        y = y_offset
        icon_size = 20
        gap_y = 8
        if planet.features is not None:
            for feature in getattr(planet, "features", []):
                # --- Feature Title ---
                title_text = feature.get("name", "Unknown Feature")
                title_label = pygame_gui.elements.UILabel(
                    relative_rect=pygame.Rect(x, y, 300, 20),
                    text=title_text,
                    manager=self.ui_manager,
                    container=self,
                    object_id="@feature_title"
                )
                self._objects.append(title_label)
                y += 22

                # --- Feature Description ---
                desc_text = feature.get("description", "")
                desc_label = pygame_gui.elements.UILabel(
                    relative_rect=pygame.Rect(x + 10, y, 400, 40),  # indent
                    text=desc_text,
                    manager=self.ui_manager,
                    container=self,
                    object_id="@feature_desc"
                )
                self._objects.append(desc_label)
                y += 42

                # --- Optional Tooltip for effects ---
                effects = feature.get("effects", {})
                if effects:
                    effect_str = ", ".join([f"{k}: {v*100:.0f}%" if isinstance(v, float) else f"{k}: {v}" 
                                            for k, v in effects.items()])
                    title_label.set_tooltip(effect_str)

                # --- Optional Tags ---
                # tags = feature.get("tags", [])
                # if tags:
                #     tag_text = ", ".join(tags)
                #     tag_label = pygame_gui.elements.UILabel(
                #         relative_rect=pygame.Rect(x + 10, y, 300, 20),
                #         text=f"Tags: {tag_text}",
                #         manager=self.ui_manager,
                #         container=self,
                #         object_id="@feature_tags"
                #     )
                #     self._objects.append(tag_label)
                #     y += 22

                # Gap between features
                y += gap_y
        else :
            planet_features_none_label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(10, y_offset, 300, 20),
                text="None",
                manager=self.ui_manager,
                container=self,
                object_id="@left_label"
            )
            self._objects.append(planet_features_none_label)
            y += gap_y
            y += 10

        return y


    def update_content(self, planet):
        """Refresh or populate panel data."""
        if planet is None or planet == self.selected_planet:
            return
        self.selected_planet = planet
        self.clear_panel()
        self.show_info(planet)
        #self.draw()
    
    def clear_panel(self):
        for obj in getattr(self, "_objects", []):
            obj.kill()
        self._objects.clear() 

    # def draw(self, surface):
    #     """Draw cached static content and animated GIF."""
    #     if self._cached_surface:
    #         surface.blit(self._cached_surface, self.get_abs_rect().topleft)

    #     # draw animated planet
    #     if self.animated_gif:
    #         frame = self.animated_gif.get_frame()
    #         surface.blit(frame, (self.get_abs_rect().x + 250, self.get_abs_rect().y + 10))

    def update(self, dt):
        """Call every frame to advance animation."""
        if self.animated_gif:
            self.animated_gif.update(dt)
            current_frame = self.animated_gif.get_frame()
            self.gif_image.set_image(current_frame)



class SlotsManagement(pygame_gui.elements.UIPanel):
    def __init__(self, ui_manager, assets, rect, on_action=None, **kwargs):
        super().__init__(
            relative_rect=rect,
            starting_height=1,
            manager=ui_manager,
            visible=False,
            object_id='@planet_mgmt_panel',
            **kwargs
        )
        self.ui_manager = ui_manager
        self.assets = assets
        self._objects = []
        self.selected_planet = None
        self.font = pygame.font.SysFont("arial", 16)
        self.tooltip_manager = TooltipManager(self.font)
        #self.notifications= notifications_manager
        #self.building_mgmt=building_mgmt

        self.icon_size = 19
        self.icon_gap = 6

        self.slot_icon_rect=[] #for tooltips

        #callback
        self.on_action=on_action
    
    def show_info(self, planet):
        for obj in getattr(self, '_objects', []):
            obj.kill()
        self._objects = []
        self.tooltip_manager.clear_tooltip()
        self.slot_icon_rect = []
        title = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 5, 180, 30),
            text='Slots management',
            manager=self.ui_manager,
            container=self,
            object_id="@planet_name_label_18"
        )
        self._objects.append(title)
        # Dynamic stacking
        current_y = 40
        for slot_type in ["farm", "mine", "refine", "industry", "energy", "science"]:
            consumed_height = self._display_slots_row(planet, slot_type, current_y)
            current_y += consumed_height + 10  # 10px gap between sections

    
    def _display_slots_row(self, planet, slot_type, y_offset):
        y = y_offset
        title = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, y, 100, 30),
            text=f"{slot_type}",
            manager=self.ui_manager,
            container=self,
            object_id='@left_label'
        )
        self._objects.append(title)
            
        statistic = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(110, y, 100, 30),
            text=f"{self.selected_planet.statistics[slot_type]}/min",
            manager=self.ui_manager,
            container=self
        )
        self._objects.append(statistic)
        y+=30

        max_per_row = 10

        # Filter only type slots
        type_slots = [s for s in planet.slots if s.type == slot_type]

        # Add utility icons
        display_slots = type_slots + ["icon_plus", "icon_plus_02", "icon_moins"]

        # Calculate rows needed
        rows = (len(display_slots) + max_per_row - 1) // max_per_row
        total_height = rows * (self.icon_size + self.icon_gap)

        for i, slot in enumerate(display_slots):
            row = i // max_per_row
            col = i % max_per_row
            rect = pygame.Rect(
                20 + col * (self.icon_size + self.icon_gap),
                y + row * (self.icon_size + self.icon_gap),
                self.icon_size,
                self.icon_size
            )

            # Handle special icons
            # Skip "plus_icon" if no capacity left
            # Before creating the UIImage
            if slot in ("icon_plus", "icon_plus_02"):
                # Skip the plus icons if no empty slots remain
                if not planet.get_available_slots():
                    continue  # no space left, don't show plus icon
            if slot in ("icon_plus", "icon_plus_02", "icon_moins"):
                icon_surface = self.assets.get(slot)
                icon_image = pygame_gui.elements.UIImage(
                    relative_rect=rect,
                    image_surface=icon_surface,
                    manager=self.ui_manager,
                    container=self
                )
                self._objects.append(icon_image)

                # Create invisible button
                button = pygame_gui.elements.UIButton(
                    relative_rect=rect,
                    text="",  # invisible
                    manager=self.ui_manager,
                    container=self,
                    object_id="@transparent_button"
                )
                button.set_relative_position(rect.topleft)
                self._objects.append(button)

                # Store metadata for later reference
                self.slot_icon_rect.append({
                    "button": button,
                    "tooltip": {
                        "icon_plus": "enough space for one more slot",
                        "icon_plus_02": f"click to build one {slot_type}",
                        "icon_moins": f"click to remove one {slot_type}"
                    }[slot],
                    "action": {
                        "icon_plus": None,
                        "icon_plus_02": "add_slot",
                        "icon_moins": "remove_slot"
                    }[slot],
                    "slot_type": slot_type
                })
                continue

                # Define tooltip and action
                tooltip_data = {
                    "icon_plus": ("enough space for one more slot", None),
                    "icon_plus_02": (f"click to build one {slot_type}", "add_slot"),
                    "icon_moins": (f"click to remove one {slot_type}", "remove_slot"),
                }
                tooltip, action = tooltip_data[slot]
                self.slot_icon_rect.append({
                    "rect": rect,
                    "tooltip": tooltip,
                    "action": action,
                    "slot_type": slot_type,
                })
                continue
            # Handle normal slot
            # Handle real slots
            icon_surface = self.assets.get(f"icon_{slot_type}").copy()

            # If inactive, tint to grey
            if not slot.active:
                grey_surface = pygame.Surface(icon_surface.get_size(), pygame.SRCALPHA)
                grey_surface.fill((100, 100, 100, 150))  # semi-transparent grey overlay
                icon_surface.blit(grey_surface, (0, 0))
            
            slot_index = i  # index within that slot_type only

            icon_image = pygame_gui.elements.UIImage(
                relative_rect=rect,
                image_surface=icon_surface,
                manager=self.ui_manager,
                container=self
            )
            self._objects.append(icon_image)
            self.slot_icon_rect.append({
                "rect": rect,
                "tooltip": f"click to activate/deactivate {slot_type} slot",
                "action": None,
                "slot_type": slot_type,
                "slot_index": slot_index,
            })

            # Invisible button over slot
            button = pygame_gui.elements.UIButton(
                relative_rect=rect,
                text="",
                manager=self.ui_manager,
                container=self,
                object_id="@transparent_button"
            )
            self._objects.append(button)

            self.slot_icon_rect.append({
                "button": button,
                "tooltip": f"click to activate/deactivate {slot_type} slot",
                "action": "toggle_slot",
                "slot_type": slot_type,
                "slot_index": i
            })


        # Return vertical height used by this section
        return total_height + 30  # includes title height
    
    def update_tooltips(self, mouse_pos):
        """Check if mouse is hovering over slots and show tooltips."""
        self.tooltip_manager.clear_tooltip()
        
        # Adjust mouse position relative to panel
        panel_rect = self.rect
        relative_mouse_pos = (mouse_pos[0] - panel_rect.x, mouse_pos[1] - panel_rect.y)
        
        for entry in self.slot_icon_rect:
            if entry.get("rect").collidepoint(relative_mouse_pos):
                self.tooltip_manager.show_tooltip(entry.get("tooltip"), entry["rect"])
                break
    
    def draw_tooltips(self, surface):
        """Draw tooltips on the given surface."""
        if self.panel.visible:
            self.tooltip_manager.draw(surface)
    
    def process_event(self, event):
        handled = super().process_event(event)

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            for slot_data in self.slot_icon_rect:
                # print(f"slot_data: {slot_data}")
                # print(f"self.slot_icon_rect: {self.slot_icon_rect}")
                if "button" not in slot_data:
                    continue  # skip non-button entries
                if event.ui_element == slot_data["button"]:
                    action = slot_data["action"]
                    slot_type = slot_data["slot_type"]
                    if action == "add_slot":
                        self.on_action(f"{action}", self.selected_planet, f"{slot_type}")
                    elif action == "remove_slot":
                        self.on_action(f"{action}", self.selected_planet, f"{slot_type}")
                    elif action == "toggle_slot":
                        slot_index = slot_data["slot_index"]
                        slots_of_type = [s for s in self.selected_planet.slots if s.type == slot_type]
                        if slot_index < len(slots_of_type):
                            slot = slots_of_type[slot_index]
                            self.on_action("toggle_slot", self.selected_planet, slot)
                    return True

        return handled

    def update_content(self, planet):
        """Refresh or populate panel data."""
        if planet is None or planet == self.selected_planet:
            return
        self.selected_planet = planet
        self.clear_panel()
        self.show_info(planet)

    def clear_panel(self):
        for obj in getattr(self, "_objects", []):
            obj.kill()
        self._objects.clear() 

    def show(self):
        super().show()

    def hide(self):
        super().hide()
        if not hasattr(self, "tooltip_manager"):
            return  # early exit during initialization
        for obj in getattr(self, '_objects', []):
            obj.kill()
        self._objects = []
        self.selected_planet = None
        self.tooltip_manager.clear_tooltip()

class UnitStatsPanel:
    HIDDEN_KEYS = {"id", "icon", "description", "tags", "name", "category"}
    def __init__(self, ui_manager, container, planet,
                 panel_width=250, panel_height=350,
                 start_x=10, start_y=10,
                 on_action=None):
        self.ui_manager = ui_manager
        self.container = container
        self.selected_planet = planet
        self.panel_width = panel_width
        self.panel_height = panel_height
        self.start_x = start_x
        self.start_y = start_y

        # Callbacks for buttons
        self.on_action = on_action

        # Internal tracking
        self._stats_labels = {}
        self._cost_elements = []
        self._panel_objects = []
        self._buttons = []

        self.icon_size = 24
        self.spacing_y = 30
        self.col_width = 90
        self.max_per_column = 3

    def display_unit(self, unit_data):
        # Clear previous UI elements
        self._clear_panel()

        # Dynamic labels for unit properties
        y_offset = 0
        for key, value in unit_data.items():
            if key in self.HIDDEN_KEYS or key in ("stats", "cost"):
                continue
            # Special handling
            if key == "upkeep":
                label_text = f"Upkeep: {value.get('credits', 0)}"
                self._add_label(label_text, y_offset)
                y_offset += 24
            elif isinstance(value, dict):
                for subkey, subvalue in value.items():
                    label_text = f"{subkey.replace('_', ' ').capitalize()}: {subvalue}"
                    self._add_label(label_text, y_offset)
                    y_offset += 24
            else:
                label_text = f"{key.replace('_', ' ').capitalize()}: {value}"
                self._add_label(label_text, y_offset)
                y_offset += 24

        # Stats dictionary
        stats_dict = unit_data.get("stats", {})
        for key, value in stats_dict.items():
            label_text = f"{key.capitalize()}: {value}"
            self._add_label(label_text, y_offset)
            y_offset += 24

        # Costs
        if "cost" in unit_data:
            self._display_costs(unit_data["cost"], y_offset)

        # Add buttons at the bottom of the panel
        self._add_buttons(unit_data)

    def _clear_panel(self):
        for label in self._stats_labels.values():
            label.kill()
        self._stats_labels.clear()

        for icon, label in self._cost_elements:
            icon.kill()
            label.kill()
        self._cost_elements.clear()

        for btn in self._buttons:
            btn.kill()
        self._buttons.clear()
    
    def kill(self):
        self._clear_panel()

    def _add_label(self, text, y_offset):
        label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(self.start_x, self.start_y + y_offset, self.panel_width - 20, 24),
            text=text,
            manager=self.ui_manager,
            container=self.container,
            object_id="@left_label"
        )
        self._stats_labels[text] = label
        self._panel_objects.append(label)

    def _display_costs(self, cost, y_offset):
        cost_index = 0
        x_start = self.start_x
        y_start = self.start_y + y_offset + 10

        def add_cost(icon_path, text, index, is_warning=False, tooltip_text=""):
            col = index // self.max_per_column
            row = index % self.max_per_column
            x = x_start + col * self.col_width
            y = y_start + row * self.spacing_y

            try:
                icon_surface = pygame.image.load(icon_path).convert_alpha()
            except FileNotFoundError:
                icon_surface = pygame.Surface((self.icon_size, self.icon_size))
                icon_surface.fill((120, 120, 120))

            icon_elem = pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect(x, y, self.icon_size, self.icon_size),
                image_surface=icon_surface,
                manager=self.ui_manager,
                container=self.container,
            )

            label_elem = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(x + self.icon_size + 8, y, 150, self.icon_size),
                text=text,
                manager=self.ui_manager,
                container=self.container,
                object_id="@left_label_red" if is_warning else "@left_label"
            )

            if tooltip_text:
                icon_elem.set_tooltip(tooltip_text, object_id="@tool_tip")
                label_elem.set_tooltip(tooltip_text, object_id="@tool_tip")

            self._cost_elements.append((icon_elem, label_elem))

        # Credits
        if "credits" in cost:
            add_cost("assets/icons/coin.png", str(cost["credits"]), cost_index, tooltip_text="Credits")
            cost_index += 1

        # Industry
        if "industry" in cost:
            add_cost("assets/icons/industry.jpg", str(cost["industry"]), cost_index, tooltip_text="Industry Points")
            cost_index += 1

        # Resources
        for res_name, amount in cost.get("resources", {}).items():
            planet_amount = getattr(self.selected_planet, "resources", {}).get(res_name, 0)
            is_warning = planet_amount < amount
            tooltip = f"{res_name.capitalize()} ({planet_amount}/{amount})" if is_warning else res_name
            add_cost(f"assets/resources/{res_name}.png", str(amount), cost_index, is_warning, tooltip_text=tooltip)
            cost_index += 1

    def _add_buttons(self, unit_data):
        # TODO later, add a build in batch button, and make the according logic behind it. it should offer lesser costs per units
        btn_width = 100
        btn_height = 30
        btn_pad = 10
        y_pos = self.start_y + self.panel_height - btn_height*2
        #y_pos=5

        if self.on_action:
            build_btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(self.start_x, y_pos, btn_width, btn_height),
                text="Build",
                manager=self.ui_manager,
                container=self.container,
                object_id="@build_button_defense"
            )
            build_btn.unit_data = unit_data  # store reference
            self._buttons.append(build_btn)

            destroy_btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(self.start_x + btn_width + btn_pad, y_pos, btn_width, btn_height),
                text="Destroy",
                manager=self.ui_manager,
                container=self.container,
                object_id="@build_button_defense"
            )
            destroy_btn.unit_data = unit_data
            self._buttons.append(destroy_btn)
    
    def process_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            # Check if clicked button is one of our panel buttons
            if event.ui_element in self._buttons:
                unit_data = getattr(event.ui_element, "unit_data", None)
                if unit_data is None:
                    return
                if event.ui_element.object_id == "@build_button" and self.on_action:
                    self.on_action("build_defense_unit", self.selected_planet, unit_data['id'])
                elif event.ui_element.object_id == "@destroy_button" and self.on_destroy:
                    # TODO: Replace this print with your destroy logic
                    print(f"Destroying one {unit_data['name']}")

# ------------------ Helper Functions ------------------
def create_triangle_surface(size, color, direction="up"):
    """Create a triangle surface (up or down)"""
    surf = pygame.Surface(size, pygame.SRCALPHA)
    w, h = size
    if direction == "up":
        points = [(w//2, 0), (0, h), (w, h)]
    else:  # down
        points = [(0, 0), (w, 0), (w//2, h)]
    pygame.draw.polygon(surf, color, points)
    return surf

class ScrollableUnitList:
    def __init__(self, ui_manager, container, units_dict,
                 panel_rect, visible_rows=5,
                 icon_size=(32, 32), row_height=48, pad_y=8,
                 on_unit_click=None, assets=None):
        self.ui_manager = ui_manager
        self.container = container
        self.units_dict = units_dict
        self.units_list = list(units_dict.items())
        self.panel_rect = panel_rect
        self.visible_rows = visible_rows
        self.icon_size = icon_size
        self.row_height = row_height
        self.pad_y = pad_y
        self.on_unit_click = on_unit_click
        self.assets=assets

        self.start_index = 0
        self._unit_row_map = {}
        self.ui_rows = []
        self.current_filter = "All"

        self._init_panel()
        self.show_visible_units()

    # ----------------------------------------------------------------
    def _init_panel(self):
        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=self.panel_rect,
            manager=self.ui_manager,
            container=self.container,
            object_id='@planet_mgmt_panel'
        )

        # Arrow buttons
        arrow_width, arrow_height = 30, 30
        arrow_x = self.panel_rect.width - arrow_width - 10
        self.arrow_up = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(arrow_x, 10, arrow_width, arrow_height),
            text="",
            manager=self.ui_manager,
            container=self.panel,
            object_id="@transparent_button"
        )
        self.image_arrow_up = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(arrow_x, 10, arrow_width, arrow_height),
            image_surface=create_triangle_surface((arrow_width, arrow_height), (200,200,200), "up"),
            manager=self.ui_manager,
            container=self.panel
        )
        self.arrow_down = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(arrow_x, self.panel_rect.height - arrow_height - 10, arrow_width, arrow_height),
            text="",
            manager=self.ui_manager,
            container=self.panel,
            object_id="@transparent_button"
        )
        self.image_arrow_down = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(arrow_x, self.panel_rect.height - arrow_height - 10, arrow_width, arrow_height),
            image_surface=create_triangle_surface((arrow_width, arrow_height), (200,200,200), "down"),
            manager=self.ui_manager,
            container=self.panel
        )
        #self.arrow_up.set_image(create_triangle_surface((arrow_width, arrow_height), (200,200,200), "up"))
        #self.arrow_down.set_image(create_triangle_surface((arrow_width, arrow_height), (200,200,200), "down"))

        # --- Dropdown Filter ---
        sort_txt = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 5, 80, 40),
            text="Sort",
            manager=self.ui_manager,
            container=self.panel,
            object_id="@Spar_font_label_15"
        )
        all_layers = sorted({u.get("layer", "Unknown") for u in self.units_dict.values()})
        options_list = ["All"] + all_layers
        self._layer_filter = pygame_gui.elements.UIDropDownMenu(
            options_list=options_list,
            starting_option="All",
            relative_rect=pygame.Rect(100, 10, 180, 24),
            manager=self.ui_manager,
            container=self.panel,
            object_id="@dropdown_units_layer_filter"
        )

        # --- Pre-create UI rows (icons + buttons) ---
        for i in range(self.visible_rows):
            row_y = 50 + i * (self.row_height + self.pad_y)

            icon_rect = pygame.Rect(10, row_y, self.icon_size[0], self.icon_size[1])
            ui_icon_image = pygame_gui.elements.UIImage(
                relative_rect=icon_rect,
                image_surface=pygame.Surface(self.icon_size),
                manager=self.ui_manager,
                container=self.panel
            )

            btn_rect = pygame.Rect(50, row_y + 8, 200, 24)
            ui_button = pygame_gui.elements.UIButton(
                relative_rect=btn_rect,
                text="",
                manager=self.ui_manager,
                container=self.panel,
                object_id="@unit_button"
            )
            ui_button.unit_id = None
            self._unit_row_map[ui_button] = None
            self.ui_rows.append((ui_icon_image, ui_button))

        # --- Compute filtered list once ---
        self._update_filtered_units()

    # ----------------------------------------------------------------
    def _update_filtered_units(self):
        """Update self.filtered_units based on current dropdown filter."""
        if self.current_filter == "All":
            self.filtered_units = self.units_list
        else:
            self.filtered_units = [
                (uid, data) for uid, data in self.units_list
                if data.get("layer") == self.current_filter
            ]
        self.start_index = 0
        self.show_visible_units()

    # ----------------------------------------------------------------
    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.arrow_down:
                if self.start_index + self.visible_rows < len(self.filtered_units):
                    self.start_index += 1
                    self.show_visible_units()
            elif event.ui_element == self.arrow_up:
                if self.start_index > 0:
                    self.start_index -= 1
                    self.show_visible_units()
            else:
                unit_id = getattr(event.ui_element, "unit_id", None)
                if unit_id is not None and self.on_unit_click:
                    self.on_unit_click(unit_id)

        elif event.type == pygame.MOUSEWHEEL:
            if event.y > 0 and self.start_index > 0:
                self.start_index -= 1
                self.show_visible_units()
            elif event.y < 0 and self.start_index + self.visible_rows < len(self.filtered_units):
                self.start_index += 1
                self.show_visible_units()

        elif event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
            if event.ui_element == self._layer_filter:
                self.current_filter = event.text
                self._update_filtered_units()
                return True

    # ----------------------------------------------------------------
    def show_visible_units(self):
        """Refresh visible unit buttons/icons."""
        for i in range(self.visible_rows):
            unit_index = self.start_index + i
            icon, button = self.ui_rows[i]
            if unit_index < len(self.filtered_units):
                unit_id, data = self.filtered_units[unit_index]
                button.set_text(data.get("name", "Unknown Unit"))
                button.unit_id = unit_id
                surf = self.assets.get(f"unit_{unit_id}")
                #surf.fill((50 + (i * 30) % 200, 100, 150))
                icon.set_image(surf)
            else:
                button.set_text("")
                button.unit_id = None
                surf = pygame.Surface(self.icon_size)
                surf.fill((0, 0, 0))
                icon.set_image(surf)


class PlanetaryDefenseManagement(pygame_gui.elements.UIPanel):
    def __init__(self, ui_manager, assets, rect, on_action=None, **kwargs):
        super().__init__(
            relative_rect=rect,
            starting_height=1,
            manager=ui_manager,
            visible=False,
            object_id='@planet_mgmt_panel',
            **kwargs
        )

        self.ui_manager = ui_manager
        self.assets = assets
        self._objects = []
        self.on_action= on_action
        self.selected_planet = None
        self.font = pygame.font.SysFont("arial", 16)
        self.tooltip_manager = TooltipManager(self.font)
        self.icons_rect = [] #for tooltips
    
    def show_info(self, planet, filter_layer="All"):
        for obj in getattr(self, '_objects', []):
            obj.kill()
        self._objects = []
        self.tooltip_manager.clear_tooltip()
        self.icons_rect = []
        title = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 5, 320, 40),
            text='Defense management',
            manager=self.ui_manager,
            container=self,
            object_id="@Spar_font_label_15"
        )
        self._objects.append(title)

        def on_unit_selected(unit_id):
            unit_data = REGISTRY["defense_units"][unit_id]
            self.stats_panel.display_unit(unit_data)

        ROW_HEIGHT=40
        VISIBLE_ROWS=6
        PAD_Y=10
        # Create scrollable list
        self.scrollable_units = ScrollableUnitList(
            self.ui_manager,
            container=self,
            units_dict=REGISTRY["defense_units"],  # or offense/ships
            panel_rect=pygame.Rect(5, 50, 330, 430),
            visible_rows=5,
            on_unit_click=on_unit_selected,
            assets=self.assets
        )

        


        

        # Example placement (top-right)
        stats_x = 340
        stats_y = 5
        stats_w = 250
        stats_h = 325

        self._stats_container = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(stats_x, stats_y, stats_w, stats_h),
            manager=self.ui_manager,
            container=self,
            object_id='@planet_mgmt_panel'
        )
        self._objects.append(self._stats_container)

        self.stats_panel = UnitStatsPanel(
            self.ui_manager,
            self._stats_container,
            self.selected_planet,
            panel_height=stats_h,
            on_action=self.on_action
        )
        self._objects.append(self.stats_panel)
    # When a unit is clicked
    def handle_unit_click(self, clicked_button):
        unit_id = self._unit_row_map.get(clicked_button)
        if unit_id:
            unit_data = REGISTRY["defense_units"][unit_id]
            self.stats_panel.display_unit(unit_data)

    def process_event(self, event):

        self.stats_panel.process_event(event)
        self.scrollable_units.handle_event(event)
        # --- Handle button clicks ---
        # if event.type == pygame_gui.UI_BUTTON_PRESSED:
        #     # --- Unit selection (left pane) ---
        #     if event.ui_element in self._unit_row_map:
        #         self.handle_unit_click(event.ui_element)
        #         return  # stop here; we don't want to process further this frame

            # --- Build / Destroy actions ---
            # if event.ui_element == self._build_button:
            #     if hasattr(self, "_selected_unit") and self._selected_unit:
            #         unit = self._selected_unit
            #         self.on_action("build_defense_unit", self.selected_planet, unit['id'])
            #     else:
            #         log.warning("⚠️ No unit selected to build.")
            #     return

            # if event.ui_element == self._destroy_button:
            #     if hasattr(self, "_selected_unit") and self._selected_unit:
            #         unit = self._selected_unit
            #         # TODO: Replace this print with your destroy logic
            #         print(f"Destroying one {unit['name']}")
            #         # Example: self.game.destroy_defense_unit(self.current_planet, unit['id'])
            #     else:
            #         print("⚠️ No unit selected to destroy.")
            #     return
        
        # if event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
        #     if event.ui_element == self._layer_filter:
        #         selected_layer = event.text
        #         self.show_info(self.selected_planet, filter_layer=selected_layer)
        #         return True
        # --- Let parent class handle anything else (if needed) ---
        super().process_event(event)

    
    def update_content(self, planet):
        """Refresh or populate panel data."""
        if planet is None or planet == self.selected_planet:
            return
        self.selected_planet = planet
        self.clear_panel()
        self.show_info(planet)

    def clear_panel(self):
        for obj in getattr(self, "_objects", []):
            obj.kill()
        self._objects.clear() 

    def show(self):
        super().show()

    def hide(self):
        super().hide()
        if not hasattr(self, "tooltip_manager"):
            return  # early exit during initialization
        for obj in getattr(self, '_objects', []):
            obj.kill()
        self._objects = []
        self.selected_planet = None
        self.tooltip_manager.clear_tooltip()

class PlanetaryOffenseMangement(pygame_gui.elements.UIPanel):
    def __init__(self, ui_manager, assets, rect, on_action=None, **kwargs):
        super().__init__(
            relative_rect=rect,
            starting_height=1,
            manager=ui_manager,
            visible=False,
            object_id='@planet_mgmt_panel',
            **kwargs
        )

        self.ui_manager = ui_manager
        self.assets = assets
        self._objects = []
        self.on_action= on_action
        self.selected_planet = None
        self.font = pygame.font.SysFont("arial", 16)
        self.tooltip_manager = TooltipManager(self.font)
        self.icons_rect = [] #for tooltips
    
    def show_info(self, planet, filter_layer="All"):
        for obj in getattr(self, '_objects', []):
            obj.kill()
        self._objects = []
        self.tooltip_manager.clear_tooltip()
        self.icons_rect = []
        title = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 5, 320, 40),
            text='Offense management',
            manager=self.ui_manager,
            container=self,
            object_id="@Spar_font_label_15"
        )
        self._objects.append(title)

        def on_unit_selected(unit_id):
            unit_data = REGISTRY["offense_units"][unit_id]
            self.stats_panel.display_unit(unit_data)

        ROW_HEIGHT=40
        VISIBLE_ROWS=6
        PAD_Y=10
        # Create scrollable list
        self.scrollable_units = ScrollableUnitList(
            self.ui_manager,
            container=self,
            units_dict=REGISTRY["offense_units"],  # or offense/ships
            panel_rect=pygame.Rect(5, 50, 330, 430),
            visible_rows=5,
            on_unit_click=on_unit_selected,
            assets=self.assets
        )
        # Example placement (top-right)
        stats_x = 340
        stats_y = 5
        stats_w = 250
        stats_h = 325

        self._stats_container = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(stats_x, stats_y, stats_w, stats_h),
            manager=self.ui_manager,
            container=self,
            object_id='@planet_mgmt_panel'
        )
        self._objects.append(self._stats_container)

        self.stats_panel = UnitStatsPanel(
            self.ui_manager,
            self._stats_container,
            self.selected_planet,
            panel_height=stats_h,
            on_action=self.on_action
        )
        self._objects.append(self.stats_panel)
    # When a unit is clicked
    def handle_unit_click(self, clicked_button):
        unit_id = self._unit_row_map.get(clicked_button)
        if unit_id:
            unit_data = REGISTRY["offense_units"][unit_id]
            self.stats_panel.display_unit(unit_data)

    def process_event(self, event):

        self.stats_panel.process_event(event)
        self.scrollable_units.handle_event(event)
        super().process_event(event)

    
    def update_content(self, planet):
        """Refresh or populate panel data."""
        if planet is None or planet == self.selected_planet:
            return
        self.selected_planet = planet
        self.clear_panel()
        self.show_info(planet)

    def clear_panel(self):
        for obj in getattr(self, "_objects", []):
            obj.kill()
        self._objects.clear() 

    def show(self):
        super().show()

    def hide(self):
        super().hide()
        if not hasattr(self, "tooltip_manager"):
            return  # early exit during initialization
        for obj in getattr(self, '_objects', []):
            obj.kill()
        self._objects = []
        self.selected_planet = None
        self.tooltip_manager.clear_tooltip()

    # def handle_unit_click(self, clicked_button):
    #     unit_id = self._unit_row_map.get(clicked_button)
    #     if unit_id:
    #         self._selected_unit = REGISTRY["offense_units"][unit_id]
    #         # Update stats panel
    #         self._stats_labels["Offense"].set_text(f"Offense: {self._selected_unit['offense_value']}")
    #         self._stats_labels["Credit Cost"].set_text(f"Credit Cost: {self._selected_unit['cost'].get('credits', 0)}")
    #         self._stats_labels["Industry Cost"].set_text(f"Industry Cost: {self._selected_unit['cost'].get('industry', 0)}")
    #         self._stats_labels["Upkeep"].set_text(f"Upkeep: {self._selected_unit['upkeep'].get('credits', 0)}")
    
    def update_content(self, planet):
        """Refresh or populate panel data."""
        if planet is None or planet == self.selected_planet:
            return
        self.selected_planet = planet
        self.clear_panel()
        self.show_info(planet)

    def clear_panel(self):
        for obj in getattr(self, "_objects", []):
            obj.kill()
        self._objects.clear() 

    def show(self):
        super().show()

    def hide(self):
        super().hide()
        if not hasattr(self, "tooltip_manager"):
            return  # early exit during initialization
        for obj in getattr(self, '_objects', []):
            obj.kill()
        self._objects = []
        self.selected_planet = None
        self.tooltip_manager.clear_tooltip()

class PlanetShipyardManagement(pygame_gui.elements.UIPanel):
    def __init__(self, ui_manager, assets, rect, on_action=None, **kwargs):
        super().__init__(
            relative_rect=rect,
            starting_height=1,
            manager=ui_manager,
            visible=False,
            object_id='@planet_mgmt_panel',
            **kwargs
        )

        self.ui_manager = ui_manager
        self.assets = assets
        self._objects = []
        self.on_action= on_action
        self.selected_planet = None
        self.font = pygame.font.SysFont("arial", 16)
        self.tooltip_manager = TooltipManager(self.font)
        self.icons_rect = [] #for tooltips
    
    def show_info(self, planet, filter_layer="All"):
        for obj in getattr(self, '_objects', []):
            obj.kill()
        self._objects = []
        self.tooltip_manager.clear_tooltip()
        self.icons_rect = []
        title = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 5, 320, 40),
            text='Shipyard',
            manager=self.ui_manager,
            container=self,
            object_id="@Spar_font_label_15"
        )
        self._objects.append(title)

        def on_unit_selected(unit_id):
            unit_data = REGISTRY["ships"][unit_id]
            self.stats_panel.display_unit(unit_data)

        ROW_HEIGHT=40
        VISIBLE_ROWS=6
        PAD_Y=10
        # Create scrollable list
        self.scrollable_units = ScrollableUnitList(
            self.ui_manager,
            container=self,
            units_dict=REGISTRY["ships"],  # or offense/ships
            panel_rect=pygame.Rect(5, 50, 330, 430),
            visible_rows=5,
            on_unit_click=on_unit_selected,
            assets=self.assets
        )

        # Example placement (top-right)
        stats_x = 340
        stats_y = 5
        stats_w = 250
        stats_h = 325

        self._stats_container = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(stats_x, stats_y, stats_w, stats_h),
            manager=self.ui_manager,
            container=self,
            object_id='@planet_mgmt_panel'
        )
        self._objects.append(self._stats_container)

        self.stats_panel = UnitStatsPanel(
            self.ui_manager,
            self._stats_container,
            self.selected_planet,
            panel_height=stats_h,
            on_action=self.on_action
        )
        self._objects.append(self.stats_panel)
    # When a unit is clicked
    def handle_unit_click(self, clicked_button):
        unit_id = self._unit_row_map.get(clicked_button)
        if unit_id:
            unit_data = REGISTRY["defense_units"][unit_id]
            self.stats_panel.display_unit(unit_data)

    def process_event(self, event):

        self.stats_panel.process_event(event)
        self.scrollable_units.handle_event(event)
        # --- Let parent class handle anything else (if needed) ---
        super().process_event(event)

    
    def update_content(self, planet):
        """Refresh or populate panel data."""
        if planet is None or planet == self.selected_planet:
            return
        self.selected_planet = planet
        self.clear_panel()
        self.show_info(planet)

    def clear_panel(self):
        for obj in getattr(self, "_objects", []):
            obj.kill()
        self._objects.clear() 

    def show(self):
        super().show()

    def hide(self):
        super().hide()
        if not hasattr(self, "tooltip_manager"):
            return  # early exit during initialization
        for obj in getattr(self, '_objects', []):
            obj.kill()
        self._objects = []
        self.selected_planet = None
        self.tooltip_manager.clear_tooltip()

class TradeRoutePlanetaryManagement(pygame_gui.elements.UIPanel):
    def __init__(self, ui_manager, assets, rect, on_action=None, **kwargs):
        super().__init__(
            relative_rect=rect,
            starting_height=1,
            manager=ui_manager,
            visible=False,
            object_id='@planet_mgmt_panel',
            **kwargs
        )

        self.ui_manager = ui_manager
        self.assets = assets
        self._objects = []
        self.on_action= on_action
        self.selected_planet = None
        self.font = pygame.font.SysFont("arial", 16)
        self.tooltip_manager = TooltipManager(self.font)
        self.icons_rect = [] #for tooltips
    
    def show_info(self, planet, filter_layer="All"):
        for obj in getattr(self, '_objects', []):
            obj.kill()
        self._objects = []
        self.tooltip_manager.clear_tooltip()
        self.icons_rect = []
        title = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 5, 320, 40),
            text='Trade Routes',
            manager=self.ui_manager,
            container=self,
            object_id="@Spar_font_label_15"
        )
        self._objects.append(title)

        self.info_panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(7, 40, 250, 100),
            manager=self.ui_manager,
            container=self,
            object_id='@planet_mgmt_panel'
        )
        y_offset=5
        summary_txt = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(5, 5, 230, 15),
            text="Summary",
            manager=self.ui_manager,
            container=self.info_panel,
            object_id="@Spar_font_label_10"
        )
        self._objects.append(summary_txt)
        y_offset += 15
        txt1 = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(15, y_offset, 230, 15),
            text="Trade capacity :",
            manager=self.ui_manager,
            container=self.info_panel,
            object_id="@Spar_font_label_8"
        )
        self._objects.append(txt1)
        y_offset += 15
        txt2 = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(15, y_offset, 230, 15),
            text="Export volume :",
            manager=self.ui_manager,
            container=self.info_panel,
            object_id="@Spar_font_label_8"
        )
        self._objects.append(txt2)
        y_offset += 15
        txt3 = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(15, y_offset, 230, 15),
            text="Import volume :",
            manager=self.ui_manager,
            container=self.info_panel,
            object_id="@Spar_font_label_8"
        )
        self._objects.append(txt3)
        y_offset += 15
        txt4 = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(15, y_offset, 230, 15),
            text="Balance :",
            manager=self.ui_manager,
            container=self.info_panel,
            object_id="@Spar_font_label_8"
        )
        self._objects.append(txt4)

        self.active_routes_panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(7, 150, 250, 340),
            manager=self.ui_manager,
            container=self,
            object_id='@planet_mgmt_panel'
        )
        txt5 = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(5, 5, 230, 15),
            text="Active Routes",
            manager=self.ui_manager,
            container=self.active_routes_panel,
            object_id="@Spar_font_label_10"
        )
        self._objects.append(txt5)

    def process_event(self, event):

        # --- Let parent class handle anything else (if needed) ---
        super().process_event(event)

    
    def update_content(self, planet):
        """Refresh or populate panel data."""
        if planet is None or planet == self.selected_planet:
            return
        self.selected_planet = planet
        self.clear_panel()
        self.show_info(planet)

    def clear_panel(self):
        for obj in getattr(self, "_objects", []):
            obj.kill()
        self._objects.clear() 

    def show(self):
        super().show()

    def hide(self):
        super().hide()
        if not hasattr(self, "tooltip_manager"):
            return  # early exit during initialization
        for obj in getattr(self, '_objects', []):
            obj.kill()
        self._objects = []
        self.selected_planet = None
        self.tooltip_manager.clear_tooltip()