import os
from typing import List, Optional
from dotenv import load_dotenv
from pygame import Surface
import pygame
from pygame.event import Event
from ui.button import Button
from ui.difficulty_menu_scene import DifficultyMenuScene
from ui.offline_pvp_match_scene import OfflinePvPMatchScene
from ui.game_scene import GameScene
from ui.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
)
from ui.matchmaking_scene import MatchmakingScene
from controller.network import ServerConnector


load_dotenv()


class MenuScene(GameScene):
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
            "Computer vs Player",
            "Player vs Player",
            "Online",
            "Quit",
        ]
        self.buttons = []
        for i, text in enumerate(buttons_info):
            x = SCREEN_WIDTH // 2 - button_width // 2
            y = start_y + i * (button_height + button_spacing)
            self.buttons.append(
                Button(x, y, button_width, button_height, text, self.button_font)
            )

    def step(self, events: List[Event]) -> Optional[GameScene]:
        mouse_pos = pygame.mouse.get_pos()
        for button in self.buttons:
            button.update(mouse_pos)
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, button in enumerate(self.buttons):
                    if button.is_clicked(mouse_pos):
                        if i == 0:
                            return DifficultyMenuScene(self.screen)
                        elif i == 1:
                            return OfflinePvPMatchScene(self.screen)
                        elif i == 2:
                            ip = os.getenv("SERVER_ADDRESS") or "0.0.0.0"
                            port = int(os.getenv("SERVER_PORT") or "8686")
                            connector = ServerConnector(ip=ip, port=port)
                            connector.Connect()
                            return MatchmakingScene(self.screen, connector)
                        elif i == 3:
                            pygame.quit()
                            exit()
        self.draw()
        return None

    def draw(self) -> None:
        self.screen.blit(self.background, (0, 0))
        title_text = self.title_font.render("Animal Chess", True, (255, 255, 255))
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, 150))
        self.screen.blit(title_text, title_rect)
        for button in self.buttons:
            button.draw(self.screen)
