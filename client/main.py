import asyncio
import pygame
from client.network import NetworkClient
from client.gui import GameGUI
from client.game import Game
from client.input import InputHandler

async def main_async():
    network = NetworkClient(server_ip="192.168.0.40", server_port=5000)
    await network.connect()
        

    game = Game(galaxy=network.client_galaxy, network=network, online=True)
    #For offline : game = Game(galaxy=local_galaxy, online=False)
    gui = GameGUI(game)
    #load planet gif
    for hex in game.galaxy:
        if hex.feature == "star_system":
            for planet in hex.contents.planets:
                if planet.rotation_gif_path is not None :
                    planet.animation = gui.assets.load_gif_as_frames(
                        key = f"planet_anim_{planet.planet_type_id}_{planet.global_id}",
                        path = planet.rotation_gif_path,
                        size=(64,64),
                        frame_duration=0.167 #0.08
                    )
    game.gui = gui
    input_handler = InputHandler(game, gui.camera)

    clock = pygame.time.Clock()

    while gui.running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            gui.ui_manager.process_events(event)
            action = input_handler.handle_event(event)
            if action == "quit":
                gui.running = False
            elif action == "show_tile_info_panel":
                gui.tile_info_panel.show_info(input_handler.selected_hextile)
            elif action == "close_window":
                gui.close_window()
            

        input_handler.handle_keys()
        game.update(dt)
        gui.ui_manager.update(dt)
        gui.render(dt)

        await asyncio.sleep(0)

if __name__ == "__main__":
    asyncio.run(main_async())