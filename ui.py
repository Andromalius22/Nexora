import pygame
import pygame_gui
import json
import os
from assetsmanager import AssetsManager
from defense import *
from registry import REGISTRY

from logger_setup import *

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

class NotificationManager:
    def __init__(self, ui_manager, screen_rect):
        self.ui_manager = ui_manager
        self.screen_rect = screen_rect
        self.active_notifications = []
        self.display_time = 5000  # milliseconds (5 seconds)

        # === Visual style for a 4X sci-fi feel ===
        self.font_color = pygame.Color("#00FF99")  # bright neon green
        self.bg_color = pygame.Color(10, 20, 15)   # deep dark greenish background
        self.border_color = pygame.Color(0, 255, 153)  # same as font, slightly glowing border
        self.alpha = 210  # semi-transparent

    def show(self, message, duration=None):
        """Display a notification at the top center of the screen."""
        if duration is None:
            duration = self.display_time

        # Create the label
        notif_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(0, 0, 420, 36),
            text=message,
            manager=self.ui_manager,
            anchors={'centerx': 'centerx', 'top': 'top'},
            object_id=pygame_gui.core.ObjectID(class_id='@notification_label')
        )

        # Center horizontally
        notif_label.set_position((
            self.screen_rect.centerx - notif_label.rect.width // 2,
            25
        ))

        # Store for timed removal
        self.active_notifications.append((notif_label, pygame.time.get_ticks(), duration))


    def update(self):
        """Remove expired notifications."""
        current_time = pygame.time.get_ticks()
        new_notifications = []
        y_offset = 20

        for notif, start_time, duration in self.active_notifications:
                elapsed = current_time - start_time
                if elapsed > duration:
                    notif.kill()
                    continue

                # stack vertically
                notif.set_position((
                    self.screen_rect.centerx - notif.rect.width // 2,
                    y_offset
                ))
                y_offset += notif.rect.height + 10
                new_notifications.append((notif, start_time, duration))

        self.active_notifications = new_notifications

##############################################################################################################################

