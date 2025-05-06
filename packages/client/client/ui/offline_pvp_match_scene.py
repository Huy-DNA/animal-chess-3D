# import os
# import functools

# from direct.showbase.ShowBase import ShowBase
# from direct.gui.DirectButton import DirectButton
# from direct.gui.OnscreenText import OnscreenText
# from direct.task import Task
# from panda3d.core import TextNode, TransparencyAttrib, Point3, CardMaker
# from panda3d.core import PNMImage, Texture, NodePath
# from panda3d.core import (
#     CollisionTraverser,
#     CollisionHandlerQueue,
#     CollisionRay,
#     CollisionNode,
# )

# from core.map import Position
# from core.piece import Color, PieceType
# from ui.game_scene import GameScene
# from ui.constants import (
#     BOARD_COLS,
#     BOARD_ROWS,
#     ASSETS_PATH,
# )
# from core.game import Game, Piece


# class OfflinePvPMatchScene(GameScene):
#     def __init__(self, base: ShowBase):
#         super().__init__(base)
#         self.game_over = False
#         self.game = Game()

#         self.selected_piece = None
#         self.piece_nodes = {}
#         self.tile_nodes = {}
#         self.next_scene = None

#         self.status_message = ""

#         self.textures = {}
#         self.dragging = False
#         self.drag_piece_node = None

#         # Initialize collision detection
#         self.app.cTrav = CollisionTraverser()
#         self.app.pq = CollisionHandlerQueue()
#         self.app.pickerRay = CollisionRay()
#         self.picker_node = CollisionNode("mouseRay")
#         self.picker_node.addSolid(self.app.pickerRay)
#         self.picker_np = self.app.camera.attachNewNode(self.picker_node)
#         self.app.cTrav.addCollider(self.picker_np, self.app.pq)

#     def setup(self):
#         self.app.setBackgroundColor(0.5, 0.8, 1.0)

#         self.app.disableMouse()
#         self.app.camera.setPos(BOARD_COLS / 2, -10, BOARD_ROWS / 2 + 2)
#         self.app.camera.lookAt(BOARD_COLS / 2, 0, BOARD_ROWS / 2)

#         self.board_root = self.app.render.attachNewNode("board_root")

#         self.load_textures()

#         self.create_board()

#         self.create_ui()

#         self.setup_mouse_picking()

#         self.app.taskMgr.add(self.step, "GameStepTask")

#     def load_textures(self):
#         name_to_type = {
#             "elephant": PieceType.ELEPHANT,
#             "lion": PieceType.LION,
#             "tiger": PieceType.TIGER,
#             "leopard": PieceType.LEOPARD,
#             "dog": PieceType.DOG,
#             "wolf": PieceType.WOLF,
#             "cat": PieceType.CAT,
#             "mouse": PieceType.MOUSE,
#         }

#         for name in os.listdir(ASSETS_PATH):
#             if name.endswith(".png") and name not in [
#                 "trap-image.png",
#                 "board-image.png",
#                 "forest-bg.png",
#                 "board-bg.png",
#                 "cave-image.png",
#                 "river-image.png",
#             ]:
#                 texture = self.app.loader.loadTexture(os.path.join(ASSETS_PATH, name))
#                 key = name_to_type[name.replace("-image.png", "")]
#                 self.textures[key] = texture

#         self.textures["trap"] = self.app.loader.loadTexture(
#             os.path.join(ASSETS_PATH, "trap-image.png")
#         )
#         self.textures["cave"] = self.app.loader.loadTexture(
#             os.path.join(ASSETS_PATH, "cave-image.png")
#         )
#         self.textures["river"] = (
#             self.app.loader.loadTexture(os.path.join(ASSETS_PATH, "river-image.png"))
#             if os.path.exists(os.path.join(ASSETS_PATH, "river-image.png"))
#             else None
#         )
#         self.textures["normal_tile"] = self.create_color_texture(0.96, 0.87, 0.7)
#         self.textures["river_tile"] = self.create_color_texture(0, 0.59, 1.0)

#     def create_color_texture(self, r, g, b):
#         image = PNMImage(2, 2)
#         image.fill(r, g, b)
#         texture = Texture()
#         texture.load(image)
#         return texture

#     def create_board(self):
#         state = self.game.get_state()
#         game_map = state.get_map()

