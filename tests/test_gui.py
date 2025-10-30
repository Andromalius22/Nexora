import pygame

pygame.init()
screen = pygame.display.set_mode((200, 200))
pygame.display.set_caption("Test Window")

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

pygame.quit()
print("Pygame window closed!")
