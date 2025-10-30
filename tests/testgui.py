import pygame
import pygame_gui

pygame.init()

# ------------------ Constants ------------------
WINDOW_WIDTH, WINDOW_HEIGHT = 800, 600
ROW_HEIGHT = 48
PAD_Y = 8
ICON_SIZE = (32, 32)
VISIBLE_ROWS = 5  # number of rows visible at a time

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

# ------------------ Setup ------------------
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
clock = pygame.time.Clock()
ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))

# Sample units dict
units = {
    1: {"name": "Scout"},
    2: {"name": "Fighter"},
    3: {"name": "Bomber"},
    4: {"name": "Destroyer"},
    5: {"name": "Cruiser"},
    6: {"name": "Battleship"},
    7: {"name": "Carrier"},
}
units_list = list(units.items())

# Shipyard panel
shipyard_rect = pygame.Rect(50, 50, 300, ROW_HEIGHT * VISIBLE_ROWS + PAD_Y * (VISIBLE_ROWS-1))
shipyard_panel = pygame_gui.elements.UIPanel(
    relative_rect=shipyard_rect,
    starting_height=1,
    manager=ui_manager
)

# Arrow buttons
arrow_width, arrow_height = 30, 30
arrow_x = shipyard_rect.width - arrow_width - 10
arrow_up = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect(arrow_x, 10, arrow_width, arrow_height),
    text="",
    manager=ui_manager,
    container=shipyard_panel
)
arrow_down = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect(arrow_x, shipyard_rect.height - arrow_height - 10, arrow_width, arrow_height),
    text="",
    manager=ui_manager,
    container=shipyard_panel
)

# Set triangle images
arrow_up.set_image(create_triangle_surface((arrow_width, arrow_height), (200,200,200), "up"))
arrow_down.set_image(create_triangle_surface((arrow_width, arrow_height), (200,200,200), "down"))

# Pre-create UI rows
ui_rows = []
_unit_row_map = {}  # map button -> unit_id
start_index = 0

for i in range(VISIBLE_ROWS):
    row_y = i * (ROW_HEIGHT + PAD_Y)
    
    icon_rect = pygame.Rect(10, row_y, ICON_SIZE[0], ICON_SIZE[1])
    ui_icon_image = pygame_gui.elements.UIImage(
        relative_rect=icon_rect,
        image_surface=pygame.Surface(ICON_SIZE),  # placeholder
        manager=ui_manager,
        container=shipyard_panel
    )
    
    btn_rect = pygame.Rect(50, row_y + 8, 200, 24)
    ui_button = pygame_gui.elements.UIButton(
        relative_rect=btn_rect,
        text="",
        manager=ui_manager,
        container=shipyard_panel
    )
    
    ui_rows.append((ui_icon_image, ui_button))
    _unit_row_map[ui_button] = None

# ------------------ Function to refresh visible units ------------------
def show_visible_units():
    for i in range(VISIBLE_ROWS):
        unit_index = start_index + i
        icon, button = ui_rows[i]
        if unit_index < len(units_list):
            unit_id, data = units_list[unit_index]
            button.set_text(data.get("name", "Unknown Unit"))
            _unit_row_map[button] = unit_id
            # Placeholder icon color
            surf = pygame.Surface(ICON_SIZE)
            surf.fill((50 + i*30, 100, 150))
            icon.set_image(surf)
        else:
            button.set_text("")
            _unit_row_map[button] = None
            surf = pygame.Surface(ICON_SIZE)
            surf.fill((0,0,0))
            icon.set_image(surf)

show_visible_units()

# ------------------ Main loop ------------------
running = True
while running:
    time_delta = clock.tick(60) / 1000.0
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == arrow_down:
                    if start_index + VISIBLE_ROWS < len(units_list):
                        start_index += 1
                        show_visible_units()
                elif event.ui_element == arrow_up:
                    if start_index > 0:
                        start_index -= 1
                        show_visible_units()
        
            # Mouse wheel scroll
        elif event.type == pygame.MOUSEWHEEL:
                # Scroll up
                if event.y > 0 and start_index > 0:
                    start_index -= 1
                    show_visible_units()
                # Scroll down
                elif event.y < 0 and start_index + VISIBLE_ROWS < len(units_list):
                    start_index += 1
                    show_visible_units()
        
        ui_manager.process_events(event)
    
    ui_manager.update(time_delta)
    screen.fill((20, 20, 20))
    ui_manager.draw_ui(screen)
    pygame.display.flip()

pygame.quit()