#         for row in range(BOARD_ROWS):
#             for col in range(BOARD_COLS):
#                 tile_pos = Position(col, row)

#                 cm = CardMaker(f"tile_{col}_{row}")
#                 cm.setFrame(0, 1, 0, 1)
#                 tile_node = self.board_root.attachNewNode(cm.generate())
#                 tile_node.setPos(col, 0, row)
#                 tile_node.setP(-90)

#                 cn = CollisionNode(f"tile_collision_{col}_{row}")
#                 cm.setFrame(0, 1, 0, 1)
#                 cn_np = tile_node.attachNewNode(cn)

#                 self.tile_nodes[tile_pos] = tile_node

#                 if self.is_river(tile_pos):
#                     tile_node.setTexture(self.textures["river_tile"])
#                 else:
#                     tile_node.setTexture(self.textures["normal_tile"])

#                 if self.is_trap(tile_pos):
#                     trap_overlay = self.board_root.attachNewNode(cm.generate())
#                     trap_overlay.setPos(col, 0.01, row)
#                     trap_overlay.setP(-90)
#                     trap_overlay.setTexture(self.textures["trap"])
#                     trap_overlay.setTransparency(TransparencyAttrib.MAlpha)

#                 if self.is_cave(tile_pos):
#                     cave_overlay = self.board_root.attachNewNode(cm.generate())
#                     cave_overlay.setPos(col, 0.01, row)
#                     cave_overlay.setP(-90)
#                     cave_overlay.setTexture(self.textures["cave"])
#                     cave_overlay.setTransparency(TransparencyAttrib.MAlpha)

#         for y in range(game_map.height()):
#             for x in range(game_map.width()):
#                 piece = state.get_piece_at_position(Position(x, y))
#                 if piece:
#                     self.create_piece_node(piece)

#     def create_piece_node(self, piece: Piece):
#         state = self.game.get_state()
#         position = state.get_piece_position(piece)
#         if not position:
#             return
#         cm = CardMaker(f"piece_{piece}")
#         cm.setFrame(-0.45, 0.45, -0.45, 0.45)

#         piece_node = self.board_root.attachNewNode(cm.generate())
#         piece_node.setPos(position.x, 0.1, position.y)
#         piece_node.setP(-90)

#         cn = CollisionNode(f"piece_collision_{piece}")
#         cm.setFrame(-0.45, 0.45, -0.45, 0.45)
#         cn_np = piece_node.attachNewNode(cn)

#         piece_node.setTexture(self.textures[piece.type])
#         piece_node.setTransparency(TransparencyAttrib.MAlpha)

#         border_color = (1, 0, 0, 1) if piece.color == Color.RED else (0, 0, 1, 1)
#         self.create_piece_border(piece_node, border_color)

#         self.piece_nodes[piece] = piece_node

#     def create_piece_border(self, piece_node: NodePath, color):
#         cm = CardMaker("border")
#         cm.setFrame(-0.48, 0.48, -0.48, 0.48)

#         border = piece_node.attachNewNode(cm.generate())
#         border.setPos(0, -0.01, 0)
#         border.setColor(*color)

#     def create_ui(self):
#         self.turn_text = OnscreenText(
#             text="RED'S TURN",
#             pos=(-0.9, 0.9),
#             scale=0.07,
#             fg=(1, 0, 0, 1),
#             align=TextNode.ALeft,
#         )

#         self.status_text = OnscreenText(
#             text="", pos=(-0.9, -0.9), scale=0.05, fg=(0, 0, 0, 1), align=TextNode.ALeft
#         )

#         self.quit_button = DirectButton(
#             text="QUIT",
#             scale=0.07,
#             pos=(0.9, 0, 0.9),
#             frameColor=(0.8, 0.2, 0.2, 1),
#             command=self.quit_game,
#         )

#         self.menu_button = DirectButton(
#             text="MENU",
#             scale=0.07,
#             pos=(0.7, 0, 0.9),
#             frameColor=(0.3, 0.3, 0.8, 1),
#             command=self.return_to_menu,
#         )

#     def setup_mouse_picking(self):
#         self.app.accept("mouse1", self.on_mouse_down)
#         self.app.accept("mouse1-up", self.on_mouse_up)

#     def on_mouse_down(self):
#         if self.game_over:
#             return

#         if not self.app.mouseWatcherNode.hasMouse():
#             return

#         mouse_pos = self.app.mouseWatcherNode.getMouse()

