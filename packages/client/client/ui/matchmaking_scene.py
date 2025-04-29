from typing import List, Optional
from core.piece import Color
import pygame
from pygame.event import Event
from pygame.font import Font
from pygame.surface import Surface
from ui.game_scene import GameScene
from ui.button import Button
from ui.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
)
from controller.network import ServerConnector
from time import time

from ui.online_pvp_match_scene import OnlinePvPMatchScene


class MatchmakingScene(GameScene):
    screen: Surface
    connector: ServerConnector
    font: Font
    small_font: Font
    state: str  # 'connecting', 'searching', 'match_found', 'waiting_for_ready', 'ready'
    message: str
    match_id: Optional[str]
    opponent: Optional[str]
    opponent_ready: bool
    start_time: float
    quit_button: Button
    menu_button: Button

    def __init__(self, screen: Surface, connector: ServerConnector):
        pygame.display.set_caption("Animal Chess - Matchmaking")
        self.screen = screen
        self.connector = connector
        self.font = pygame.font.SysFont(None, 48)
        self.small_font = pygame.font.SysFont(None, 24)
        self.state = "connecting"
        self.message = "Connecting to server..."
        self.match_id = None
        self.opponent = None
        self.opponent_ready = False
        self.start_time = time()

        # Create the quit button
        self.quit_button = Button(
            SCREEN_WIDTH - 120, 20, 100, 40, "QUIT", self.small_font
        )
        self.quit_button.normal_color = (200, 50, 50)
        self.quit_button.hover_color = (255, 70, 70)

        # Create the menu button
        self.menu_button = Button(
            SCREEN_WIDTH - 230, 20, 100, 40, "MENU", self.small_font
        )
        self.menu_button.normal_color = (70, 70, 200)
        self.menu_button.hover_color = (100, 100, 255)

        self.connector.set_connected_callback(self.on_connected)
        self.connector.set_error_callback(self.on_error)
        self.connector.set_queued_callback(self.on_queued)
        self.connector.set_queue_cancelled_callback(self.on_queue_cancelled)
        self.connector.set_match_found_callback(self.on_match_found)
        self.connector.set_ready_confirmed_callback(self.on_ready_confirmed)
        self.connector.set_opponent_ready_callback(self.on_opponent_ready)
        self.connector.set_match_started_callback(self.on_match_started)
        self.connector.set_match_cancelled_callback(self.on_match_cancelled)

        self.next_scene = None

    def on_connected(self, message: str):
        self.state = "idle"
        self.message = "Connected! Press SPACE to search for a match."

    def on_error(self, message: str):
        self.message = f"Error: {message}"

    def on_queued(self, message: str):
        self.state = "searching"
        self.message = message
        self.start_time = time()

    def on_queue_cancelled(self, message: str):
        self.state = "idle"
        self.message = message

    def on_match_found(self, match_id: str, opponent: str):
        self.state = "match_found"
        self.match_id = match_id
        self.opponent = opponent
        self.message = f"Match found! Opponent: {opponent}. Press SPACE to ready up."

    def on_ready_confirmed(self, match_id: str):
        self.state = "ready"
        self.message = "Ready! Waiting for opponent..."

    def on_opponent_ready(self, match_id: str):
        self.opponent_ready = True
        if self.state == "match_found":
            self.message = f"Opponent is ready! Press SPACE to ready up."
        elif self.state == "ready":
            self.message = "Both players ready. Starting game..."

    def on_match_started(self, match_id: str, color: Color):
        self.message = "Match starting..."
        self.next_scene = OnlinePvPMatchScene(
            self.screen, self.connector, match_id, self.opponent, color,
        )

    def on_match_cancelled(self, match_id: str, reason: str):
        self.state = "idle"
        self.match_id = None
        self.opponent = None
        self.opponent_ready = False
        self.message = f"Match cancelled: {reason}. Press SPACE to search again."

    def draw(self):
        self.screen.fill((240, 240, 240))

        # Draw buttons
        self.quit_button.draw(self.screen)
        self.menu_button.draw(self.screen)

        text = self.font.render("Animal Chess Matchmaking", True, (0, 0, 0))
        self.screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 100))

        text = self.small_font.render(self.message, True, (0, 0, 0))
        self.screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 180))

        if self.state == "searching":
            elapsed = int(time() - self.start_time)
            time_text = self.small_font.render(
                f"Searching for {elapsed}s... (Press ESC to cancel)",
                True,
                (100, 100, 100),
            )
            self.screen.blit(
                time_text, (SCREEN_WIDTH // 2 - time_text.get_width() // 2, 220)
            )

        if self.state in ["match_found", "ready"]:
            match_text = self.small_font.render(
                f"Match ID: {self.match_id}", True, (100, 100, 100)
            )
            self.screen.blit(
                match_text, (SCREEN_WIDTH // 2 - match_text.get_width() // 2, 220)
            )

            ready_status = "You: "
            ready_status += "Ready ✓" if self.state == "ready" else "Not Ready ✗"
            ready_status += " | Opponent: "
            ready_status += "Ready ✓" if self.opponent_ready else "Not Ready ✗"

            status_text = self.small_font.render(ready_status, True, (100, 100, 100))
            self.screen.blit(
                status_text, (SCREEN_WIDTH // 2 - status_text.get_width() // 2, 250)
            )

        if self.state == "idle":
            help_text = self.small_font.render(
                "Press SPACE to find a match", True, (100, 100, 100)
            )
            self.screen.blit(
                help_text,
                (SCREEN_WIDTH // 2 - help_text.get_width() // 2, SCREEN_HEIGHT - 100),
            )
        elif self.state == "searching":
            help_text = self.small_font.render(
                "Press ESC to cancel search", True, (100, 100, 100)
            )
            self.screen.blit(
                help_text,
                (SCREEN_WIDTH // 2 - help_text.get_width() // 2, SCREEN_HEIGHT - 100),
            )
        elif self.state == "match_found":
            help_text = self.small_font.render(
                "Press SPACE to ready up or ESC to cancel", True, (100, 100, 100)
            )
            self.screen.blit(
                help_text,
                (SCREEN_WIDTH // 2 - help_text.get_width() // 2, SCREEN_HEIGHT - 100),
            )
        elif self.state == "ready":
            help_text = self.small_font.render(
                "Press ESC to cancel", True, (100, 100, 100)
            )
            self.screen.blit(
                help_text,
                (SCREEN_WIDTH // 2 - help_text.get_width() // 2, SCREEN_HEIGHT - 100),
            )

    def step(self, events: List[Event]) -> GameScene:
        self.connector.Pump()

        mouse_pos = pygame.mouse.get_pos()
        self.quit_button.update(mouse_pos)
        self.menu_button.update(mouse_pos)

        if self.next_scene:
            return self.next_scene

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.quit_button.is_clicked(mouse_pos):
                    self.connector.Disconnect()
                    pygame.quit()
                    exit()

                elif self.menu_button.is_clicked(mouse_pos):
                    from ui.menu_scene import MenuScene

                    self.connector.Disconnect()
                    return MenuScene(self.screen)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if self.state == "idle":
                        self.connector.find_game()
                    elif self.state == "match_found":
                        self.connector.start_game(self.match_id)

                elif event.key == pygame.K_ESCAPE:
                    if self.state == "searching":
                        self.connector.cancel_find_game()
                    elif self.state in ["match_found", "ready"]:
                        self.connector.cancel_start_game(self.match_id)
                    else:
                        from ui.menu_scene import MenuScene

                        self.connector.Disconnect()
                        return MenuScene(self.screen)

        self.draw()
        return None
