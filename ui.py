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

class TileInfoPanel(pygame_gui.elements.UIWindow):
    def __init__(self, ui_manager, assets, rect):
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
        # Preload default icons once using assetsmanager for performance
        self.slots_icon = pygame.image.load(SLOTS_ICON_PLACEHOLDER).convert_alpha()
        self.defense_icon = pygame.image.load(DEFENSE_ICON_PLACEHOLDER).convert_alpha()
        
        # Store planet icon rects for tooltip detection
        self.planet_icon_rects = []

        # This container is now the main content area inside the window
        self.container = self.get_container()


    def show_info(self, hex_obj):
        self.clear()
        if not hex_obj or hex_obj.feature != "star_system":
            return
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
                container=self.container
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
                text=f"{planet.used_slots}/{planet.slots}",
                manager=self.ui_manager,
                container=self.container
            )
            self._objects.append(slots_text)
            # 5. Defense icon and value (rightmost)
            defense_image = pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect(175, this_y+16, 26, 22),
                image_surface=self.defense_icon,
                manager=self.ui_manager,
                container=self.container
            )
            self._objects.append(defense_image)
            # Placeholder logic for defense value. Replace with real intel/ownership detection
            defense_value = 0
            defense_text = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(204, this_y+16, 30, 20),
                text=f"{defense_value}",
                manager=self.ui_manager,
                container=self.container,
                object_id='@left_label'
            )
            self._objects.append(defense_text)
            y += 40
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
    
    def draw_tooltips(self, surface):
        """Draw tooltips on the given surface."""
        if self.visible:
            self.tooltip_manager.draw(surface)

    def clear(self):
        for obj in getattr(self, '_objects', []):
            obj.kill()
        self._objects = []
        self.planet_icon_rects = []
        self.tooltip_manager.clear_tooltip()

    def hide(self):
        self.clear()


class PlanetManagement:
    def __init__(self, ui_manager, assets, rect):
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
        self.mode_icons_rect = []
        self.resource_category_buttons = {}
        self.selected_category = None
        self.selected_tier = None
        self.selected_resource = None #the resource the panet will mine/refine
        # Header
        self.header = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 10, rect.width - 20, 28),
            text='Planet Management',
            manager=self.ui_manager,
            container=self.panel
        )
        # Planet name
        self.planet_name_lbl = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 40, rect.width - 20, 24),
            text='-'
            ,manager=self.ui_manager,
            container=self.panel
        )
        y=70
        # Resource dropdown
        self.mode_lbl = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, y, 100, 24),
            text='Mode : ',
            manager=self.ui_manager,
            container=self.panel,
            object_id='@left_label'
        )
        self.mode_icons = {
            'mine': pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect(80,y, 48, 48),
                image_surface=self.assets.get("mine_icon"),
                manager=self.ui_manager,
                container=self.panel
            ),
            'refine': pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect(148, y, 48, 48),
                image_surface=self.assets.get("industry_icon"),
                manager=self.ui_manager,
                container=self.panel
            ),
        }
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

        # Resource dropdown
        self.resource_lbl = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, y, 100, 24),
            text='Resource',
            manager=self.ui_manager,
            container=self.panel,
            object_id='@left_label'
        )
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
            x += size + spacing
        y+=30
        #resources by caterories (see below)
        y+=70
        self.apply_resource_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(10, y, rect.width - 20, 28),
            text='Apply Extraction/Refining',
            manager=self.ui_manager,
            container=self.panel
        )
        y+=30
        # Buildings section
        self.build_lbl = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, y, rect.width - 20, 22),
            text='Constructions',
            manager=self.ui_manager,
            container=self.panel
        )
        y+=25
        self.btn_build_farm = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(10, y, (rect.width - 30)//2, 28),
            text='Build Farm',
            manager=self.ui_manager,
            container=self.panel
        )
        self.btn_build_mine = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(20 + (rect.width - 30)//2, y, (rect.width - 30)//2, 28),
            text='Build Mine',
            manager=self.ui_manager,
            container=self.panel
        )
        y+=30
        self.btn_build_industry = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(10, y, (rect.width - 30)//2, 28),
            text='Build Industry',
            manager=self.ui_manager,
            container=self.panel
        )
        self.btn_build_forge = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(20 + (rect.width - 30)//2, y, (rect.width - 30)//2, 28),
            text='Build Forge',
            manager=self.ui_manager,
            container=self.panel
        )
        y+=30
        # Defense section
        self.defense_lbl = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, y, rect.width - 20, 22),
            text='Planetary Defense',
            manager=self.ui_manager,
            container=self.panel
        )
        y+=25
        self.btn_build_defense = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(10, y, rect.width - 20, 28),
            text='Build Defense +1',
            manager=self.ui_manager,
            container=self.panel
        )
        # Status line
        self.status_lbl = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 338, rect.width - 20, 22),
            text='',
            manager=self.ui_manager,
            container=self.panel
        )

    def _rebuild_resource_options(self, resources_data):
        # Flatten resource names
        names = list(resources_data.keys())
        if not names:
            names = ['-']
        current = names[0]
        # Recreate dropdown (pygame_gui does not support dynamic option change cleanly)
        self.resource_dropdown.kill()
        self.resource_dropdown = pygame_gui.elements.UIDropDownMenu(
            options_list=names,
            starting_option=current,
            relative_rect=pygame.Rect(120, 105, self.panel.rect.width - 130, 26),
            manager=self.ui_manager,
            container=self.panel
        )

    def show(self, planet, resources_data):
        self.selected_planet = planet
        self.planet_name_lbl.set_text(f"{planet.name}")
        # Build resource options
        #self._rebuild_resource_options(resources_data)
        self.panel.show()

    def hide(self):
        self.panel.hide()
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
            x += size + spacing


    def process_event(self, event, resources_data):
        if event.type == pygame_gui.UI_BUTTON_PRESSED and self.selected_planet:
            if event.ui_element == self.btn_build_farm:
                self.selected_planet.buildings['farm'] += 1
                self.status_lbl.set_text("Built Farm")
            elif event.ui_element == self.btn_build_mine:
                self.selected_planet.buildings['mine'] += 1
                self.status_lbl.set_text("Built Mine")
            elif event.ui_element == self.btn_build_industry:
                self.selected_planet.buildings['industry'] += 1
                self.status_lbl.set_text("Built Industry")
            elif event.ui_element == self.btn_build_forge:
                self.selected_planet.buildings['forge'] += 1
                self.status_lbl.set_text("Built Forge")
            elif event.ui_element == self.btn_build_defense:
                self.selected_planet.defense_value += 1
                self.status_lbl.set_text(f"Defense {self.selected_planet.defense_value}")
            elif event.ui_element == self.apply_resource_btn:
                self.selected_planet.current_resource = self.selected_resource
                print("[UI] test click")
                print(f"[UI] self.selected_planet: {self.selected_planet}")
                print(f"[UI] self.selected_resource: {self.selected_resource}")
                print(f"[UI] self.selected_planet.current_resource: {self.selected_planet.current_resource}")

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


