import asyncio
from client.network import NetworkClient
from client.gui import GameGUI

async def network_loop(network):
    await network.connect()
    while True:
        # just sleep; updates are handled in network object
        await asyncio.sleep(0.05)

async def main_async():
    network = NetworkClient(server_ip="192.168.0.40", server_port=5000)
    await network.connect()  # wait until the full galaxy is received

    gui = GameGUI(galaxy=network.client_galaxy)

    running = True
    while gui.running:
        gui.run_one_frame()
        await asyncio.sleep(0)  # let asyncio tasks run

if __name__ == "__main__":
    asyncio.run(main_async())


####################################################################################

import pygame
import pygame_gui
import os
from client.camera import *
from core.config import *

class GameGUI:
    def __init__(self, galaxy=None):
        pygame.init()
        pygame.display.set_caption("Nexora Client")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.manager = pygame_gui.UIManager((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT) #dummy placeholder for now

        self.galaxy = galaxy or []  # list of Hex objects

        self.label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 10, 400, 30),
            text="Waiting for galaxy data...",
            manager=self.manager
        )

    def run_one_frame(self):
        time_delta = self.clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            self.manager.process_events(event)

        keys = pygame.key.get_pressed()
        if self.camera.move(keys):
            self.redraw_tiles = True
        if keys[pygame.K_ESCAPE]:
            self.running = False

        self.manager.update(time_delta)
        self.screen.fill((20, 20, 30))

        # Draw the galaxy map
        self.draw_galaxy(center=(500, 300), hex_size=HEX_SIZE)

        # Optionally still draw planet UI when a system is selected
        # self.render_planets()

        self.manager.draw_ui(self.screen)
        pygame.display.update()

    def draw_galaxy(self, center=(500, 300), hex_size=HEX_SIZE, current_empire=None):
            cam_offset = (0, 0)  # later you can add a camera system
            for hex in self.galaxy:
                points = hex.polygon(center, hex_size, cam_offset)
                # Draw the hex border
                color = (100, 100, 100)
                if hex.feature == "star_system":
                    pygame.draw.polygon(self.screen, (255, 215, 0), points)  # gold
                    # draw star system center
                    hx, hy = hex.hex_to_pixel(center, hex_size, cam_offset)
                    pygame.draw.circle(self.screen, (255, 255, 255), (int(hx), int(hy)), 6)
                elif hex.feature == "nebula":
                    pygame.draw.polygon(self.screen, (100, 150, 255), points)
                elif hex.feature == "asteroid_field":
                    pygame.draw.polygon(self.screen, (120, 120, 120), points)
                elif hex.feature == "black_hole":
                    pygame.draw.polygon(self.screen, (0, 0, 0), points)
                else:
                    pygame.draw.polygon(self.screen, (30, 30, 40), points)  # empty space
                # hex border
                pygame.draw.polygon(self.screen, (60, 60, 80), points, 1)

########################################################################################################

def load_image(self, key, path, size=None):
        try:
            img = pygame.image.load(path).convert_alpha()
            log.info(f"[AssetManager] Loaded image '{key}' from '{path}'.")
        except FileNotFoundError:
            log.warning(f"[AssetManager] Missing image '{path}' for key '{key}', using fallback.")
            try:
                img = pygame.image.load("assets/resources/question.png").convert_alpha()
            except FileNotFoundError:
                log.error("[AssetManager] Fallback image missing! Check 'assets/resources/question.png'.")
                return  # Could raise or just skip storing the image
        if size:
            img = pygame.transform.scale(img, size)
            log.debug(f"[AssetManager] Scaled image '{key}' to {size}.")
        self.assets[key] = img

def load_unit_icons(self, size=(48, 48)):
        try:
            with open("data/defense_units.json") as f:
                units_data = json.load(f)
        except Exception as e:
            log.error("Failed to load defense_units.json", exc_info=True)
            return

        # Iterate through each unit in the list
        for unit in units_data:
            unit_name = unit["name"]
            icon_path = unit.get("icon")
            if not unit_name:
                log.warning("A unit in defense_units.json is missing a 'name' field, skipping.")
                continue
            if icon_path:
                self.load_image(f"unit_{unit_name}", icon_path, size)
            else:
                log.warning(f"No icon defined for unit '{unit_name}', using fallback.")
                self.load_image(f"unit_{unit_name}", "assets/resources/question.png", size)

