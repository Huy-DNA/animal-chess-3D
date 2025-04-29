import os


ASSETS_PATH = os.path.join(os.path.dirname(__file__), "assets")
CHECKPOINT_PATH = os.path.join(os.path.dirname(__file__), "../ai/checkpoints")

SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 800
TILE_SIZE = 80
BOARD_COLS = 7
BOARD_ROWS = 9

BOARD_WIDTH = BOARD_COLS * TILE_SIZE
BOARD_HEIGHT = BOARD_ROWS * TILE_SIZE
BOARD_X = (SCREEN_WIDTH - BOARD_WIDTH) // 2
BOARD_Y = (SCREEN_HEIGHT - BOARD_HEIGHT) // 2

TURN_TIME_LIMIT = 31000
