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
        self.piece_labels: dict[Piece, NodePath] = {}

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
        # 1) Tạo OnscreenImage full‑screen
        # 1) build path
        # 1) Load PNMImage từ file
        bg_file = Filename.fromOsSpecific(os.path.join(ASSETS_PATH, "forest-bg-3d.png"))
        img = PNMImage()
        if not img.read(bg_file):
            print(f"[ERROR] Không load được ảnh nền: {bg_file}")
            return
        bg_tex = Texture()
        bg_tex.load(img)

        self.board_root = self.app.render.attachNewNode("board_root")

        
        cm = CardMaker("bg_card")
    # Frame này là toạ độ local của card: (-1..1) trên cả hai trục
        cm.setFrame(-1, 1, -1, 1)
        bg_np = self.board_root.attachNewNode(cm.generate())

        # 2b) Đổi thành kích thước phù hợp world‑space:
        # Ví dụ: bàn cờ rộng BOARD_COLS*CELL_SIZE, dài BOARD_ROWS*CELL_SIZE
        width  = BOARD_COLS * CELL_SIZE
        height = BOARD_ROWS * CELL_SIZE
        bg_np.setScale(width/2, 1, height/2)

        # 2c) Đặt tấm phẳng "đằng sau" bàn cờ:
        #    - Tọa độ X,Y nằm cùng center bàn
        #    - Z (height) = một chút dương để tránh z-fighting
        center_x = (BOARD_COLS - 1) * CELL_SIZE / 2
        center_y = (BOARD_ROWS - 1) * CELL_SIZE / 2
        bg_np.setPos(center_x, center_y + 1, height/2)   # đặt Y sau bàn
        #  Xoay để nó hướng vào camera (CardMaker sinh ra trên mặt XZ, quay 90° về phía Y)
        bg_np.setHpr(0, 90, 0)

        # 2d) Gán texture và bin
        bg_np.setTexture(bg_tex)
        bg_np.setTransparency(TransparencyAttrib.MAlpha)
        # Đặt vào bin "background" của camera 3D, depth‑write off
        bg_np.setBin("background", 0)
        bg_np.setDepthWrite(False)
        bg_np.setDepthTest(False)

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
        self.clear_status_task = None        

    def show_temporary_message(self, msg: str, duration: float = 3.0):
        # 1) cập nhật text ngay
        self.status_text.setText(msg)
        # 2) hủy task clear cũ (nếu vẫn đang chờ)
        if self.clear_status_task is not None:
            self.app.taskMgr.remove(self.clear_status_task)
        # 3) đăng ký task mới clear sau `duration` giây
        def _clear(task):
            self.status_text.setText("") 
            return Task.done
        # lưu tên task để có thể hủy nếu show lại nhanh
        self.clear_status_task = f"clear_status_{id(self)}"
        self.app.taskMgr.doMethodLater(duration, _clear, self.clear_status_task)

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
    def create_piece_node(self, piece: Piece):        
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
