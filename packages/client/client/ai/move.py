from core.map import Position
from core.piece import Piece


class Move:
    def __init__(self, piece: Piece, to_pos: Position):
        self.piece = piece
        self.to_pos = to_pos
    
    def __str__(self):
        return f"{self.piece.color.name} {self.piece.type.name} -> {self.to_pos}"
