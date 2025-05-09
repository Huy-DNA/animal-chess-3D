from typing import List, Optional, Union
from core.map import Cell, Position
from core.piece import Color, Piece, PieceType
from core.state import State


class Game:
    __state: State

    def __init__(self):
        self.__state = State()
        self.level_bonus: dict[Piece, int] = {
            p: 0 for p in self.__state.get_all_pieces()
        }
        # mỗi bên chỉ được nâng tối đa 3 lần
        self.upgrades_by_color: dict[Color, int] = {
            Color.RED: 0,
            Color.BLUE: 0,
        }

    def get_possible_moves(self, piece: Piece) -> List[Cell]:
        pos = self.__state.get_piece_position(piece)
        if pos is None:
            return []
        adj_cells = (
            self.__state.get_adjacent_cells(pos)
            if piece.type not in [PieceType.TIGER, PieceType.LION]
            else self.__state.get_adjacent_non_river_cells(pos)
        )

        standable_cells = []

        for cell in adj_cells:
            adj_loc = cell.location

            if adj_loc.is_river:
                if piece.type == PieceType.MOUSE:
                    standable_cells.append(cell)
            elif adj_loc.cave_color != piece.color:
                standable_cells.append(cell)

        not_blocked_by_other_pieces_cells = []
        for cell in standable_cells:
            adj_loc = cell.location
            adj_pos = cell.position
            adj_piece = self.__state.get_piece_at_position(adj_pos)

            if adj_piece is None:
                not_blocked_by_other_pieces_cells.append(cell)
                continue
            elif adj_piece.color == piece.color:
                continue
            elif cell.location.trap_color == piece.color:
                not_blocked_by_other_pieces_cells.append(cell)
                continue
            elif piece.type == PieceType.MOUSE and adj_piece.type == PieceType.ELEPHANT:
                not_blocked_by_other_pieces_cells.append(cell)
                continue
            elif piece.type == PieceType.ELEPHANT and adj_piece.type == PieceType.MOUSE:
                continue
            # elif piece.get_default_level() >= adj_piece.get_default_level():
            #     not_blocked_by_other_pieces_cells.append(cell)
            #     continue
            elif self.get_current_level(piece) >= self.get_current_level(adj_piece):
                not_blocked_by_other_pieces_cells.append(cell)

        return not_blocked_by_other_pieces_cells

    def move(self, piece: Piece, position: Position) -> Union[bool, Optional[Piece]]:
        if self.is_game_over():
            return False

        possible_pos = list(map(lambda x: x.position, self.get_possible_moves(piece)))
        if position not in possible_pos:
            return False

        replaced_piece = self.__state.get_piece_at_position(position)
        # if replaced_piece is not None:
        #     self.__state.kill_piece(replaced_piece)
        if replaced_piece is not None:
            attacker = piece
            defender = replaced_piece

            attacker_level = self.get_current_level(attacker)
            defender_level = self.get_current_level(defender)

            self.__state.kill_piece(defender)

            # ✅ Nếu ăn hợp lệ và chưa nâng quá 3 lần → tăng cấp
            if attacker_level >= defender_level and self.upgrades_by_color[piece.color] < 3:
                self.level_bonus[piece] += 1
                self.upgrades_by_color[piece.color] += 1
                print(f"[UPGRADE] {piece.type.name} của {piece.color.name} lên cấp {self.get_current_level(piece)}")
        
        self.__state.set_piece_position(piece, position)
        self.__state.next_turn()
        return replaced_piece or True

    def is_game_over(self) -> Optional[Color]:
        for piece in self.__state.get_all_pieces():
            pos = self.__state.get_piece_position(piece)
            if pos is None:
                continue
            loc = self.__state.get_location_definitely(pos)
            if loc.cave_color is None:
                continue
            return loc.cave_color
        return None

    def get_state(self) -> State:
        return self.__state

    def get_turn(self) -> Color:
        return self.__state.get_turn()
    
    def get_current_level(self, piece: Piece) -> int:
        # default level + bonus
        return piece.get_default_level().value + self.level_bonus.get(piece, 0)