class TileInfoPanel(pygame_gui.elements.UIWindow):
    def __init__(self, ui_manager, assets, rect, callback_on_planet_click=None):
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
                image_surface=self.assets.get("defense_icon"),
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
                    icon_surface = self.assets.get(f"{slot.type}_icon") if slot.type != "empty" else self.assets.get("plus_icon")
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
                tooltip_text = f"{planet.name_display}\n{planet.description}\nRarity: {planet.rarity.title()}"
                self.tooltip_manager.show_tooltip(tooltip_text, icon_info['rect'])
                break
        for icon_info in self.slot_icon_rects:
            if icon_info['rect'].collidepoint(relative_mouse_pos):
                slot = icon_info['slot']
                tooltip_text = f"{slot}"
                self.tooltip_manager.show_tooltip(tooltip_text, icon_info['rect'])
                break
    
    def draw_tooltips(self, surface):
        """Draw tooltips on the given surface."""
        if self.visible:
            self.tooltip_manager.draw(surface)
    
    def handle_events(self, event):
        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            for button, planet in self.planet_buttons:
                if event.ui_element == button and self.callback_on_planet_click:
                    self.callback_on_planet_click(planet)
                if event.ui_element == button :
                     self.set_selected_planet(planet)
    
    def set_selected_planet(self, planet):
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
    def __init__(self, ui_manager, assets, rect, building_mgmt=None, notifications_manager=None):
        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=rect,
            starting_height=1,
            manager=ui_manager,
            visible=False
        )
        self.rect_input=rect
        self.ui_manager = ui_manager
        self.assets = assets
        self._objects = []
        self.selected_planet = None
        self.font = pygame.font.SysFont("arial", 16)
        self.tooltip_manager = TooltipManager(self.font)
        self.building_mgmt=building_mgmt
        self.notifications= notifications_manager
        self.mode_icons_rect = []
        self.resource_category_buttons = {}
        self.selected_category = None
        self.selected_tier = None
        self.selected_resource = None #the resource the panet will mine/refine
        self._objects = []

    def show_info(self):
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
                image_surface=self.assets.get("mine_icon"),
                manager=self.ui_manager,
                container=self.panel
            ),
            'refine': pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect(148, y, 48, 48),
                image_surface=self.assets.get("refine_icon"),
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
            text='Select resource to extract',
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

        for cat in ['ore', 'gas', 'liquid', 'organics']:
            btn = pygame_gui.elements.UIImage( 
                relative_rect=pygame.Rect(x, y, size, size), 
                image_surface=self.assets.get(f"{cat}_icon"), 
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

    def show(self, planet, resources_data):
        self.selected_planet = planet
        self.panel.show()
        self.show_info()
        self.planet_name_lbl.set_text(f"{planet.name}")

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
        with open("resources.json") as f:
            self.resources_data = json.load(f)
        # Remove previous resource icons if any
        for img in getattr(self, "resource_icons", {}).values():
            img.kill()
        self.resource_icons = {}

        # Filter by type
        resources_of_type = [
            (name, info)
            for name, info in self.resources_data.items()
            if info.get("resource_type") == category
        ]

        # Filter and sort: keep only tiers 1–4
        resources_of_type = [
            (name, info)
            for name, info in self.resources_data.items()
            if info.get("resource_type") == category and 1 <= info.get("tier", 0) <= 4
        ]
        resources_of_type.sort(key=lambda x: x[1]["tier"])


        # Create icons
        x = 10
        y = 200
        size = 40
        spacing = 8

        for name, info in resources_of_type:
            icon_path = info.get("resource_icon")
            if not icon_path:
                continue
            #print(f"[UI] name: {name}")
            icon_surface=self.assets.get(f"resource_{name}")
            #icon_surface = pygame.image.load(icon_path).convert_alpha()
            btn = pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect(x, y, size, size),
                image_surface=icon_surface,
                manager=self.ui_manager,
                container=self.panel
            )
            self.resource_icons[name] = btn
            self._objects.append(btn)
            x += size + spacing


    def process_event(self, event, planet):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:

            if event.ui_element == self.apply_resource_btn:
                self.selected_planet.current_resource = self.selected_resource

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            # Convert mouse_pos relative to panel
            panel_rect = self.panel.rect
            rel = (mouse_pos[0] - panel_rect.x, mouse_pos[1] - panel_rect.y)

            # Detect click inside the icons
            if self.mode_icons['mine'].relative_rect.collidepoint(rel):
                self.mode_selected = 'mine'
            elif self.mode_icons['refine'].relative_rect.collidepoint(rel):
                self.mode_selected = 'refine'
            
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
                    self.selected_planet.current_resource=self.selected_resource
                    return

