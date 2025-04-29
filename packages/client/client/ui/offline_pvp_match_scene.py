from typing import Dict, List, Optional
from core.map import Position
from core.piece import Color, PieceType
import pygame
import os
import functools
from pygame.event import Event
from pygame.font import Font
from pygame.surface import Surface
from ui.button import Button
from ui.game_scene import GameScene
from ui.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    TILE_SIZE,
    BOARD_COLS,
    BOARD_ROWS,
    BOARD_X,
    BOARD_Y,
    ASSETS_PATH,
)
from core.game import Game, Piece


class OfflinePvPMatchScene(GameScene):
    animal_images: Dict[PieceType, Surface]
    background_image: Surface
    inner_background_image: Surface
    trap_image: Surface
    cave_image: Surface
    font: Font

    game: Game
    screen: Surface
    selected_piece: Optional[Piece]
    offset_x: int
    offset_y: int
    game_over: bool
    status_message: str

    def __init__(self, screen: Surface):
        pygame.display.set_caption("Animal chess")
        self.game_over = False
        self.game = Game()

        self.screen = screen
        self.selected_piece = None

        self.animal_images = OfflinePvPMatchScene.load_animal_images()
        self.background_image = pygame.transform.scale(
            pygame.image.load(
                os.path.join(ASSETS_PATH, "board-image.png")
            ).convert_alpha(),
            (SCREEN_WIDTH, SCREEN_HEIGHT),
        )

        self.inner_background_image: Surface = pygame.transform.scale(
            pygame.image.load(os.path.join(ASSETS_PATH, "forest-bg.png")).convert(),
            (SCREEN_WIDTH, SCREEN_HEIGHT),
        )

        self.trap_image = pygame.transform.scale(
            pygame.image.load(os.path.join(ASSETS_PATH, "trap-image.png")),
            (TILE_SIZE, TILE_SIZE),
        )

        self.cave_image = pygame.transform.scale(
            pygame.image.load(os.path.join(ASSETS_PATH, "cave-image.png")),
            (TILE_SIZE, TILE_SIZE),
        )

        self.small_font = pygame.font.SysFont(None, 24)
        self.font = pygame.font.SysFont(None, 36)

        self.quit_button = Button(
            SCREEN_WIDTH - 120, 20, 100, 40, "QUIT", self.small_font
        )
        self.quit_button.normal_color = (200, 50, 50)
        self.quit_button.hover_color = (255, 70, 70)

        self.menu_button = Button(
            SCREEN_WIDTH - 230, 20, 100, 40, "MENU", self.small_font
        )
        self.menu_button.normal_color = (70, 70, 200)
        self.menu_button.hover_color = (100, 100, 255)
        self.status_message = ''

    def get_board_mouse_pos(self, mouse_x: float, mouse_y: float) -> Optional[Position]:
        col = (mouse_x - BOARD_X) // TILE_SIZE
        row = (mouse_y - BOARD_Y) // TILE_SIZE
        if 0 <= col < BOARD_COLS and 0 <= row < BOARD_ROWS:
            return Position(col, row)
        return None

    @staticmethod
    @functools.cache
    def load_animal_images():
        images = {}
        name_to_type = {
            "elephant": PieceType.ELEPHANT,
            "lion": PieceType.LION,
            "tiger": PieceType.TIGER,
            "leopard": PieceType.LEOPARD,
            "dog": PieceType.DOG,
            "wolf": PieceType.WOLF,
            "cat": PieceType.CAT,
            "mouse": PieceType.MOUSE,
        }
        for name in os.listdir(ASSETS_PATH):
            if name.endswith(".png") and name not in [
                "trap-image.png",
                "board-image.png",
                "forest-bg.png",
                "board-bg.png",
                "cave-image.png",
                "river-image.png",
            ]:
                img = pygame.image.load(os.path.join(ASSETS_PATH, name)).convert_alpha()
                img = pygame.transform.smoothscale(img, (TILE_SIZE, TILE_SIZE))
                key = name_to_type[name.replace("-image.png", "")]
                images[key] = img
        return images

    @functools.cache
    def rivers(self) -> List[Position]:
        state = self.game.get_state()
        map = state.get_map()

        river_positions = []
        for y in range(map.height()):
            for x in range(map.width()):
                location = map[y, x]
                if location and location.is_river:
                    river_positions.append(Position(x, y))

        return river_positions

    @functools.cache
    def caves(self) -> List[Position]:
        state = self.game.get_state()
        map = state.get_map()

        cave_positions = []
        for y in range(map.height()):
            for x in range(map.width()):
                location = map[y, x]
                if location and location.cave_color is not None:
                    cave_positions.append(Position(x, y))

        return cave_positions

    @functools.cache
    def traps(self) -> List[Position]:
        state = self.game.get_state()
        map = state.get_map()

        trap_positions = []
        for y in range(map.height()):
            for x in range(map.width()):
                location = map[y, x]
                if location and location.trap_color is not None:
                    trap_positions.append(Position(x, y))

        return trap_positions

    def draw_board(self):
        self.screen.blit(self.inner_background_image, (0, 0))
        self.screen.blit(self.background_image, (0, 0))

        for row in range(BOARD_ROWS):
            for col in range(BOARD_COLS):
                rect = pygame.Rect(
                    BOARD_X + col * TILE_SIZE,
                    BOARD_Y + row * TILE_SIZE,
                    TILE_SIZE,
                    TILE_SIZE,
                )
                tile_pos = Position(col, row)

                if tile_pos in self.rivers():
                    pygame.draw.rect(self.screen, (0, 150, 255), rect)
                elif tile_pos in self.traps():
                    pygame.draw.rect(self.screen, (255, 230, 200), rect)
                else:
                    pygame.draw.rect(self.screen, (245, 222, 179), rect)

                if tile_pos not in self.rivers():
                    pygame.draw.rect(self.screen, (0, 0, 0), rect, 1)

                if tile_pos in self.caves():
                    self.screen.blit(self.cave_image, rect.topleft)

                if tile_pos in self.traps():
                    self.screen.blit(self.trap_image, rect.topleft)

                piece = self.game.get_state().get_piece_at_position(tile_pos)
                if piece and piece != self.selected_piece:
                    img = self.animal_images[piece.type]
                    center = (rect.centerx, rect.centery)
                    pygame.draw.circle(
                        self.screen, (255, 255, 255), center, TILE_SIZE // 2 - 4
                    )

                    img_rect = img.get_rect(center=center)
                    self.screen.blit(img, img_rect.topleft)

                    team_color = (
                        (255, 0, 0) if piece.color == Color.RED else (0, 0, 255)
                    )
                    pygame.draw.circle(
                        self.screen, team_color, center, TILE_SIZE // 2 - 4, 4
                    )

        turn_text = self.font.render(
            f"{self.game.get_turn().to_string().upper()}'s TURN",
            True,
            (255, 0, 0) if self.game.get_turn() == Color.RED else (0, 0, 255),
        )
        self.screen.blit(turn_text, (20, 20))

        self.quit_button.draw(self.screen)
        self.menu_button.draw(self.screen)

        status_text = self.small_font.render(self.status_message, True, (0, 0, 0))
        self.screen.blit(status_text, (20, SCREEN_HEIGHT - 30))

    def step(self, events: List[Event]) -> GameScene:
        mouse_pos = pygame.mouse.get_pos()
        self.quit_button.update(mouse_pos)
        self.menu_button.update(mouse_pos)

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.quit_button.is_clicked(mouse_pos):
                    pygame.quit()
                    exit()

                elif self.menu_button.is_clicked(mouse_pos):
                    from ui.menu_scene import MenuScene

                    return MenuScene(self.screen)

            if not self.game_over and event.type == pygame.MOUSEBUTTONDOWN:
                pos = self.get_board_mouse_pos(*pygame.mouse.get_pos())
                if pos is not None:
                    piece = self.game.get_state().get_piece_at_position(pos)
                    if piece and piece.color == self.game.get_turn():
                        self.selected_piece = piece

            elif not self.game_over and event.type == pygame.MOUSEBUTTONUP:
                if self.selected_piece:
                    mx, my = event.pos
                    pos = self.get_board_mouse_pos(mx, my)
                    if pos is not None:
                        self.game.move(self.selected_piece, pos)
                self.selected_piece = None

        winner = self.game.is_game_over()
        if winner is not None:
            self.status_message = f"{winner.to_string()} won! Game over."
            self.game_over = True
        self.draw_board()

        if self.selected_piece:
            mx, my = pygame.mouse.get_pos()
            img = self.animal_images[self.selected_piece.type]
            pygame.draw.circle(
                self.screen, (255, 255, 255), (mx, my), TILE_SIZE // 2 - 4
            )
            img_rect = img.get_rect(center=(mx, my))
            self.screen.blit(img, img_rect.topleft)

            team_color = (
                (255, 0, 0) if self.selected_piece.color == Color.RED else (0, 0, 255)
            )
            pygame.draw.circle(self.screen, team_color, (mx, my), TILE_SIZE // 2 - 4, 4)

        return None
