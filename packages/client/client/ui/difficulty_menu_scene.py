from typing import List
from pygame import Surface
import pygame
from pygame.event import Event
from ui.offline_cvp_match_scene import DifficultyMode, OfflineCvPMatchScene
from ui.button import Button
import ui.menu_scene
from ui.game_scene import GameScene
from ui.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
)


class DifficultyMenuScene(GameScene):
    def __init__(self, screen: Surface):
        self.screen = screen

        self.background = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.background.fill((50, 100, 50))

        self.title_font = pygame.font.SysFont("Arial", 64, bold=True)
        self.button_font = pygame.font.SysFont("Arial", 36)

        button_width = 400
        button_height = 60
        button_spacing = 20
        start_y = SCREEN_HEIGHT // 2 - 100

        buttons_info = [
            "Easy",
            "Medium",
            "Hard",
            "Back",
        ]

        self.buttons = []
        for i, text in enumerate(buttons_info):
            x = SCREEN_WIDTH // 2 - button_width // 2
            y = start_y + i * (button_height + button_spacing)
            self.buttons.append(
                Button(x, y, button_width, button_height, text, self.button_font)
            )

    def step(self, events: List[Event]) -> GameScene:
        mouse_pos = pygame.mouse.get_pos()

        for button in self.buttons:
            button.update(mouse_pos)

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, button in enumerate(self.buttons):
                    if button.is_clicked(mouse_pos):
                        if i == 0:
                            return OfflineCvPMatchScene(
                                DifficultyMode.EASY, self.screen
                            )
                        elif i == 1:
                            return OfflineCvPMatchScene(
                                DifficultyMode.MEDIUM, self.screen
                            )
                        elif i == 2:
                            return OfflineCvPMatchScene(
                                DifficultyMode.HARD, self.screen
                            )
                        elif i == 3:
                            return ui.menu_scene.MenuScene(self.screen)

        self.draw()

        return None

    def draw(self) -> None:
        self.screen.blit(self.background, (0, 0))

        title_text = self.title_font.render("Difficulty", True, (255, 255, 255))
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, 150))
        self.screen.blit(title_text, title_rect)

        for button in self.buttons:
            button.draw(self.screen)