########################################################################################################

def load_animation(self, key, folder, size=None):
        frames = []
        for filename in sorted(os.listdir(folder)):
            if filename.endswith(".png"):
                path = os.path.join(folder, filename)
                img = pygame.image.load(path).convert_alpha()
                if size:
                    img = pygame.transform.scale(img, size)
                frames.append(img)
        self.assets[key] = frames  # list of frames

########################################################################################################
        self.resource_bonus = planet.resource_bonus
        x_img = 10
        x_bonuses = x_img
        bonus_icon_size = 30
        text_gap = 6
        for key, bonus_dict in self.resource_bonus.items():
            if not bonus_dict:
                continue
            icon_key = f"icon_{key}"
            icon_surf = self.assets.get(icon_key)
            if icon_surf:
                icon_scaled = pygame.transform.smoothscale(icon_surf, (bonus_icon_size, bonus_icon_size))
                icon_image = pygame_gui.elements.UIImage(
                    relative_rect=pygame.Rect(x_bonuses, y_offset, bonus_icon_size, bonus_icon_size),
                    image_surface=icon_scaled,
                    manager=self.ui_manager,
                    container=self
                )
                self._objects.append(icon_image)
                x_bonuses += bonus_icon_size + text_gap

            # Render bonus text
            bonus_text_raw = "<br>".join(f"{k.title()} {v}" for k, v in bonus_dict.items())
            planet_resources_bonus_label = pygame_gui.elements.UITextBox(
                relative_rect=pygame.Rect(x_bonuses, y_offset, 600, 80),
                html_text=f"<p align='left'>{bonus_text_raw}</p>",
                manager=self.ui_manager,
                container=self,
                object_id="@resources_bonus_text_box"
            )
            self._objects.append(planet_resources_bonus_label)
            y_offset += 80
            x_bonuses = x_img  # reset x for next line

########################################################################################################