#         self.app.pickerRay.setFromLens(
#             self.app.camNode, mouse_pos.getX(), mouse_pos.getY()
#         )
#         self.app.cTrav.traverse(self.app.render)

#         if self.app.pq.getNumEntries() > 0:
#             self.app.pq.sortEntries()
#             picked_obj = self.app.pq.getEntry(0).getIntoNodePath()

#             for piece, node in self.piece_nodes.items():
#                 if picked_obj.isAncestorOf(node) or node.isAncestorOf(picked_obj):
#                     current_state = self.game.get_state()
#                     for game_piece in current_state.get_all_pieces():
#                         if (
#                             game_piece == piece
#                             and game_piece.color == self.game.get_turn()
#                         ):
#                             self.selected_piece = game_piece
#                             self.dragging = True
#                             self.drag_piece_node = node
#                             return

#     def on_mouse_up(self):
#         if not self.dragging or not self.selected_piece:
#             return

#         self.dragging = False

#         if not self.app.mouseWatcherNode.hasMouse():
#             self.cancel_drag()
#             return

#         mouse_pos = self.app.mouseWatcherNode.getMouse()
#         self.app.pickerRay.setFromLens(
#             self.app.camNode, mouse_pos.getX(), mouse_pos.getY()
#         )
#         self.app.cTrav.traverse(self.app.render)

#         if self.app.pq.getNumEntries() > 0:
#             self.app.pq.sortEntries()
#             picked_obj = self.app.pq.getEntry(0).getIntoNodePath()

#             for pos, node in self.tile_nodes.items():
#                 if picked_obj.isAncestorOf(node) or node.isAncestorOf(picked_obj):
#                     self.game.move(self.selected_piece, pos)
#                     break

#         self.update_board_state()
#         self.selected_piece = None
#         self.drag_piece_node = None

#     def cancel_drag(self):
#         state = self.game.get_state()
#         if self.selected_piece:
#             node = self.piece_nodes.get(self.selected_piece)
#             position = state.get_piece_position(self.selected_piece)
#             if node and position:
#                 node.setPos(position.x, 0.1, position.y)

#         self.selected_piece = None
#         self.drag_piece_node = None
#         self.dragging = False

#     def update_board_state(self):
#         state = self.game.get_state()

#         for piece in state.get_all_pieces():
#             node = self.piece_nodes.get(piece)
#             position = state.get_piece_position(piece)
#             if node and position:
#                 node.setPos(position.x, 0.1, position.y)

#         for piece_id in list(self.piece_nodes.keys()):
#             found = False
#             for piece in state.get_all_pieces():
#                 if piece == piece_id:
#                     found = True
#                     break

#             if not found:
#                 self.piece_nodes[piece_id].removeNode()
#                 del self.piece_nodes[piece_id]

#         turn_color = (1, 0, 0, 1) if self.game.get_turn() == Color.RED else (0, 0, 1, 1)
#         turn_text = f"{self.game.get_turn().to_string().upper()}'S TURN"
#         self.turn_text.setText(turn_text)
#         self.turn_text.setFg(turn_color)

#     @functools.lru_cache(maxsize=None)
#     def is_river(self, pos: Position) -> bool:
#         state = self.game.get_state()
#         map_obj = state.get_map()
#         location = map_obj[pos.y, pos.x]
#         return location is not None and location.is_river

#     @functools.lru_cache(maxsize=None)
#     def is_cave(self, pos: Position) -> bool:
#         state = self.game.get_state()
#         map_obj = state.get_map()
#         location = map_obj[pos.y, pos.x]
#         return location is not None and location.cave_color is not None

#     @functools.lru_cache(maxsize=None)
#     def is_trap(self, pos: Position) -> bool:
#         state = self.game.get_state()
#         map_obj = state.get_map()
#         location = map_obj[pos.y, pos.x]
#         return location is not None and location.trap_color is not None

#     def quit_game(self):
#         import sys

#         sys.exit()

#     def return_to_menu(self):
#         self.cleanup()
#         from ui.menu_scene import MenuScene

#         self.next_scene = MenuScene(self.app)

#     def step(self, task):
#         winner = self.game.is_game_over()
#         if winner is not None and not self.game_over:
#             self.status_message = f"{winner.to_string()} won! Game over."
#             self.status_text.setText(self.status_message)
#             self.game_over = True

