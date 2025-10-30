import pygame

class InputHandler:
    def __init__(self, game, camera):
        self.game = game
        self.camera = camera
        self.selected_hextile = None

    def handle_event(self, event):
        """Handle one pygame event."""
        gui = self.game.gui

        #pygame_gui consume the event so we process pygame events first
        # if gui.planet_mgmt_tab_row.container.visible:
        #     gui.dispatch_event_to_active_panel(event)

        # --- 1. Global mouse input ---
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # left click
                if not gui.tile_info_panel.visible:
                    mouse_pos = pygame.mouse.get_pos()
                    for h in self.game.galaxy:
                            if h.contains_point(mouse_pos, origin=(500, 300), pixel_offset=self.camera.offset):
                                self.selected_hextile = h
                                return "show_tile_info_panel"
        
            elif event.button == 3:
                return "close_window"
            
        elif event.type == pygame.MOUSEMOTION and gui.tile_info_panel.visible:
            pos = pygame.mouse.get_pos()
            gui.tile_info_panel.draw_planet_tooltip(pos)


        # --- 2. Global keyboard / quit handling ---
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "quit"
        
        elif event.type == pygame.QUIT:
                return "quit"
        
        # --- 3. UI dispatch (pygame_gui) ---
        

        if gui.tile_info_panel.visible:
            gui.tile_info_panel.handle_events(event)
        if gui.planet_mgmt_panel.panel.visible:
            gui.planet_mgmt_panel.process_event(event, gui.tile_info_panel.selected_planet)
        if gui.planet_mgmt_tab_row.container.visible:
            gui.planet_mgmt_tab_row.process_event(event)
        

    def handle_keys(self):
        """Handle continuous key state (e.g. movement)."""
        keys = pygame.key.get_pressed()
        self.camera.move(keys)
