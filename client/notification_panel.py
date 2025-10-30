import pygame
import pygame_gui

class NotificationPanel:
    def __init__(self, ui_manager, rect):
        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=rect,
            manager=ui_manager,
            visible=False,
            starting_height=5
        )
        self.labels = []

    def update(self, notifications):
        # Clear existing labels
        for label in self.labels:
            label.kill()
        self.labels.clear()

        y_offset = 0
        for note in notifications[-5:]:  # show last 5
            color = (255, 255, 255)
            if note["level"] == "warning":
                color = (255, 200, 100)
            elif note["level"] == "error":
                color = (255, 100, 100)

            label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(0, y_offset, 300, 25),
                text=note["message"],
                container=self.panel,
                manager=self.panel.ui_manager,
                object_id="#notification_label"
            )
            label.text_colour = color
            self.labels.append(label)
            y_offset += 30