#         if (
#             self.dragging
#             and self.drag_piece_node
#             and self.app.mouseWatcherNode.hasMouse()
#         ):
#             mouse_pos = self.app.mouseWatcherNode.getMouse()

#             near_point = Point3()
#             far_point = Point3()
#             self.app.camLens.extrude(mouse_pos, near_point, far_point)

#             t = -near_point.y / (far_point.y - near_point.y)
#             x = near_point.x + t * (far_point.x - near_point.x)
#             z = near_point.z + t * (far_point.z - near_point.z)

#             x = max(0, min(BOARD_COLS - 1, x))
#             z = max(0, min(BOARD_ROWS - 1, z))

#             self.drag_piece_node.setPos(x, 0.2, z)

#         return self.next_scene

#     def cleanup(self):
#         self.board_root.removeNode()

#         self.turn_text.destroy()
#         self.status_text.destroy()
#         self.quit_button.destroy()
#         self.menu_button.destroy()

#         self.app.ignore("mouse1")
#         self.app.ignore("mouse1-up")

#         self.app.taskMgr.remove("GameStepTask")
from enum import Enum
import sys
from core.map import Position
from core.piece import Color, PieceType
import os
import functools

from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectButton import DirectButton
from direct.gui.OnscreenText import OnscreenText
from direct.gui.OnscreenImage import OnscreenImage
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
    CELL_SIZE
)
from core.game import Game, Piece

from panda3d.core import Filename
from panda3d.core import Vec3, CollisionSphere, BitMask32, CollisionBox
# from panda3d.core import Actor
import struct
import math