def show_info(self, planet):
        for obj in getattr(self, '_objects', []):
            obj.kill()
        self._objects = []
        self.tooltip_manager.clear_tooltip()
        self.icons_rect = []
        title = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 5, 210, 30),
            text='Defense management',
            manager=self.ui_manager,
            container=self,
            object_id="@planet_name_label_18"
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
        credit_key = "icon_coin"
        energy_key = "icon_energy"
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
                    container=self
                )
            else:
                ui_icon = pygame_gui.elements.UILabel(
                    relative_rect=icon_rect,
                    text="?",
                    manager=self.ui_manager,
                    container=self
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
                container=self,
                object_id='@left_label'
            )
            self._objects.append(name_label)

            # optional subtitle or stats line (defense value)
            defense_icon=pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect(name_x, row_y +30, 15, 15),
                image_surface=self.assets.get("icon_defense"),
                manager=self.ui_manager,
                container=self
            )
            self._objects.append(defense_icon)
            stats_text = f"{data.get("defense_value", 0)}"
            stats_label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(name_x + 20, row_y + 30, 18, 18),
                text=stats_text,
                manager=self.ui_manager,
                container=self,
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
                    container=self
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
                container=self,
                object_id='@left_label'
            )
            self._objects.append(cost_label)
            rect=pygame.Rect(cost_x, row_y+30, 80, 20)
            self.icons_rect.append((rect, "cost (+upkeep)"))

            cost_res= f"{cost.get("industry")}"
            cost_res_label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(credit_label_x, row_y + 30, cost_w, 20),
                text=cost_res,
                manager=self.ui_manager,
                container=self,
                object_id='@left_label'
            )
            self._objects.append(cost_res_label)
            rect=pygame.Rect(cost_x, row_y+30, 80, 20)
            # 4) Energy usage (energy icon + power_use)
            energy_x = credit_label_x + 60 + PAD_X
            if energy_surface:
                energy_img = pygame_gui.elements.UIImage(
                    relative_rect=pygame.Rect(energy_x, row_y + 30, 20, 20),
                    image_surface=energy_surface,
                    manager=self.ui_manager,
                    container=self
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
                container=self,
                object_id='@left_label'
            )
            self._objects.append(energy_label)
            rect=pygame.Rect(energy_x, row_y+30, 60, 20)
            self.icons_rect.append((rect, "energy cost \n(while in use)"))

            # 5) Build button (right side)
            build_btn_rect = pygame.Rect(self.relative_rect.width - 80 - 70, row_y + (ROW_HEIGHT - 28)//2 + 10, 70, 28)
            build_btn = pygame_gui.elements.UIButton(
                relative_rect=build_btn_rect,
                text="Build",
                manager=self.ui_manager,
                container=self,
                object_id="@build_button_defense"
            )
            self._objects.append(build_btn)
            self.icons_rect.append((build_btn_rect, f"Construct one {data.get("name", "Unknown Unit")}"))
            # 6) Destroy button (right side)
            destroy_btn_rect = pygame.Rect(self.relative_rect.width - 80, row_y + (ROW_HEIGHT - 28)//2 + 10, 70, 28)
            destroy_btn = pygame_gui.elements.UIButton(
                relative_rect=destroy_btn_rect,
                text="Destroy",
                manager=self.ui_manager,
                container=self,
                object_id="@build_button_defense"
            )
            self._objects.append(destroy_btn)
            self.icons_rect.append((destroy_btn_rect, f"Destroy one {data.get("name", "Unknown Unit")}"))

            # store mapping if you want to handle clicks on this button later:
            # e.g. self._unit_row_map[build_btn] = unit
            if not hasattr(self, "_unit_row_map"):
                self._unit_row_map = {}
            self._unit_row_map[build_btn] = unit_id
            i+=1

########################################################################################################

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

########################################################################################################
 
def ex(self):
        #Populate inside the panel (example labels)
        self._stats_labels = {}
        stat_names = ["Defense", "Offense", "Energy Use", "Upkeep", "storage space", "Costs"]
        for j, stat in enumerate(stat_names):
            label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(10, 10 + j*25, stats_w-20, 24),
                text=f"{stat}: ",
                manager=self.ui_manager,
                container=self._stats_container,
                object_id="@left_label"
            )
            self._stats_labels[stat] = label
            self._objects.append(label)
        
        btn_width = 100
        btn_height = 30
        btn_pad = 10

        self._build_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(10, stats_h - btn_height - btn_pad, btn_width, btn_height),
            text="Build",
            manager=self.ui_manager,
            container=self._stats_container,
            object_id="@build_button_defense"
        )
        self._objects.append(self._build_button)

        self._destroy_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(10+btn_width, stats_h - btn_height - btn_pad, btn_width, btn_height),
            text="Destroy",
            manager=self.ui_manager,
            container=self._stats_container,
            object_id="@build_button_defense"
        )
        self._objects.append(self._destroy_button)

