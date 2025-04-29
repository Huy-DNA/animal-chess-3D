from typing import Dict, List, Optional
from core.map import Position
from core.piece import Color, PieceType, Piece
import pygame
import os
import functools
from pygame.event import Event
from pygame.font import Font
from pygame.surface import Surface
from ui.game_scene import GameScene
from ui.button import Button
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
from core.game import Game
from client.controller.network import ServerConnector


class OnlinePvPMatchScene(GameScene):
    animal_images: Dict[PieceType, Surface]
    background_image: Surface
    inner_background_image: Surface
    trap_image: Surface
    cave_image: Surface
    font: Font
    quit_button: Button

    game: Game
    screen: Surface
    selected_piece: Optional[Piece]
    connector: ServerConnector
    player_color: Color
    opponent_addr: str
    match_id: str
    status_message: str
    game_over: bool = False
    winner: Optional[str] = None

    def __init__(
        self,
        screen: Surface,
        connector: ServerConnector,
        match_id: str,
        opponent_addr: str,
        color: Color,
    ):
        pygame.display.set_caption("Animal Chess - Online Match")
        self.game = Game()
        self.screen = screen
        self.connector = connector
        self.match_id = match_id
        self.opponent_addr = opponent_addr
        self.selected_piece = None
        self.status_message = "Waiting for opponent..."

        self.small_font = pygame.font.SysFont(None, 24)
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

        self.player_color = color

        self.connector.set_move_made_callback(self.on_move_made)
        self.connector.set_game_over_callback(self.on_game_over)
        self.connector.set_error_callback(self.on_error)

        self.animal_images = self.load_animal_images()
        self.background_image = pygame.transform.scale(
            pygame.image.load(
                os.path.join(ASSETS_PATH, "board-image.png")
            ).convert_alpha(),
            (SCREEN_WIDTH, SCREEN_HEIGHT),
        )

        self.inner_background_image = pygame.transform.scale(
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

        self.font = pygame.font.SysFont(None, 36)

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

    def on_move_made(self, piece: Piece, position: Position, player: str):
        if player != str(self.opponent_addr):
            pass
        else:
            self.game.move(piece, position)
            self.status_message = "Your turn"

    def on_game_over(self, winner: str, reason: str):
        self.game_over = True
        self.winner = winner
        if winner == str(self.opponent_addr):
            self.status_message = f"Game over. You lost. Reason: {reason}"
        else:
            self.status_message = f"Game over. You won! Reason: {reason}"

    def on_error(self, message: str):
        self.status_message = f"Error: {message}"

    def draw_board(self):
        self.screen.blit(self.inner_background_image, (0, 0))
        self.screen.blit(self.background_image, (0, 0))

        # Draw buttons
        self.quit_button.draw(self.screen)
        self.menu_button.draw(self.screen)

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

        current_turn = self.game.get_turn()
        turn_text = self.font.render(
            f"{current_turn.to_string().upper()}'s TURN",
            True,
            (255, 0, 0) if current_turn == Color.RED else (0, 0, 255),
        )
        self.screen.blit(turn_text, (20, 20))

        player_text = self.small_font.render(
            f"You are {self.player_color.to_string().upper()}",
            True,
            (255, 0, 0) if self.player_color == Color.RED else (0, 0, 255),
        )
        self.screen.blit(player_text, (20, 60))

        status_text = self.small_font.render(self.status_message, True, (0, 0, 0))
        self.screen.blit(status_text, (20, SCREEN_HEIGHT - 30))

        # Display game over message if applicable
        if self.game_over:
            game_over_text = self.font.render("GAME OVER", True, (255, 0, 0))
            self.screen.blit(
                game_over_text, (SCREEN_WIDTH // 2 - 80, SCREEN_HEIGHT // 2 - 50)
            )

            if self.winner:
                winner_text = self.font.render(
                    f"{'You' if self.winner != str(self.opponent_addr) else 'Opponent'} won!",
                    True,
                    (0, 0, 0),
                )
                self.screen.blit(
                    winner_text, (SCREEN_WIDTH // 2 - 80, SCREEN_HEIGHT // 2)
                )

    def step(self, events: List[Event]) -> GameScene:
        self.connector.Pump()

        # Update buttons with mouse position
        mouse_pos = pygame.mouse.get_pos()
        self.quit_button.update(mouse_pos)
        self.menu_button.update(mouse_pos)

        if self.game.get_turn() != self.player_color and not self.game_over:
            self.status_message = "Opponent's turn"
        elif not self.game_over:
            self.status_message = "Your turn"

        winner = self.game.is_game_over()
        if winner is not None and not self.game_over:
            if winner == self.player_color:
                self.status_message = "You won! Game over."
            else:
                self.status_message = "You lost. Game over."
            self.game_over = True

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Check if any buttons were clicked
                if self.quit_button.is_clicked(mouse_pos):
                    self.connector.Disconnect()
                    pygame.quit()
                    exit()

                elif self.menu_button.is_clicked(mouse_pos):
                    from ui.menu_scene import MenuScene

                    self.connector.Disconnect()
                    return MenuScene(self.screen)

                # Handle game piece selection
                elif self.game.get_turn() == self.player_color and not self.game_over:
                    pos = self.get_board_mouse_pos(*pygame.mouse.get_pos())
                    if pos is not None:
                        piece = self.game.get_state().get_piece_at_position(pos)
                        if piece and piece.color == self.player_color:
                            self.selected_piece = piece

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if (
                    self.selected_piece
                    and self.game.get_turn() == self.player_color
                    and not self.game_over
                ):
                    mx, my = event.pos
                    pos = self.get_board_mouse_pos(mx, my)
                    if pos is not None:
                        # Try to make the move locally first
                        result = self.game.move(self.selected_piece, pos)
                        if result:  # If move was successful locally
                            # Send move to server
                            self.connector.move(self.selected_piece, pos)
                            self.status_message = "Move sent. Waiting for opponent..."
                    self.selected_piece = None

            elif event.type == pygame.KEYDOWN:
                if (
                    event.key == pygame.K_c and not self.game_over
                ):  # Press 'c' to concede
                    self.connector.concede()
                    self.status_message = "You conceded. Game over."
                    self.game_over = True
                elif event.key == pygame.K_ESCAPE:  # Press ESC to return to menu
                    from ui.menu_scene import MenuScene

                    self.connector.Disconnect()
                    return MenuScene(self.screen)

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

        if self.game_over:
            return_text = self.small_font.render(
                "Press ESC to return to menu", True, (0, 0, 0)
            )
            self.screen.blit(
                return_text,
                (SCREEN_WIDTH // 2 - return_text.get_width() // 2, SCREEN_HEIGHT - 60),
            )

        return None
