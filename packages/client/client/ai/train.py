from core.game import Game
from core.map import Color
from ai.mcts import MCTSAI
from ai.minimax import MinimaxAI


def self_play_training(
    num_games=150,
    max_moves=300,
    mcts_checkpoint=None,
    save_checkpoints=True,
):
    minimax_ai = MinimaxAI(Color.RED, max_depth=3)
    mcts_ai = MCTSAI(Color.BLUE, num_simulations=500, checkpoint_path=mcts_checkpoint)

    results = {"RED": 0, "BLUE": 0, "DRAW": 0}

    for game_num in range(num_games):
        print(f"Starting game {game_num + 1}/{num_games}")
        game = Game()
        current_color = Color.RED

        for move_num in range(max_moves):
            winner = game.is_game_over()
            if winner is not None:
                results[winner.name] += 1
                print(f"Game {game_num + 1}: {winner.name} wins in {move_num} moves")
                break

            if current_color == Color.RED:
                move = minimax_ai.choose_move(game)
            else:
                move = mcts_ai.choose_move(game)

            if move is None:
                results["DRAW"] += 1
                print(
                    f"Game {game_num + 1}: Draw (no valid moves) after {move_num} moves"
                )
                break

            game.move(move.piece, move.to_pos)

            current_color = Color.BLUE if current_color == Color.RED else Color.RED

        else:
            results["DRAW"] += 1
            print(
                f"Game {game_num + 1}: Draw (move limit reached) after {max_moves} moves"
            )

    print("\nTraining Results:")
    print(f"Games played: {num_games}")
    print(
        f"RED (Minimax) wins: {results['RED']} ({results['RED'] / num_games * 100:.1f}%)"
    )
    print(
        f"BLUE (MCTS) wins: {results['BLUE']} ({results['BLUE'] / num_games * 100:.1f}%)"
    )
    print(f"Draws: {results['DRAW']} ({results['DRAW'] / num_games * 100:.1f}%)")

    if save_checkpoints:
        mcts_ai.save_checkpoint("mcts_latest.pkl")

    return results


if __name__ == "__main__":
    self_play_training()
