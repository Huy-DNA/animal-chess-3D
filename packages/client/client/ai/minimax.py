import time
import random
from typing import List, Optional
from core.game import Game
from ai.ai import AI
from ai.move import Move
from core.piece import Color, PieceType
import copy


class MinimaxAI(AI):
    def __init__(self, color: Color, max_depth: int = 3):
        self.color = color
        self.max_depth = max_depth
        self.nodes_evaluated = 0
        self.opponent_color = Color.BLUE if color == Color.RED else Color.RED
        self.piece_values = {
            PieceType.ELEPHANT: 8,
            PieceType.LION: 7,
            PieceType.TIGER: 6,
            PieceType.LEOPARD: 5,
            PieceType.WOLF: 4,
            PieceType.DOG: 3,
            PieceType.CAT: 2,
            PieceType.MOUSE: 1,
        }
        self.den_distance_weight = 3
        self.center_control_weight = 1

    def choose_move(self, game: Game) -> Optional[Move]:
        self.nodes_evaluated = 0
        start_time = time.time()
        all_moves = self._get_all_possible_moves(game, self.color)
        if not all_moves:
            return None

        # Store all moves with their scores
        move_scores = []
        best_score = float("-inf")

        for move in all_moves:
            game_copy = copy.deepcopy(game)
            game_copy.move(move.piece, move.to_pos)
            score = self._minimax(
                game_copy, self.max_depth - 1, False, float("-inf"), float("inf")
            )
            move_scores.append((move, score))
            if score > best_score:
                best_score = score

        best_moves = [move for move, score in move_scores if score == best_score]

        best_move = random.choice(best_moves)

        end_time = time.time()
        print(
            f"Minimax AI evaluated {self.nodes_evaluated} nodes in {end_time - start_time:.2f} seconds"
        )
        print(f"Best move: {best_move} with score: {best_score}")
        print(f"Selected from {len(best_moves)} equally good moves")

        return best_move

    def _minimax(
        self, game: Game, depth: int, is_maximizing: bool, alpha: float, beta: float
    ) -> float:
        self.nodes_evaluated += 1
        winner = game.is_game_over()
        if winner is not None:
            return 1000 if winner == self.color else -1000
        if depth == 0:
            return self._evaluate_board(game)

        if is_maximizing:
            max_eval = float("-inf")
            moves = self._get_all_possible_moves(game, self.color)
            for move in moves:
                game_copy = copy.deepcopy(game)
                game_copy.move(move.piece, move.to_pos)
                eval = self._minimax(game_copy, depth - 1, False, alpha, beta)
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                if beta <= alpha:
                    break
            return max_eval
        else:
            min_eval = float("inf")
            moves = self._get_all_possible_moves(game, self.opponent_color)
            for move in moves:
                game_copy = copy.deepcopy(game)
                game_copy.move(move.piece, move.to_pos)
                eval = self._minimax(game_copy, depth - 1, True, alpha, beta)
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                if beta <= alpha:
                    break
            return min_eval

    def _get_all_possible_moves(self, game: Game, color: Color) -> List[Move]:
        moves = []
        state = game.get_state()
        for piece in state.get_all_pieces():
            if piece.color == color and state.is_alive(piece):
                possible_cells = game.get_possible_moves(piece)
                for cell in possible_cells:
                    moves.append(Move(piece, cell.position))
        return moves

    def _evaluate_board(self, game: Game) -> float:
        state = game.get_state()
        score = 0
        for piece in state.get_all_pieces():
            if not state.is_alive(piece):
                continue
            value = self.piece_values[piece.type] * 10
            if piece.color == self.color:
                score += value
                pos = state.get_piece_position_definitely(piece)
                enemy_den_y = 0 if self.color == Color.BLUE else 8
                distance_to_den = abs(pos.y - enemy_den_y)
                score += (9 - distance_to_den) * self.den_distance_weight
                center_x, center_y = 3, 4
                center_dist = abs(pos.x - center_x) + abs(pos.y - center_y)
                score += (9 - center_dist) * self.center_control_weight
            else:
                score -= value
        return score
