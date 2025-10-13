import pygame

class Camera:
    def __init__(self, screen_width, screen_height, world_width, world_height, speed=10):
        self.offset = [0, 0]  # camera offset (x, y)
        self.speed = speed

        self.screen_width = screen_width
        self.screen_height = screen_height
        self.world_width = world_width
        self.world_height = world_height

    def move(self, keys):
        if keys[pygame.K_w]:
            self.offset[1] += self.speed
            return True
        if keys[pygame.K_s]:
            self.offset[1] -= self.speed
            return True
        if keys[pygame.K_a]:
            self.offset[0] += self.speed
            return True
        if keys[pygame.K_d]:
            self.offset[0] -= self.speed
            return True

        self.clamp()

    def clamp(self):
        # Prevent camera from moving beyond world boundaries
        #self.offset[0] = min(0, max(self.offset[0], self.screen_width - self.world_width))
        #self.offset[1] = min(0, max(self.offset[1], self.screen_height - self.world_height))
        pass

        # max_x_offset = 0
        # min_x_offset = self.screen_width - self.world_width

        # max_y_offset = 0
        # min_y_offset = self.screen_height - self.world_height

        # self.offset[0] = max(min(self.offset[0], max_x_offset), min_x_offset)
        # self.offset[1] = max(min(self.offset[1], max_y_offset), min_y_offset)

    def apply(self, pos):
        """Apply camera offset to a position (e.g., for drawing)"""
        return (pos[0] + self.offset[0], pos[1] + self.offset[1])

    def apply_rect(self, rect):
        """Apply offset to a Rect (if you're using pygame.Rects)"""
        return rect.move(self.offset)
    
    def get_offset(self):
        return self.offset[0], self.offset[1]