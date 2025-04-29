from typing import Tuple
import pygame
from pygame.font import Font
from pygame.surface import Surface


class Button:
    def __init__(self, x: int, y: int, width: int, height: int, text: str, font: Font):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.is_hovered = False
        self.normal_color = (100, 100, 100)
        self.hover_color = (150, 150, 150)
        self.text_color = (255, 255, 255)
        self.border_radius = 10

    def draw(self, screen: Surface) -> None:
        color = self.hover_color if self.is_hovered else self.normal_color
        pygame.draw.rect(screen, color, self.rect, border_radius=self.border_radius)
        pygame.draw.rect(
            screen, (0, 0, 0), self.rect, 2, border_radius=self.border_radius
        )

        text_surface = self.font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def update(self, mouse_pos: Tuple[int, int]) -> None:
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def is_clicked(self, mouse_pos: Tuple[int, int]) -> bool:
        return self.rect.collidepoint(mouse_pos)