class SlotsManagement:
    def __init__(self, ui_manager, assets, rect, notifications_manager=None, building_mgmt=None):
        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=rect,
            starting_height=1,
            manager=ui_manager,
            visible=False
        )
        self.ui_manager = ui_manager
        self.assets = assets
        self._objects = []
        self.selected_planet = None
        self.font = pygame.font.SysFont("arial", 16)
        self.tooltip_manager = TooltipManager(self.font)
        self.notifications= notifications_manager
        self.building_mgmt=building_mgmt

        self.icon_size = 19
        self.icon_gap = 6

        self.slot_icon_rect=[] #for tooltips
    
    def show_info(self, planet):
        for obj in getattr(self, '_objects', []):
            obj.kill()
        self._objects = []
        self.tooltip_manager.clear_tooltip()
        self.slot_icon_rect = []
        title = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(self.panel.relative_rect.width/4, 5, 150, 30),
            text='Slots management',
            manager=self.ui_manager,
            container=self.panel
        )
        self._objects.append(title)
        # Dynamic stacking
        current_y = 40
        for slot_type in ["farm", "mine", "refine", "industry", "energy"]:
            consumed_height = self._display_slots_row(planet, slot_type, current_y)
            current_y += consumed_height + 10  # 10px gap between sections

    
    def _display_slots_row(self, planet, slot_type, y_offset):
        y = y_offset
        title = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, y, 100, 30),
            text=f"{slot_type}",
            manager=self.ui_manager,
            container=self.panel,
            object_id='@left_label'
        )
        self._objects.append(title)
            
        statistic = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(110, y, 100, 30),
            text=f"{self.selected_planet.statistics[slot_type]}/min",
            manager=self.ui_manager,
            container=self.panel
        )
        self._objects.append(statistic)
        y+=30

        max_per_row = 10

        # Filter only type slots
        type_slots = [s for s in planet.slots if s.type == slot_type]

        # Add utility icons
        display_slots = type_slots + ["plus_icon", "plus_02_icon", "moins_icon"]

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
            if slot in ("plus_icon", "plus_02_icon"):
                # Skip the plus icons if no empty slots remain
                if not planet.get_available_slots():
                    continue  # no space left, don't show plus icon
            if slot in ("plus_icon", "plus_02_icon", "moins_icon"):
                icon_surface = self.assets.get(slot)
                icon_image = pygame_gui.elements.UIImage(
                    relative_rect=rect,
                    image_surface=icon_surface,
                    manager=self.ui_manager,
                    container=self.panel
                )
                self._objects.append(icon_image)

                # Define tooltip and action
                tooltip_data = {
                    "plus_icon": ("enough space for one more slot", None),
                    "plus_02_icon": (f"click to build one {slot_type}", "add_slot"),
                    "moins_icon": (f"click to remove one {slot_type}", "remove_slot"),
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
            icon_surface = self.assets.get(f"{slot_type}_icon").copy()

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
                container=self.panel
            )
            self._objects.append(icon_image)
            self.slot_icon_rect.append({
                "rect": rect,
                "tooltip": f"click to activate/deactivate {slot_type} slot",
                "action": None,
                "slot_type": slot_type,
                "slot_index": slot_index,
            })

        # Return vertical height used by this section
        return total_height + 30  # includes title height
    
    def update_tooltips(self, mouse_pos):
        """Check if mouse is hovering over slots and show tooltips."""
        self.tooltip_manager.clear_tooltip()
        
        # Adjust mouse position relative to panel
        panel_rect = self.panel.rect
        relative_mouse_pos = (mouse_pos[0] - panel_rect.x, mouse_pos[1] - panel_rect.y)
        
        for entry in self.slot_icon_rect:
            if entry.get("rect").collidepoint(relative_mouse_pos):
                self.tooltip_manager.show_tooltip(entry.get("tooltip"), entry["rect"])
                break
    
    def draw_tooltips(self, surface):
        """Draw tooltips on the given surface."""
        if self.panel.visible:
            self.tooltip_manager.draw(surface)
    
    def process_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            panel_rect = self.panel.rect
            rel_mouse = (mouse_pos[0] - panel_rect.x, mouse_pos[1] - panel_rect.y)
            msg=' '

            # Check slot action icons
            for entry in getattr(self, "slot_icon_rect", []):
                if entry["rect"].collidepoint(rel_mouse):
                    action = entry.get("action")
                    slot_type = entry.get("slot_type")
                    slot_index = entry.get("slot_index")

                    # Handle slot activation toggle
                    if action is None and slot_index is not None:
                        # Find the actual slot object for this rect
                        # (assuming same order of slots as display)
                        slots_of_type = [s for s in self.selected_planet.slots if s.type == slot_type]
                        if slot_index < len(slots_of_type):
                            slot = slots_of_type[slot_index]
                            slot.active = not slot.active  # toggle activation
                            self.selected_planet.on_slots_changed(slot_type=slot_type)
                            log.debug(f"slot {slot_index} of type {slot_type} toggled {slot.active} on {self.selected_planet.name}. new stats : {self.selected_planet.statistics["farm"]}")
                            self.show_info(self.selected_planet)  # refresh UI
                            
                        break

                    elif action == "add_slot":
                        msg = self.selected_planet.start_build(f"{slot_type}", self.building_mgmt)
                        self.selected_planet.on_slots_changed(slot_type=slot_type, action="add")
                        self.show_info(self.selected_planet)  # refresh UI
                        self.notifications.show(msg)
                        
                        return

                    elif action == "remove_slot":
                        msg = self.selected_planet.remove_building_from_slot(slot_type)
                        self.selected_planet.on_slots_changed(slot_type=slot_type, action="remove")
                        self.show_info(self.selected_planet)
                        self.notifications.show(msg)
                        
                        return

        

    def show(self, planet):
        self.selected_planet = planet
        self.panel.show()
        self.show_info(planet)

    def hide(self):
        self.panel.hide()
        for obj in getattr(self, '_objects', []):
            obj.kill()
        self._objects = []
        self.selected_planet = None
        self.tooltip_manager.clear_tooltip()
    
