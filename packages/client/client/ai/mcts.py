import time
import random
import math
import copy
import pickle
import os
from typing import List, Optional

from core.game import Game
from ai.ai import AI
from ai.move import Move
from core.piece import Color


class MCTSNode:
    def __init__(self, game, parent=None, move=None, player_color=None):
        self.game = copy.deepcopy(game)
        self.parent = parent
        self.move = move
        self.player_color = player_color
        self.children = []
        self.visits = 0
        self.wins = 0
        self.untried_moves = None

    def __getstate__(self):
        """Custom state for pickle that excludes parent to avoid recursion issues"""
        state = self.__dict__.copy()
        state["parent"] = None
        return state

    def get_untried_moves(self, ai):
        if self.untried_moves is None:
            next_color = self.player_color
            self.untried_moves = ai._get_all_possible_moves(self.game, next_color)
        return self.untried_moves

    def add_child(self, move, next_color):
        game_copy = copy.deepcopy(self.game)

        game_copy.move(move.piece, move.to_pos)

        child = MCTSNode(game_copy, parent=self, move=move, player_color=next_color)
        self.children.append(child)
        return child

    def select_child(self):
        c = 1.41

        return max(
            self.children,
            key=lambda child: (child.wins / child.visits)
            + c * math.sqrt(2 * math.log(self.visits) / child.visits),
        )

    def update(self, result):
        self.visits += 1
        self.wins += result


class MCTSAI(AI):
    def __init__(
        self,
        color: Color,
        num_simulations=1000,
        simulation_depth=50,
        exploration_constant=1.41,
        checkpoint_path: Optional[str] = None,
    ):
        self.color = color
        self.num_simulations = num_simulations
        self.simulation_depth = simulation_depth
        self.exploration_constant = exploration_constant
        self.opponent_color = Color.BLUE if color == Color.RED else Color.RED
        self.tree_root = None

        if checkpoint_path and os.path.exists(checkpoint_path):
            self.load_checkpoint(checkpoint_path)

    def choose_move(self, game: Game) -> Optional[Move]:
        start_time = time.time()

        if self.tree_root is None or not self._is_state_compatible(
            self.tree_root.game, game
        ):
            root = MCTSNode(game, player_color=self.color)
            self.tree_root = root
        else:
            print("Reusing existing MCTS tree")
            root = self.tree_root

        for _ in range(self.num_simulations):
            node = root

            # Selection phase
            while node.children and not node.get_untried_moves(self):
                node = node.select_child()

            # Expansion phase
            if node.get_untried_moves(self):
                next_color = (
                    self.opponent_color
                    if node.player_color == self.color
                    else self.color
                )

                move = random.choice(node.get_untried_moves(self))
                node.untried_moves.remove(move)

                node = node.add_child(move, next_color)

            # Simulation phase
            result = self._simulate(node)

            # Backpropagation phase
            while node:
                node.update(result)
                node = node.parent
                result = 1 - result

        if not root.children:
            return None

        best_child = max(root.children, key=lambda c: c.visits)

        # Update the root to the chosen child for future use
        self.tree_root = best_child
        # Detach from parent to avoid memory issues
        self.tree_root.parent = None

        end_time = time.time()
        print(
            f"MCTS ran {self.num_simulations} simulations in {end_time - start_time:.2f} seconds"
        )
        print(
            f"Best move: {best_child.move} with {best_child.visits} visits and win rate {best_child.wins / best_child.visits:.2f}"
        )

        return best_child.move

    def _is_state_compatible(self, saved_game, current_game):
        """Check if the saved game state matches the current game state"""
        try:
            saved_state = saved_game.get_state()
            current_state = current_game.get_state()

            return saved_state == current_state
        except:
            return False

    def _get_all_possible_moves(self, game, color: Color) -> List[Move]:
        moves = []
        state = game.get_state()

        for piece in state.get_all_pieces():
            if piece.color == color and state.is_alive(piece):
                possible_cells = game.get_possible_moves(piece)
                for cell in possible_cells:
                    moves.append(Move(piece, cell.position))

        return moves

    def _simulate(self, node):
        sim_game = copy.deepcopy(node.game)
        current_color = node.player_color

        for _ in range(self.simulation_depth):
            winner = sim_game.is_game_over()
            if winner is not None:
                break

            moves = self._get_all_possible_moves(sim_game, current_color)
            if not moves:
                break

            move = random.choice(moves)
            sim_game.move(move.piece, move.to_pos)

            current_color = (
                self.opponent_color if current_color == self.color else self.color
            )

        winner = sim_game.is_game_over()
        if winner == self.color:
            return 1.0
        elif winner == self.opponent_color:
            return 0.0
        else:
            state = sim_game.get_state()

            our_pieces = sum(
                1
                for piece in state.get_all_pieces()
                if piece.color == self.color and state.is_alive(piece)
            )
            opponent_pieces = sum(
                1
                for piece in state.get_all_pieces()
                if piece.color == self.opponent_color and state.is_alive(piece)
            )

            total_pieces = our_pieces + opponent_pieces
            if total_pieces == 0:
                return 0.5
            return our_pieces / total_pieces

    def save_checkpoint(self, path: str) -> None:
        checkpoint_data = {
            "color": self.color,
            "num_simulations": self.num_simulations,
            "simulation_depth": self.simulation_depth,
            "exploration_constant": self.exploration_constant,
            "tree_root": self.tree_root,
        }

        try:
            with open(path, "wb") as f:
                pickle.dump(checkpoint_data, f)
            print(f"MCTSAI checkpoint with tree state saved to {path}")
        except Exception as e:
            print(f"Error saving checkpoint: {e}")
            self._save_basic_checkpoint(path)

    def _save_basic_checkpoint(self, path: str) -> None:
        """Fallback function to save just the parameters if tree saving fails"""
        checkpoint_data = {
            "color": self.color,
            "num_simulations": self.num_simulations,
            "simulation_depth": self.simulation_depth,
            "exploration_constant": self.exploration_constant,
        }

        with open(path, "wb") as f:
            pickle.dump(checkpoint_data, f)
        print(f"MCTSAI basic checkpoint (without tree) saved to {path}")

    def load_checkpoint(self, path: str) -> None:
        try:
            with open(path, "rb") as f:
                checkpoint_data = pickle.load(f)

            self.color = checkpoint_data.get("color", self.color)
            self.num_simulations = checkpoint_data.get(
                "num_simulations", self.num_simulations
            )
            self.simulation_depth = checkpoint_data.get(
                "simulation_depth", self.simulation_depth
            )
            self.exploration_constant = checkpoint_data.get(
                "exploration_constant", self.exploration_constant
            )

            if "tree_root" in checkpoint_data:
                self.tree_root = checkpoint_data["tree_root"]
                print("MCTS tree structure loaded from checkpoint")

            self.opponent_color = Color.BLUE if self.color == Color.RED else Color.RED

            print(f"MCTSAI checkpoint loaded from {path}")
        except Exception as e:
            print(f"Error loading checkpoint: {e}")
            self.tree_root = None
