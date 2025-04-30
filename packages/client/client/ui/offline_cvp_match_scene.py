from enum import Enum
import sys
from core.map import Position
from core.piece import Color, PieceType
import os
import functools

from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectButton import DirectButton
from direct.gui.OnscreenText import OnscreenText
from direct.task import Task
from panda3d.core import TextNode, TransparencyAttrib, Point3, CardMaker
from panda3d.core import PNMImage, Texture, NodePath
from panda3d.core import (
    CollisionTraverser,
    CollisionHandlerQueue,
    CollisionRay,
    CollisionNode,
)

from ai.mcts import MCTSAI
from ai import mcts
from ai.minimax import MinimaxAI
from ui.game_scene import GameScene
from ui.constants import (
    BOARD_COLS,
    BOARD_ROWS,
    CHECKPOINT_PATH,
    ASSETS_PATH,
)
from core.game import Game, Piece

sys.modules["mcts"] = mcts


class DifficultyMode(Enum):
    EASY = 0
    MEDIUM = 1
    HARD = 2


class OfflineCvPMatchScene(GameScene):
    def __init__(self, mode: DifficultyMode, base: ShowBase):
        super().__init__(base)

        self.game_over = False
        self.game = Game()

        self.selected_piece = None
        self.piece_nodes = {}
        self.tile_nodes = {}

        self.status_message = ""

        if mode == DifficultyMode.EASY:
            self.ai = MinimaxAI(Color.BLUE, 2)
        elif mode == DifficultyMode.MEDIUM:
            self.ai = MinimaxAI(Color.BLUE, 3)
        else:
            self.ai = MCTSAI(
                Color.BLUE,
                num_simulations=1000,
                simulation_depth=50,
                exploration_constant=1.41,
                checkpoint_path=os.path.join(CHECKPOINT_PATH, "mcts.pkl"),
            )

        self.textures = {}
        self.dragging = False
        self.drag_piece_node = None

        # Initialize collision detection
        self.app.cTrav = CollisionTraverser()
        self.app.pq = CollisionHandlerQueue()
        self.app.pickerRay = CollisionRay()
        self.picker_node = CollisionNode("mouseRay")
        self.picker_node.addSolid(self.app.pickerRay)
        self.picker_np = self.app.camera.attachNewNode(self.picker_node)
        self.app.cTrav.addCollider(self.picker_np, self.app.pq)

    def setup(self):
        self.app.setBackgroundColor(0.5, 0.8, 1.0)

        self.app.disableMouse()
        self.app.camera.setPos(BOARD_COLS / 2, -10, BOARD_ROWS / 2 + 2)
        self.app.camera.lookAt(BOARD_COLS / 2, 0, BOARD_ROWS / 2)

        self.board_root = self.app.render.attachNewNode("board_root")

        self.load_textures()

        self.create_board()

        self.create_ui()

        self.setup_mouse_picking()

        self.app.taskMgr.add(self.step, "GameStepTask")

    def load_textures(self):
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
                texture = self.app.loader.loadTexture(os.path.join(ASSETS_PATH, name))
                key = name_to_type[name.replace("-image.png", "")]
                self.textures[key] = texture

        self.textures["trap"] = self.app.loader.loadTexture(
            os.path.join(ASSETS_PATH, "trap-image.png")
        )
        self.textures["cave"] = self.app.loader.loadTexture(
            os.path.join(ASSETS_PATH, "cave-image.png")
        )
        self.textures["river"] = (
            self.app.loader.loadTexture(os.path.join(ASSETS_PATH, "river-image.png"))
            if os.path.exists(os.path.join(ASSETS_PATH, "river-image.png"))
            else None
        )
        self.textures["normal_tile"] = self.create_color_texture(0.96, 0.87, 0.7)
        self.textures["river_tile"] = self.create_color_texture(0, 0.59, 1.0)

    def create_color_texture(self, r, g, b):
        image = PNMImage(2, 2)
        image.fill(r, g, b)
        texture = Texture()
        texture.load(image)
        return texture

    def create_board(self):
        state = self.game.get_state()
        game_map = state.get_map()

        for row in range(BOARD_ROWS):
            for col in range(BOARD_COLS):
                tile_pos = Position(col, row)

                cm = CardMaker(f"tile_{col}_{row}")
                cm.setFrame(0, 1, 0, 1)
                tile_node = self.board_root.attachNewNode(cm.generate())
                tile_node.setPos(col, 0, row)
                tile_node.setP(-90)

                # Add collision solid for mouse picking
                cn = CollisionNode(f"tile_collision_{col}_{row}")
                cm.setFrame(0, 1, 0, 1)
                cn_np = tile_node.attachNewNode(cn)

                self.tile_nodes[tile_pos] = tile_node

                if self.is_river(tile_pos):
                    tile_node.setTexture(self.textures["river_tile"])
                else:
                    tile_node.setTexture(self.textures["normal_tile"])

                if self.is_trap(tile_pos):
                    trap_overlay = self.board_root.attachNewNode(cm.generate())
                    trap_overlay.setPos(col, 0.01, row)
                    trap_overlay.setP(-90)
                    trap_overlay.setTexture(self.textures["trap"])
                    trap_overlay.setTransparency(TransparencyAttrib.MAlpha)

                if self.is_cave(tile_pos):
                    cave_overlay = self.board_root.attachNewNode(cm.generate())
                    cave_overlay.setPos(col, 0.01, row)
                    cave_overlay.setP(-90)
                    cave_overlay.setTexture(self.textures["cave"])
                    cave_overlay.setTransparency(TransparencyAttrib.MAlpha)

        for y in range(game_map.height()):
            for x in range(game_map.width()):
                piece = state.get_piece_at_position(Position(x, y))
                if piece:
                    self.create_piece_node(piece)

    def create_piece_node(self, piece: Piece):
        cm = CardMaker(f"piece_{piece}")
        cm.setFrame(-0.45, 0.45, -0.45, 0.45)

        piece_node = self.board_root.attachNewNode(cm.generate())
        piece_node.setPos(piece.position.x, 0.1, piece.position.y)
        piece_node.setP(-90)

        # Add collision for piece
        cn = CollisionNode(f"piece_collision_{piece}")
        cm.setFrame(-0.45, 0.45, -0.45, 0.45)
        cn_np = piece_node.attachNewNode(cn)

        piece_node.setTexture(self.textures[piece.type])
        piece_node.setTransparency(TransparencyAttrib.MAlpha)

        border_color = (1, 0, 0, 1) if piece.color == Color.RED else (0, 0, 1, 1)
        self.create_piece_border(piece_node, border_color)

        self.piece_nodes[piece] = piece_node

    def create_piece_border(self, piece_node: NodePath, color):
        cm = CardMaker("border")
        cm.setFrame(-0.48, 0.48, -0.48, 0.48)

        border = piece_node.attachNewNode(cm.generate())
        border.setPos(0, -0.01, 0)
        border.setColor(*color)

    def create_ui(self):
        self.turn_text = OnscreenText(
            text="RED'S TURN",
            pos=(-0.9, 0.9),
            scale=0.07,
            fg=(1, 0, 0, 1),
            align=TextNode.ALeft,
        )

        self.status_text = OnscreenText(
            text="", pos=(-0.9, -0.9), scale=0.05, fg=(0, 0, 0, 1), align=TextNode.ALeft
        )

        self.quit_button = DirectButton(
            text="QUIT",
            scale=0.07,
            pos=(0.9, 0, 0.9),
            frameColor=(0.8, 0.2, 0.2, 1),
            command=self.quit_game,
        )

        self.menu_button = DirectButton(
            text="MENU",
            scale=0.07,
            pos=(0.7, 0, 0.9),
            frameColor=(0.3, 0.3, 0.8, 1),
            command=self.return_to_menu,
        )

    def setup_mouse_picking(self):
        self.app.accept("mouse1", self.on_mouse_down)
        self.app.accept("mouse1-up", self.on_mouse_up)

    def on_mouse_down(self):
        if self.game_over or self.game.get_turn() == Color.BLUE:
            return

        if not self.app.mouseWatcherNode.hasMouse():
            return

        mouse_pos = self.app.mouseWatcherNode.getMouse()

        self.app.pickerRay.setFromLens(
            self.app.camNode, mouse_pos.getX(), mouse_pos.getY()
        )
        self.app.cTrav.traverse(self.app.render)

        if self.app.pq.getNumEntries() > 0:
            self.app.pq.sortEntries()
            picked_obj = self.app.pq.getEntry(0).getIntoNodePath()

            for piece, node in self.piece_nodes.items():
                if picked_obj.isAncestorOf(node) or node.isAncestorOf(picked_obj):
                    current_state = self.game.get_state()
                    for game_piece in current_state.get_pieces():
                        if (
                            game_piece == piece
                            and game_piece.color == self.game.get_turn()
                        ):
                            self.selected_piece = game_piece
                            self.dragging = True
                            self.drag_piece_node = node
                            return

    def on_mouse_up(self):
        """Handle mouse button up event"""
        if not self.dragging or not self.selected_piece:
            return

        self.dragging = False

        if not self.app.mouseWatcherNode.hasMouse():
            self.cancel_drag()
            return

        mouse_pos = self.app.mouseWatcherNode.getMouse()
        self.app.pickerRay.setFromLens(
            self.app.camNode, mouse_pos.getX(), mouse_pos.getY()
        )
        self.app.cTrav.traverse(self.app.render)

        if self.app.pq.getNumEntries() > 0:
            self.app.pq.sortEntries()
            picked_obj = self.app.pq.getEntry(0).getIntoNodePath()

            for pos, node in self.tile_nodes.items():
                if picked_obj.isAncestorOf(node) or node.isAncestorOf(picked_obj):
                    self.game.move(self.selected_piece, pos)
                    break

        self.update_board_state()
        self.selected_piece = None
        self.drag_piece_node = None

    def cancel_drag(self):
        if self.selected_piece:
            node = self.piece_nodes.get(self.selected_piece)
            if node:
                node.setPos(
                    self.selected_piece.position.x, 0.1, self.selected_piece.position.y
                )

        self.selected_piece = None
        self.drag_piece_node = None
        self.dragging = False

    def update_board_state(self):
        state = self.game.get_state()

        for piece in state.get_pieces():
            node = self.piece_nodes.get(piece)
            if node:
                node.setPos(piece.position.x, 0.1, piece.position.y)

        for piece_id in list(self.piece_nodes.keys()):
            found = False
            for piece in state.get_pieces():
                if piece == piece_id:
                    found = True
                    break

            if not found:
                self.piece_nodes[piece_id].removeNode()
                del self.piece_nodes[piece_id]

        turn_color = (1, 0, 0, 1) if self.game.get_turn() == Color.RED else (0, 0, 1, 1)
        turn_text = f"{self.game.get_turn().to_string().upper()}'S TURN"
        self.turn_text.setText(turn_text)
        self.turn_text.setFg(turn_color)

    @functools.lru_cache(maxsize=None)
    def is_river(self, pos: Position) -> bool:
        state = self.game.get_state()
        map_obj = state.get_map()
        location = map_obj[pos.y, pos.x]
        return location and location.is_river

    @functools.lru_cache(maxsize=None)
    def is_cave(self, pos: Position) -> bool:
        state = self.game.get_state()
        map_obj = state.get_map()
        location = map_obj[pos.y, pos.x]
        return location and location.cave_color is not None

    @functools.lru_cache(maxsize=None)
    def is_trap(self, pos: Position) -> bool:
        state = self.game.get_state()
        map_obj = state.get_map()
        location = map_obj[pos.y, pos.x]
        return location and location.trap_color is not None

    def quit_game(self):
        sys.exit()

    def return_to_menu(self):
        self.cleanup()
        from ui.menu_scene import MenuScene

        new_scene = MenuScene(self.app)
        new_scene.setup()
        return new_scene

    def step(self, task):
        winner = self.game.is_game_over()
        if winner is not None and not self.game_over:
            self.status_message = f"{winner.to_string()} won! Game over."
            self.status_text.setText(self.status_message)
            self.game_over = True

        if not self.game_over and self.game.get_turn() == Color.BLUE:
            self.ai.play_with_ai(self.game)
            self.update_board_state()

        if (
            self.dragging
            and self.drag_piece_node
            and self.app.mouseWatcherNode.hasMouse()
        ):
            mouse_pos = self.app.mouseWatcherNode.getMouse()

            near_point = Point3()
            far_point = Point3()
            self.app.camLens.extrude(mouse_pos, near_point, far_point)

            t = -near_point.y / (far_point.y - near_point.y)
            x = near_point.x + t * (far_point.x - near_point.x)
            z = near_point.z + t * (far_point.z - near_point.z)

            x = max(0, min(BOARD_COLS - 1, x))
            z = max(0, min(BOARD_ROWS - 1, z))

            self.drag_piece_node.setPos(x, 0.2, z)

        return Task.cont

    def cleanup(self):
        self.board_root.removeNode()

        self.turn_text.destroy()
        self.status_text.destroy()
        self.quit_button.destroy()
        self.menu_button.destroy()

        self.app.ignore("mouse1")
        self.app.ignore("mouse1-up")

        self.app.taskMgr.remove("GameStepTask")