class PlanetaryDefenseManagement:
    def __init__(self, ui_manager, assets, rect, notifications_manager=None):
        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=rect,
            starting_height=1,
            manager=ui_manager,
            visible=False
        )
        self.ui_manager = ui_manager
        self.assets = assets
        self._objects = []
        self.selected_planet = None
        self.font = pygame.font.SysFont("arial", 16)
        self.tooltip_manager = TooltipManager(self.font)
        self.notifications= notifications_manager
        self.icons_rect = [] #for tooltips
    
    def show_info(self, planet):
        for obj in getattr(self, '_objects', []):
            obj.kill()
        self._objects = []
        self.tooltip_manager.clear_tooltip()
        self.icons_rect = []
        title = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(self.panel.relative_rect.width/4, 5, 150, 30),
            text='Defense management',
            manager=self.ui_manager,
            container=self.panel
        )
        self._objects.append(title)

        # Load defense units (use your loader or an injected list)
        # Assuming you have a function load_defense_units() that returns objects with .name, .layer, .defense_value, .upkeep, .power_use
        units = REGISTRY["defense_units"]


        # Layout constants
        PAD_X = 8
        PAD_Y = 8
        ROW_HEIGHT = 56
        ICON_SIZE = (48, 48)
        start_x = 8
        start_y = 50

        # icons for cost/energy — these should be preloaded in your AssetManager with keys 'icon_credit' and 'icon_energy'
        credit_key = "credit_icon"
        energy_key = "energy_icon"
        credit_surface = self.assets.get(credit_key) if hasattr(self, "assets") else None
        energy_surface = self.assets.get(energy_key) if hasattr(self, "assets") else None

        # Iterate units and create a row per unit
        i=0
        for unit_id, data in units.items():
            row_y = start_y + i * (ROW_HEIGHT + PAD_Y)

            # 1) Unit icon (use asset key convention "unit_<name>")
            asset_key = f"unit_{data.get("name", "Unknown Unit")}"
            icon_surface = None
            if hasattr(self, "assets"):
                icon_surface = self.assets.get(asset_key)
            if icon_surface is None:
                # fallback to a generic icon if the specific unit icon is missing
                icon_surface = self.assets.get("assets/resources/question.png") if hasattr(self, "assets") else None

            # Create UIImage for unit icon
            icon_rect = pygame.Rect(start_x, row_y + (ROW_HEIGHT - ICON_SIZE[1]) // 2, ICON_SIZE[0], ICON_SIZE[1])
            if icon_surface:
                ui_icon = pygame_gui.elements.UIImage(
                    relative_rect=icon_rect,
                    image_surface=icon_surface,
                    manager=self.ui_manager,
                    container=self.panel
                )
            else:
                ui_icon = pygame_gui.elements.UILabel(
                    relative_rect=icon_rect,
                    text="?",
                    manager=self.ui_manager,
                    container=self.panel
                )
            self._objects.append(ui_icon)

            # 2) Unit name + layer text
            name_x = icon_rect.right + PAD_X
            name_w = 260
            name_text = f"{data.get("name", "Unknown Unit")} — {data.get("layer", "UNKNOWN")}"  # layer in capitals via Enum.name
            name_label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(name_x, row_y + 8, name_w, 20),
                text=name_text,
                manager=self.ui_manager,
                container=self.panel,
                object_id='@left_label'
            )
            self._objects.append(name_label)

            # optional subtitle or stats line (defense value)
            defense_icon=pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect(name_x, row_y +30, 15, 15),
                image_surface=self.assets.get("defense_icon"),
                manager=self.ui_manager,
                container=self.panel
            )
            self._objects.append(defense_icon)
            stats_text = f"{data.get("defense_value", 0)}"
            stats_label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(name_x + 20, row_y + 30, 18, 18),
                text=stats_text,
                manager=self.ui_manager,
                container=self.panel,
                object_id="#small_label"
            )
            self._objects.append(stats_label)
            rect=pygame.Rect(name_x, row_y+30, 40, 18)
            self.icons_rect.append((rect, "defense points"))

            # 3) Cost/upkeep block (credit icon + "cost (+upkeep)")
            cost_x = name_x + 40 + PAD_X
            cost_w = 120
            # credit icon
            if credit_surface:
                credit_img = pygame_gui.elements.UIImage(
                    relative_rect=pygame.Rect(cost_x, row_y + 30, 20, 20),
                    image_surface=credit_surface,
                    manager=self.ui_manager,
                    container=self.panel
                )
                self._objects.append(credit_img)
                credit_label_x = cost_x + 24
            else:
                credit_label_x = cost_x

            # Format cost text: use defense_value as cost placeholder (tweak as needed)
            # You mentioned cost (+upkeep). I assume `upkeep` is the recurring cost, and there might be a build cost field later.
            cost = data.get("cost", {})
            cost_text = f"{cost.get("credits", 0)}  (+{data.get("upkeep", {}).get("credits", 0)})"
            cost_label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(credit_label_x, row_y + 30, cost_w, 20),
                text=cost_text,
                manager=self.ui_manager,
                container=self.panel,
                object_id='@left_label'
            )
            self._objects.append(cost_label)
            rect=pygame.Rect(cost_x, row_y+30, 80, 20)
            self.icons_rect.append((rect, "cost (+upkeep)"))

            # 4) Energy usage (energy icon + power_use)
            energy_x = credit_label_x + 60 + PAD_X
            if energy_surface:
                energy_img = pygame_gui.elements.UIImage(
                    relative_rect=pygame.Rect(energy_x, row_y + 30, 20, 20),
                    image_surface=energy_surface,
                    manager=self.ui_manager,
                    container=self.panel
                )
                self._objects.append(energy_img)
                energy_label_x = energy_x + 24
            else:
                energy_label_x = energy_x

            energy_text = f"{data.get("power_use", 0)}"
            energy_label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(energy_label_x, row_y + 30, 20, 20),
                text=energy_text,
                manager=self.ui_manager,
                container=self.panel,
                object_id='@left_label'
            )
            self._objects.append(energy_label)
            rect=pygame.Rect(energy_x, row_y+30, 60, 20)
            self.icons_rect.append((rect, "energy cost \n(while in use)"))

            # 5) Build button (right side)
            build_btn_rect = pygame.Rect(self.panel.relative_rect.width - 80, row_y + (ROW_HEIGHT - 28)//2 + 10, 70, 28)
            build_btn = pygame_gui.elements.UIButton(
                relative_rect=build_btn_rect,
                text="Build",
                manager=self.ui_manager,
                container=self.panel
            )
            self._objects.append(build_btn)
            self.icons_rect.append((build_btn_rect, f"Construct one {data.get("name", "Unknown Unit")}"))

            # store mapping if you want to handle clicks on this button later:
            # e.g. self._unit_row_map[build_btn] = unit
            if not hasattr(self, "_unit_row_map"):
                self._unit_row_map = {}
            self._unit_row_map[build_btn] = unit_id
            i+=1

    def update_tooltips(self, mouse_pos):
        """Check if mouse is hovering over slots and show tooltips."""
        self.tooltip_manager.clear_tooltip()
        
        # Adjust mouse position relative to panel
        panel_rect = self.panel.rect
        relative_mouse_pos = (mouse_pos[0] - panel_rect.x, mouse_pos[1] - panel_rect.y)
        
        for rect, tooltip in self.icons_rect:
            if rect.collidepoint(relative_mouse_pos):
                self.tooltip_manager.show_tooltip(tooltip, rect)
                break
    
    def draw_tooltips(self, surface):
        """Draw tooltips on the given surface."""
        if self.panel.visible:
            self.tooltip_manager.draw(surface)
        
    def process_event(self, event):
        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            btn = event.ui_element
            if btn in self._unit_row_map:
                unit = self._unit_row_map[btn]
                msg = self.selected_planet.start_build(f"{unit}")
                self.notifications.show(msg)
                #print(f"[Defense] Queued build: {unit.name} on {self.selected_planet.name}")

    def show(self, planet):
        self.selected_planet = planet
        self.panel.show()
        self.show_info(planet)

    def hide(self):
        self.panel.hide()
        for obj in getattr(self, '_objects', []):
            obj.kill()
        self._objects = []
        self.selected_planet = None
        self.tooltip_manager.clear_tooltip()