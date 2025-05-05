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
    CELL_SIZE
)
from core.game import Game, Piece

from panda3d.core import Filename
from panda3d.core import Vec3, CollisionSphere, BitMask32, CollisionBox
# from panda3d.core import Actor
import struct
import math


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
        self.next_scene = None

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
        self.tag_to_piece = {}

        # self.app.cTrav = CollisionTraverser()
        # self.app.pq = CollisionHandlerQueue()
        # self.app.pickerRay = CollisionRay()
        # self.picker_node = CollisionNode("mouseRay")
        # self.picker_node.addSolid(self.app.pickerRay)
        # self.picker_np = self.app.camera.attachNewNode(self.picker_node)
        # self.app.cTrav.addCollider(self.picker_np, self.app.pq)
        
        self.camera_angle = 0
        self.camera_distance = 25  # khoảng cách camera với bàn cờ
        self.selected_model = None

    def setup(self):        
        self.app.setBackgroundColor(0.5, 0.8, 1.0)

        self.app.disableMouse()

        center_x = (BOARD_COLS - 1) * CELL_SIZE / 2
        center_y = (BOARD_ROWS - 1) * CELL_SIZE / 2

        self.app.camera.setPos(center_x, center_y - 20, 20)  # Ra xa theo trục Y, cao lên trục Z
        self.app.camera.lookAt(center_x, center_y, 0)        # Nhìn vào tâm bàn cờ
        # self.app.camera.setPos(BOARD_COLS / 2, -10, BOARD_ROWS / 2 + 2)
        # self.app.camera.lookAt(BOARD_COLS / 2, 0, BOARD_ROWS / 2)

        self.board_root = self.app.render.attachNewNode("board_root")

        self.load_textures()

        self.create_board()

        self.spawn_pieces()

        self.create_ui()

        self.setup_mouse_picking()

        # self.app.taskMgr.add(self.step, "GameStepTask")
        # Ray từ camera -> chuột
        self.dragging = False
        self.dragging_piece = None
        self.offset_x = 0
        self.offset_y = 0
        self.picker    = CollisionTraverser()
        self.pq        = CollisionHandlerQueue()
        self.picker_ray= CollisionRay()
        self.picker_node = CollisionNode("mouseRay")
        self.picker_node.addSolid(self.picker_ray)
        self.picker_node.set_from_collide_mask(BitMask32.bit(1))
        self.picker_node.set_into_collide_mask(BitMask32.allOff())
        self.picker_np = self.app.camera.attach_new_node(self.picker_node)
        self.picker.addCollider(self.picker_np, self.pq)
        self.app.accept("mouse1", self.on_mouse_down)
        # self.app.accept("mouse1-up", self.on_mouse_up)
        self.app.taskMgr.add(self.on_mouse_move, "MouseMoveTask")

        # self.dragging_model = None
        self.selected_model = None        

        self.app.taskMgr.add(self.update_camera, "CameraUpdateTask")
        # self.app.taskMgr.add(self.drag_task, "dragTask")


        # box = self.app.loader.loadModel("models/box")
        # box.reparentTo(self.app.render)
        # box.setPos(BOARD_COLS / 2, 0, BOARD_ROWS / 2)

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
    
    def spawn_pieces(self):
        # # Tạo piece_node cho mỗi Piece trong state ban đầu
        # self.piece_nodes.clear()
        # self.tag_to_piece.clear()
        # # state = self.game.get_state()
        # # for piece in state.get_all_pieces():
        # #     self.create_piece_node(piece)
        # for i, piece in enumerate(self.game.get_state().get_all_pieces()):
        #     piece_np = self.create_piece_node(piece)
        #     # đánh tag trực tiếp lên NodePath mẹ
        #     piece_np.setTag("piece_id", str(i))
        #     self.tag_to_piece[str(i)] = piece
        #     self.piece_nodes[piece] = piece_np
        # self.piece_nodes.clear()
        # self.tag_to_piece.clear()

        # for i, piece in enumerate(self.game.get_state().get_all_pieces()):
        #     proto = self.prototypes.get(piece.type)
        #     if proto is None:
        #         continue
        #     piece_np = proto.copyTo(self.board_root)
        #     piece_np.setName(f"piece_{i}")
        #     piece_np.setTag("piece_id", str(i))
        #     self.tag_to_piece[str(i)] = piece

        #     # Đặt đúng vị trí trên bàn
        #     pos = self.game.get_state().get_piece_position(piece)
        #     piece_np.setPos(pos.x * 2, pos.y * 2, 1)

        #     # *** TẠO CollisionBox ngay từ tight bounds ***
        #     minb, maxb = piece_np.getTightBounds()
        #     box = CollisionBox(minb, maxb)
        #     cn = CollisionNode("modelCollider")
        #     cn.addSolid(box)
        #     cn.setIntoCollideMask(BitMask32.bit(1))
        #     piece_np.attachNewNode(cn)

        #     self.piece_nodes[piece] = piece_np
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
                
    def load_textures(self):
        # name_to_type = {
        #     "elephant": PieceType.ELEPHANT,
        #     "lion": PieceType.LION,
        #     "tiger": PieceType.TIGER,
        #     "leopard": PieceType.LEOPARD,
        #     "dog": PieceType.DOG,
        #     "wolf": PieceType.WOLF,
        #     "cat": PieceType.CAT,
        #     "mouse": PieceType.MOUSE,
        # }

        # for name in os.listdir(ASSETS_PATH):
        #     if name.endswith(".png") and name not in [
        #         "trap-image.png",
        #         "board-image.png",
        #         "forest-bg.png",
        #         "board-bg.png",
        #         "cave-image.png",
        #         "river-image.png",
        #     ]:
        #         texture = self.app.loader.loadTexture(os.path.join(ASSETS_PATH, name))
        #         key = name_to_type[name.replace("-image.png", "")]
        #         self.textures[key] = texture

        # self.textures["trap"] = self.app.loader.loadTexture(
        #     os.path.join(ASSETS_PATH, "trap-image.png")
        # )
        # self.textures["cave"] = self.app.loader.loadTexture(
        #     os.path.join(ASSETS_PATH, "cave-image.png")
        # )
        # self.textures["river"] = (
        #     self.app.loader.loadTexture(os.path.join(ASSETS_PATH, "river-image.png"))
        #     if os.path.exists(os.path.join(ASSETS_PATH, "river-image.png"))
        #     else None
        # )
        # self.textures["normal_tile"] = self.create_color_texture(0.96, 0.87, 0.7)
        # self.textures["river_tile"] = self.create_color_texture(0, 0.59, 1.0)
        # name_to_type = {
        #     "elephant": PieceType.ELEPHANT,
        #     "lion": PieceType.LION,
        #     "tiger": PieceType.TIGER,
        #     "leopard": PieceType.LEOPARD,
        #     "dog": PieceType.DOG,
        #     "wolf": PieceType.WOLF,
        #     "cat": PieceType.CAT,
        #     "mouse": PieceType.MOUSE,
        # }
        

        # # Cập nhật danh sách vị trí con thú
        # # Bạn có thể thay thế các tọa độ này bằng các tọa độ phù hợp với bàn cờ cờ thú
        # piece_positions = {
        #     'elephant': (0, 0),  # Hàng 1, Cột 1
        #     'lion': (1, 0),      # Hàng 1, Cột 2
        #     'tiger': (2, 0),     # Hàng 1, Cột 3
        #     'leopard': (3, 0),   # Hàng 1, Cột 4
        #     'dog': (4, 0),       # Hàng 2, Cột 1
        #     'wolf': (5, 0),      # Hàng 2, Cột 2
        #     'cat': (6, 0),       # Hàng 2, Cột 3
        #     'mouse': (7, 0),     # Hàng 3, Cột 1
        # }
        # self.models = {}
        # for name, piece_type in name_to_type.items():
        #     model_filename = f"{name}.egg"
        #     raw_path = os.path.join(ASSETS_PATH, model_filename)
            
        #     # Chuyển path đúng cho loadModel (có thể chứa dấu cách, unicode, ...)
        #     model_path = Filename.fromOsSpecific(raw_path).getFullpath()
            
        #     if os.path.exists(raw_path):  # dùng đường dẫn hệ thống để kiểm tra tồn tại
        #         try:
        #             model = self.app.loader.loadModel(model_path)
        #             model.setScale(0.4)
        #             model.setHpr(180, 0, 0)  # Xoay nếu cần
        #             position = piece_positions[name]  # Lấy vị trí từ dictionary
        #             x, y = position
        #             model.setPos(x * 2, y * 2, 1)  # Điều chỉnh vị trí theo hệ tọa độ bàn cờ
        #             # model.reparentTo(self.app.render)
        #             # model.setTag("modelCollider", "1")
        #             # # Gắn collider để bắt click
        #             # bounds = model.getTightBounds()
        #             # center = (bounds[0] + bounds[1]) / 2
        #             # radius = (bounds[1] - bounds[0]).length() / 2

        #             # # col_sphere = CollisionSphere(center, radius)
        #             # col_sphere = CollisionSphere(0, 0, 1, 1.2)
        #             # col_node = CollisionNode('modelCollider')
        #             # col_node.addSolid(col_sphere)
        #             # col_node.set_into_collide_mask(BitMask32.bit(1))

        #             # model.attach_new_node(col_node)
                    
        #             # self.models[piece_type] = model
        #             piece_node = self.app.render.attachNewNode(f"piece_{name}")
        #             model.reparentTo(piece_node)  # Gắn model vào node mẹ để dễ kéo
        #             model.setPos(0, 0, 0)
        #             model.setScale(0.4)
        #             model.setHpr(180, 0, 0)

        #             # Collider nằm trên piece_node, KHÔNG phải model!
        #             col_sphere = CollisionSphere(0, 0, 1, 1.2)
        #             col_node = CollisionNode('modelCollider')
        #             col_node.addSolid(col_sphere)
        #             col_node.set_into_collide_mask(BitMask32.bit(1))

        #             piece_node.attachNewNode(col_node)
        #             piece_node.setTag("modelCollider", "1")

        #             piece_node.setPos(x * 2, y * 2, 1)
        #             self.models[piece_type] = piece_node  # lưu cả node để dễ điều khiển
        #             print(f"[OK] Loaded model: {model_filename}")
        #         except Exception as e:
        #             print(f"[ERROR] Không load được model {name}: {e}")
        #     else:
        #         print(f"[WARN] Không tìm thấy file: {raw_path}")
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
    # def create_color_texture(self, r, g, b):
    #     image = PNMImage(2, 2)
    #     image.fill(r, g, b)
    #     texture = Texture()
    #     texture.load(image)
    #     return texture

    def on_mouse_click(self):
        # if not self.app.mouseWatcherNode.hasMouse():
        #     return
        # mpos = self.app.mouseWatcherNode.getMouse()
        # self.picker_ray.setFromLens(self.app.camNode, mpos.getX(), mpos.getY())
        # self.picker.traverse(self.app.render)
        # if self.pq.getNumEntries() > 0:
        #     self.pq.sortEntries()
        #     picked = self.pq.getEntry(0).getIntoNodePath()
        #     model = picked.findNetTag('modelCollider').getParent()
        #     self.selected_model = model
        #     self.dragging = True
        if self.mouseWatcherNode.hasMouse():
            mpos = self.mouseWatcherNode.getMouse()
            self.picker_ray.setFromLens(self.camNode, mpos.getX(), mpos.getY())

            self.picker.traverse(self.render)
            if self.pq.getNumEntries() > 0:
                self.pq.sortEntries()
                picked_obj = self.pq.getEntry(0).getIntoNodePath()

                picked_node = picked_obj.findNetTag("modelCollider")
                if not picked_node.isEmpty():
                    piece_node = picked_node.getParent()  # Vì collider nằm trong piece_node
                    print(f"Clicked on piece: {piece_node.getName()}")
                    # Bạn có thể lưu lại node được chọn để kéo/di chuyển:
                    self.selected_piece_node = piece_node

    def on_mouse_release(self):
        self.dragging = False
        self.selected_model = None    
    

    def get_3d_pos_from_mouse(self, mpos):
        # Lấy tia từ chuột xuống mặt bàn Z = 0
        from panda3d.core import Plane, Point3, Vec3
        plane = Plane(Vec3(0, 0, 1), Point3(0, 0, 1))  # Mặt phẳng Z = 1
        near = Point3()
        far = Point3()
        self.app.camLens.extrude(mpos, near, far)
        near = self.app.render.getRelativePoint(self.app.camera, near)
        far = self.app.render.getRelativePoint(self.app.camera, far)
        intersection_point = Point3()
        if plane.intersectsLine(intersection_point, near, far):
            return intersection_point
        return None

    def get_mouse_plane_intersection(self, mouse_pos):
        from panda3d.core import Plane, Point3, Vec3
        near_point = Point3()
        far_point = Point3()
        self.app.camLens.extrude(mouse_pos, near_point, far_point)
        near_point = self.app.render.getRelativePoint(self.app.camera, near_point)
        far_point = self.app.render.getRelativePoint(self.app.camera, far_point)
        plane = Plane(Vec3(0, 0, 1), Point3(0, 0, 0))  # Z = 0 mặt bàn
        intersection = Point3()
        if plane.intersectsLine(intersection, near_point, far_point):
            return intersection
        return None

    def create_board(self):
        # state = self.game.get_state()
        # game_map = state.get_map()

        # for row in range(BOARD_ROWS):
        #     for col in range(BOARD_COLS):
        #         tile_pos = Position(col, row)

        #         cm = CardMaker(f"tile_{col}_{row}")
        #         cm.setFrame(0, 1, 0, 1)
        #         tile_node = self.board_root.attachNewNode(cm.generate())
        #         tile_node.setPos(col, 0, row)
        #         tile_node.setP(-90)

        #         # Add collision solid for mouse picking
        #         cn = CollisionNode(f"tile_collision_{col}_{row}")
        #         cm.setFrame(0, 1, 0, 1)
        #         cn_np = tile_node.attachNewNode(cn)

        #         self.tile_nodes[tile_pos] = tile_node

        #         if self.is_river(tile_pos):
        #             tile_node.setTexture(self.textures["river_tile"])
        #         else:
        #             tile_node.setTexture(self.textures["normal_tile"])

        #         if self.is_trap(tile_pos):
        #             trap_overlay = self.board_root.attachNewNode(cm.generate())
        #             trap_overlay.setPos(col, 0.01, row)
        #             trap_overlay.setP(-90)
        #             trap_overlay.setTexture(self.textures["trap"])
        #             trap_overlay.setTransparency(TransparencyAttrib.MAlpha)

        #         if self.is_cave(tile_pos):
        #             cave_overlay = self.board_root.attachNewNode(cm.generate())
        #             cave_overlay.setPos(col, 0.01, row)
        #             cave_overlay.setP(-90)
        #             cave_overlay.setTexture(self.textures["cave"])
        #             cave_overlay.setTransparency(TransparencyAttrib.MAlpha)

        # for y in range(game_map.height()):
        #     for x in range(game_map.width()):
        #         piece = state.get_piece_at_position(Position(x, y))
        #         if piece:
        #             self.create_piece_node(piece)
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
        # card_maker = CardMaker('color_card')
        # card_maker.setFrame(-1, 1, -1, 1)
        # color_card = card_maker.generate()
        # texture = self.app.loader.loadTexture('color.png')
        # color_card.setColor(r, g, b, 1)  # Đặt màu cho ô
        # return texture
        # Create a CardMaker to make a square
        # Create a CardMaker to make a square
        # Create a CardMaker to make a square
        # Create a CardMaker to make a square
        # Create a CardMaker to make a square
        # card_maker = CardMaker('card')
        # card_maker.setFrame(-1, 1, -1, 1)  # Square from (-1, -1) to (1, 1)

        # # Create the card (square)
        # card = card_maker.generate()

        # # Create the texture
        # texture = Texture()
        # texture.setup2dTexture(2, 2, Texture.T_unsigned_byte, Texture.F_rgb8)

        # # Create the pixel data (2x2 texture)
        # tex_data = bytearray()
        # # Add 4 pixels (2x2) with the RGB values
        # for _ in range(4):
        #     tex_data.extend([int(r * 255), int(g * 255), int(b * 255)])  # RGB values in range [0, 255]

        # # Set the texture data (ensure it is in the correct format)
        # texture.setRamImageAs(bytes(tex_data), Texture.F_rgb8)

        # # Apply the texture to the card (you might want to do this elsewhere in your game logic)
        # card.setTexture(texture)

        # return texture
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
    def create_piece_node(self, piece: Piece):
        # state = self.game.get_state()
        # position = state.get_piece_position(piece)
        # if not position:
        #     return

        # cm = CardMaker(f"piece_{piece}")
        # cm.setFrame(-0.45, 0.45, -0.45, 0.45)

        # piece_node = self.board_root.attachNewNode(cm.generate())
        # piece_node.setPos(position.x, 0.1, position.y)
        # piece_node.setP(-90)

        # # Add collision for piece
        # cn = CollisionNode(f"piece_collision_{piece}")
        # cm.setFrame(-0.45, 0.45, -0.45, 0.45)
        # cn_np = piece_node.attachNewNode(cn)

        # piece_node.setTexture(self.textures[piece.type])
        # piece_node.setTransparency(TransparencyAttrib.MAlpha)

        # border_color = (1, 0, 0, 1) if piece.color == Color.RED else (0, 0, 1, 1)
        # self.create_piece_border(piece_node, border_color)

        # self.piece_nodes[piece] = piece_node

        # model = self.models.get(piece.type)
        # if model:
        #     piece_node = self.board_root.attachNewNode(f"piece_{piece}")
        #     model_instance = model.copyTo(piece_node)
        #     model_instance.setPos(0, 0, 0)  # hoặc căn giữa
        #     model_instance.setScale(0.4)
         # Lấy NodePath gốc đã load trong load_textures (có sẵn collider)
       # 1) Copy model (đã scale sẵn) vào board
        model_np = self.models[piece.type]
        piece_np = model_np.copyTo(self.board_root)
        pos = self.game.get_state().get_piece_position(piece)
        piece_np.setPos(pos.x * 2, pos.y * 2, 1)

        # 3) Xây dựng collider dựa trên tight bounds của piece_np
        from panda3d.core import CollisionNode, CollisionSphere, BitMask32

        # Lấy bounds (Point3) của toàn bộ node con trong piece_np
        minb, maxb = piece_np.getTightBounds()
        # Tâm của bounding box
        center = (minb + maxb) * 0.5
        # Bán kính = ½ độ dài đường chéo của bounding box, nhân thêm 1.2 để “đệm”
        radius = ((maxb - minb).length() * 0.5) * 1.2

        # Tạo CollisionSphere từ tâm và bán kính
        col_sphere = CollisionSphere(center.x, center.y, center.z, radius)
        col_node = CollisionNode('modelCollider')
        col_node.addSolid(col_sphere)
        col_node.setIntoCollideMask(BitMask32.bit(1))

        # Attach collider lên chính piece_np
        piece_np.attachNewNode(col_node)

        # 4) Lưu mapping để later select & move
        self.piece_nodes[piece] = piece_np
        return piece_np

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
        # self.app.accept("mouse1-up", self.on_mouse_up)

    def on_mouse_down(self):
        # if self.game_over or self.game.get_turn() == Color.BLUE:
        #     return

        # if not self.app.mouseWatcherNode.hasMouse():
        #     return

        # mouse_pos = self.app.mouseWatcherNode.getMouse()

        # self.picker_ray.setFromLens(self.app.camNode, mouse_pos.getX(), mouse_pos.getY())
        # self.picker.traverse(self.app.render)

        # if self.pq.getNumEntries() > 0:
        #     self.pq.sortEntries()
        #     picked_obj = self.pq.getEntry(0).getIntoNodePath()
        #     print("[CLICK] Mouse down at:", picked_obj)

        #     for piece, node in self.piece_nodes.items():
        #         if picked_obj.isAncestorOf(node) or node.isAncestorOf(picked_obj):
        #             current_state = self.game.get_state()
        #             for game_piece in current_state.get_all_pieces():
        #                 if (
        #                     game_piece == piece
        #                     and game_piece.color == self.game.get_turn()
        #                 ):
        #                     self.selected_piece = game_piece
        #                     self.dragging = True
        #                     self.drag_piece_node = node
        #                     return
        # else:
        #     print("[DEBUG] Không va chạm nào được phát hiện.")
        # if self.app.mouseWatcherNode.hasMouse():
        #     mpos = self.app.mouseWatcherNode.getMouse()
        #     self.picker_ray.setFromLens(self.app.camNode, mpos.getX(), mpos.getY())
        #     self.picker.traverse(self.app.render)
        #     if self.pq.getNumEntries() > 0:
        #         self.pq.sortEntries()
        #         entry = self.pq.getEntry(0)
        #         picked_node = entry.getIntoNodePath().findNetTag("modelCollider")
        #         if not picked_node.isEmpty():
        #             self.selected_piece = picked_node.getParent()
        #             print(f"Picked: {self.selected_piece}")
        # if not self.app.mouseWatcherNode.hasMouse():
        #     return
        # mpos = self.app.mouseWatcherNode.getMouse()

        # # A) Select piece (nếu chưa có)
        # if self.selected_piece is None:
        #     self.picker_ray.setFromLens(self.app.camNode, mpos.getX(), mpos.getY())
        #     self.picker.traverse(self.app.render)
        #     if self.pq.getNumEntries() == 0:
        #         return
        #     self.pq.sortEntries()
        #     picked = self.pq.getEntry(0).getIntoNodePath()
        #     print(f"[DEBUG] piece_nodes count = {len(self.piece_nodes)}")
        #     for piece, node in self.piece_nodes.items():
        #         if picked.isAncestorOf(node) or node.isAncestorOf(picked):
        #             print(f"[DEBUG] picked IS ancestorOf node {node.getName()}")
        #             if piece.color != self.game.get_turn():
        #                 print(f"[BLOCKED] Không phải lượt của {piece.color}")
        #                 return
        #             self.selected_piece = piece
        #             node.setColorScale(1,1,0,1)  # highlight vàng
        #             print(f"[SELECTED] {piece.type.name} tại {self.game.get_state().get_piece_position(piece)}")
        #             return

        # # B) Move piece (nếu đã select)
        # else:
        #     world_pos = self.get_mouse_plane_intersection(mpos)
        #     if not world_pos:
        #         return
        #     col = int(round(world_pos.getX() / 2))
        #     row = int(round(world_pos.getY() / 2))
        #     if 0 <= col < BOARD_COLS and 0 <= row < BOARD_ROWS:
        #         dest = Position(col, row)
        #         moved = self.game.move(self.selected_piece, dest)
        #         print(f"[MOVE] {self.selected_piece.type.name} -> {dest} : {'OK' if moved else 'INVALID'}")
        #         self.update_board_state()
        #     else:
        #         print("[OUT] Ngoài bàn")
        #     # Xóa highlight và reset chọn
        #     self.piece_nodes[self.selected_piece].clearColorScale()
        #     self.selected_piece = NoneC
         
        # if not self.app.mouseWatcherNode.hasMouse(): return
        # mpos = self.app.mouseWatcherNode.getMouse()
        # print(f"[DEBUG] mouse pos: {mpos}")
        # # A) nếu chưa select piece → thử select
        # if self.selected_piece is None:
        #     self.picker_ray.setFromLens(self.app.camNode, mpos.getX(), mpos.getY())
        #     self.picker.traverse(self.app.render)
        #     if self.pq.getNumEntries() == 0: return
        #     self.pq.sortEntries()
        #     picked = self.pq.getEntry(0).getIntoNodePath()
        #     print(f"[DEBUG] ray hit node: {picked.getName()}")
        #     for piece, node in self.piece_nodes.items():
        #         if picked.isAncestorOf(node) or node.isAncestorOf(picked):
        #             if piece.color != self.game.get_turn():
        #                 print("❌ Không phải lượt của bạn")
        #                 return
        #             self.selected_piece = piece
        #             # highlight piece
        #             node.setColorScale(1,1,0,1)
        #             # highlight ô đích
        #             self.valid_destinations = {
        #                 cell.position for cell in self.game.get_possible_moves(piece)
        #             }
        #             self.highlighted_tiles = []
        #             for dest in self.valid_destinations:
        #                 tn = self.tile_nodes.get(dest)
        #                 if tn:
        #                     tn.setColorScale(0,1,1,0.5)
        #                     self.highlighted_tiles.append(tn)
        #             print(f"[SELECTED] {piece.type.name} tại {self.game.get_state().get_piece_position(piece)}")
        #             return

        # # B) nếu đã select piece → move theo click
        # else:
        #     world_pos = self.get_mouse_plane_intersection(mpos)
        #     if not world_pos: return
        #     col = int(round(world_pos.getX() / 2))
        #     row = int(round(world_pos.getY() / 2))
        #     dest = Position(col, row)

        #     if dest in getattr(self, "valid_destinations", ()):
        #         self.game.move(self.selected_piece, dest)
        #         print(f"[MOVE] {self.selected_piece.type.name} → {dest}")
        #     else:
        #         print("⛔ Ô không hợp lệ")

        #     # cập nhật vị trí model
        #     self.update_board_state()

        #     # xóa highlight piece và tiles
        #     self.piece_nodes[self.selected_piece].clearColorScale()
        #     for tn in getattr(self, "highlighted_tiles", []):
        #         tn.clearColorScale()
        #     self.highlighted_tiles = []
        #     self.valid_destinations = set()
        #     self.selected_piece = None
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
                ok = self.game.move(self.selected_piece, clicked_pos)
                print(f"[MOVE] {self.selected_piece.type.name} → {clicked_pos} : {'OK' if ok else 'INVALID'}")
                self.update_board_state()
            else:
                print("⛔ Ô không hợp lệ")

            # clear highlight
            self.piece_nodes[self.selected_piece].clearColorScale()
            for tn in getattr(self, "highlighted_tiles", []):
                tn.clearColorScale()
            self.selected_piece = None
            self.valid_destinations = set()
            self.highlighted_tiles = []
        # def _attempt_move(self, mpos):
        #     world_pos = self.get_mouse_plane_intersection(mpos)
        #     if not world_pos:
        #         return
        #     col = int(round(world_pos.getX() / 2))
        #     row = int(round(world_pos.getY() / 2))
        #     dest = Position(col, row)

        #     if dest in self.valid_destinations:
        #         ok = self.game.move(self.selected_piece, dest)
        #         print(f"[MOVE] {self.selected_piece.type.name} → {dest} : {'OK' if ok else 'INVALID'}")
        #         self.update_board_state()
        #     else:
        #         print("⛔ Ô không hợp lệ")

        #     # clear highlight
        #     node = self.piece_nodes[self.selected_piece]
        #     node.clearColorScale()
        #     for tn in self.highlighted_tiles:
        #         tn.clearColorScale()
        #     self.highlighted_tiles = []
        #     self.valid_destinations = set()
        #     self.selected_piece = None



    def on_mouse_move(self, task):
        if self.dragging_piece and self.mouseWatcherNode.hasMouse():
            mousePos = self.mouseWatcherNode.getMouse()
            self.pickerRay.setFromLens(self.camNode, mousePos.getX(), mousePos.getY())
            self.picker.traverse(self.render)

            if self.pq.getNumEntries() > 0:
                self.pq.sortEntries()
                hitPos = self.pq.getEntry(0).getSurfacePoint(self.render)
                self.dragging_piece.setZ(0.5)  # nâng quân thú lên một chút
                self.dragging_piece.setX(hitPos.getX())
                self.dragging_piece.setY(hitPos.getY())
        return task.cont
    
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
        # state = self.game.get_state()
        # for piece, node in self.piece_nodes.items():
        #     pos = state.get_piece_position(piece)
        #     node.setPos(pos.x * 2, pos.y * 2, 1)

        # for piece_id in list(self.piece_nodes.keys()):
        #     found = False
        #     for piece in state.get_all_pieces():
        #         if piece == piece_id:
        #             found = True
        #             break

        #     if not found:
        #         self.piece_nodes[piece_id].removeNode()
        #         del self.piece_nodes[piece_id]

        # turn_color = (1, 0, 0, 1) if self.game.get_turn() == Color.RED else (0, 0, 1, 1)
        # turn_text = f"{self.game.get_turn().to_string().upper()}'S TURN"
        # self.turn_text.setText(turn_text)
        # self.turn_text.setFg(turn_color)
        state = self.game.get_state()
        for piece, node in list(self.piece_nodes.items()):
            pos = state.get_piece_position(piece)
            if pos is None:
                node.removeNode()
                del self.piece_nodes[piece]
            else:
                node.setPos(pos.x * 2, pos.y * 2, 1)

        # Cập nhật text lượt
        turn_color = (1, 0, 0, 1) if self.game.get_turn() == Color.RED else (0, 0, 1, 1)
        turn_text = f"{self.game.get_turn().to_string().upper()}'S TURN"
        self.turn_text.setText(turn_text)
        self.turn_text.setFg(turn_color)

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

    def quit_game(self):
        sys.exit()

    def return_to_menu(self):
        self.cleanup()
        from ui.menu_scene import MenuScene

        self.next_scene = MenuScene(self.app)

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

        return self.next_scene

    def cleanup(self):
        self.board_root.removeNode()

        self.turn_text.destroy()
        self.status_text.destroy()
        self.quit_button.destroy()
        self.menu_button.destroy()

        self.app.ignore("mouse1")
        self.app.ignore("mouse1-up")

        self.app.taskMgr.remove("GameStepTask")
