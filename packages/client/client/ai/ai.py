from abc import ABC, abstractmethod
from core.game import Game
from ai.move import Move


class AI(ABC):
    @abstractmethod
    def choose_move(self, game: Game) -> Move:
        pass

    def play_with_ai(self, game: Game):
        move = self.choose_move(game)
        print(move)
        if move:
            game.move(move.piece, move.to_pos)
            return True
        return False
