from typing import Dict, List, Optional
import sys
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

from ui.game_scene import GameScene
from core.map import Position
from core.piece import Color, PieceType, Piece
from core.game import Game
from client.controller.network import ServerConnector
from ui.constants import (
    ASSETS_PATH,
    BOARD_COLS,
    BOARD_ROWS,
)


class OnlinePvPMatchScene(GameScene):
    def __init__(
        self,
        base: ShowBase,
        connector: ServerConnector,
        match_id: str,
        opponent_addr: str,
        color: Color,
    ):
        super().__init__(base)
        
        self.app = base
        self.game = Game()
        self.connector = connector
        self.match_id = match_id
        self.opponent_addr = opponent_addr
        self.player_color = color
        
        self.selected_piece = None
        self.status_message = "Waiting for opponent..."
        self.game_over = False
        self.winner = None
        
        self.piece_nodes = {}
        self.tile_nodes = {}
        self.next_scene = None
        
        # Set up callback handlers
        self.connector.set_move_made_callback(self.on_move_made)
        self.connector.set_game_over_callback(self.on_game_over)
        self.connector.set_error_callback(self.on_error)
        
        self.textures = {}
        self.dragging = False
        self.drag_piece_node = None

    def setup(self):
        self.app.setBackgroundColor(0.5, 0.8, 1.0)  # Light blue background

        # Set up camera
        self.app.disableMouse()
        self.app.camera.setPos(BOARD_COLS / 2, -10, BOARD_ROWS / 2 + 2)
        self.app.camera.lookAt(BOARD_COLS / 2, 0, BOARD_ROWS / 2)
        
        # Create board root node
        self.board_root = self.app.render.attachNewNode("board_root")
        
        # Load textures for pieces and tiles
        self.load_textures()
        
        # Create the game board
        self.create_board()
        
        # Create UI elements
        self.create_ui()
        
        # Set up mouse picking for interaction
        self.setup_mouse_picking()
        
        # Set up key controls
        self.setup_keyboard()
        
        # Add the game step task
        self.app.taskMgr.add(self.step, "OnlineGameStepTask")

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
        state = self.game.get_state()
        position = state.get_piece_position(piece)
        if not position:
            return

        cm = CardMaker(f"piece_{piece}")
        cm.setFrame(-0.45, 0.45, -0.45, 0.45)

        piece_node = self.board_root.attachNewNode(cm.generate())
        piece_node.setPos(position.x, 0.1, position.y)
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

        self.player_text = OnscreenText(
            text=f"You are {self.player_color.to_string().upper()}",
            pos=(-0.9, 0.8),
            scale=0.05,
            fg=(1, 0, 0, 1) if self.player_color == Color.RED else (0, 0, 1, 1),
            align=TextNode.ALeft,
        )

        self.status_text = OnscreenText(
            text=self.status_message,
            pos=(-0.9, -0.9),
            scale=0.05,
            fg=(0, 0, 0, 1),
            align=TextNode.ALeft,
        )

        self.game_over_text = OnscreenText(
            text="",
            pos=(0, 0),
            scale=0.1,
            fg=(1, 0, 0, 1),
            align=TextNode.ACenter,
            mayChange=True,
        )
        
        self.winner_text = OnscreenText(
            text="",
            pos=(0, -0.15),
            scale=0.08,
            fg=(0, 0, 0, 1),
            align=TextNode.ACenter,
            mayChange=True,
        )
        
        self.return_text = OnscreenText(
            text="Press ESC to return to menu",
            pos=(0, -0.3),
            scale=0.05,
            fg=(0, 0, 0, 1),
            align=TextNode.ACenter,
            mayChange=True,
        )
        self.return_text.hide()

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
        # Set up collision traverser and handler
        self.app.cTrav = CollisionTraverser()
        self.app.pq = CollisionHandlerQueue()
        self.app.pickerRay = CollisionRay()
        self.picker_node = CollisionNode("mouseRay")
        self.picker_node.addSolid(self.app.pickerRay)
        self.picker_np = self.app.camera.attachNewNode(self.picker_node)
        self.app.cTrav.addCollider(self.picker_np, self.app.pq)
        
        # Set up mouse events
        self.app.accept("mouse1", self.on_mouse_down)
        self.app.accept("mouse1-up", self.on_mouse_up)

    def setup_keyboard(self):
        self.app.accept("c", self.concede)
        self.app.accept("escape", self.return_to_menu)

    def concede(self):
        if not self.game_over:
            self.connector.concede()
            self.status_message = "You conceded. Game over."
            self.game_over = True
            self.update_game_over_display()

    @functools.lru_cache(maxsize=None)
    def is_river(self, pos: Position) -> bool:
        state = self.game.get_state()
        map_obj = state.get_map()
        location = map_obj[pos.y, pos.x]
        return location is not None and location.is_river

    @functools.lru_cache(maxsize=None)
    def is_cave(self, pos: Position) -> bool:
        state = self.game.get_state()
        map_obj = state.get_map()
        location = map_obj[pos.y, pos.x]
        return location is not None and location.cave_color is not None

    @functools.lru_cache(maxsize=None)
    def is_trap(self, pos: Position) -> bool:
        state = self.game.get_state()
        map_obj = state.get_map()
        location = map_obj[pos.y, pos.x]
        return location is not None and location.trap_color is not None

    def on_mouse_down(self):
        if self.game_over or self.game.get_turn() != self.player_color:
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
                    for game_piece in current_state.get_all_pieces():
                        if (
                            game_piece == piece
                            and game_piece.color == self.player_color
                        ):
                            self.selected_piece = game_piece
                            self.dragging = True
                            self.drag_piece_node = node
                            return

    def on_mouse_up(self):
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
                    # Try to make the move locally first
                    result = self.game.move(self.selected_piece, pos)
                    if result:  # If move was successful locally
                        # Send move to server
                        self.connector.move(self.selected_piece, pos)
                        self.status_message = "Move sent. Waiting for opponent..."
                        self.status_text.setText(self.status_message)
                    break

        self.update_board_state()
        self.selected_piece = None
        self.drag_piece_node = None

    def cancel_drag(self):
        state = self.game.get_state()
        if self.selected_piece:
            node = self.piece_nodes.get(self.selected_piece)
            position = state.get_piece_position(self.selected_piece)
            if node and position:
                node.setPos(position.x, 0.1, position.y)

        self.selected_piece = None
        self.drag_piece_node = None
        self.dragging = False

    def update_board_state(self):
        state = self.game.get_state()

        for piece in state.get_all_pieces():
            node = self.piece_nodes.get(piece)
            position = state.get_piece_position(piece)
            if node and position:
                node.setPos(position.x, 0.1, position.y)

        for piece_id in list(self.piece_nodes.keys()):
            found = False
            for piece in state.get_all_pieces():
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
        
        # Update status text based on whose turn it is
        if self.game.get_turn() != self.player_color and not self.game_over:
            self.status_message = "Opponent's turn"
        elif not self.game_over:
            self.status_message = "Your turn"
            
        self.status_text.setText(self.status_message)

    def update_game_over_display(self):
        if self.game_over:
            self.game_over_text.setText("GAME OVER")
            self.game_over_text.show()
            
            if self.winner:
                win_message = "You won!" if self.winner != str(self.opponent_addr) else "Opponent won!"
                self.winner_text.setText(win_message)
                self.winner_text.show()
            
            self.return_text.show()

    def on_move_made(self, piece: Piece, position: Position, player: str):
        if player != str(self.opponent_addr):
            pass  # Our own move confirmation
        else:
            self.game.move(piece, position)
            self.status_message = "Your turn"
            self.status_text.setText(self.status_message)
            self.update_board_state()

    def on_game_over(self, winner: str, reason: str):
        self.game_over = True
        self.winner = winner
        if winner == str(self.opponent_addr):
            self.status_message = f"Game over. You lost. Reason: {reason}"
        else:
            self.status_message = f"Game over. You won! Reason: {reason}"
        
        self.status_text.setText(self.status_message)
        self.update_game_over_display()

    def on_error(self, message: str):
        self.status_message = f"Error: {message}"
        self.status_text.setText(self.status_message)

    def quit_game(self):
        self.connector.Disconnect()
        sys.exit()

    def return_to_menu(self):
        from ui.menu_scene import MenuScene
        
        self.cleanup()
        self.connector.Disconnect()
        self.next_scene = MenuScene(self.app)

    def step(self, task):
        self.connector.Pump()
        
        winner = self.game.is_game_over()
        if winner is not None and not self.game_over:
            self.game_over = True
            if winner == self.player_color:
                self.status_message = "You won! Game over."
            else:
                self.status_message = "You lost. Game over."
            self.status_text.setText(self.status_message)
            self.update_game_over_display()

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

        return self.next_scene if self.next_scene else None

    def cleanup(self):
        self.board_root.removeNode()
        
        self.turn_text.destroy()
        self.player_text.destroy()
        self.status_text.destroy() 
        self.game_over_text.destroy()
        self.winner_text.destroy()
        self.return_text.destroy()
        self.quit_button.destroy()
        self.menu_button.destroy()
        
        self.app.ignore("mouse1")
        self.app.ignore("mouse1-up")
        self.app.ignore("c")
        self.app.ignore("escape")