class OfflinePvPMatchScene(GameScene):
    def __init__(self, base: ShowBase):
        self.app = base
        super().__init__(base)
        self.game = Game()
        self.game_over = False
        self.selected_piece = None
        self.piece_nodes = {}
        self.tile_nodes = {}
        self.piece_labels = {}
        self.prototypes = {}
        self.camera_angle = 0.0
        self.camera_distance = 20.0
        # Mouse picking setup
        self.picker = CollisionTraverser()
        self.pq = CollisionHandlerQueue()
        self.picker_ray = CollisionRay()
        self.picker_node = CollisionNode("mouseRay")
        self.picker_node.addSolid(self.picker_ray)
        self.picker_node.set_from_collide_mask(BitMask32.bit(1))
        self.picker_node.set_into_collide_mask(BitMask32.allOff())
        self.picker_np = self.app.camera.attachNewNode(self.picker_node)
        self.picker.addCollider(self.picker_np, self.pq)

    def setup(self):
        cx = (BOARD_COLS - 1) * CELL_SIZE / 2
        cy = (BOARD_ROWS - 1) * CELL_SIZE / 2
        # Camera positioning
        self.app.camera.setPos(cx, cy - 15, 20)
        self.app.camera.lookAt(cx, cy, 0)

        # Background card
        # bg_cm = CardMaker('background')
        # bg_cm.setFrame(-50, 50, -50, 50)
        # bg_np = self.app.render.attachNewNode(bg_cm.generate())
        # # Load background texture via loader
        # tex = self.app.loader.loadTexture(os.path.join('assets', 'forest-bg-3d.png'))
        # bg_np.setTexture(tex)
        # bg_np.setPos(cx, cy, -1)
        # bg_np.setScale(1)

        # Initialize scene elements
        self.board_root = self.app.render.attachNewNode("board_root")
        self.load_textures()
        self.create_board()
        self.spawn_pieces()
        self.create_ui()
        self.setup_mouse_picking()
        self.app.taskMgr.add(self.on_mouse_move, 'on_mouse_move')
        self.app.taskMgr.add(self.update_camera, 'update_camera')

    def load_textures(self):
        name_to_type = {
            "elephant": PieceType.ELEPHANT,
            "lion":     PieceType.LION,
            "tiger":    PieceType.TIGER,
            "leopard":  PieceType.LEOPARD,
            "dog":      PieceType.DOG,
            "wolf":     PieceType.WOLF,
            "cat":      PieceType.CAT,
            "mouse":    PieceType.MOUSE,
        }
        
        self.prototypes = {}
        
        for name, piece_type in name_to_type.items():
            raw_path = os.path.join(ASSETS_PATH, f"{name}.egg")
            
            if not os.path.exists(raw_path):
                print(f"[WARN] Không tìm thấy file prototype: {raw_path}")
                continue

            model_path = Filename.fromOsSpecific(raw_path).getFullpath()
            try:
                model = self.app.loader.loadModel(model_path)
                model.setScale(0.4)
                model.setHpr(180, 0, 0)
                # **KHÔNG** reparent ở đây, chỉ giữ prototype
                self.prototypes[piece_type] = model
                print(f"[OK] Prototype loaded for {piece_type}")
            except Exception as e:
                print(f"[ERROR] Load prototype {name}: {e}")

    def create_board(self):
        # Tạo CardMaker để vẽ các ô
        RIVER_POSITIONS = {
            (1, 3), (2, 3), (4, 3), (5, 3),
            (1, 4), (2, 4), (4, 4), (5, 4),
            (1, 5), (2, 5), (4, 5), (5, 5),
        }
        self.tile_nodes = {}
        card_maker = CardMaker('card')
        card_maker.setFrame(-1, 1, -1, 1)
        
        # Lặp qua các ô bàn cờ
        for row in range(BOARD_ROWS):
            for col in range(BOARD_COLS):
                # card = self.board_root.attachNewNode(card_maker.generate())
                # card.setPos(Vec3(col * cell_size, row * cell_size, 0))  # Xếp theo X–Y, nằm trên Z = 0
                # card.setHpr(0, -90, 0)  # Xoay để mặt card nằm ngang (từ XY xuống XZ)
                # card.setTag("type", "tile")
                card = self.board_root.attachNewNode(card_maker.generate())
                card.setPos(col * CELL_SIZE, row * CELL_SIZE, 0)
                card.setHpr(0, -90, 0)
                card.setTag("type", "tile")
                card.setTag("col", str(col))
                card.setTag("row", str(row))
                pos = Position(col, row)
                self.tile_nodes[pos] = card
                # thêm collider
                # cn = CollisionNode(f"tile_{col}_{row}")
                # cm = CardMaker('cm')
                # cm.setFrame(-1, 1, -1, 1)
                # cn.addSolid(cm.generate().getBounds())
                # cn.setIntoCollideMask(BitMask32.bit(1))
                # tile_coll = card.attachNewNode(cn)
                # # gán tag lên chính node này để dễ tìm
                # tile_coll.setTag("tileCollider", f"{col},{row}")
                if (col, row) in RIVER_POSITIONS:
                    card.setColor(0.2, 0.4, 1.0, 1)  # xanh nước
                elif (col, row) in {(2, 0), (3, 1), (4, 0)}:
                    card.setColor(1, 0.6, 0.6, 1)
                # Bẫrow BLUE
                elif (col, row) in {(2, 8), (3, 7), (4, 8)}:
                    card.setColor(0.6, 0.6, 1, 1)
                elif (col, row) == (3, 0):
                    card.setColor(0.5,0.5,0.5)
                # Hang BLUE
                elif (col, row) == (3, 8):
                    card.setColor(0.5,0.5,0.5)
                elif (row + col) % 2 == 0:
                    texture = self.create_color_texture(0.6, 0.85, 0.95)
                else:
                    texture = self.create_color_texture(0.3, 0.6, 0.8)

                if texture:
                    card.setTexture(texture)

    def create_color_texture(self, r, g, b):        
        texture = Texture()
        texture.setup2dTexture(2, 2, Texture.T_unsigned_byte, Texture.F_rgb8)

        # Tạo dữ liệu pixel 2x2 (4 pixels RGB)
        r_byte = int(r * 255)
        g_byte = int(g * 255)
        b_byte = int(b * 255)

        # Mỗi pixel là 3 bytes (RGB), tạo 4 pixel giống nhau
        pixel_data = struct.pack("BBBBBBBBBBBB", 
                                r_byte, g_byte, b_byte,
                                r_byte, g_byte, b_byte,
                                r_byte, g_byte, b_byte,
                                r_byte, g_byte, b_byte)

        texture.setRamImage(pixel_data)

        return texture
    def spawn_pieces(self):
        colors = {
            PieceType.LION: (1.0, 0.8, 0.0, 1),     # vàng
            PieceType.TIGER: (1.0, 0.5, 0.0, 1),    # cam
            PieceType.ELEPHANT: (0.6, 0.6, 0.6, 1), # xám
            PieceType.MOUSE: (0.8, 0.8, 1.0, 1),    # xanh nhạt
            PieceType.CAT: (1.0, 0.6, 0.8, 1),
            PieceType.DOG: (0.7, 0.5, 0.3, 1),
            PieceType.WOLF: (0.5, 0.5, 0.5, 1),
            PieceType.LEOPARD: (1.0, 1.0, 0.0, 1),
        }
        self.piece_labels.clear()
        self.piece_nodes.clear()
        for piece in self.game.get_state().get_all_pieces():
            proto = self.prototypes[piece.type]
            node = proto.copyTo(self.board_root)
            pos = self.game.get_state().get_piece_position(piece)
            node.setPos(pos.x * 2, pos.y * 2, 1)

            base_color = colors.get(piece.type, (1, 1, 1, 1))
            node.setColor(*base_color)
            if piece.color == Color.RED:
                node.setColorScale(1, 0.6, 0.6, 1)  # đỏ nhạt
            else:
                node.setColorScale(0.6, 0.6, 1, 1)  # xanh nhạt
            self.piece_nodes[piece] = node

             # --- tạo label cho level ---
            tn = TextNode(f"lvl_{piece.type.name}_{piece.color.name}")
            tn.setText(str(self.game.get_current_level(piece)))
            tn.setAlign(TextNode.ACenter)
            tn.setTextColor(1,1,1,1)
            label_np = node.attachNewNode(tn)
            label_np.setScale(1.0)                # chỉnh to nhỏ tuỳ ý
            label_np.setBillboardAxis()           # luôn hướng về camera
            # đặt label nằm ngay trên đầu model:
            # giả sử model cao khoảng 1.0, bạn có thể điều chỉnh offset
            label_np.setPos(0, 0, 1.5)
            self.piece_labels[piece] = label_np

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
        self.app.accept('mouse1', self.on_mouse_down)
        # self.app.accept('mouse1-up', self.on_mouse_up)

    def on_mouse_down(self):
        # 1) Bỏ qua nếu không có chuột
        if not self.app.mouseWatcherNode.hasMouse():
            return

        # 2) Tìm điểm giao mouse → plane Z=0
        mpos = self.app.mouseWatcherNode.getMouse()
        world = self.get_mouse_plane_intersection(mpos)
        if not world:
            return

        # 3) Quy về ô (col,row) trên grid (mỗi ô size=2)
        cell_size = 2
        col = int(round(world.getX() / cell_size))
        row = int(round(world.getY() / cell_size))
        # kiểm tra trong bàn cờ
        if not (0 <= col < BOARD_COLS and 0 <= row < BOARD_ROWS):
            return

        clicked_pos = Position(col, row)
        state = self.game.get_state()

        # A) Nếu chưa chọn piece, click lên ô có piece thì select
        if self.selected_piece is None:
            piece = state.get_piece_at_position(clicked_pos)
            if piece and piece.color == self.game.get_turn():
                self.selected_piece = piece
                # highlight quân
                node = self.piece_nodes[piece]
                node.setColorScale(1, 1, 0, 1)
                # highlight ô đích hợp lệ
                self.valid_destinations = {
                    c.position for c in self.game.get_possible_moves(piece)
                }
                self.highlighted_tiles = []
                for dest in self.valid_destinations:
                    tn = self.tile_nodes.get(dest)
                    if tn:
                        tn.setColorScale(0, 1, 1, 0.5)
                        self.highlighted_tiles.append(tn)
                print(f"[SELECTED] {piece.type.name} tại {clicked_pos}")
            return

        # B) Nếu đã chọn piece, click lên ô sẽ là cố gắng di chuyển
        else:
            if clicked_pos in getattr(self, "valid_destinations", ()):
                # ok = self.game.move(self.selected_piece, clicked_pos)
                # print(f"[MOVE] {self.selected_piece.type.name} → {clicked_pos} : {'OK' if ok else 'INVALID'}")
                # self.update_board_state()
                # ghi nhớ level trước move
                old_lvl = self.game.get_current_level(self.selected_piece)

                ok = self.game.move(self.selected_piece, clicked_pos)
                self.update_board_state()

                # sau move, lấy level mới
                new_lvl = self.game.get_current_level(self.selected_piece)
                if ok and new_lvl > old_lvl:
                    # thông báo lên UI
                    msg = f"{self.selected_piece.type.name} được tăng cấp lên {new_lvl}!"
                    self.status_text.setText(msg)
                    self.show_temporary_message(
                        f"[UPGRADE] {self.selected_piece.type.name} của {self.selected_piece.color.name} lên cấp {new_lvl}",
                        duration=3.0
                    )                    
                else:
                    # xoá thông báo (hoặc hiển thị bình thường)
                    self.status_text.setText("")
            else:
                print("⛔ Ô không hợp lệ")

            # clear highlight
            self.piece_nodes[self.selected_piece].clearColorScale()
            for tn in getattr(self, "highlighted_tiles", []):
                tn.clearColorScale()
            self.selected_piece = None
            self.valid_destinations = set()
            self.highlighted_tiles = []        

    def on_mouse_up(self):
        if not self.selected_piece: return
        if not self.app.mouseWatcherNode.hasMouse(): return
        mpos = self.app.mouseWatcherNode.getMouse()
        pt = self.get_mouse_plane_intersection(mpos)
        col = int(pt.x // CELL_SIZE)
        row = int(pt.y // CELL_SIZE)
        self.game.make_move(self.selected_piece.pos, Position(col, row))
        self.selected_piece = None
        self.update_board_state()

    def on_mouse_move(self, task):
        return Task.cont

    def get_mouse_plane_intersection(self, mpos):
        from panda3d.core import Plane, Point3, Vec3
        near_point = Point3()
        far_point = Point3()
        self.app.camLens.extrude(mpos, near_point, far_point)
        near_point = self.app.render.getRelativePoint(self.app.camera, near_point)
        far_point = self.app.render.getRelativePoint(self.app.camera, far_point)
        plane = Plane(Vec3(0, 0, 1), Point3(0, 0, 0))  # Z = 0 mặt bàn
        intersection = Point3()
        if plane.intersectsLine(intersection, near_point, far_point):
            return intersection
        return None

    def update_board_state(self):
        state = self.game.get_state()
        for piece, node in list(self.piece_nodes.items()):
            pos = state.get_piece_position(piece)
            if pos is None:
                node.removeNode()
                del self.piece_nodes[piece]
                self.piece_labels[piece].removeNode()
                del self.piece_labels[piece]
            else:
                node.setPos(pos.x * 2, pos.y * 2, 1)
                # cập nhật label vị trí (nếu không dùng attach thì cần setPos label tương tự)
                label_np = self.piece_labels[piece]
                # nếu label là child của node, nó đã tự theo node nên chỉ cần đổi text
                label_np.node().setText(str(self.game.get_current_level(piece)))

        # Cập nhật text lượt
        turn_color = (1, 0, 0, 1) if self.game.get_turn() == Color.RED else (0, 0, 1, 1)
        turn_text = f"{self.game.get_turn().to_string().upper()}'S TURN"
        self.turn_text.setText(turn_text)
        self.turn_text.setFg(turn_color)

    def update_camera(self, task):
        if self.app.mouseWatcherNode.hasMouse():
            mouse = self.app.win.getPointer(0)
            x = mouse.getX()
            y = mouse.getY()

            # Nếu bạn muốn thêm điều khiển bằng chuột kéo thì thêm sau
            # Ở đây chỉ dùng các phím mũi tên để xoay camera

        # self.camera_angle += globalClock.getDt() * 10  # tự xoay nhẹ
        center = Point3(6, 6, 0)  # Tâm bàn cờ (tùy vào size)
        angle_rad = math.radians(self.camera_angle)
        x = center.getX() + self.camera_distance * math.sin(angle_rad)
        y = center.getY() - self.camera_distance * math.cos(angle_rad)
        z = 15

        self.app.camera.setPos(x, y, z)
        self.app.camera.lookAt(center)
        return Task.cont

    def is_river(self, pos: Position) -> bool:
        return False

    def is_trap(self, pos: Position) -> bool:
        return False

    def is_cave(self, pos: Position) -> bool:
        return False

    def quit_game(self):
        self.cleanup()
        sys.exit(0)

    def cleanup(self):
        self.app.taskMgr.remove('on_mouse_move')
        self.app.taskMgr.remove('update_camera')
        self.turn_text.destroy()
        self.status_text.destroy()
        self.quit_btn.destroy()
        self.board_root.removeNode()

    def step(self, task):
        return super().step(task)
    
    def return_to_menu(self):
        self.cleanup()
        from ui.menu_scene import MenuScene

        self.next_scene = MenuScene(self.app)