def handle_unit_click(self, clicked_button):
        unit_id = self._unit_row_map.get(clicked_button)
        if unit_id:
            self._selected_unit = REGISTRY["defense_units"][unit_id]
            # Update stats panel
            cost = self._selected_unit['cost']
            # Clear old cost icons (if any)
            for icon, label in getattr(self, "_cost_elements", []):
                icon.kill()
                label.kill()
            self._cost_elements = []
            self._stats_labels["Defense"].set_text(f"Defense: {self._selected_unit['stats'].get('defense', 5)}")
            self._stats_labels["Offense"].set_text(f"Offense: {self._selected_unit['stats'].get('offense', 5)}")
            self._stats_labels["Energy Use"].set_text(f"Energy Use: {self._selected_unit['power_use']}")
            self._stats_labels["Upkeep"].set_text(f"Upkeep: {self._selected_unit['upkeep'].get('credits', 0)}")
            self._stats_labels["storage space"].set_text(f"Storage space: {self._selected_unit['storage_space']}")
            # Start position for cost section
            x_start = 20
            y_start = 10 + len(self._stats_labels) * 25 + 10  # after existing stat labels
            icon_size = 24
            spacing_y = 30
            col_width = 90
            max_per_column = 3

            # Helper function to add a cost row
            def add_cost_row(icon_path, text,index, color=None, tooltip_text=""):
                # compute column and row position
                col = index // max_per_column
                row = index % max_per_column
                x = x_start + col * col_width
                y = y_start + row * spacing_y

                try:
                    icon_surface = pygame.image.load(icon_path).convert_alpha()
                except FileNotFoundError:
                    icon_surface = pygame.Surface((icon_size, icon_size))
                    icon_surface.fill((120, 120, 120))
                icon_elem = pygame_gui.elements.UIImage(
                    relative_rect=pygame.Rect(x, y, icon_size, icon_size),
                    image_surface=pygame.image.load(icon_path).convert_alpha(),
                    manager=self.ui_manager,
                    container=self._stats_container,
                )
                label_elem = pygame_gui.elements.UILabel(
                    relative_rect=pygame.Rect(x + icon_size + 8, y, 150, icon_size),
                    text=text,
                    manager=self.ui_manager,
                    container=self._stats_container,
                    object_id="@left_label"
                )
                if color:
                    label_elem.change_object_id("@left_label_red")

                if tooltip_text:
                    icon_elem.set_tooltip(tooltip_text, object_id="@tool_tip")
                    label_elem.set_tooltip(tooltip_text, object_id="@tool_tip")
                
                self._cost_elements.append((icon_elem, label_elem))

            # --- Now display cost items ---
            cost_index = 0
            if "credits" in cost:
                add_cost_row("assets/icons/coin.png", f"{cost['credits']}", cost_index, tooltip_text="credits")
                cost_index += 1

            if "industry" in cost:
                add_cost_row("assets/icons/industry.jpg", f"{cost['industry']}", cost_index, tooltip_text="industry points")
                cost_index += 1

            
            # Handle resource-based costs dynamically
            resources = cost.get("resources", {})
            for res_name, amount in resources.items():
                icon_path = f"assets/resources/{res_name}.png"
                # Check planet resource availability (customize to your data model)
                planet_amount = getattr(self.selected_planet, "resources", {}).get(res_name, 0)
                if planet_amount < amount:
                    text_color = "#FF5555"
                if text_color:
                    add_cost_row(icon_path, f"{amount}", cost_index,color="red", tooltip_text=f"{res_name}")
                else :
                    add_cost_row(icon_path, f"{amount}", cost_index, tooltip_text=f"{res_name}")
                cost_index += 1

########################################################################################################

# Create a dropdown to filter by layer
        layers = sorted({u["layer"] for u in REGISTRY["defense_units"].values()})
        options_list = ["All"] + layers
        self._layer_filter = pygame_gui.elements.UIDropDownMenu(
            options_list=options_list,
            starting_option=f"{filter_layer}",
            relative_rect=pygame.Rect(100, 45, 180, 24),
            manager=self.ui_manager,
            container=self,
            object_id="@dropdown_units_layer_filter"
        )
        self._objects.append(self._layer_filter)

        # Load defense units (use your loader or an injected list)
        # Assuming you have a function load_defense_units() that returns objects with .name, .layer, .defense_value, .upkeep, .power_use
        units = REGISTRY["defense_units"]

        # Apply filter if requested
        if filter_layer != "All":
            units = {uid: data for uid, data in units.items() if data.get("layer") == filter_layer}
        
        # Layout constants
        PAD_Y = 8
        ROW_HEIGHT = 56
        ICON_SIZE = (48, 48)
        start_x = 8
        start_y = 70

        self._unit_row_map = {}
        i = 0
        for unit_id, data in units.items():
            row_y = start_y + i * (ROW_HEIGHT + PAD_Y)

            # Unit icon
            asset_key = f"unit_{data.get('name', 'Unknown Unit')}"
            icon_surface = self.assets.get(asset_key)
            if icon_surface is None:
                icon_surface = self.assets.get("assets/resources/question.png")
            icon_rect = pygame.Rect(start_x, row_y + (ROW_HEIGHT - ICON_SIZE[1]) // 2, ICON_SIZE[0], ICON_SIZE[1])
            ui_image = pygame_gui.elements.UIImage(
                relative_rect=icon_rect,
                image_surface=icon_surface,
                manager=self.ui_manager,
                container=self
            )
            self._objects.append(ui_image)
            ui_icon = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(start_x + ICON_SIZE[0] + PAD_Y, row_y + 16, 200, 24),
                text=data.get("name", "Unknown Unit"),
                manager=self.ui_manager,
                container=self,
                object_id="@unit_button"
            )
            #ui_icon.image = icon_surface  # custom property to store icon
            self._objects.append(ui_icon)

            # Store mapping for selection
            self._unit_row_map[ui_icon] = unit_id
            i += 1